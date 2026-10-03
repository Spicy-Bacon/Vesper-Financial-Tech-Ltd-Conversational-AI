from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.repositories.profiles import ProfileRepository
from backend.app.schemas import Catalog, Interpretation


class TestCatalogProvider:
    __test__ = False

    def load(self):
        # Approval is only a fixture flag; these are not financial questions or policy.
        return Catalog.model_validate({
            "version": "test-v1", "financeApproved": True,
            "questions": [
                {"id": "q1", "label": "First test choice", "prompt": "Choose a or b.",
                 "clarification": "Please select a or b.",
                 "options": [{"id": "a", "answer": "Test choice A"}, {"id": "b", "answer": "Test choice B"}]},
                {"id": "q2", "label": "Second test choice", "prompt": "Choose x.",
                 "clarification": "Please select x.", "requiresExplicitConfirmation": True,
                 "options": [{"id": "x", "answer": "Test choice X"}]},
            ],
        })


class TestModel:
    __test__ = False

    def interpret(self, *, text, question, catalog, confirmed_answers, context):
        if text in {"pause", "support"}:
            return Interpretation(kind=text)
        if any(o.id == text for o in question.options):
            return Interpretation(kind="proposal", optionId=text)
        return Interpretation(kind="clarification")


class Journey:
    def __init__(self, client, session_id=None):
        self.client = client
        self.session_id = session_id or str(uuid4())
        self.revision = 0

    def body(self, action, **extra):
        return {"sessionId": self.session_id, "requestId": str(uuid4()),
                "revision": self.revision, "action": action, **extra}

    def post(self, body):
        return self.client.post("/api/conversation", json=body,
                                headers={"Idempotency-Key": body["requestId"]})

    def send(self, action, **extra):
        result = self.post(self.body(action, **extra))
        assert result.status_code == 200, result.text
        self.revision = result.json()["revision"]
        return result.json()

    def complete(self):
        self.send("start")
        self.send("message", message={"role": "user", "text": "a"})
        self.send("confirm", questionId="q1", optionId="a")
        self.send("message", message={"role": "user", "text": "x"})
        return self.send("confirm", questionId="q2", optionId="x", explicitConfirmation=True)


@pytest.fixture
def repository(tmp_path):
    return ProfileRepository(tmp_path / "profiles.sqlite3")


@pytest.fixture
def app(repository):
    return create_app(repository=repository, catalog=TestCatalogProvider(), model=TestModel())


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


@pytest.fixture
def journey(client):
    return Journey(client)
