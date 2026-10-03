import json

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.adapters.omlx import OmlxAdapter
from backend.app.errors import IntegrationUnavailable
from backend.app.main import create_app, create_configured_app
from backend.app.schemas import RetrievedContext
from backend.app.settings import Settings
from backend.tests.conftest import Journey, TestCatalogProvider


def completion(content, finish_reason="stop"):
    return {"choices": [{"finish_reason": finish_reason,
                         "message": {"role": "assistant", "content": content}}]}


def adapter(handler):
    return OmlxAdapter(base_url="http://model.test/v1", model="test-model", api_key="test-key",
                       transport=httpx.MockTransport(handler))


def interpret(model):
    catalog = TestCatalogProvider().load()
    return model.interpret(text="Synthetic test answer", question=catalog.questions[0], catalog=catalog,
                           confirmed_answers=[], context=[RetrievedContext(sourceId="source", text="Test context")])


def test_request_uses_server_auth_and_strict_json_interpretation():
    def handle(request):
        assert request.url == "http://model.test/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["model"] == "test-model" and body["stream"] is False
        assert body["response_format"] == {"type": "json_object"}
        assert body["chat_template_kwargs"] == {"enable_thinking": False}
        assert "test-key" not in request.content.decode()
        data = json.loads(body["messages"][1]["content"])
        assert data["user_text"] == "Synthetic test answer"
        assert data["question"]["options"][0]["id"] == "a"
        assert data["context"][0]["sourceId"] == "source"
        return httpx.Response(200, json=completion('{"kind":"proposal","optionId":"a"}'))
    assert interpret(adapter(handle)).optionId == "a"


@pytest.mark.parametrize("content", [
    '{"kind":"clarification"}', '{"kind":"pause"}', '{"kind":"support"}',
])
def test_non_proposal_decisions_are_supported(content):
    result = interpret(adapter(lambda req: httpx.Response(200, json=completion(content))))
    assert result.optionId is None


@pytest.mark.parametrize("payload", [
    completion('{"kind":"proposal","optionId":"invented"}'),
    completion('{"kind":"proposal"}'),
    completion('{"kind":"clarification","optionId":"a"}'),
    completion('{"kind":"proposal","optionId":"a","score":100}'),
    completion('```json\n{"kind":"clarification"}\n```'),
    completion(None), completion('{"kind":"clarification"}', "length"),
    {"choices": []}, {},
])
def test_malformed_or_unsafe_model_output_is_not_accepted(payload):
    with pytest.raises(IntegrationUnavailable):
        interpret(adapter(lambda req: httpx.Response(200, json=payload)))


@pytest.mark.parametrize("status", [401, 404, 429, 500])
def test_upstream_errors_are_generic(status):
    with pytest.raises(IntegrationUnavailable) as exc:
        interpret(adapter(lambda req: httpx.Response(status, text="private upstream details")))
    assert "private" not in str(exc.value) and "test-key" not in str(exc.value)


def test_timeouts_and_oversized_responses_are_unavailable():
    def timed_out(request):
        raise httpx.ReadTimeout("private connection details", request=request)
    for model in [adapter(timed_out), adapter(lambda req: httpx.Response(200, content=b"x" * 65537))]:
        with pytest.raises(IntegrationUnavailable):
            interpret(model)


def test_exact_model_identifier_is_verified():
    def handle(request):
        assert request.url.path == "/v1/models"
        return httpx.Response(200, json={"data": [{"id": "test-model"}]})
    adapter(handle).check_model()
    with pytest.raises(IntegrationUnavailable):
        adapter(lambda req: httpx.Response(200, json={"data": [{"id": "wrong-model"}]})).check_model()


def test_model_assisted_demo_uses_natural_language_and_retains_confirmation(repository):
    model = adapter(lambda req: httpx.Response(200, json=completion(
        '{"kind":"proposal","optionId":"some_fluctuation"}',
    )))
    with TestClient(create_app(repository=repository, model=model, demo_catalog=True)) as client:
        journey = Journey(client)
        started = journey.send("start")
        assert "Model-assisted demo" in started["assistant"]["text"]
        assert "No model" not in started["assistant"]["text"]
        proposed = journey.send("message", message={"role": "user", "text": "Fictionally I can handle ups and downs."})
        assert proposed["type"] == "proposed_answer" and proposed["confirmedAnswers"] == []
        confirmed = journey.send("confirm", questionId="attitude", optionId="some_fluctuation")
        assert len(confirmed["confirmedAnswers"]) == 1


def test_file_settings_environment_override_and_secret_repr(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("OMLX_API_KEY=test-secret\nOMLX_MODEL=file-model\n"
                        "OMLX_BASE_URL=http://model.test/v1/\nVESPER_MODEL_BACKEND=omlx\n", encoding="utf-8")
    settings = Settings.load(env_file, environ={"OMLX_MODEL": "environment-model"})
    assert settings.OMLX_MODEL == "environment-model"
    assert settings.OMLX_BASE_URL == "http://model.test/v1"
    assert "test-secret" not in repr(settings)
    assert settings.OMLX_API_KEY.get_secret_value() == "test-secret"


@pytest.mark.parametrize("base_url", [
    "file:///etc/passwd", "http://secret@example.test/v1", "http://model.test/v1?key=secret",
    "http://model.test/v1#fragment", "http://model.test", "http:///v1",
])
def test_invalid_base_urls_are_rejected(base_url):
    with pytest.raises(ValidationError):
        Settings(OMLX_BASE_URL=base_url)


def test_configuration_selects_omlx_and_rejects_mixed_scripted_mode():
    settings = Settings(OMLX_API_KEY="test", OMLX_MODEL="test-model", VESPER_MODEL_BACKEND="omlx",
                        VESPER_DEMO_CATALOG=True, VESPER_SERVE_FRONTEND=False)
    configured = create_configured_app(settings)
    assert isinstance(configured.state.conversation.model, OmlxAdapter)
    assert configured.state.conversation.catalog.load().demo is True
    settings.VESPER_DEMO = True
    with pytest.raises(ValueError):
        create_configured_app(settings)
    with pytest.raises(ValueError):
        create_configured_app(Settings(VESPER_MODEL_BACKEND="omlx"))
