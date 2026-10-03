from ..errors import ConversationError, IntegrationUnavailable
from ..schemas import Answer, Catalog, ConversationRequest, Proposal, Question


def approved_catalog(catalog: Catalog, *, allow_demo: bool = False) -> Catalog:
    if (catalog.demo and not allow_demo) or (not catalog.financeApproved and not (allow_demo and catalog.demo)):
        raise IntegrationUnavailable()
    return catalog


def question_for(catalog: Catalog, question_id: str) -> Question:
    question = next((q for q in catalog.questions if q.id == question_id), None)
    if question is None:
        raise ConversationError(422, "Unknown question.")
    return question


def next_question(catalog: Catalog, answers: list[Answer]) -> Question | None:
    confirmed = {a.questionId for a in answers}
    return next((q for q in catalog.questions if q.id not in confirmed), None)


def canonical_proposal(question: Question, option_id: str) -> Proposal:
    option = next((o for o in question.options if o.id == option_id), None)
    if option is None:
        raise IntegrationUnavailable()
    return Proposal(
        questionId=question.id, optionId=option.id, label=question.label,
        answer=option.answer, safety=question.requiresExplicitConfirmation,
    )


def confirm_proposal(request: ConversationRequest, proposal: Proposal | None) -> Answer:
    if proposal is None or request.questionId != proposal.questionId or request.optionId != proposal.optionId:
        raise ConversationError(422, "Review the current proposal before confirming.")
    if proposal.safety and not request.explicitConfirmation:
        raise ConversationError(422, "This answer requires explicit confirmation.")
    return Answer(**proposal.model_dump(exclude={"safety"}))


def require_complete(catalog: Catalog, answers: list[Answer]) -> None:
    if len(answers) != len(catalog.questions) or len({a.questionId for a in answers}) != len(answers):
        raise ConversationError(422, "Confirm every question before saving.")
    for answer in answers:
        expected = canonical_proposal(question_for(catalog, answer.questionId), answer.optionId)
        if answer.model_dump() != expected.model_dump(exclude={"safety"}):
            raise ConversationError(422, "Confirmed answers do not match the approved catalog.")
