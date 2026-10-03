"""SYNTHETIC / PROVISIONAL unit fixtures, never a released finance catalog.

Approval flags below simulate gate inputs only. They do not assert finance
approval. No runtime loader imports tests or publishes these records.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.repositories.profiles import ProfileRepository
from backend.app.schemas import Catalog, Interpretation

from app.schemas.inference import (
    AllowedOption, ExplanationRecord, InferenceQuestion, InterpretationInput,
)
from app.services.retrieval import QuestionScopedRetriever

SYNTHETIC_VERSION = "SYNTHETIC-UNIT-TEST-NOT-A-RELEASE"


@pytest.fixture
def synthetic_question():
    return InferenceQuestion(
        catalog_version=SYNTHETIC_VERSION, question_id="Q4",
        text="SYNTHETIC Q4 fixture: describe the fictional separate accessible savings.",
        options=[
            AllowedOption(question_id="Q4", option_id="Q4_C",
                          label="SYNTHETIC fixture: three months of essentials",
                          playback="SYNTHETIC playback only; not finance-reviewed policy."),
            AllowedOption(question_id="Q4", option_id="Q4_U",
                          label="SYNTHETIC unsure", is_unsure=True),
        ],
    )


@pytest.fixture
def synthetic_record():
    def make(**changes):
        values = dict(
            catalog_version=SYNTHETIC_VERSION, question_id="Q4",
            content_id="SYNTHETIC-EXPLANATION-1",
            text="SYNTHETIC fixture about separate accessible savings; not finance policy.",
            source_sheet="Explanations", source_row=2,
            approval_status="approved",  # Simulated gate input, not real approval.
            retrievable=True,
        )
        values.update(changes)
        return ExplanationRecord(**values)
    return make


@pytest.fixture
def context(synthetic_question, synthetic_record):
    reply = "Fictional separate accessible savings cover three months of essentials."
    retrieval = QuestionScopedRetriever([synthetic_record()]).retrieve(
        catalog_version=SYNTHETIC_VERSION, question_id="Q4", user_reply=reply,
    )
    return InterpretationInput(question=synthetic_question, options=synthetic_question.options,
                               user_reply=reply, retrieval=retrieval)


@pytest.fixture
def proposal():
    return dict(action="propose_option", option_id="Q4_C",
                evidence_quote="three months of essentials", clarification_question=None,
                explanation_content_ids=[], support_reason=None)


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
