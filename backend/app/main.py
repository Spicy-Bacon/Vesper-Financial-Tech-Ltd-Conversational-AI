import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .api.catalog import router as catalog_router
from .api.conversation import router as conversation_router
from .api.frontend import mount_frontend
from .api.health import router as health_router
from .api.v1 import router as v1_router
from .adapters.omlx import OmlxAdapter
from .demo import DemoCatalog, ScriptedDemoAdapter
from .errors import ConversationError
from .interfaces import CatalogProvider, FinancePolicy, ModelAdapter, Retriever
from .repositories.profiles import ProfileRepository
from .services.conversation import ConversationService
from .services.scoring import ScoringService
from .settings import Settings


def create_app(
    *, repository: ProfileRepository | None = None, catalog: CatalogProvider | None = None,
    model: ModelAdapter | None = None, retrieval: Retriever | None = None,
    finance_policy: FinancePolicy | None = None, demo: bool = False, session_ttl: int = 3600,
    serve_frontend: bool = False, demo_catalog: bool = False,
) -> FastAPI:
    if demo and any(value is not None for value in (catalog, model, retrieval, finance_policy)):
        raise ValueError("Demo mode must use only the fictional catalog and scripted adapter.")
    if demo:
        catalog, model = DemoCatalog(), ScriptedDemoAdapter()
    elif demo_catalog:
        if catalog is not None or finance_policy is not None:
            raise ValueError("The fictional catalog cannot be mixed with a real catalog or Finance policy.")
        catalog = DemoCatalog(natural_language=True)
    repository = repository or ProfileRepository(
        os.environ.get("VESPER_DB_PATH", str(Path(__file__).resolve().parents[1] / "data" / "profiles.sqlite3")),
    )
    service = ConversationService(
        repository, catalog, model, retrieval, ScoringService(finance_policy),
        allow_demo=demo or demo_catalog, session_ttl=session_ttl,
    )

    @asynccontextmanager
    async def lifespan(app):
        repository.initialize()
        yield

    app = FastAPI(title="Vesper Conversation API", version="1.0.0", lifespan=lifespan)
    app.state.conversation = service

    @app.middleware("http")
    async def no_store(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ConversationError)
    async def conversation_error(request, exc):
        return JSONResponse(status_code=exc.status, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # FastAPI's default details include input. Keep conversation text out of error payloads.
        return JSONResponse(status_code=422, content={"detail": "Invalid conversation request."})

    @app.exception_handler(sqlite3.Error)
    async def storage_error(request, exc):
        return JSONResponse(status_code=503, content={"detail": "Storage is temporarily unavailable. Retry the same request."})

    app.include_router(health_router)
    app.include_router(catalog_router)
    app.include_router(conversation_router)
    app.include_router(v1_router)
    if serve_frontend:
        mount_frontend(app)
    return app


def create_configured_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.load()
    model = None
    if settings.VESPER_DEMO and settings.VESPER_MODEL_BACKEND == "omlx":
        raise ValueError("Choose the scripted demo or oMLX, not both.")
    if settings.VESPER_MODEL_BACKEND == "omlx":
        if not settings.OMLX_API_KEY or not settings.OMLX_MODEL:
            raise ValueError("Configure the server-side oMLX API key and model name.")
        model = OmlxAdapter(
            base_url=settings.OMLX_BASE_URL, model=settings.OMLX_MODEL,
            api_key=settings.OMLX_API_KEY.get_secret_value(),
        )
    return create_app(
        model=model, demo=settings.VESPER_DEMO, demo_catalog=settings.VESPER_DEMO_CATALOG,
        serve_frontend=settings.VESPER_SERVE_FRONTEND,
    )


app = create_configured_app()
