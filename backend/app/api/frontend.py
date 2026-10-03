"""Optional local same-origin preview of the existing frontend."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles


def mount_frontend(app: FastAPI) -> None:
    root = Path(__file__).resolve().parents[3]

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(root / "index.html")

    @app.get("/src/config.js", include_in_schema=False)
    def public_configuration():
        return Response(
            "export const config = {mode: 'http', endpoint: '/api/conversation', timeoutMs: 20000};",
            media_type="text/javascript",
        )

    app.mount("/src", StaticFiles(directory=root / "src"), name="frontend-assets")
