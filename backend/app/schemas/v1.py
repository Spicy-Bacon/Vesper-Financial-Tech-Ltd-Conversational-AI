"""Frontend wire models and projection of the existing service's pinned state.

No financial wording, option meaning or retrieval provenance is inferred here.
"""
from datetime import datetime, timezone
from typing import Literal

from pydantic import Field

from ..errors import IntegrationUnavailable
from . import Answer, Catalog, Identifier, Profile, Schema, ScoreResult, Text


class SessionCommand(Schema):
    request_id: Identifier
    expected_revision: int = Field(ge=0, strict=True)


class MessageCommand(SessionCommand):
    text: Text


class ConfirmationCommand(SessionCommand):
    proposal_id: Identifier
    explicit_confirmation: bool = Field(default=False, strict=True)


class FinalizeCommand(SessionCommand):
    review_version: Text


class CorrectionCommand(SessionCommand):
    question_id: Identifier


class OptionSnapshot(Schema):
    option_id: Identifier
    label: Text
    playback: Text
    is_unsure: bool


class QuestionSnapshot(Schema):
    question_id: Identifier
    text: Text
    label: Text
    order: int = Field(ge=1, le=6)
    safety: bool
    options: list[OptionSnapshot] = Field(min_length=1)


class AnswerSnapshot(Schema):
    question_id: Identifier
    option_id: Identifier
    label: Text
    playback: Text
    is_unsure: bool
    order: int = Field(ge=1, le=6)


class ProposalSnapshot(Schema):
    proposal_id: Identifier
    question_id: Identifier
    option_id: Identifier
    playback: Text
    is_unsure: bool
    origin: Literal["model", "button", "demo"]
    safety: bool


class ReviewSnapshot(Schema):
    statements: list[AnswerSnapshot] = Field(min_length=6, max_length=6)
    help_text: Text


class ProfileSnapshot(Schema):
    profile_id: Identifier
    session_id: Identifier
    catalog_version: Text
    review_version: Text
    accepted_at: Text
    simulated: bool
    answers: list[AnswerSnapshot] = Field(min_length=6, max_length=6)
    score: ScoreResult | None = None


class SnippetSnapshot(Schema):
    content_id: Text
    text: Text
    source_sheet: Text
    source_row: int = Field(gt=0)


class FindingSnapshot(Schema):
    flag: Text
    quote: Text
    explanation: Text


class SessionSnapshot(Schema):
    session_id: Identifier
    revision: int = Field(ge=0)
    catalog_version: Text
    catalog_status: Literal["provisional", "approved"]
    state: Literal["ASKING", "AWAITING_CONFIRMATION", "REVIEW", "PAUSED", "ENDED", "SAVED"]
    active_question: QuestionSnapshot | None
    pending_proposal: ProposalSnapshot | None
    confirmed_answers: list[AnswerSnapshot] = Field(max_length=6)
    assistant_message: Text
    response_type: Literal[
        "message", "clarification", "explanation", "proposal", "support",
        "out_of_scope", "fallback", "review", "paused", "ended", "saved",
    ]
    allowed_actions: list[Literal[
        "message", "select", "confirm", "change", "pause", "end", "resume",
        "finalize", "explain_review",
    ]]
    review_version: Text | None
    review: ReviewSnapshot | None
    receipt: ProfileSnapshot | None
    explanations: list[SnippetSnapshot] = Field(default_factory=list)
    findings: list[FindingSnapshot] = Field(default_factory=list)


def frontend_catalog(catalog: Catalog) -> None:
    """Require explicit owner metadata, without changing legacy catalog gates."""
    if len(catalog.questions) != 6:
        raise IntegrationUnavailable()
    for question in catalog.questions:
        if any(o.label is None or o.is_unsure is None for o in question.options):
            raise IntegrationUnavailable()
        if sum(o.is_unsure is True for o in question.options) != 1:
            raise IntegrationUnavailable()


def snapshot_for(session_id: str, state: dict) -> SessionSnapshot:
    catalog = Catalog.model_validate(state["catalog"])
    frontend_catalog(catalog)
    questions = {q.id: (index + 1, q) for index, q in enumerate(catalog.questions)}

    def answer(raw: dict) -> AnswerSnapshot:
        value = Answer.model_validate(raw)
        order, question = questions[value.questionId]
        option = next(o for o in question.options if o.id == value.optionId)
        return AnswerSnapshot(
            question_id=value.questionId, option_id=value.optionId,
            label=value.label, playback=value.answer, is_unsure=option.is_unsure, order=order,
        )

    order, current = questions[state["currentQuestion"]]
    active = QuestionSnapshot(
        question_id=current.id, text=current.prompt, label=current.label, order=order,
        safety=current.requiresExplicitConfirmation,
        options=[OptionSnapshot(option_id=o.id, label=o.label, playback=o.answer,
                                is_unsure=o.is_unsure) for o in current.options],
    )
    pending = None
    answers = [answer(a) for a in state["answers"]]
    response_type = {
        "proposed_answer": "proposal", "final_playback": "review", "pause": "paused",
    }.get(state["type"], state["type"])
    review = None
    review_version = None
    receipt = None
    if state["proposal"]:
        value = state["proposal"]
        option = next(o for o in current.options if o.id == value["optionId"])
        pending = ProposalSnapshot(
            proposal_id=state["proposalId"], question_id=value["questionId"],
            option_id=value["optionId"], playback=value["answer"], is_unsure=option.is_unsure,
            origin=state["proposalOrigin"], safety=value["safety"],
        )
        stage, actions = "AWAITING_CONFIRMATION", ["confirm", "change"]
    elif state["type"] in {"pause", "support"}:
        stage, actions = "PAUSED", ["resume"]
        active = None
    elif state["type"] == "final_playback":
        stage, actions = "REVIEW", ["finalize"]
        active = None
        review_version = state["reviewVersion"]
        review = ReviewSnapshot(statements=answers, help_text=state["assistantMessage"])
    elif state["type"] == "saved":
        stage, actions = "SAVED", []
        active = None
        review_version = state["reviewVersion"]
        profile = Profile.model_validate(state["acceptedProfile"])
        receipt = ProfileSnapshot(
            profile_id=profile.id, session_id=profile.sessionId,
            catalog_version=profile.catalogVersion, review_version=review_version,
            accepted_at=datetime.fromtimestamp(profile.createdAt, timezone.utc).isoformat(),
            simulated=False,
            answers=[answer(a.model_dump(mode="json")) for a in profile.answers],
            score=profile.score,
        )
    else:
        stage = "ASKING"
        actions = ["message"] if state["canMessage"] else []
    return SessionSnapshot(
        session_id=session_id, revision=state["revision"], catalog_version=catalog.version,
        catalog_status="approved" if catalog.financeApproved and not catalog.demo else "provisional",
        state=stage, active_question=active, pending_proposal=pending,
        confirmed_answers=answers, assistant_message=state["assistantMessage"],
        response_type=response_type, allowed_actions=actions,
        review_version=review_version, review=review, receipt=receipt,
    )
