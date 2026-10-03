"""SYNTHETIC integration fixtures, never a Finance-approved runtime catalog.

Six fictional questions exercise the unchanged frontend contract. Explicit labels
and Unsure flags are fixture data, not inferred production financial semantics.
"""
import json
import os
import shutil
import sqlite3
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.schemas import Catalog, Interpretation
from backend.app.schemas.v1 import SessionSnapshot


class SyntheticSixCatalog:
    def __init__(self):
        self.calls = 0
        self.value = Catalog.model_validate({
            "version": "SYNTHETIC-SIX-NOT-A-RELEASE", "financeApproved": False, "demo": True,
            "questions": [
                {"id": f"S{i}", "label": f"SYNTHETIC question {i}",
                 "prompt": f"SYNTHETIC question {i}: describe the fictional choice.",
                 "clarification": "SYNTHETIC clarification: please clarify your fictional answer.",
                 "requiresExplicitConfirmation": i == 1,
                 "options": [
                     {"id": "a", "answer": "SYNTHETIC canonical choice A.",
                      "label": "SYNTHETIC choice A", "is_unsure": False},
                     {"id": "u", "answer": "SYNTHETIC unsure playback.",
                      "label": "SYNTHETIC unsure", "is_unsure": True},
                 ]}
                for i in range(1, 7)
            ],
        })

    def load(self):
        self.calls += 1
        return self.value.model_copy(deep=True)


class SyntheticModel:
    def __init__(self):
        self.calls = 0

    def interpret(self, *, text, question, catalog, confirmed_answers, context):
        self.calls += 1
        if text in {"pause", "support"}:
            return Interpretation(kind=text)
        if text in {"a", "u"}:
            return Interpretation(kind="proposal", optionId=text)
        return Interpretation(kind="clarification")


@pytest.fixture
def v1_app(repository):
    app = create_app(repository=repository, catalog=SyntheticSixCatalog(), model=SyntheticModel())
    # Permit only this injected fictional fixture; no production approval is asserted.
    app.state.conversation.allow_demo = True
    return app


@pytest.fixture
def v1_client(v1_app):
    with TestClient(v1_app) as client:
        yield client


class V1Journey:
    def __init__(self, client):
        self.client = client
        self.snapshot = None

    def body(self, **extra):
        return {"request_id": str(uuid4()),
                "expected_revision": self.snapshot["revision"] if self.snapshot else 0, **extra}

    def post(self, action, body):
        url = "/api/v1/sessions"
        if action != "start":
            url += f"/{self.snapshot['session_id']}/{action}"
        return self.client.post(url, json=body, headers={"Idempotency-Key": body["request_id"]})

    def send(self, action, **extra):
        response = self.post(action, self.body(**extra))
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        self.snapshot = response.json()
        assert SessionSnapshot.model_validate(self.snapshot).model_dump(mode="json") == self.snapshot
        return self.snapshot

    def load(self):
        return self.client.get(f"/api/v1/sessions/{self.snapshot['session_id']}")

    def propose(self, text="a"):
        return self.send("messages", text=text)

    def confirm(self, **extra):
        return self.send("confirmations", proposal_id=self.snapshot["pending_proposal"]["proposal_id"],
                         explicit_confirmation=True, **extra)


@pytest.fixture
def v1(v1_client):
    return V1Journey(v1_client)


