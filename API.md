# Frontend contract aligned to product spec v1.0

The group leader's PDF (section 9) replaces the earlier single `/api/conversation` proposal. The frontend now calls relative `/api/v1` routes. This is the TARGET contract: the preserved FastAPI backend currently implements `/api/conversation`, `/api/catalog`, `/health` and `/ready`. CS2 will adapt it in subsequent work. The backend teammate must agree the render fields below before integration; the PDF's snapshot was only a partial example.

The existing backend provides canonical option validation, explicit confirmation, SQLite transactions and idempotent retries under its older request/snapshot shape. See [backend/INTEGRATIONS.md](backend/INTEGRATIONS.md) for its existing Python interfaces. These implementation notes do not change the target routes below.

## Transport

- `POST /sessions`: `{request_id, expected_revision: 0}`; server generates the opaque session ID and pins its catalog. Return a snapshot with revision > 0. Creation must also be idempotent.
- `GET /sessions/{id}`: current snapshot, no inference. Used to recover after an uncertain response and before interrupting with pause/end.
- `POST /sessions/{id}/messages`: `{text, request_id, expected_revision}`.
- `POST /sessions/{id}/selections`: `{option_id, request_id, expected_revision}`; produces a proposal, never a confirmation.
- `POST /sessions/{id}/confirmations`: `{proposal_id, explicit_confirmation, request_id, expected_revision}`. `explicit_confirmation: true` is sent only after the safety checkbox. The button itself remains mandatory for every answer.
- `POST /sessions/{id}/corrections`: `{question_id, request_id, expected_revision}`.
- `POST /sessions/{id}/pause` and `/resume`: `{request_id, expected_revision}`.
- `DELETE /sessions/{id}`: JSON `{request_id, expected_revision}`. Return the common `ENDED` snapshot after clearing temporary answers and audit; the current client expects JSON, not a 204 response.
- `POST /sessions/{id}/finalize`: `{review_version, request_id, expected_revision}`. Return `SAVED` and an acceptance receipt only after the transaction succeeds.
- `GET /sessions/{id}/audit`: `{session_id, events}` below.
- `GET /profiles/{id}`: the accepted profile matching the receipt. Used only on explicit export.

All routes have `/api/v1` before the paths above. Every mutation also has `Idempotency-Key: request_id`. Exactly the same command/key is retried. Resolve duplicates before checking revisions; conflicting reuse must fail. A 409 prompts Refresh session state. A 404/410 on an existing session route disables its controls and offers a local Return to start action; a 404/410 on creation identifies an unavailable endpoint. A 422 gives safe correction guidance. Errors never expose raw backend messages or stack traces. Use `Cache-Control: no-store`.

The client sends same-origin credentials and retains IDs only in memory. The PDF does not fully specify session/profile token transport. Agree that seam with CS2: the current client uses the opaque session ID in session paths and profile ID in the export path, with any backend-issued same-origin capability cookie sent by fetch. If the backend requires a separate header/token, add it in `client.ts`; do not persist it in localStorage or introduce product authentication infrastructure. Local synthetic use only until that seam is settled.

`GET /sessions/{id}/review` from the PDF is not needed by the UI when each snapshot includes the complete versioned review. If the backend omits review content, fetch that route inside the adapter and validate the combined snapshot before rendering.

## Common snapshot

The runtime-validated source of truth is `frontend/src/api/contracts.ts` (Zod schemas plus inferred TypeScript types). Required fields:

