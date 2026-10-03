import pytest
from fastapi.testclient import TestClient

from backend.app.demo import DemoCatalog, ScriptedDemoAdapter
from backend.app.main import create_app
from backend.tests.conftest import Journey, TestCatalogProvider, TestModel


def test_unconfigured_backend_is_explicitly_unavailable(repository):
    with TestClient(create_app(repository=repository)) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/ready").status_code == 503
        assert client.get("/api/catalog").status_code == 503
        journey = Journey(client)
        assert journey.post(journey.body("start")).status_code == 503


def test_catalog_and_no_store_headers(client):
    assert client.get("/api/catalog").json()["version"] == "test-v1"
    assert client.get("/ready").json()["financeScoring"] is False
    for result in [client.get("/health"), client.get("/api/catalog"), client.post("/api/conversation", json={})]:
        assert result.headers["cache-control"] == "no-store"


def test_missing_mismatched_key_and_missing_session(journey, client):
    body = journey.body("start")
    assert client.post("/api/conversation", json=body).status_code == 422
    assert client.post("/api/conversation", json=body, headers={"Idempotency-Key": "wrong"}).status_code == 422
    assert journey.post(journey.body("message", message={"role": "user", "text": "a"})).status_code == 404
    assert journey.post({**journey.body("start"), "revision": 1}).status_code == 409


@pytest.mark.parametrize("extra", [
    {"revision": -1}, {"revision": True}, {"revision": "0"}, {"action": "unknown"},
    {"unexpected": "value"}, {"sessionId": "../escape"},
    {"action": "message"}, {"action": "confirm", "questionId": "q1"},
    {"action": "message", "message": {"role": "assistant", "text": "a"}},
    {"action": "message", "message": {"role": "user", "text": " "}},
    {"action": "message", "message": {"role": "user", "text": "a" * 8001}},
    {"explicitConfirmation": "true"}, {"explicitConfirmation": True},
    {"questionId": "q1"}, {"optionId": "a"},
])
def test_invalid_input_returns_422_without_echoing_input(journey, extra):
    result = journey.post({**journey.body("start"), **extra})
    assert result.status_code == 422
    assert result.json() == {"detail": "Invalid conversation request."}


def test_live_rejects_unapproved_or_demo_catalog(repository):
    class Unapproved(TestCatalogProvider):
        def load(self):
            catalog = super().load()
            catalog.financeApproved = False
            return catalog
    for catalog in [Unapproved(), DemoCatalog()]:
        with TestClient(create_app(repository=repository, catalog=catalog, model=TestModel())) as client:
            assert client.get("/api/catalog").status_code == 503
            journey = Journey(client)
            assert journey.post(journey.body("start")).status_code == 503


def test_demo_catalog_and_complete_saved_synthetic_profile(repository):
    with TestClient(create_app(repository=repository, demo=True)) as client:
        catalog = client.get("/api/catalog").json()
        assert catalog["demo"] is True and catalog["financeApproved"] is False
        journey = Journey(client)
        started = journey.send("start")
        assert "Scripted demo" in started["assistant"]["text"]
        for question in catalog["questions"]:
            option = question["options"][0]
            proposal = journey.send("message", message={"role": "user", "text": option["id"]})
            assert proposal["proposal"]["optionId"] == option["id"]
            journey.send("confirm", questionId=question["id"], optionId=option["id"],
                         explicitConfirmation=question["requiresExplicitConfirmation"])
        saved = journey.send("save")
        assert "fictional demo answers" in saved["assistant"]["text"]
        assert repository.list_for_session(journey.session_id)[0].score.status == "not_configured"


def test_demo_is_exact_selection_and_cannot_mix_live_integrations(repository):
    question = DemoCatalog().load().questions[0]
    result = ScriptedDemoAdapter().interpret(text="some prose", question=question,
                                            catalog=DemoCatalog().load(), confirmed_answers=[], context=[])
    assert result.kind == "clarification"
    with pytest.raises(ValueError):
        create_app(repository=repository, demo=True, model=TestModel())


def test_backend_defaults_to_api_only_after_legacy_frontend_removal(repository):
    from backend.app.settings import Settings

    assert Settings().VESPER_SERVE_FRONTEND is False
    with TestClient(create_app(repository=repository, demo=True)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/catalog").status_code == 200
        assert client.get("/").status_code == 404
        assert client.get("/src/config.js").status_code == 404
        assert client.get("/src/../backend/data/profiles.sqlite3").status_code == 404
