"""SYNTHETIC / PROVISIONAL unit fixtures, never a released finance catalog.

Approval flags below simulate gate inputs only. They do not assert finance
approval. No runtime loader imports tests or publishes these records.
"""

import pytest

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