| Field                           | Shape                                                                                                                              |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `session_id`, `catalog_version` | Nonempty strings                                                                                                                   |
| `revision`                      | Nonnegative integer, greater than mutation's expected revision                                                                     |
| `catalog_status`                | `provisional` or `approved`                                                                                                        |
| `state`                         | `ASKING`, `AWAITING_CONFIRMATION`, `REVIEW`, `PAUSED`, `ENDED`, `SAVED`                                                            |
| `active_question`               | Question below, or null                                                                                                            |
| `pending_proposal`              | Proposal below, or null                                                                                                            |
| `confirmed_answers`             | Full current answer list; no unconfirmed proposals                                                                                 |
| `assistant_message`             | Backend-supplied plain text                                                                                                        |
| `response_type`                 | `message`, `clarification`, `explanation`, `proposal`, `support`, `out_of_scope`, `fallback`, `review`, `paused`, `ended`, `saved` |
| `allowed_actions`               | Subset of `message`, `select`, `confirm`, `change`, `pause`, `end`, `resume`, `finalize`, `explain_review`                         |
| `review_version`                | Exact opaque version string in review/saved state; otherwise null                                                                  |
| `review`                        | `{statements: Answer[6], help_text: string}` or null                                                                               |
| `receipt`                       | Accepted profile below, only in SAVED; otherwise null                                                                              |
| `explanations`                  | Optional snippet array, default []                                                                                                 |
| `retention_notice`              | Optional verified server-retention wording                                                                                         |
| `findings`                      | Optional existing-detector findings `{flag, quote, explanation}[]`; no detector is implemented                                     |

A question: `{question_id, text, label, order, safety, options}`. Order is 1–6. An option: `{option_id, label, playback, is_unsure}`. Return every allowed option, including exactly one Unsure. `playback` is the exact finance-reviewed catalog text, never replacement model prose.

A proposal: `{proposal_id, question_id, option_id, playback, is_unsure, origin, safety}`. Origin is `model`, `button` or `demo`. IDs and playback must match the active question/option. `safety` comes from the catalog, not frontend inference.

An answer: `{question_id, option_id, label, playback, is_unsure, order}`. Q7 statements must exactly match the six current confirmed records. The UI sorts by order and never rewrites them. `Change an answer` focuses the per-question Edit controls, which submit `corrections`. The review's Unsure control sends a message requesting explanation, without accepting, confirming or changing any answer. These implement the PDF's Q7_B/Q7_U behaviour; they are UI controls, not invented model option IDs.

An accepted profile: `{profile_id, session_id, catalog_version, review_version, accepted_at, simulated, answers: Answer[6]}`. The receipt answers and version must match the session. Real mode rejects simulated receipts and unapproved catalogs. Exports contain only this allowlisted shape; chat and audit are separate.

A snippet: `{content_id, text, source_sheet, source_row}`. Render reviewed source text, not raw model reasoning. The question/version/approval gate belongs to retrieval and the backend. Missing explanations remain missing; do not invent them.

## Audit

`GET .../audit` returns `{session_id, events: [...]}`. Each chronological event has:

```text
event_id, at, question_id (string or null),
event_type (started | proposed | confirmed | corrected | message | paused | resumed | accepted),
raw_reply (string or null), catalog_version, retrieval_method,
snippets: Snippet[], model_action (string or null),
proposal_id (string or null), option_id (string or null),
validation_result, state_before, state_after, latency_ms,
model_id (string or null), synthetic (boolean)
```

No private reasoning traces, hidden vulnerability traits or secrets. Demo records show actual demo button events, synthetic explanations and no model call. The panel fetches only when opened, refreshes after mutations, and exports only after explicit user confirmation that the download includes messages.

## State requirements and races

Backend must enforce six confirmations, proposal ID/revision matching, question/option membership, explicit safety checks, catalog approval and exact review-version acceptance. Correction removes only the edited confirmation, clears the pending proposal and invalidates the review. Pause clears the pending proposal and review version; Resume re-asks or rebuilds review. Refusal does not become Unsure. End clears drafts/audit; it must not delete an already saved profile.

The browser serializes normal submissions. Pause/End can abort a pending fetch, discard its eventual result and reload current state before a new mutation. If the pending operation already saved, the receipt is displayed honestly. Backend per-session locking and delayed-inference revision checks remain necessary. Do not treat browser cancellation as a rollback.

The mock adapter is UI scaffolding only, not a backend implementation or a substitute for backend state, model, catalog and storage tests.

The HTTP adapter pins the first returned catalog version for each session and rejects any later snapshot with a different version. This complements the backend’s catalog pinning. Only `VITE_API_MODE=demo` or `http` is accepted; an invalid value stops startup with visible configuration guidance.
