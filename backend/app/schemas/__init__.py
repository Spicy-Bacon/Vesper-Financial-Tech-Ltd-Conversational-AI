from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8000)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.:-]{1,128}$")]
ActionId = Literal["start", "message", "confirm", "change", "not_sure", "save", "edit", "resume"]


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserMessage(Schema):
    role: Literal["user"] = "user"
    text: Text


class ConversationRequest(Schema):
    sessionId: Identifier
    requestId: Identifier
    revision: int = Field(ge=0, strict=True)
    action: ActionId
    message: UserMessage | None = None
    questionId: Identifier | None = None
    optionId: Identifier | None = None
    explicitConfirmation: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def validate_action(self):
        if (self.action == "message") != (self.message is not None):
            raise ValueError("Only message actions require a message.")
        if self.action in {"confirm", "change"}:
            if self.questionId is None:
                raise ValueError("This action requires questionId.")
        elif self.questionId is not None:
            raise ValueError("This action does not accept questionId.")
        if (self.action == "confirm") != (self.optionId is not None):
            raise ValueError("Only confirm actions require optionId.")
        if self.explicitConfirmation and self.action != "confirm":
            raise ValueError("Explicit confirmation only applies to confirm.")
        return self


class AssistantMessage(Schema):
    role: Literal["assistant"] = "assistant"
    text: Text


class Answer(Schema):
    questionId: Identifier
    optionId: Identifier
    label: Text
    answer: Text


class Proposal(Answer):
    safety: bool


class Action(Schema):
    id: Literal["confirm", "change", "not_sure", "save", "edit", "resume"]
    label: Text
    questionId: Identifier | None = None
    optionId: Identifier | None = None


class Finding(Schema):
    flag: Identifier
    quote: Text
    explanation: Text


class ConversationResponse(Schema):
    sessionId: Identifier
    revision: int = Field(ge=1)
    assistant: AssistantMessage
    type: Literal["message", "clarification", "proposed_answer", "final_playback", "saved", "pause", "support"]
    canMessage: bool
    proposal: Proposal | None = None
    actions: list[Action] = Field(default_factory=list)
    confirmedAnswers: list[Answer] = Field(default_factory=list)
    saveStatus: Literal["unsaved", "saved"] = "unsaved"
    findings: list[Finding] = Field(default_factory=list)


class Option(Schema):
    id: Identifier
    answer: Text


class Question(Schema):
    id: Identifier
    label: Text
    prompt: Text
    clarification: Text
    requiresExplicitConfirmation: bool = False
    options: list[Option] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_options(self):
        if len({o.id for o in self.options}) != len(self.options):
            raise ValueError("Option IDs must be unique within a question.")
        return self


class Catalog(Schema):
    version: Identifier
    financeApproved: bool
    demo: bool = False
    questions: list[Question] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_questions(self):
        if len({q.id for q in self.questions}) != len(self.questions):
            raise ValueError("Question IDs must be unique.")
        return self


class RetrievedContext(Schema):
    sourceId: Identifier
    text: Text


class Interpretation(Schema):
    kind: Literal["proposal", "clarification", "pause", "support"]
    optionId: Identifier | None = None

    @model_validator(mode="after")
    def proposal_requires_option(self):
        if (self.kind == "proposal") != (self.optionId is not None):
            raise ValueError("Only a proposal must have optionId.")
        return self


class ScoreResult(Schema):
    status: Literal["not_configured", "scored"] = "not_configured"
    policyVersion: Identifier | None = None
    catalogVersion: Identifier
    values: dict[Identifier, Decimal] = Field(default_factory=dict)
    classification: Text | None = None

    @model_validator(mode="after")
    def valid_score(self):
        if self.status == "scored" and not self.policyVersion:
            raise ValueError("Scored results require a Finance policy version.")
        if self.status == "not_configured" and (self.policyVersion or self.values or self.classification):
            raise ValueError("Unconfigured scoring cannot report scores or classifications.")
        if any(not value.is_finite() for value in self.values.values()):
            raise ValueError("Scores must be finite.")
        return self


class Profile(Schema):
    id: Identifier
    sessionId: Identifier
    version: int = Field(ge=1)
    acceptedRevision: int = Field(ge=1)
    catalogVersion: Identifier
    demo: bool = False
    answers: list[Answer]
    score: ScoreResult
    createdAt: float
