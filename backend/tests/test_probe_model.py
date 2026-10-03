import asyncio
import json

import httpx
import pytest

from app.services.model_client import ModelConfig
from scripts.probe_model import run_probe, synthetic_probe_context


def response_content(action="propose_option"):
    return json.dumps(dict(
        action=action, option_id="SYNTHETIC_Q4_C",
        evidence_quote="three months of essentials", clarification_question=None,
        explanation_content_ids=[], support_reason=None,
    ))


@pytest.mark.parametrize("model_id", [None, "SYNTHETIC-MISSING"])
def test_probe_lists_models_and_requires_exact_configured_id(model_id, capsys):
    calls = []
    def handler(request):
        calls.append(request)
        assert request.method == "GET"
        assert request.url.path == "/v1/models"
        return httpx.Response(200, json={"data": [{"id": "SYNTHETIC-DISCOVERED"}]})
    result = asyncio.run(run_probe(ModelConfig(model_id=model_id), transport=httpx.MockTransport(handler)))
    output = capsys.readouterr().out
    assert result == 2
    assert "SYNTHETIC-DISCOVERED" in output
    assert "MODEL_ID" in output
    assert "No completion sent" in output
    assert "Latency" in output
    assert len(calls) == 1


@pytest.mark.parametrize("content,expected_status", [
    (response_content(), 0), (response_content("save"), 1),
    (response_content().replace("SYNTHETIC_Q4_C", "Q3_C"), 1),
    (response_content().replace("three months of essentials", "invented quote"), 1),
    ("malformed JSON", 1),
])
def test_probe_one_completion_uses_production_semantic_parser(content, expected_status, capsys, caplog):
    calls = []
    def handler(request):
        calls.append(request)
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "SYNTHETIC-DISCOVERED"}]})
        assert request.url.path == "/v1/chat/completions"
        body = json.loads(request.content)
        assert body["model"] == "SYNTHETIC-DISCOVERED"
        return httpx.Response(200, json={"choices": [{
            "finish_reason": "stop", "message": {
                "role": "assistant", "content": content, "reasoning_content": "PRIVATE-HIDDEN-REASONING",
            },
        }]})
    config = ModelConfig.from_env({"MODEL_ID": "SYNTHETIC-DISCOVERED", "MODEL_API_KEY": "PRIVATE-API-KEY"})
    status = asyncio.run(run_probe(config, transport=httpx.MockTransport(handler)))
    output = capsys.readouterr().out
    assert status == expected_status
    assert len(calls) == 2
    assert [r.method for r in calls] == ["GET", "POST"]
    assert "PRIVATE" not in output + caplog.text
    assert "three months of essentials" not in output
    assert "Latency" in output
    assert "parsed structured action" in output
    assert "SUCCESS" in output if expected_status == 0 else "FAILURE" in output


@pytest.mark.parametrize("discovery", [
    {"data": []}, {"data": [{"id": None}]}, {"data": [{"id": 1}]},
    {"data": "not a list"}, [], {"error": "PRIVATE server response"},
])
def test_probe_handles_bad_or_empty_discovery(discovery, capsys):
    status = asyncio.run(run_probe(ModelConfig(model_id="SYNTHETIC-DISCOVERED"),
                                   transport=httpx.MockTransport(lambda _: httpx.Response(200, json=discovery))))
    assert status != 0
    assert "PRIVATE" not in capsys.readouterr().out


def test_probe_offline_prints_safe_failure(capsys):
    def handler(request):
        raise httpx.ConnectError("PRIVATE diagnostic")
    assert asyncio.run(run_probe(ModelConfig(), transport=httpx.MockTransport(handler))) == 1
    output = capsys.readouterr().out
    assert "model_unavailable" in output
    assert "PRIVATE" not in output


def test_probe_has_no_released_catalog_or_approved_test_explanation():
    context = synthetic_probe_context()
    assert context.question.catalog_version == "SYNTHETIC-PROBE-NOT-A-RELEASE"
    assert all(o.option_id.startswith("SYNTHETIC_") for o in context.options)
    assert context.retrieval.snippets == []
