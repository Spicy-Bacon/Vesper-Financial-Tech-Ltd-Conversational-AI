# The Careful Conversation

Frontend for the Vesper hackathon, updated against **Careful Conversation Product and Build Spec v1.0 (3 October 2026)**. React + TypeScript + Vite, with npm workspaces. The existing calm visual style is retained. There is no backend, model runtime, approved workbook or detector in this checkout.

## Run

Use Node.js 22.12+ and npm. From the repository root:

```sh
npm ci
npm run dev
```

Open http://127.0.0.1:5173. Default mode is visibly labelled **Scripted demo**. Only `demo` and `http` are valid modes; a typo displays a configuration error and sends no conversation requests. All content is synthetic and provisional. Free text is not interpreted by a model; use the fixed options to complete the demo.

```sh
npm run check         # TypeScript
npm test              # Contract and mock-adapter tests
npm run build         # frontend/dist; suitable for FastAPI static serving
npm run test:browser  # Playwright; requires installed Google Chrome
```

Browser tests start isolated Vite instances on ports 5173 and 5174 and use isolated Chrome profiles. Close existing servers on those ports first. They use synthetic data and stub HTTP responses; they do not prove that a real backend/model works. Playwright screenshots go to the macOS temporary directory. Safari, Firefox and screen-reader verification remain manual.

## What is implemented

- Start, Q1–Q6 conversation and fixed options, approved-text explanation rendering, proposal confirmation, Q7 review, per-answer editing, Pause/Resume, End and acceptance receipt.
- Every option, including Unsure, requires explicit confirmation. Q3–Q5 require an extra checkbox. Unsure stays visibly unresolved in the review; refusal leaves the session incomplete.
- Proposed, confirmed and accepted records stay distinct. Corrections remove the edited confirmation and old review; Pause clears unconfirmed proposals; resume re-asks or rebuilds review.
- Versioned `/api/v1` adapter: request IDs, expected revision, proposal IDs and exact review versions. Retries reuse the same request without duplicating messages. Pause/End can interrupt a pending request; stale browser replies are discarded.
- Temporary audit panel with separate raw reply, retrieved snippets, model action, validation and confirmation fields. Demo events are labelled synthetic and show no live model call.
- Accepted-profile export only after a receipt, with simulated exports clearly named. Audit export is a separate explicit action with a warning that it includes messages.
- Keyboard controls, native confirmation dialogs, mobile layout, in-memory state and no analytics or conversation logging.

## Connect your teammate's FastAPI service

Copy `frontend/.env.example` to `frontend/.env.local`, set `VITE_API_MODE=http`, and restart Vite. Run FastAPI on port **8001**; Vite proxies `/api` to that port. The browser never calls the model server (oMLX on port 8000 in the team plan).

[API.md](API.md) documents the exact frontend contract. The PDF supplies routes and a partial snapshot; [frontend/src/api/contracts.ts](frontend/src/api/contracts.ts) defines the additional render fields that the backend teammate must agree and return. Use `allowed_actions` and the returned snapshot as the source of truth. No model credentials belong in Vite variables.

The backend must enforce state transitions, proposal/review matching, atomic idempotency, catalog approval, session expiry and accepted-only persistence. A frontend pause cancels a fetch but cannot undo server work. The UI reloads session state before sending pause/end; the backend must still reject stale mutations and discard delayed model output. Saved profiles remain saved when the screen is restarted.

The live adapter accepts a real save only with a matching receipt and approved catalog. It does not fall back to demo responses when the backend is unavailable. Fixed-option fallback must be returned in a valid snapshot by the backend when model inference fails. For transport failure, Retry or Refresh session state first to avoid using an unknown revision. Missing or expired sessions have a local Return to start action. That clears the screen without pretending to delete server data or undo a save. A catalog-version change within a session is rejected and also requires a fresh start.

## Provisional content and remaining handoff

The approved workbook is not present. `frontend/src/api/fixtures.ts` contains six **UI development placeholders**, not reconstructed workbook policy. Q1–Q6 question IDs are preserved, while option IDs are explicitly namespaced `demo_Q…` so they cannot be mistaken for finance-approved options. Replace these only through the backend's approved catalog release; the live UI has no hardcoded financial mapping or risk calculation.

See [docs/spec-alignment.md](docs/spec-alignment.md) for scope, missing decisions and changes from the first frontend. The PDF's whole-system paste-ready implementation prompt was not treated as authority to build the backend or model service. [docs/demo-script.md](docs/demo-script.md) gives a short walkthrough.

No real usability sessions, model accuracy, regulatory compliance, actual saves or model-server retention have been verified. The prototype uses fictional circumstances throughout.
