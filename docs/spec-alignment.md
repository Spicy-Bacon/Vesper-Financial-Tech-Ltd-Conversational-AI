# Frontend alignment: product/build spec v1.0, 3 October 2026

Source: `Careful_Conversation_Product_and_Build_Spec.pdf`, supplied by the group leader. Sections 1, 3, 8–11 drive this frontend change. The PDF's section 14 whole-system agent prompt is reference material, not a separate instruction to implement teammates' work.

| Spec requirement                        | Frontend change                                                                                   |
| --------------------------------------- | ------------------------------------------------------------------------------------------------- |
| React, TypeScript, Vite                 | Migrate native JS app into frontend/; retain visual style and root npm commands                   |
| Six substantive questions; Q7 is review | Six provisional UI fixtures; live questions/options come from the backend                         |
| Confirm every answer including Unsure   | Fixed selection always creates an unconfirmed proposal; Q3–Q5 fixture safety checkboxes           |
| Refusal differs from uncertainty        | Scripted refusal offers only pause/end and never fills an answer                                  |
| Exact playback and IDs                  | Render catalog playback; confirm proposal ID; no risk score or browser financial mapping          |
| Edit/review version invalidation        | Remove edited answer immediately; backend supplies fresh proposal/review versions                 |
| Pause, resume, end                      | Backend actions; temporary state cleared only after acknowledgement; late browser replies ignored |
| Explanation/retrieval evidence          | Approved source text cards and optional chronological audit viewer                                |
| Accepted receipt and export             | Save acknowledged only by returned receipt; export fetched accepted profile explicitly            |
| Separate audit export                   | Explicit confirmation explains raw replies are included                                           |
| Port 5173 and /api proxy                | Vite proxies /api to backend 8001; model remains backend-only                                     |
| Retention honesty                       | Browser memory-only wording; no claim that the model server has no logs/caches                    |

## Still needed from teammates

1. **Finance-reviewed workbook/catalog.** No workbook was attached. Existing finance policy, precise option boundaries, Q1 bands, Q4 qualifiers, Q5 debt overlap, Q6 withdrawal meaning and reviewed explanations must not be inferred from this UI. `demo_Q…` option IDs and fixture wording are synthetic placeholders. Real saving is disabled for provisional catalogs.
2. **Backend snapshot details.** Agree the typed extensions in API.md: options, safety/Unsure fields, review statements, receipt, explanation and audit schemas, token transport. Implement /api/v1 routes and return safe fallback snapshots on model failure.
3. **Model and retention configuration.** oMLX/Qwen/OpenWebUI setup and inspection of caches/logs stay with backend/model owners. The frontend makes no claim about model availability, accuracy or storage policy.
4. **Genuine tests with people.** No usability results are fabricated. Complete the five real roleplays and approved-catalog acceptance checks before the judged demo.

The original repo had only the initial frontend prototype at inspection (`49bb7f7`); no backend routes or detector were present. No FastAPI, SQLite, RAG, model setup, classifier, authentication, infrastructure or deployment has been added in this change.

## Verification performed

- TypeScript check and production Vite build passed.
- 16 Vitest tests passed: explicit confirmations, Unsure, early-save rejection, stale proposal/review rejection, correction, safety checks, pause/resume, refusal, end, duplicate acceptance, malformed snapshots, timeout, transport failures, explicit mode validation, terminal session responses and catalog version pinning.
- 6 Playwright tests passed in installed Chrome: complete six-answer journey and export, mobile/keyboard and restart/end, HTTP retry without duplicated messages/answers, delayed HTTP reply after Pause. Audit export consent was checked separately from accepted-profile export. HTTP 404/410 recovery was verified: the user can return to start and create a new session without refreshing the browser.
- Desktop and 390px phone screenshots were visually inspected. Evidence has a bounded scroll area for long sessions.

These use the demo adapter or synthetic HTTP stubs. They do not validate a real backend, reviewed workbook, model interpretation, SQLite writes or regulatory compliance. Safari, Firefox, screen-reader testing and five genuine roleplays remain outstanding.

## Repository and branch inspection

The selected working checkout is `Documents/Hackathon-Vesper-Project/Vesper-Financial-Tech-Ltd-Conversational-AI`. After fetching every remote branch and checking GitHub’s branch heads, `origin/main` was the only available branch on 3 October 2026. Local `main` is already checked out. The frontend migration is uncommitted in this checkout; the deleted root `src/app.js`, `build.mjs` and `scripts/browser-check.mjs` are replaced by `frontend/src/App.tsx`, Vite and the Playwright tests. Teammates must publish their existing backend/model branches before those branches can be inspected or checked out.
