# Vesper team context

Updated: 4 October 2026 (Europe/London). Presentation: Sunday 4 October 2026.
Inspected branch: `main`. Inspected commit:
`38fcf212f12c675da18cacb8794a259bc862a88f` (`38fcf21`, merge of the completed application).
The working tree was clean before this documentation task. After setup, the user
authorized a local package commit on 4 October 2026; no push or merge was authorized.

No `Vesper_Team_Context_Package_v1.zip` or matching extracted folder was found in
Downloads. No existing `AGENTS.md` or `docs/ai-context` files were present. This package
uses existing repository docs and current source; it does not claim to reproduce
the unavailable ZIP. Older root README, API/spec alignment and demo-script text
contains historical or target behaviour; distinguish that from the code below.

## Product and trust boundaries

Vesper records six questionnaire answers, proposes canonical playback for each,
requires explicit confirmation and presents a final review. Q7 is a review control,
not another scored question. Final acceptance saves a profile and receipt. The
existing saved panel displays a prototype bucket and exports `accepted-profile.json`.
This is not investment advice or a validated suitability assessment.

The LLM only interprets free text into an allowed option proposal. Backend code
validates the proposal, canonical wording and confirmation; deterministic Finance
code scores confirmed IDs. SQLite persists accepted profiles. No automatic
confirmation, inferred missing answer or LLM risk-bucket decision is permitted.

## Inspected implementation

| Area | Current source behaviour | Source |
| --- | --- | --- |
| Frontend | React/TypeScript/Vite; HTTP is the adapter default. Explicit `VITE_API_MODE=demo` selects scripted fixtures. Browser `/api` traffic is proxied to port 8001; no direct oMLX call. | [client](../../frontend/src/api/client.ts), [Vite](../../frontend/vite.config.ts) |
| Real composition | With `VESPER_MODEL_BACKEND=omlx` and both demo flags false, injects `JsonCatalogProvider`, `CatalogRetriever`, configured `OmlxAdapter` and `WorkbookFinancePolicy`. Release directory is repository-relative. Invalid/missing release or approval fails startup; no demo fallback. | [main](../../backend/app/main.py) |
| Catalog | Approved, non-demo `catalog-v2` with six answer questions, separate Q7 metadata, authored labels and explicit Unsure flags. Importer preserves confirmation text and refuses different output under an existing version. | [provider](../../backend/app/catalog/provider.py), [release](../../backend/app/catalog/release.py), [importer](../../backend/scripts/import_finance_workbook.py), [catalog](../../data/catalog/catalog-v2/catalog.json) |
| Retrieval | Validated pinned catalog, approved Explanations records only, current question only, at most three snippets; Q7 is excluded from answer interpretation. Lexical/order retrieval; no embeddings. | [retrieval](../../backend/app/services/retrieval.py) |
| Model | Existing oMLX `/chat/completions` adapter requests structured JSON and validates allowed option IDs. Prompt supports paraphrases and qualitative extremes; this does not establish general accuracy. | [adapter](../../backend/app/adapters/omlx.py) |
| Conversation | Existing legacy state machine under the V1 bridge. ASKING allows message; pending proposal allows confirm/change; REVIEW allows finalize; SAVED has a receipt and no actions. Corrections only reject the current pending proposal. | [service](../../backend/app/services/conversation.py), [snapshots](../../backend/app/schemas/v1.py) |
| Persistence | Sessions, request deduplication and immutable accepted profiles commit together in SQLite. Expected revision, proposal ID and exact review version protect mutations. | [repository](../../backend/app/repositories/profiles.py) |
| Save/export | Finalize reuses legacy save. Receipt contains accepted answers and score. Export downloads the validated receipt directly, without profile lookup or chat/audit content. | [routes](../../backend/app/api/v1.py), [saved panel](../../frontend/src/components/Panels.tsx) |
| Readiness | `/health` is liveness. `/ready` reports configured catalog/model, actual demo permission and whether scoring is wired; it does not probe live inference. | [health](../../backend/app/api/health.py) |

Implemented V1 routes in [v1.py](../../backend/app/api/v1.py):

- `POST /api/v1/sessions`
- `GET /api/v1/sessions/{session_id}`
- `POST /api/v1/sessions/{session_id}/messages`
- `POST /api/v1/sessions/{session_id}/confirmations`
- `POST /api/v1/sessions/{session_id}/corrections` (current pending proposal only)
- `POST /api/v1/sessions/{session_id}/finalize`

Legacy `/api/conversation` and `/api/catalog` also remain. Do not assume a legacy
transition or a frontend/demo control is available through V1. See dated gaps in
[STATUS](STATUS.md) before selecting a journey to explore.

## Deterministic Finance scoring

[WorkbookFinancePolicy](../../backend/app/services/finance_policy.py), policy version
`team-scoring-v2`, transcribes the archived Judge_Ready workbook's approved rules.
The source is [the workbook](../../data/source/212d7a0a7649f6add4706d683539822f3d518e625164ce6e8379eef06c4fdf57/CC_Question_Set_Scored_v2_Judge_Ready.xlsx).

- Attitude: raw Q1 + Q2; scaled `(raw - 2) / 6 * 100`.
- Capacity: raw Q3 + Q4 + Q5; scaled `(raw - 3) / 9 * 100`.
- Horizon: raw Q6; scaled `(raw - 1) / 5 * 100`.
- Each dimension rounds to whole numbers, halves up. Overall is the minimum of the
  three scaled scores, not an average. All tied limiting dimensions are recorded.
- Inclusive buckets: Low 0–39, Medium 40–69, High 70–100.
- Unsure has no points: affected dimensions and overall have no numeric value,
  unresolved dimensions are recorded, and the category is `Not assigned`.
  Incomplete/missing answers cannot finalize. Never substitute zero or a middle score.
- SAVED exposes `receipt.score.classification`, `receipt.score.values`,
  `limitingDimensions` and `unresolvedDimensions`. Older saved profiles are not
  retroactively scored. Preserve this behaviour unless an explicitly claimed task changes it.

## Local run reference

See [backend run instructions](../../backend/README.md) for oMLX/key/model setup.
Keys stay in ignored server-side configuration; the selected model is configuration,
not a claim that Qwen is currently running. Do not expose key contents.

From the repository root, with the model server separately running on port 8000:

```sh
VESPER_MODEL_BACKEND=omlx VESPER_DEMO=0 VESPER_DEMO_CATALOG=0 VESPER_SERVE_FRONTEND=0 \
  backend/.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001 --no-access-log
VITE_API_MODE=http npm run dev
```

Use separate terminals. Default Vite port is 5173. Each person uses their own
checkout/processes; agree on ports if sharing one machine. Do not stop another
person's server or mutate their database. Inspect local ignored configuration;
it is not shared by Git. Keep the unsupported legacy static frontend disabled.

## Evidence boundary

This setup used Git/source/document inspection only. No application tests, browser
journeys, model calls or readiness checks were run for it. Previous session checks
are historical observations, not tonight's verification. Existing test files and
old reports may use synthetic fixtures or stub HTTP; they do not prove live Qwen
or the current browser works. Record new evidence with date, commit, mode and limitations
in a claimed task's handoff. No new bug was reproduced during this setup.
