from typing import Annotated

from fastapi import APIRouter, Header, Request

from ..errors import ConversationError
from ..schemas import ConversationRequest, ConversationResponse

router = APIRouter(prefix="/api", tags=["conversation"])


@router.post("/conversation", response_model=ConversationResponse)
def converse(
    body: ConversationRequest, request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", max_length=128)],
) -> ConversationResponse:
    if idempotency_key != body.requestId:
        raise ConversationError(422, "Idempotency-Key must match requestId.")
    return request.app.state.conversation.send(body)