def test_first_question_snapshot_proposal_confirmation_and_get(v1, v1_app, repository):
    initial = v1.send("start")
    assert initial["catalog_status"] == "provisional"
    assert initial["state"] == "ASKING" and initial["allowed_actions"] == ["message"]
    assert initial["revision"] == 1 and initial["confirmed_answers"] == []
    assert initial["review"] is initial["review_version"] is initial["receipt"] is None
    assert initial["pending_proposal"] is None
    assert initial["explanations"] == []  # No invented retrieval provenance.
    assert initial["active_question"]["question_id"] == "S1"
    assert initial["active_question"]["order"] == 1
    assert initial["active_question"]["options"][1]["is_unsure"] is True
    proposed = v1.propose()
    assert proposed["state"] == "AWAITING_CONFIRMATION"
    assert proposed["allowed_actions"] == ["confirm", "change"] and proposed["confirmed_answers"] == []
    assert proposed["pending_proposal"]["origin"] == "model"
    assert proposed["pending_proposal"]["playback"] == initial["active_question"]["options"][0]["playback"]
    assert v1.load().json() == proposed
    confirmed = v1.confirm()
    assert confirmed["state"] == "ASKING" and confirmed["allowed_actions"] == ["message"]
    assert confirmed["pending_proposal"] is None
    assert confirmed["active_question"]["question_id"] == "S2"
    assert confirmed["confirmed_answers"] == [{
        "question_id": "S1", "option_id": "a", "label": "SYNTHETIC question 1",
        "playback": "SYNTHETIC canonical choice A.", "is_unsure": False, "order": 1,
    }]
    assert v1.load().json() == confirmed
    assert v1_app.state.conversation.model.calls == 1
    assert repository.list_for_session(initial["session_id"]) == []


def test_retries_return_original_full_snapshots_after_later_revisions(v1, v1_app):
    start_body = v1.body()
    initial = v1.send("start", **start_body)
    message_body = v1.body(text="a")
    proposal = v1.send("messages", **message_body)
    confirm_body = v1.body(proposal_id=proposal["pending_proposal"]["proposal_id"], explicit_confirmation=True)
    confirmed = v1.send("confirmations", **confirm_body)
    latest = v1.propose("u")
    for action, body, original in [("start", start_body, initial), ("messages", message_body, proposal),
                                    ("confirmations", confirm_body, confirmed)]:
        assert v1.post(action, body).json() == original
    assert v1.load().json() == latest
    assert v1_app.state.conversation.model.calls == 2
    assert len(latest["confirmed_answers"]) == 1


@pytest.mark.parametrize("action", ["start", "messages", "confirmations"])
def test_concurrent_identical_retries_have_one_effect(v1, v1_app, action):
    if action != "start":
        v1.send("start")
    if action == "confirmations":
        v1.propose()
        body = v1.body(proposal_id=v1.snapshot["pending_proposal"]["proposal_id"], explicit_confirmation=True)
    else:
        body = v1.body(**({"text": "a"} if action == "messages" else {}))
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(lambda _: v1.post(action, body), range(3)))
    assert all(r.status_code == 200 for r in responses)
    assert all(r.json() == responses[0].json() for r in responses)
    assert v1_app.state.conversation.model.calls == (0 if action == "start" else 1)
    if action == "confirmations":
        assert len(responses[0].json()["confirmed_answers"]) == 1


def test_restart_preserves_creation_cache_proposal_id_and_recovery(v1, repository):
    body = v1.body()
    initial = v1.send("start", **body)
    proposed = v1.propose()
    new_app = create_app(repository=repository)  # Recovery/replay needs no wired integrations.
    with TestClient(new_app) as client:
        assert client.post("/api/v1/sessions", json=body,
                           headers={"Idempotency-Key": body["request_id"]}).json() == initial
        assert client.get(f"/api/v1/sessions/{initial['session_id']}").json() == proposed


def test_get_and_messages_use_pinned_catalog_without_reloading(v1, v1_app):
    initial = v1.send("start")
    provider = v1_app.state.conversation.catalog
    provider.value.version = "SYNTHETIC-CHANGED"
    provider.value.questions[0].options[0].answer = "SYNTHETIC changed wording."
    provider.value.questions[0].options[0].label = "SYNTHETIC changed label"
    assert v1.load().json() == initial
    proposed = v1.propose()
    assert proposed["catalog_version"] == initial["catalog_version"]
    assert proposed["pending_proposal"]["playback"] == "SYNTHETIC canonical choice A."
    assert provider.calls == 1


@pytest.mark.parametrize("action", ["messages", "confirmations"])
def test_stale_revision_does_not_change_state(v1, v1_app, action):
    v1.send("start")
    if action == "confirmations":
        v1.propose()
        extra = {"proposal_id": v1.snapshot["pending_proposal"]["proposal_id"], "explicit_confirmation": True}
    else:
        extra = {"text": "a"}
    before = v1.snapshot
    calls = v1_app.state.conversation.model.calls
    response = v1.post(action, v1.body(expected_revision=0, **extra))
    assert response.status_code == 409 and response.headers["cache-control"] == "no-store"
    assert v1.load().json() == before and v1_app.state.conversation.model.calls == calls


