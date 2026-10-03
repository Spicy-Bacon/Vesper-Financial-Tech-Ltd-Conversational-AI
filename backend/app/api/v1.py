"""First integration milestone; the legacy conversation API remains available."""
from typing import Annotated

from fastapi import APIRouter, Header, Request

from ..errors import ConversationError
from ..schemas.v1 import ConfirmationCommand, MessageCommand, SessionCommand, SessionSnapshot

router = APIRouter(prefix="/api/v1", tags=["sessions-v1"])
Key = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)]


def check_key(body: SessionCommand, key: str) -> None:
    if key != body.request_id:
        raise ConversationError(422, "Idempotency-Key must match request_id.")


@router.post("/sessions", response_model=SessionSnapshot)
def create_session(body: SessionCommand, request: Request, idempotency_key: Key):
    check_key(body, idempotency_key)
    return request.app.state.conversation.send_v1("start", body)


@router.get("/sessions/{session_id}", response_model=SessionSnapshot)
def get_session(session_id: str, request: Request):
    return request.app.state.conversation.load_v1(session_id)


@router.post("/sessions/{session_id}/messages", response_model=SessionSnapshot)
def message(session_id: str, body: MessageCommand, request: Request, idempotency_key: Key):
    check_key(body, idempotency_key)
    return request.app.state.conversation.send_v1("message", body, session_id)


@router.post("/sessions/{session_id}/confirmations", response_model=SessionSnapshot)
def confirm(session_id: str, body: ConfirmationCommand, request: Request, idempotency_key: Key):
    check_key(body, idempotency_key)
    return request.app.state.conversation.send_v1("confirm", body, session_id)
