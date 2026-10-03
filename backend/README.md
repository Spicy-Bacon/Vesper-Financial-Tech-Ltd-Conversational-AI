# Conversation backend

## Approved six-question application (Mac)

The configured oMLX path now injects `JsonCatalogProvider` and `CatalogRetriever`
from `data/catalog/catalog-v2` when both demo flags are false. The directory is
resolved from the repository location, regardless of the terminal directory.
Missing/invalid files, incomplete option metadata or missing Finance approval fail
startup clearly. No demo fallback is used. Finance scoring remains optional.

Keep `OMLX_API_KEY`, `OMLX_BASE_URL=http://127.0.0.1:8000/v1` and the exact
`OMLX_MODEL=Qwen3.5-9B-4bit` in the ignored root `.env`. From the repository root,
start oMLX in one terminal (uses the existing key without printing it):

```bash
backend/.venv/bin/python - <<'PY'
import subprocess
from pathlib import Path
from backend.app.settings import Settings
s = Settings.load()
if not s.OMLX_API_KEY:
    raise SystemExit("Configure OMLX_API_KEY in .env first.")
raise SystemExit(subprocess.call([
    "omlx", "serve", "--model-dir", str(Path.home() / ".omlx/models/mlx-community"),
    "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning",
    "--api-key", s.OMLX_API_KEY.get_secret_value(),
]))
PY
```

Then check model discovery and start FastAPI in a second terminal:

```bash
backend/.venv/bin/python -m backend.scripts.check_omlx
VESPER_MODEL_BACKEND=omlx VESPER_DEMO=0 VESPER_DEMO_CATALOG=0 VESPER_SERVE_FRONTEND=0 \
  backend/.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001 --no-access-log
```

Start the React frontend in a third terminal:

```bash
VITE_API_MODE=http npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to `http://127.0.0.1:8001`.
Only FastAPI calls oMLX; the browser receives no model key or direct model URL.
Restart Vite when changing its environment. The local `frontend/.env.local` also
selects HTTP mode; it is ignored by Git.

`/health` checks process liveness. `/ready` reports dependency wiring and the actual
demo flag; it does not prove model reachability or successful inference. Verify an
actual answer proposal, confirmation and six-answer finalize before presenting a
live demo. Local verification found the installed oMLX server aborting at startup
with an MLX/nanobind duplicate `cpu` registration error; that must be resolved for
live inference.

The importer preserves `option_label` as `label`, the explicit Excel Boolean
`is_uncertain` as `is_unsure`, and `confirmation_text` unchanged. Approval is
explicit and recorded; re-importing different output under an existing catalog
version is refused. Do not overwrite a previously published release to change
Finance wording or metadata.

FastAPI exposes the React `/api/v1` session contract, including final acceptance
and saved receipts, alongside the legacy `/api/conversation` contract.
[API.md](../API.md) describes the broader frontend contract; only the session,
message, confirmation and finalize routes are currently implemented.
Finance owns approved
question meanings, option meanings, safety requirements, points and formulas. The backend
contains no financial scoring formula.

## Run the fictional backend demo (PowerShell, from the repository root)

```powershell
python -m venv backend/.venv
& .\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt 'pydantic>=2.12,<3'
$env:VESPER_DEMO = '1'
$env:VESPER_MODEL_BACKEND = 'unconfigured'
$env:VESPER_SERVE_FRONTEND = '0'
& .\backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001 --no-access-log
```

The Pydantic minimum also satisfies the isolated model module's `pyproject.toml`.
If `python` is missing from PATH,
use the full path to your installed Python for the first command. No activation is required.
For the exact tested Windows/Python 3.13 environment, install `backend/requirements-lock.txt`
instead of the ranged development requirements.

Open **http://127.0.0.1:8001/docs** for the existing API; the demo catalog is at `/api/catalog`.
The React frontend runs separately on port 5173 in scripted demo mode. API-only hosting is now
the default. Keep `VESPER_SERVE_FRONTEND=0`: the optional legacy preview module references the
removed root web app and is not supported in this baseline.

Demo selections are exact option IDs, not natural-language interpretation:

1. `some_fluctuation` or `less_fluctuation`, then Confirm.
2. `five_plus` or `within_three`, then Confirm.
3. `essentials_covered` or `essentials_affected`, then explicitly confirm.
4. Review and save. Fictional answers are actually saved in local SQLite, marked `demo=true`.
   No financial score or classification is produced. Edit an answer to create a new accepted version.

`VESPER_DEMO` defaults to off. Without configured integrations, `/api/conversation`, `/api/catalog`
and `/ready` return 503. `/health` reports process liveness. `/ready` checks that dependencies
are wired; it does not probe model/retrieval connectivity. The real composition root should call
`create_app(catalog=..., model=..., retrieval=..., finance_policy=...)`. See
[INTEGRATIONS.md](INTEGRATIONS.md) for the proposed handoff contracts.

## Connect the provided oMLX model

