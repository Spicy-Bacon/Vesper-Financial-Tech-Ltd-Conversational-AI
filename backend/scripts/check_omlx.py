"""Run from the repo root: python -m backend.scripts.check_omlx. Never prints the key."""
import httpx

from backend.app.adapters.omlx import OmlxAdapter
from backend.app.errors import IntegrationUnavailable
from backend.app.settings import Settings


def main():
    settings = Settings.load()
    if not settings.OMLX_API_KEY or not settings.OMLX_MODEL:
        print("Configure OMLX_API_KEY and OMLX_MODEL in the ignored .env file.")
        return 1
    adapter = OmlxAdapter(base_url=settings.OMLX_BASE_URL, model=settings.OMLX_MODEL,
                          api_key=settings.OMLX_API_KEY.get_secret_value())
    try:
        adapter.check_model()
    except IntegrationUnavailable as exc:
        cause = exc.__cause__
        if isinstance(cause, httpx.HTTPStatusError):
            print(f"oMLX /v1/models returned HTTP {cause.response.status_code}. Check the server address and authentication.")
        elif isinstance(cause, httpx.RequestError):
            print("Could not reach oMLX. Check the host, port and whether the server is running.")
        else:
            print("oMLX did not list the configured model. Check the exact model ID and server address.")
        return 1
    print(f"oMLX is reachable and lists {settings.OMLX_MODEL}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