def test_foreign_and_old_proposal_ids_cannot_confirm(v1):
    v1.send("start")
    proposed = v1.propose()
    old = proposed["pending_proposal"]["proposal_id"]
    assert v1.post("confirmations", v1.body(proposal_id="foreign", explicit_confirmation=True)).status_code == 422
    assert v1.load().json() == proposed
    v1.confirm()
    current = v1.propose()
    assert current["pending_proposal"]["proposal_id"] != old
    assert v1.post("confirmations", v1.body(proposal_id=old, explicit_confirmation=True)).status_code == 422
    assert v1.load().json() == current


def test_safety_requires_explicit_check_but_non_safety_requires_only_confirm_action(v1):
    v1.send("start")
    proposed = v1.propose()
    body = v1.body(proposal_id=proposed["pending_proposal"]["proposal_id"])
    assert v1.post("confirmations", body).status_code == 422
    assert v1.load().json() == proposed
    # A failed validation is not cached; the corrected command can reuse its key.
    v1.send("confirmations", **body, explicit_confirmation=True)
    v1.propose()
    confirmed = v1.send("confirmations", proposal_id=v1.snapshot["pending_proposal"]["proposal_id"],
                        explicit_confirmation=False)
    assert len(confirmed["confirmed_answers"]) == 2


@pytest.mark.parametrize("action", ["start", "messages", "confirmations"])
def test_conflicting_idempotency_keys_are_rejected_before_current_state_checks(v1, action):
    if action != "start":
        v1.send("start")
    if action == "confirmations":
        v1.propose()
        body = v1.body(proposal_id=v1.snapshot["pending_proposal"]["proposal_id"], explicit_confirmation=True)
        change = {"proposal_id": "foreign"}
    elif action == "messages":
        body, change = v1.body(text="a"), {"text": "u"}
    else:
        body, change = v1.body(), {"expected_revision": 1}
    original = v1.send(action, **body)
    assert v1.post(action, {**body, **change}).status_code == 409
    assert v1.load().json() == original
    if action == "messages":
        # Sharing a key across operations also conflicts, not an implicit confirmation.
        conflict = {"request_id": body["request_id"], "expected_revision": original["revision"],
                    "proposal_id": original["pending_proposal"]["proposal_id"], "explicit_confirmation": True}
        assert v1.post("confirmations", conflict).status_code == 409


@pytest.mark.parametrize("failure", ["foreign_option", "model_failure", "retrieval_failure"])
def test_failed_integrations_roll_back_and_same_request_can_retry(v1, v1_app, repository, failure):
    initial = v1.send("start")
    service = v1_app.state.conversation
    original_model = service.model

    class BrokenModel:
        def interpret(self, **kwargs):
            if failure == "foreign_option":
                return Interpretation(kind="proposal", optionId="invented")
            raise RuntimeError("PRIVATE upstream payload")

    class BrokenRetriever:
        def retrieve(self, **kwargs):
            raise RuntimeError("PRIVATE retrieval details")

    if failure == "retrieval_failure":
        service.retrieval = BrokenRetriever()
    else:
        service.model = BrokenModel()
    body = v1.body(text="a")
    with repository.transaction() as db:
        before = repository.load_session(db, initial["session_id"])
    response = v1.post("messages", body)
    assert response.status_code == 503 and "PRIVATE" not in response.text
    assert response.headers["cache-control"] == "no-store" and v1.load().json() == initial
    with repository.transaction() as db:
        assert repository.load_session(db, initial["session_id"]) == before
        assert repository.cached_request(db, initial["session_id"], body["request_id"]) is None
    service.model, service.retrieval = original_model, None
    retried = v1.send("messages", **body)
    assert retried["confirmed_answers"] == [] and retried["pending_proposal"] is not None


