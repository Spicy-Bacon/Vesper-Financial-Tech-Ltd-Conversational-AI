import hashlib
import json
import time
from collections.abc import Callable
from uuid import uuid4

from ..errors import ConversationError, IntegrationUnavailable
from ..demo import ScriptedDemoAdapter
from ..interfaces import CatalogProvider, ModelAdapter, Retriever
from ..repositories.profiles import ProfileRepository
from ..schemas import (
    Action, Answer, AssistantMessage, Catalog, ConversationRequest, ConversationResponse,
    Interpretation, Profile, Proposal, RetrievedContext,
)
from .rules import approved_catalog, canonical_proposal, confirm_proposal, next_question, question_for
from .scoring import ScoringService
from ..schemas.v1 import (
    ConfirmationCommand, CorrectionCommand, FinalizeCommand, MessageCommand, SessionCommand, SessionSnapshot,
    frontend_catalog, snapshot_for,
)


class ConversationService:
    def __init__(
        self, repository: ProfileRepository, catalog: CatalogProvider | None = None,
        model: ModelAdapter | None = None, retrieval: Retriever | None = None,
        scoring: ScoringService | None = None, *, allow_demo: bool = False,
        session_ttl: int = 3600, clock: Callable[[], float] = time.time,
    ):
        if session_ttl <= 0:
            raise ValueError("Session TTL must be positive.")
        self.repository = repository
        self.catalog = catalog
        self.model = model
        self.retrieval = retrieval
        self.scoring = scoring or ScoringService()
        self.allow_demo = allow_demo
        self.session_ttl = session_ttl
        self.clock = clock

    def send(self, request: ConversationRequest) -> ConversationResponse:
        with self.repository.transaction() as db:
            return self._send(request, db)

    def _send(self, request: ConversationRequest, db, *, cache_request: bool = True) -> ConversationResponse:
        """Existing transition pipeline, with an externally owned transaction for V1."""
        fingerprint = hashlib.sha256(json.dumps(
            request.model_dump(mode="json"), sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest()
        # Replays must win over revision checks, including after a later save/edit.
        cached = self.repository.cached_request(db, request.sessionId, request.requestId) if cache_request else None
        if cached:
            if cached["fingerprint"] != fingerprint:
                raise ConversationError(409, "Idempotency key was reused with a different request.")
            return ConversationResponse.model_validate_json(cached["response"])
        now = self.clock()
        state = self.repository.load_session(db, request.sessionId)
        if state is None:
            if request.action != "start":
                raise ConversationError(404, "Session not found. Start a new conversation.")
            if request.revision != 0:
                raise ConversationError(409, "A new session must start at revision zero.")
            if self.catalog is None or self.model is None:
                raise IntegrationUnavailable()
            try:
                catalog = approved_catalog(
                    Catalog.model_validate(self.catalog.load()), allow_demo=self.allow_demo,
                )
            except ConversationError:
                raise
            except Exception as exc:
                raise IntegrationUnavailable() from exc
            state = {
                "catalog": catalog.model_dump(mode="json"), "revision": 0,
                "answers": [], "proposal": None, "type": "message", "actions": [],
                "canMessage": True, "currentQuestion": catalog.questions[0].id,
                "expiresAt": now + self.session_ttl, "profileVersion": 0,
            }
        else:
            if cache_request and state.get("apiVersion") == 1:
                raise ConversationError(422, "Use the versioned API for this session.")
            if state["expiresAt"] <= now:
                raise ConversationError(410, "Session expired. Start a new conversation.")
            if request.revision != state["revision"]:
                raise ConversationError(409, "Session revision has changed.")
            if request.action == "start":
                raise ConversationError(409, "Session already exists. Use a new session identifier.")
        catalog = Catalog.model_validate(state["catalog"])
        if not cache_request:
            frontend_catalog(catalog)
        answers = [Answer.model_validate(a) for a in state["answers"]]
        response = self._advance(request, state, catalog, answers, db, now)
        state.update(
            revision=response.revision, answers=[a.model_dump(mode="json") for a in response.confirmedAnswers],
            proposal=response.proposal.model_dump(mode="json") if response.proposal else None,
            type=response.type, actions=[a.model_dump(mode="json") for a in response.actions],
            canMessage=response.canMessage, assistantMessage=response.assistant.text,
            proposalId=str(uuid4()) if response.proposal else None,
            proposalOrigin="demo" if isinstance(self.model, ScriptedDemoAdapter) else "model",
            reviewVersion=(str(uuid4()) if response.type == "final_playback"
                           else state.get("reviewVersion") if response.type == "saved" else None),
        )
        self.repository.store_session(db, request.sessionId, state)
        if cache_request:
            self.repository.store_request(db, request.sessionId, request.requestId,
                                          fingerprint, response.model_dump_json())
        return response

    def _v1_state(self, db, session_id: str) -> dict:
        state = self.repository.load_session(db, session_id)
        if state is None or state.get("apiVersion") != 1:
            raise ConversationError(404, "Session not found. Start a new conversation.")
        if state["expiresAt"] <= self.clock():
            raise ConversationError(410, "Session expired. Start a new conversation.")
        return state

    def load_v1(self, session_id: str) -> SessionSnapshot:
        with self.repository.transaction() as db:
            return snapshot_for(session_id, self._v1_state(db, session_id))

    def send_v1(
        self, action: str, command: SessionCommand, session_id: str | None = None,
    ) -> SessionSnapshot:
        """Translate commands, then use _send/_advance in the same SQLite transaction."""
        if action not in {"start", "message", "confirm", "finalize", "change", "resume"}:
            raise ConversationError(422, "This versioned action is not implemented.")
        with self.repository.transaction() as db:
            if action == "start":
                session_id = self.repository.creation_session(db, command.request_id) or str(uuid4())
            elif session_id is None:
                raise ConversationError(404, "Session not found. Start a new conversation.")
            fingerprint = hashlib.sha256(json.dumps(
                {"api": "v1", "action": action, "session_id": session_id,
                 "command": command.model_dump(mode="json")},
                sort_keys=True, separators=(",", ":"),
            ).encode()).hexdigest()
            cached = self.repository.cached_request(db, session_id, command.request_id)
            if cached:
                if cached["fingerprint"] != fingerprint:
                    raise ConversationError(409, "Idempotency key was reused with a different request.")
                return SessionSnapshot.model_validate_json(cached["response"])
            extra = {}
            if action != "start":
                state = self._v1_state(db, session_id)
                if command.expected_revision != state["revision"]:
                    raise ConversationError(409, "Session revision has changed.")
                # Only commands actually advertised by this milestone are accepted.
                if action not in snapshot_for(session_id, state).allowed_actions:
                    raise ConversationError(422, "This action is not available in the current state.")
            if action == "message":
                assert isinstance(command, MessageCommand)
                extra["message"] = {"role": "user", "text": command.text}
            elif action == "confirm":
                assert isinstance(command, ConfirmationCommand)
                if command.proposal_id != state["proposalId"] or not state["proposal"]:
                    raise ConversationError(422, "Review the current proposal before confirming.")
                extra.update(
                    questionId=state["proposal"]["questionId"], optionId=state["proposal"]["optionId"],
                    explicitConfirmation=command.explicit_confirmation,
                )
            elif action == "change":
                assert isinstance(command, CorrectionCommand)
                if not state["proposal"] or command.question_id != state["proposal"]["questionId"]:
                    raise ConversationError(422, "Only the current proposed answer can be changed.")
                extra["questionId"] = command.question_id
            elif action == "finalize":
                assert isinstance(command, FinalizeCommand)
                if state["type"] != "final_playback" or command.review_version != state["reviewVersion"]:
                    raise ConversationError(422, "Review the current final playback before saving.")
            self._send(ConversationRequest(
                sessionId=session_id, requestId=command.request_id, revision=command.expected_revision,
                action="save" if action == "finalize" else action, **extra,
            ), db, cache_request=False)
            state = self.repository.load_session(db, session_id)
            state["apiVersion"] = 1
            result = snapshot_for(session_id, state)
            self.repository.store_session(db, session_id, state)
            if action == "start":
                self.repository.store_creation(db, command.request_id, session_id)
            self.repository.store_request(db, session_id, command.request_id, fingerprint, result.model_dump_json())
            return result

    def _advance(self, request, state, catalog, answers, db, now) -> ConversationResponse:
        actions = []
        proposal = None
        response_type = "message"
        can_message = True
        save_status = "unsaved"
        current = question_for(catalog, state["currentQuestion"])

        if request.action not in {"start", "message"}:
            allowed = any(
                action["id"] == request.action
                and (action.get("questionId") is None or action["questionId"] == request.questionId)
                and (action.get("optionId") is None or action["optionId"] == request.optionId)
                for action in state["actions"]
            )
            if not allowed:
                raise ConversationError(422, "This action is not available in the current state.")
        if request.action == "message" and not state["canMessage"]:
            raise ConversationError(422, "Review the current response before sending another message.")

        if request.action == "start":
            if catalog.demo and isinstance(self.model, ScriptedDemoAdapter):
                prefix = ("Scripted demo: use fictional circumstances and the option IDs below. "
                          "No model or Finance scoring is connected. Accepted demo answers are stored locally. ")
            elif catalog.demo:
                prefix = ("Model-assisted demo: please use fictional circumstances. "
                          "You review each proposed answer before confirming. No Finance scoring is configured. "
                          "Accepted demo answers are stored locally. ")
            else:
                prefix = "You review each proposed answer before confirming it. "
            text = prefix + current.prompt
        elif request.action == "message":
            interpretation = self._interpret(request.message.text, current, catalog, answers)
            if interpretation.kind == "proposal":
                proposal = canonical_proposal(current, interpretation.optionId)
                response_type = "proposed_answer"
                text = "Please review this proposed answer before confirming."
                can_message = False
                actions = [
                    Action(id="confirm", label="Confirm", questionId=current.id, optionId=proposal.optionId),
                    Action(id="change", label="Change answer", questionId=current.id),
                    Action(id="not_sure", label="Not sure"),
                ]
            elif interpretation.kind == "clarification":
                response_type = "clarification"
                text = current.clarification
            else:
                response_type = interpretation.kind
                text = "Take your time. You can pause here and resume when ready."
                can_message = False
                actions = [Action(id="resume", label="Resume")]
        elif request.action == "confirm":
            previous = Proposal.model_validate(state["proposal"]) if state["proposal"] else None
            answer = confirm_proposal(request, previous)
            if any(a.questionId == answer.questionId for a in answers):
                raise ConversationError(422, "Change the confirmed answer before replacing it.")
            answers.append(answer)
            upcoming = next_question(catalog, answers)
            if upcoming:
                state["currentQuestion"] = upcoming.id
                text = "Answer confirmed. " + upcoming.prompt
            else:
                answers = sorted(answers, key=lambda a: [q.id for q in catalog.questions].index(a.questionId))
                response_type = "final_playback"
                text = "Review all your confirmed answers before accepting and saving."
                if self.scoring.policy is None:
                    text += " No financial score or classification is configured."
                can_message = False
                actions = [Action(id="save", label="Accept and save"), Action(id="edit", label="Change an answer")]
        elif request.action == "change":
            current = question_for(catalog, request.questionId)
            state["currentQuestion"] = current.id
            was_confirmed = any(a.questionId == current.id for a in answers)
            answers = [a for a in answers if a.questionId != current.id]
            text = (
                "The previous confirmation has been removed. Review and accept the final answers again. "
                if was_confirmed else "The proposed answer has been discarded. Please answer again. "
            ) + current.prompt
        elif request.action == "not_sure":
            response_type = "clarification"
            text = current.clarification
        elif request.action == "resume":
            text = current.prompt
        elif request.action == "edit":
            text = "Choose a confirmed answer to change."
            can_message = False
            actions = [Action(id="change", label=a.label, questionId=a.questionId) for a in answers]
        elif request.action == "save":
            if state["type"] != "final_playback":
                raise ConversationError(422, "Review the final playback before saving.")
            score = self.scoring.score(answers, catalog)
            state["profileVersion"] += 1
            profile = Profile(
                id=str(uuid4()), sessionId=request.sessionId, version=state["profileVersion"],
                acceptedRevision=request.revision, catalogVersion=catalog.version,
                demo=catalog.demo, answers=answers, score=score, createdAt=now,
            )
            self.repository.save(db, profile)
            state["acceptedProfile"] = profile.model_dump(mode="json")
            response_type = "saved"
            save_status = "saved"
            can_message = False
            text = "Your accepted answers have been saved."
            if catalog.demo:
                text = "Your fictional demo answers have been saved locally. No financial classification was calculated."
            elif score.status == "not_configured":
                text += " No financial score or classification was calculated."
            actions = [Action(id="edit", label="Change an answer")]
        return ConversationResponse(
            sessionId=request.sessionId, revision=request.revision + 1,
            assistant=AssistantMessage(text=text), type=response_type, canMessage=can_message,
            proposal=proposal, actions=actions, confirmedAnswers=answers, saveStatus=save_status,
        )

    def _interpret(self, text, question, catalog, answers) -> Interpretation:
        if self.model is None:
            raise IntegrationUnavailable()
        try:
            context = []
            if self.retrieval is not None:
                # Copies prevent adapters from mutating the pinned catalog or confirmed state.
                raw_context = self.retrieval.retrieve(
                    text=text, question=question.model_copy(deep=True), catalog=catalog.model_copy(deep=True),
                )
                for index, item in enumerate(raw_context):
                    if index >= 10:
                        raise ValueError("Too much retrieval context.")
                    context.append(RetrievedContext.model_validate(item))
            return Interpretation.model_validate(self.model.interpret(
                text=text, question=question.model_copy(deep=True), catalog=catalog.model_copy(deep=True),
                confirmed_answers=[a.model_copy(deep=True) for a in answers], context=context,
            ))
        except Exception as exc:
            raise IntegrationUnavailable() from exc
