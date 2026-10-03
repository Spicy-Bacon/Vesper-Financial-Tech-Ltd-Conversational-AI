# Frontend integration checks

Run from the repository root:

```sh
npm ci
npm run check
npm test
npm run build
npm run test:browser
```

Default browser tests retain the existing demo and intercepted HTTP projects.
They require Google Chrome and free ports 5173/5174, but no backend.

## Manual HTTP mode

```sh
VITE_API_MODE=http npm run dev
```

Open http://127.0.0.1:5173. Vite proxies `/api` to FastAPI at
http://127.0.0.1:8001. Start the backend separately using CS2's agreed setup.
The frontend never connects to oMLX on port 8000. Alternatively set
`VITE_API_MODE=http` in `frontend/.env.local` and restart Vite.

## Opt-in real backend smoke test

The test starts its own HTTP-mode Vite on 5173 by default. If that port is
occupied, use `LIVE_HTTP_PORT` to choose a free port without stopping the existing
server. The test uses the real proxy and does not start or reconfigure FastAPI/oMLX.
It never intercepts requests or falls back to the demo adapter.

Configure these variables with CS2/CS1's agreed **fictional** first-question
test case. There are deliberately no guessed answers or demo option IDs:

| Variable                | Meaning                                                                          |
| ----------------------- | -------------------------------------------------------------------------------- |
| `LIVE_QUESTION_ID`      | Expected first active question ID                                                |
| `LIVE_ANSWER`           | Fictional free-text input agreed to yield a model proposal                       |
| `LIVE_OPTION_ID`        | Expected catalog option ID for that input (Unsure is valid)                      |
| `LIVE_AMBIGUOUS_ANSWER` | Optional agreed input that must yield clarification before `LIVE_ANSWER` is sent |

After exporting those variables, run:

```sh
npm run test:browser --workspace frontend -- --project=live-http
```

Alternate frontend port (if 5175 is free):

```sh
LIVE_HTTP_PORT=5175 npm run test:browser --workspace frontend -- --project=live-http
```

`LIVE_HTTP_PORT` must be a decimal integer from 1 to 65535, without whitespace
or leading zeros. Empty, fractional, nonnumeric and out-of-range values fail
before Vite starts. The override applies consistently to the live project's
base URL, Vite command and readiness URL; it is ignored by default demo/mocked
runs. It changes only the frontend port: `/api` still proxies to port 8001.

`--project live-http` also works. This explicit selection is required: ordinary
runs do not register the live project. Use `--list` to inspect discovery without
contacting the backend. The live run requires Chrome and a free selected port.

The test checks HTTP mode, Zod-valid snapshots, IDs/revisions and idempotency
headers, question rendering, optional clarification, free-text model proposal,
unconfirmed UI and authoritative GET state, safety checkbox when required,
explicit confirmation, one confirmed answer and the next question. A
clarification/fallback from `LIVE_ANSWER` fails rather than counting as success.
Without `LIVE_AMBIGUOUS_ANSWER`, clarification coverage is explicitly annotated
as not exercised. This is a smoke check, not a guarantee of model determinism.

Unavailable `/api/v1` endpoints, malformed snapshots and missing input
configuration fail; they are never skipped. Diagnostics contain stage/status
and schema paths rather than request text or response bodies. Traces, screenshots
and video are disabled for the live project. Only use fictional data, including
in local failure artifacts. The test does not finalize or save a profile; its
temporary session is left for backend expiry.

CS2 must return the snake_case, unwrapped `SessionSnapshot` defined in
`src/api/contracts.ts`, start at revision > 0, increase revisions on mutation,
resolve duplicates before revision checks, pin the catalog, and supply matching
proposals/options plus appropriate `allowed_actions`. The smoke requires POST
session, messages, confirmations and GET session. The remaining frontend flow
also needs selections, corrections, pause/resume, finalize, audit, profile reads
and JSON DELETE responses (not 204), as documented in the root `API.md`.
The current adapter needs no extra token header; any capability cookies must
work through the same-origin Vite proxy. Its 35-second request budget is unchanged.