@pytest.mark.parametrize("action", ["start", "confirmations"])
def test_storage_failure_rolls_back_creation_or_confirmation_and_retry_cache(v1, repository, monkeypatch, action):
    if action == "confirmations":
        v1.send("start")
        before = v1.propose()
        body = v1.body(proposal_id=before["pending_proposal"]["proposal_id"], explicit_confirmation=True)
    else:
        body = v1.body()
    original_store = repository.store_request

    def fail_after_store(*args):
        original_store(*args)
        raise sqlite3.OperationalError("PRIVATE database path")

    monkeypatch.setattr(repository, "store_request", fail_after_store)
    response = v1.post(action, body)
    assert response.status_code == 503 and "PRIVATE" not in response.text
    with repository.transaction() as db:
        if action == "start":
            assert repository.creation_session(db, body["request_id"]) is None
            assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
        else:
            assert v1.snapshot == before
            assert repository.load_session(db, before["session_id"])["answers"] == []
            assert repository.cached_request(db, before["session_id"], body["request_id"]) is None
    monkeypatch.setattr(repository, "store_request", original_store)
    if action == "confirmations":
        assert v1.load().json() == before
    assert v1.send(action, **body)["revision"] == (1 if action == "start" else 3)


@pytest.mark.parametrize("kind", ["ambiguous", "pause", "support"])
def test_clarification_and_vulnerable_user_handling_do_not_confirm_or_guess(v1, kind):
    v1.send("start")
    result = v1.propose(kind)
    assert result["pending_proposal"] is None and result["confirmed_answers"] == []
    if kind == "ambiguous":
        assert result["state"] == "ASKING" and result["response_type"] == "clarification"
        assert result["allowed_actions"] == ["message"]
    else:
        assert result["state"] == "PAUSED" and result["allowed_actions"] == []
        assert result["response_type"] == ("paused" if kind == "pause" else "support")
        assert v1.post("messages", v1.body(text="a")).status_code == 422
    assert v1.load().json() == result


def test_confirmed_unsure_is_explicit_and_six_answers_produce_valid_read_only_review(v1):
    v1.send("start")
    for index in range(6):
        proposal = v1.propose("u" if index == 0 else "a")
        assert len(proposal["confirmed_answers"]) == index
        final = v1.confirm()
    assert final["state"] == "REVIEW" and final["allowed_actions"] == ["finalize"]
    assert final["review"]["statements"] == final["confirmed_answers"]
    assert final["confirmed_answers"][0]["is_unsure"] is True
    assert final["review_version"] and final["receipt"] is None
    assert v1.load().json() == final
    assert v1.post("messages", v1.body(text="a")).status_code == 422


def test_expiry_preserves_original_retries_but_blocks_get_and_new_work(v1, v1_app):
    clock = [1000.0]
    v1_app.state.conversation.clock = lambda: clock[0]
    body = v1.body()
    initial = v1.send("start", **body)
    message_body = v1.body(text="a")
    proposed = v1.send("messages", **message_body)
    confirmation_body = v1.body(proposal_id=proposed["pending_proposal"]["proposal_id"], explicit_confirmation=True)
    confirmed = v1.send("confirmations", **confirmation_body)
    clock[0] += 3601
    for action, command, original in [("start", body, initial), ("messages", message_body, proposed),
                                       ("confirmations", confirmation_body, confirmed)]:
        assert v1.post(action, command).json() == original
    assert v1.load().status_code == 410
    assert v1.post("messages", v1.body(text="a")).status_code == 410
    assert v1.client.get("/api/v1/sessions/missing").status_code == 404


@pytest.mark.parametrize("metadata", ["missing_label", "missing_unsure", "no_unsure", "two_unsure", "wrong_count", "unapproved"])
def test_incomplete_catalog_metadata_is_rejected_without_fabrication(v1, v1_app, repository, metadata):
    service = v1_app.state.conversation
    catalog = service.catalog.value
    if metadata == "missing_label":
        catalog.questions[0].options[0].label = None
    elif metadata == "missing_unsure":
        catalog.questions[0].options[0].is_unsure = None
    elif metadata == "no_unsure":
        catalog.questions[0].options[1].is_unsure = False
    elif metadata == "two_unsure":
        catalog.questions[0].options[0].is_unsure = True
    elif metadata == "wrong_count":
        catalog.questions.pop()
    else:
        service.allow_demo = False
    body = v1.body()
    assert v1.post("start", body).status_code == 503
    assert service.model.calls == 0
    with repository.transaction() as db:
        assert repository.creation_session(db, body["request_id"]) is None
        assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0


