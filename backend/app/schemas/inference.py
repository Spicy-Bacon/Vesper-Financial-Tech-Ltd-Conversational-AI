"""Strict inference contracts. Catalog ownership stays with the caller."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Identifier = Annotated[str, StringConstraints(min_length=1, max_length=160, pattern=r"^\S+$")]
ShortText = Annotated[str, StringConstraints(min_length=1, max_length=600, pattern=r"\S")]
QuestionText = Annotated[str, StringConstraints(min_length=1, max_length=1200, pattern=r"\S")]
UserReply = Annotated[str, StringConstraints(min_length=1, max_length=4000, pattern=r"\S")]

# A finite set makes neutral wording enforceable without another model or a
# brittle keyword blacklist. Catalog-reviewed templates can extend this later.
CLARIFICATION_QUESTIONS = (
    "Could you clarify what you mean in relation to the current question?",
    "Could you clarify the details requested by the current question?",
    "Which of the listed options best describes your answer, or are you unsure?",
)


class StrictContract(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, frozen=True, revalidate_instances="always",
        hide_input_in_errors=True,
    )


class RetrievalSnippet(StrictContract):
    content_id: Identifier
    text: ShortText
    source_sheet: Identifier
    source_row: Annotated[int, Field(gt=0)]


class ExplanationRecord(RetrievalSnippet):
    catalog_version: Identifier
    question_id: Identifier
    approval_status: Literal["approved", "draft", "unapproved", "retired"]
    retrievable: bool


class RetrievalResult(StrictContract):
    catalog_version: Identifier
    question_id: Identifier
    snippets: Annotated[list[RetrievalSnippet], Field(max_length=3)]
    retrieval_method: Literal["question_scoped_lexical", "question_scoped_order", "question_scoped_empty"]

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        if len({s.content_id for s in self.snippets}) != len(self.snippets):
            raise ValueError("duplicate snippet IDs")
        return self


class AllowedOption(StrictContract):
    question_id: Identifier
    option_id: Identifier
    label: ShortText
    playback: ShortText | None = None
    is_unsure: bool = False


class InferenceQuestion(StrictContract):
    catalog_version: Identifier
    question_id: Identifier
    text: QuestionText
    options: Annotated[list[AllowedOption], Field(min_length=1, max_length=20)]
    help_text: ShortText | None = None

    @model_validator(mode="after")
    def option_ownership(self) -> Self:
        if any(o.question_id != self.question_id for o in self.options):
            raise ValueError("option belongs to another question")
        if len({o.option_id for o in self.options}) != len(self.options):
            raise ValueError("duplicate option IDs")
        return self


class InterpretationInput(StrictContract):
    question: InferenceQuestion
    options: Annotated[list[AllowedOption], Field(min_length=1, max_length=20)]
    user_reply: UserReply
    retrieval: RetrievalResult

    @model_validator(mode="after")
    def scope(self) -> Self:
        if (self.question.question_id != self.retrieval.question_id
                or self.question.catalog_version != self.retrieval.catalog_version):
            raise ValueError("retrieval scope differs from active question")
        expected = {o.option_id: o for o in self.question.options}
        supplied = {o.option_id: o for o in self.options}
        if len(supplied) != len(self.options) or supplied != expected:
            raise ValueError("supply every active option without changes")
        return self


class ModelDecision(StrictContract):
    action: Literal["propose_option", "clarify", "explain", "offer_pause", "out_of_scope"]
    option_id: Identifier | None
    evidence_quote: ShortText | None
    clarification_question: Annotated[str, StringConstraints(min_length=1, max_length=180)] | None
    explanation_content_ids: Annotated[list[Identifier], Field(max_length=3)]
    # Codes only: no reasoning, generated advice or arbitrary support prose.
    support_reason: Literal[
        "user_requested_pause", "user_declined", "user_distress", "outside_questionnaire"
    ] | None

    @model_validator(mode="after")
    def action_fields(self) -> Self:
        if self.action == "propose_option":
            if self.option_id is None or self.evidence_quote is None:
                raise ValueError("proposal requires option and literal evidence")
        elif self.option_id is not None or self.evidence_quote is not None:
            raise ValueError("only proposals may carry option and evidence")

        if self.action == "clarify":
            if self.clarification_question not in CLARIFICATION_QUESTIONS:
                raise ValueError("use an allowed neutral clarification template")
        elif self.clarification_question is not None:
            raise ValueError("clarification text only belongs to clarify")

        if self.action == "explain":
            if not self.explanation_content_ids:
                raise ValueError("explain requires retrieved content")
            if len(set(self.explanation_content_ids)) != len(self.explanation_content_ids):
                raise ValueError("duplicate explanation IDs")
        elif self.explanation_content_ids:
            raise ValueError("explanation IDs only belong to explain")

        if self.action == "offer_pause":
            if self.support_reason not in {"user_requested_pause", "user_declined", "user_distress"}:
                raise ValueError("pause requires a support code")
        elif self.action == "out_of_scope":
            if self.support_reason != "outside_questionnaire":
                raise ValueError("out of scope requires its support code")
        elif self.support_reason is not None:
            raise ValueError("support code is not applicable")
        return self


FallbackReason = Literal[
    "model_not_configured", "model_unavailable", "model_timeout", "invalid_model_output"
]


class InferenceOutcome(StrictContract):
    retrieval: RetrievalResult
    decision: ModelDecision | None
    model_id: Identifier | None
    latency_ms: Annotated[int, Field(ge=0)]
    fallback_reason: FallbackReason | None
    retry_count: Annotated[int, Field(ge=0, le=1)]

    @model_validator(mode="after")
    def decision_or_failure(self) -> Self:
        if (self.decision is None) == (self.fallback_reason is None):
            raise ValueError("return either a decision or a fallback reason")
        return self
