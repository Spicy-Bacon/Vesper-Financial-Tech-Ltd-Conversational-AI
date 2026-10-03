from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from backend.app.errors import IntegrationUnavailable
from backend.app.main import create_app
from backend.app.schemas import Interpretation
from backend.tests.conftest import Journey, TestCatalogProvider, TestModel


def test_full_journey_requires_proposal_and_explicit_confirmation(journey, repository):
    journey.send("start")
    premature = journey.post(journey.body("save"))
    assert premature.status_code == 422
    clarified = journey.send("message", message={"role": "user", "text": "uncertain"})
    assert clarified["type"] == "clarification"
    proposal = journey.send("message", message={"role": "user", "text": "a"})
    assert proposal["proposal"]["answer"] == "Test choice A"
    assert proposal["confirmedAnswers"] == []
    assert journey.post(journey.body("confirm", questionId="q1", optionId="b")).status_code == 422
    journey.send("confirm", questionId="q1", optionId="a")
    proposal = journey.send("message", message={"role": "user", "text": "x"})
    assert proposal["proposal"]["safety"] is True
    assert journey.post(journey.body("confirm", questionId="q2", optionId="x")).status_code == 422
    playback = journey.send("confirm", questionId="q2", optionId="x", explicitConfirmation=True)
    assert playback["type"] == "final_playback"
    assert len(playback["confirmedAnswers"]) == 2
    accepted_revision = journey.revision
    saved = journey.send("save")
    assert saved["type"] == "saved" and saved["saveStatus"] == "saved"
    profile = repository.list_for_session(journey.session_id)[0]
    assert profile.acceptedRevision == accepted_revision
    assert profile.score.status == "not_configured"
    assert profile.score.values == {} and profile.score.classification is None


def test_edit_invalidates_acceptance_and_preserves_saved_history(journey, repository):
    journey.complete()
    journey.send("save")
    old = repository.list_for_session(journey.session_id)[0]
    journey.send("edit")
    changed = journey.send("change", questionId="q1")
    assert changed["saveStatus"] == "unsaved"
    assert [a["questionId"] for a in changed["confirmedAnswers"]] == ["q2"]
    assert journey.post(journey.body("save")).status_code == 422
    journey.send("message", message={"role": "user", "text": "b"})
    playback = journey.send("confirm", questionId="q1", optionId="b")
    assert playback["type"] == "final_playback"
    assert [a["questionId"] for a in playback["confirmedAnswers"]] == ["q1", "q2"]
    journey.send("save")
    profiles = repository.list_for_session(journey.session_id)
    assert [p.version for p in profiles] == [1, 2]
    assert profiles[0] == old
    assert profiles[1].answers[0].optionId == "b"


def test_replay_before_revision_check_and_changed_key_conflict(journey):
    original = journey.body("start")
    first = journey.post(original)
    journey.revision = first.json()["revision"]
    journey.send("message", message={"role": "user", "text": "a"})
    assert journey.post(original).json() == first.json()
    changed = {**original, "revision": 99}
    assert journey.post(changed).status_code == 409
    assert journey.post(journey.body("start")).status_code == 409
    assert journey.post({**journey.body("confirm", questionId="q1", optionId="a"), "revision": 0}).status_code == 409


@pytest.mark.parametrize("operation", ["confirm", "save"])
def test_concurrent_duplicate_side_effects_are_atomic(journey, repository, operation):
    if operation == "save":
        journey.complete()
        body = journey.body("save")
    else:
        journey.send("start")
        journey.send("message", message={"role": "user", "text": "a"})
        body = journey.body("confirm", questionId="q1", optionId="a")
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: journey.post(body), range(4)))
    assert all(r.status_code == 200 for r in responses)
    assert all(r.json() == responses[0].json() for r in responses)
    assert len(responses[0].json()["confirmedAnswers"]) == (2 if operation == "save" else 1)
    assert len(repository.list_for_session(journey.session_id)) == (1 if operation == "save" else 0)


def test_concurrent_different_save_keys_reject_stale_revision(journey, repository):
    journey.complete()
    bodies = [journey.body("save"), journey.body("save")]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(journey.post, bodies))
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert len(repository.list_for_session(journey.session_id)) == 1


def test_save_failure_rolls_back_profile_session_and_retry_cache(journey, repository, monkeypatch):
    journey.complete()
    body = journey.body("save")
    real_save = repository.save

    def fail_after_insert(db, profile):
        real_save(db, profile)
        raise IntegrationUnavailable()

    monkeypatch.setattr(repository, "save", fail_after_insert)
    assert journey.post(body).status_code == 503
    assert repository.list_for_session(journey.session_id) == []
    monkeypatch.setattr(repository, "save", real_save)
    assert journey.post(body).status_code == 200
    profiles = repository.list_for_session(journey.session_id)
    assert len(profiles) == 1 and profiles[0].version == 1


@pytest.mark.parametrize("kind", ["pause", "support"])
def test_pause_support_resume_and_not_sure(journey, kind):
    journey.send("start")
    result = journey.send("message", message={"role": "user", "text": kind})
    assert result["type"] == kind and result["canMessage"] is False
    assert journey.post(journey.body("message", message={"role": "user", "text": "a"})).status_code == 422
    journey.send("resume")
    journey.send("message", message={"role": "user", "text": "a"})
    result = journey.send("not_sure")
    assert result["proposal"] is None and result["type"] == "clarification"
    assert journey.post(journey.body("confirm", questionId="q1", optionId="a")).status_code == 422


