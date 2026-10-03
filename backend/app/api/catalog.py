from fastapi import APIRouter, Request

from ..errors import ConversationError, IntegrationUnavailable
from ..schemas import Catalog
from ..services.rules import approved_catalog

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/catalog", response_model=Catalog)
def get_catalog(request: Request) -> Catalog:
    service = request.app.state.conversation
    if service.catalog is None:
        raise IntegrationUnavailable()
    try:
        return approved_catalog(Catalog.model_validate(service.catalog.load()), allow_demo=service.allow_demo)
    except ConversationError:
        raise
    except Exception as exc:
        raise IntegrationUnavailable() from exc
