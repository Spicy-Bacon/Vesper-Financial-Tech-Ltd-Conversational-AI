from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request):
    from ..errors import IntegrationUnavailable

    service = request.app.state.conversation
    if service.catalog is None or service.model is None:
        raise IntegrationUnavailable()
    return {"status": "configured", "demo": service.allow_demo, "financeScoring": service.scoring.policy is not None}