The ignored root `.env` configures the server-only key, base URL and model. OS environment
variables override that file. `.env.example` documents the names with a placeholder key.
For model-assisted testing with the fictional catalog, set:

```ini
OMLX_BASE_URL=http://127.0.0.1:8000/v1
OMLX_MODEL=Qwen3.8-27B-MLX-4bit
VESPER_MODEL_BACKEND=omlx
VESPER_DEMO=0
VESPER_DEMO_CATALOG=1
```

Keep `OMLX_API_KEY` in `.env`. Run the same Uvicorn command on port 8001, without setting
`VESPER_DEMO=1`. If you previously ran the scripted demo, clear those shell overrides with
`Remove-Item Env:VESPER_DEMO,Env:VESPER_MODEL_BACKEND -ErrorAction SilentlyContinue`.
The model-assisted demo asks natural-language questions. Only suggestions are model-generated;
canonical wording, safety confirmation, final acceptance and persistence stay in the backend.
The catalog and all profiles remain explicitly fictional, with no Finance scoring.

Check reachability and the exact model ID without sending conversation text:

```powershell
& .\backend\.venv\Scripts\python.exe -m backend.scripts.check_omlx
```

oMLX normally runs on an Apple Silicon Mac. `127.0.0.1` refers to the computer running this
Python backend. If oMLX is on another computer, use a reachable hostname/IP or an authenticated
local tunnel in `OMLX_BASE_URL`. A 404 from `/v1/models` means the configured address is not
serving the expected endpoint. Keep the backend on port 8001 and oMLX on port 8000.

The adapter sends non-streaming `/v1/chat/completions`, requests JSON output, disables thinking
through `chat_template_kwargs`, and independently validates model JSON/option IDs. HTTP errors,
timeouts, oversized responses, truncated output and invalid JSON return 503; there is no scripted
fallback. It uses a 3-second connect and 12-second per-operation timeout, with no automatic HTTP
retry. First model loading may need to complete in oMLX before trying the conversation.
This thin client can be replaced by Harry/CS3 through the existing `ModelAdapter` interface.
See [oMLX's official API schemas](https://github.com/jundot/omlx/blob/main/omlx/api/openai_models.py)
and [server setup](https://github.com/jundot/omlx#quickstart).

## API and persistence

- `POST /api/conversation`: body and `Idempotency-Key` must share `requestId`.
- `GET /api/catalog`: active public question catalog, with version/approval/demo metadata.
- `GET /health`, `GET /ready`: liveness and configuration checks.

Each session pins its catalog at start and expires after one hour (configurable through
`create_app(session_ttl=...)`). Unknown sessions return 404, expired new work 410, revision/key
conflicts 409 and invalid inputs/actions 422. Exact successful retries return their original
snapshot even after the session revision advances or expires. Failed requests have no cached
success and may retry with the same key. All responses use `Cache-Control: no-store`.

The database defaults to `backend/data/profiles.sqlite3`; set `VESPER_DB_PATH` to override it.
Session state, deduplication records and immutable profile versions commit together using
SQLite `BEGIN IMMEDIATE`. Save acknowledges only after commit. A profile records the exact
accepted revision, catalog version, canonical confirmed answers and versioned Finance result
(or explicit `not_configured`). Changing an answer removes its confirmation and requires a new
final review. Historical accepted profiles remain unchanged.

This local implementation serializes writes across the database, including adapter calls.
Adapters must enforce bounded network timeouts below the frontend's 20-second timeout; SQLite
lock acquisition waits up to five seconds and returns retryable 503 on contention. This is a
low-volume local design, not a high-throughput deployment. Sessions use opaque identifiers as
local capabilities; authentication/authorization, retention/deletion and production hosting
remain separate integration work. There is no public profile-read route. Request validation
errors do not echo user input. Run without access logs as above to avoid logging URL identifiers.

## Test

```powershell
& .\backend\.venv\Scripts\python.exe -m pytest backend/tests -q
```

The historical `backend/scripts/check-demo.mjs` depends on the removed root frontend validator
and must not be used with this baseline. The Python tests cover the existing backend demo journey;
the React frontend has its own unit and browser tests at the repository root.

Tests use synthetic catalogs and policy outputs, not Finance-approved formulas. They cover API
validation, canonical proposals, explicit safety confirmation, pause/resume, revisions, key
reuse, concurrent requests, rollback, persistence across restarts, expiry, catalog pinning,
retrieval/model boundaries, correction history, scoring delegation and the complete backend demo.

Reference documentation: [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/),
[lifespan testing](https://fastapi.tiangolo.com/advanced/testing-events/), and
[Python SQLite transactions](https://docs.python.org/3/library/sqlite3.html).

## Separate model/RAG module

See [MODEL_RAG.md](MODEL_RAG.md) for the existing isolated inference module.
The conversation backend currently uses `OmlxAdapter`; this merge does not wire
the separate retrieval/interpreter service into the conversation flow.
