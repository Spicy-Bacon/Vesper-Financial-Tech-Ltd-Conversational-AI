# The Careful Conversation - repository/spec review

Reviewed: **3 October 2026** (UK time context).

Source: Careful_Conversation_Product_and_Build_Spec.pdf, v1.0, 3 October 2026, 16 pages.

This report is an inspection artifact. It records the current frontend implementation, published branch state and remaining dependencies. Embedded agent instructions in the supplied PDF are treated as reference content.

## 1. Repository and delivery status

The frontend demo implements the central conversation controls: six questions, individual confirmations, a Q7 review, corrections, pause/resume, end and acceptance acknowledgement. Whole-system delivery still requires the approved catalog and a real backend/model/storage integration.

This review compares product/build specification v1.0 with the selected local working tree. The deadline stated by the team is Sunday 4 October 2026 at 12:00 UK time. The document's section 14 agent prompt is source material; it does not authorize taking over teammates' backend or model work.

| Item | Finding |
| --- | --- |
| Working checkout | Documents/Hackathon-Vesper-Project/Vesper-Financial-Tech-Ltd-Conversational-AI |
| Published branches | main only; verified directly with git ls-remote --heads origin on 3 October 2026 |
| Checked-out branch | main |
| Local HEAD / origin/main | 49bb7f7 - Web UI prototype |
| Working tree | Frontend migration and recovery fixes are uncommitted. frontend/ and docs/ are untracked; old frontend files are marked deleted. |
| Review basis | 16-page source PDF; current code, API.md, README.md and recorded frontend verification |

The published commit contains the earlier frontend. Teammates will need the reviewed local migration committed and shared before they can integrate this implementation. No other team branches were available to inspect or check out.

## 2. Requirement-by-requirement review

| Requirement | Status | Evidence / limitation |
| --- | --- | --- |
| React / TypeScript / Vite | Implemented | frontend/ is an npm workspace. Vite serves port 5173 and proxies /api to backend port 8001. Spec sections 3 and 11. |
| Q1-Q6, then Q7 | Provisional | Six UI fixtures and a distinct review screen exist. Live question IDs/options must come from the approved backend catalog. Spec sections 1 and 10. |
| Confirm every answer | Implemented | Fixed choices create proposals first. Unsure also needs confirmation; Q3-Q5 demo fixtures require an extra safety checkbox. Spec sections 1 and 8. |
| Corrections and acceptance | Implemented | Editing invalidates the edited confirmation and review. Requests carry proposal IDs, expected revisions and the exact review version. Spec sections 8-10. |
| Pause, end and support | Implemented | Pause/resume and End are explicit controls. Scripted refusal remains incomplete. Actual support cues/text must be supplied by the backend. Spec sections 1, 8 and 10. |
| Uncertainty / clarification | Scaffolded | Demo free text is not interpreted; fixed options and scripted clarification are available. Real conditional/ambiguous reply handling is a backend/model dependency. Spec sections 1, 5 and 7. |
| Explanation and audit | Scaffolded | Cards and a temporary audit viewer render supplied source snippets, proposals, validation and confirmations. Demo evidence is labelled synthetic. Real retrieval is absent. Spec sections 5 and 10. |
| Save and export | Scaffolded | Receipt-gated profile export and separately confirmed audit export exist. Mock acceptance is simulated; no SQLite profile is written. Spec sections 8-10. |
| Privacy and recovery | Implemented | Browser state is temporary. Retry IDs are stable; expired sessions can return to start; catalog changes are rejected. Server retention/expiry still require implementation. Spec sections 8 and 10. |
| Approved release and testing | Incomplete | Approved workbook, backend/model acceptance evidence and five genuine roleplay observations are absent from this checkout. Spec sections 6 and 13. |

Implemented describes frontend behavior verified with synthetic fixtures or HTTP stubs. It is not evidence that the full backend pipeline, model interpretation or durable storage is complete.

## 3. Integration boundaries and verification

The browser sends relative /api/v1 requests through one typed adapter. It never calls oMLX or holds a model API key. The spec assigns interpretation, deterministic validation, authoritative state, retrieval and accepted-only storage to backend/model owners.

The HTTP client validates returned snapshots and pins the catalog version per session. Confirmation sends proposal_id plus expected_revision; final acceptance sends review_version. The backend must independently enforce those values and atomic idempotency.