@pytest.mark.parametrize("headers", [{}, {"Idempotency-Key": "different"}])
@pytest.mark.parametrize("action", ["start", "messages", "confirmations"])
def test_missing_or_mismatched_keys(v1, headers, action):
    if action != "start":
        v1.send("start")
    if action == "confirmations":
        v1.propose()
        body = v1.body(proposal_id=v1.snapshot["pending_proposal"]["proposal_id"])
    else:
        body = v1.body(**({"text": "a"} if action == "messages" else {}))
    url = "/api/v1/sessions" + (f"/{v1.snapshot['session_id']}/{action}" if action != "start" else "")
    response = v1.client.post(url, json=body, headers=headers)
    assert response.status_code == 422 and response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("bad", [{"expected_revision": True}, {"expected_revision": "0"},
                                  {"request_id": "bad key"}, {"session_id": "client-picked"}])
def test_invalid_creation_payloads_are_safe(v1, bad):
    assert v1.post("start", v1.body(**bad)).status_code == 422


def test_only_four_routes_and_protocols_cannot_mutate_each_others_sessions(v1, v1_app):
    paths = {path for path in v1_app.openapi()["paths"] if path.startswith("/api/v1")}
    assert paths == {"/api/v1/sessions", "/api/v1/sessions/{session_id}",
                     "/api/v1/sessions/{session_id}/messages", "/api/v1/sessions/{session_id}/confirmations",
                     "/api/v1/sessions/{session_id}/finalize", "/api/v1/sessions/{session_id}/corrections"}
    initial = v1.send("start")
    body = {"sessionId": initial["session_id"], "requestId": "legacy-command", "revision": 1,
            "action": "message", "message": {"text": "a"}}
    assert v1.client.post("/api/conversation", json=body,
                         headers={"Idempotency-Key": body["requestId"]}).status_code == 422
    assert v1.load().json() == initial
    body.update(sessionId="legacy-session", revision=0, action="start")
    body.pop("message")
    assert v1.client.post("/api/conversation", json=body,
                         headers={"Idempotency-Key": body["requestId"]}).status_code == 200
    assert v1.client.get("/api/v1/sessions/legacy-session").status_code == 404


def test_snapshots_pass_actual_unchanged_frontend_zod_contract(v1):
    """Optional cross-language check; set VESPER_TEST_ZOD_MODULE for a temp install.

    With normal root npm dependencies installed, no environment override is needed.
    Only the Zod import is redirected; the actual contracts.ts schema is executed.
    """
    root = Path(__file__).resolve().parents[2]
    zod = Path(os.environ.get("VESPER_TEST_ZOD_MODULE", root / "node_modules/zod/index.js"))
    node = shutil.which("node")
    if not node or not zod.is_file():
        pytest.skip("Install frontend Zod dependencies and Node, or set VESPER_TEST_ZOD_MODULE.")
    snapshots = [v1.send("start"), v1.propose("ambiguous"), v1.propose(), v1.confirm()]
    for _ in range(5):
        snapshots.extend([v1.propose(), v1.confirm()])
    other = V1Journey(v1.client)
    snapshots.extend([other.send("start"), other.propose("support")])
    runner = r"""
        import {readFileSync} from 'node:fs';
        import {stripTypeScriptTypes} from 'node:module';
        import {pathToFileURL} from 'node:url';
        const source = readFileSync(process.argv[1], 'utf8')
            .replace('from "zod"', 'from ' + JSON.stringify(pathToFileURL(process.argv[2]).href));
        const code = stripTypeScriptTypes(source);
        const {snapshotSchema} = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
        const snapshots = JSON.parse(readFileSync(0, 'utf8'));
        for (const snapshot of snapshots) snapshotSchema.parse(snapshot);
        process.stdout.write(String(snapshots.length));
    """
    result = subprocess.run(
        [node, "--input-type=module", "-e", runner, str(root / "frontend/src/api/contracts.ts"), str(zod)],
        input=json.dumps(snapshots), text=True, capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == str(len(snapshots))