def test_sessions_are_isolated(client):
    first, second = Journey(client), Journey(client)
    first.send("start")
    first.send("message", message={"role": "user", "text": "a"})
    second.send("start")
    assert second.post(second.body("confirm", questionId="q1", optionId="a")).status_code == 422
    assert len(first.send("confirm", questionId="q1", optionId="a")["confirmedAnswers"]) == 1


def test_restart_persists_sessions_and_replay(repository):
    with TestClient(create_app(repository=repository, catalog=TestCatalogProvider(), model=TestModel())) as client:
        journey = Journey(client)
        journey.complete()
        body = journey.body("save")
        saved = journey.post(body).json()
    with TestClient(create_app(repository=repository, catalog=TestCatalogProvider(), model=TestModel())) as client:
        assert Journey(client).post(body).json() == saved
        assert len(repository.list_for_session(body["sessionId"])) == 1


def test_expiry_allows_original_replay_but_rejects_new_work(journey, app):
    clock = [1000.0]
    app.state.conversation.clock = lambda: clock[0]
    body = journey.body("start")
    started = journey.post(body)
    journey.revision = started.json()["revision"]
    clock[0] += 3601
    assert journey.post(body).json() == started.json()
    assert journey.post(journey.body("message", message={"role": "user", "text": "a"})).status_code == 410


def test_model_cannot_invent_option_or_confirm_answer(journey, app):
    journey.send("start")
    model = app.state.conversation.model
    class InvalidModel:
        def interpret(self, **kwargs):
            return Interpretation(kind="proposal", optionId="invented")
    app.state.conversation.model = InvalidModel()
    body = journey.body("message", message={"role": "user", "text": "a"})
    assert journey.post(body).status_code == 503
    app.state.conversation.model = model
    result = journey.post(body)
    assert result.status_code == 200 and result.json()["confirmedAnswers"] == []


def test_catalog_is_pinned_at_session_start(journey, app):
    journey.send("start")
    class NewCatalog(TestCatalogProvider):
        def load(self):
            catalog = super().load()
            catalog.version = "test-v2"
            catalog.questions[0].options[0].answer = "Changed answer"
            return catalog
    app.state.conversation.catalog = NewCatalog()
    result = journey.send("message", message={"role": "user", "text": "a"})
    assert result["proposal"]["answer"] == "Test choice A"


def test_retrieval_contract_and_adapter_mutation_do_not_change_state(journey, app):
    class Retriever:
        def retrieve(self, *, text, question, catalog):
            assert catalog.version == "test-v1" and question.id == "q1"
            question.options[0].answer = "Injected retrieval answer"
            return [{"sourceId": "test-source", "text": "Synthetic context"}]
    class Model:
        def interpret(self, *, text, question, catalog, confirmed_answers, context):
            assert context[0].sourceId == "test-source"
            assert question.options[0].answer == "Test choice A"
            catalog.questions[0].options[0].answer = "Injected model answer"
            return Interpretation(kind="proposal", optionId="a")
    app.state.conversation.retrieval = Retriever()
    app.state.conversation.model = Model()
    journey.send("start")
    result = journey.send("message", message={"role": "user", "text": "a"})
    assert result["proposal"]["answer"] == "Test choice A"


def test_retrieval_failure_does_not_silently_fallback(journey, app):
    class BrokenRetriever:
        def retrieve(self, **kwargs):
            raise RuntimeError("private vendor error")
    app.state.conversation.retrieval = BrokenRetriever()
    journey.send("start")
    result = journey.post(journey.body("message", message={"role": "user", "text": "a"}))
    assert result.status_code == 503
    assert "private vendor error" not in result.text


def test_finance_failure_prevents_save_then_same_request_can_retry(journey, app, repository):
    from backend.app.schemas import ScoreResult

    class FailingPolicy:
        def evaluate(self, **kwargs):
            raise RuntimeError("private finance error")
    class SyntheticPolicy:
        def evaluate(self, *, answers, catalog):
            return ScoreResult(status="scored", policyVersion="test-policy", catalogVersion=catalog.version,
                               values={"fixture": "1.25"})
    journey.complete()
    app.state.conversation.scoring.policy = FailingPolicy()
    body = journey.body("save")
    failure = journey.post(body)
    assert failure.status_code == 503 and "private finance error" not in failure.text
    assert repository.list_for_session(journey.session_id) == []
    app.state.conversation.scoring.policy = SyntheticPolicy()
    assert journey.post(body).status_code == 200
    score = repository.list_for_session(journey.session_id)[0].score
    assert score.policyVersion == "test-policy" and str(score.values["fixture"]) == "1.25"


def test_storage_failure_returns_generic_retryable_error(journey, repository, monkeypatch):
    import sqlite3

    def failure(*args):
        raise sqlite3.OperationalError("private database path")
    monkeypatch.setattr(repository, "load_session", failure)
    result = journey.post(journey.body("start"))
    assert result.status_code == 503
    assert "private database path" not in result.text