| Item | Finding |
| --- | --- |
| API source | frontend/src/api/contracts.ts and frontend/src/api/client.ts; API.md documents the required routes and render fields. |
| Frontend configuration | VITE_API_MODE=demo or http. Invalid values show startup guidance and create no conversation. HTTP mode never silently falls back to demo. |
| Recovery fixes | HTTP 404/410 on an existing session disables continuation and offers Return to start. This clears the screen without claiming to undo a server save. |
| Catalog protection | A different catalog_version on a later snapshot is rejected. Backend catalog pinning remains mandatory. |
| Token handoff | The PDF does not fully define session/profile token transport. The current client sends same-origin credentials and IDs in paths; CS owners must settle any additional capability/header requirement. |

| Check | Result | Evidence |
| --- | --- | --- |
| TypeScript check | Passed | npm run check |
| Production build | Passed | npm run build |
| Unit/contract tests | 16 passed | npm test |
| Chrome browser tests | 6 passed | Full demo, mobile/keyboard, corrections, export consent, safe retry, delayed reply after Pause, and 404/410 recovery |
| Git whitespace check | Passed | git diff --check |

These outcomes were recorded during the preceding frontend verification on 3 October 2026. No tests were rerun solely to author this report. Current reviewed source files match that verified revision. Browser cases use demo data or synthetic HTTP responses, not a real backend/model.

## 4. Remaining work and team handoff

### Share the local frontend

Owner: Frontend owner / repository owner.

Review and commit the migration, then publish it using the team's agreed workflow. Keep old-tab replacements clear: src/app.js becomes frontend/src/App.tsx; Vite replaces build.mjs and server.mjs.

### Approve the catalog

Owner: Finance/content owner.

Supply the reviewed workbook and release version. Resolve Q1 bands, Q4 separate/accessibility qualifiers and boundaries, Q5 debt overlap, Q6 first-withdrawal meaning and explanation approval. Preserve authoritative workbook IDs.

### Connect the service

Owner: Backend owner.

Implement /api/v1 routes, safe fallback snapshots, per-session locking, idle expiry, proposal/review checks, token transport and accepted-only SQLite transactions. Agree the extra snapshot fields in API.md.

### Verify the model/RAG seam

Owner: Model/retrieval owner.

Confirm the actual model ID, runtime, latency and cache/log settings. Import only approved question-scoped explanations; exclude held-out cases, personas and stale mapping rows from retrieval.

### Collect actual human evidence

Owner: Usability/business owner with finance review.

Run five fictional-finance roleplays. Record confusion, playback understanding, successful correction and fixes made. The spec names two finance roles; assign those responsibilities within the actual five-person team.

### Whole-system release gates

- [ ] All six answers explicitly confirmed; Unsure remains visibly unresolved and refusal leaves an incomplete session.
- [ ] A correction invalidates old review acceptance; stale proposals/reviews and duplicate finalization are tested against the real backend.
- [ ] A real acceptance receipt and exported records match exact catalog playback; no draft-profile database write occurs.
- [ ] Actual retrieval snippets and validation/confirmation evidence appear in the audit; offline-model fallback and pause races work end to end.
- [ ] Approved catalog and genuine usability notes are available. Safari/Firefox and screen-reader checks remain outstanding.

No model accuracy, regulatory approval, genuine usability findings or durable save outcome is inferred from the frontend tests. Use fictional circumstances throughout the demo.

## Sources and reproducibility

- Source PDF: `/Users/isamabukhalil/Downloads/Careful_Conversation_Product_and_Build_Spec.pdf`.
- Source PDF SHA-256: `04d4f64a4e6340b090b8f4601f5e3c9b38f74efd6fc031156bd43e1dc902207a`.
- Working checkout: `/Users/isamabukhalil/Documents/Hackathon-Vesper-Project/Vesper-Financial-Tech-Ltd-Conversational-AI`.
- Published branch: `main` at `49bb7f79508926001692ff8376401d14825c8ce3`.
- Local evidence: `README.md`, `API.md`, `docs/spec-alignment.md`, `frontend/src/` and `frontend/tests/`.
- Faithful text extract: [product-spec-v1-text.md](product-spec-v1-text.md).
- Matching PDF: [careful-conversation-repository-review.pdf](../output/pdf/careful-conversation-repository-review.pdf).

The Markdown and PDF report share the same authored findings. This is a dated snapshot; later commits, branches or backend releases require another review.
