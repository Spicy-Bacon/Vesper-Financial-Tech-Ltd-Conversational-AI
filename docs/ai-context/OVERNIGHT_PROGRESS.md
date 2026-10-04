# Presentation preparation handoff — VP-001

Morning authorization update (4 October 2026): user requested commit and push on
`feature/harry-demo-polish`; no merge. The status and restrictions below record
the overnight snapshot before that authorization. Consult Git for the resulting commit.

Updated 4 October 2026, 03:28 BST (Europe/London).
**Ready for review/integration; all changes uncommitted and unstaged.**
No commit, push, merge, publication, duplicate tunnel or dependency installation.

## Checkout and ownership

- Directory: /Users/harry/GitHub/Vesper-Financial-Tech-Ltd-Conversational-AI
- Branch: `feature/harry-demo-polish`
- Inspected base/HEAD: `d3de1acd2e0ff0db4d8c1a915c597efa9a77e60e`
- Initially clean; no other reservations or newer teammate handoffs found.
- User explicitly authorized this cross-component task. Harry's integration session
  records shared status/decisions. General teammate split remains proposed.
- Read AGENTS, TEAM_CONTEXT, STATUS, DECISIONS and HANDOFF_TEMPLATE before edits.
  Original context `38fcf21` and exploration `503af22` are historical.

## Completed failures and original reproductions

| Failure | Original reproduction/result | Final observed result |
| --- | --- | --- |
| Q3 meaning | “It would have no effect on my normal spending or plans. This is fully surplus money.” produced Q3_C. | Actual Qwen, API and browser produce Q3_D. Missing effects on plans and contradictory plans clarify. |
| Support dead end | Q1 bereavement/panic/person request paused with disabled Resume. | Browser pauses with usable Resume/End and explicitly says no person can be contacted by this prototype. Resume restores Q1 without confirmation. Real Qwen also handles distress without a human request. |
| Pause failure | Confirm Q1 Unsure, then Pause at Q2: session-unavailable. | Live API preserves Q1 Unsure and restores Q2; browser preserves confirmed answers at Q2. Pending proposal and final-review restoration also checked. |
| Review correction/help | Six confirmations, then disabled Edit/help. | Browser help stays unsaved, Pause/Resume restores review; Edit Q6 removes only its confirmation and requires reconfirmation/new review. API rejects stale review acceptance; typed yes never saves. |
| Evidence unavailable | Open evidence after support: session-unavailable/no records. | Browser shows actual support and Q3 replies, snippets/provenance, actions, transitions and measured latency. Missing evidence no longer implies session loss. Successful replay adds no event. |

Additional issue reproduced during this journey: Q6 three years proposed the wrong
band after review correction. Conservative exact-duration filtering reads bounds
from canonical authored options and retains model proposal/clarification/support/pause.
Actual Qwen checked three/five/ten/seven-year boundaries. Final browser proposed
Q6_D for three years. Catalog and Finance policy were not changed.

## Exact files changed

| Files | Purpose |
| --- | --- |
| `backend/app/adapters/omlx.py` | Compact current-question prompt/payload; literal allowed output schema; semantic support check only for catalog safety questions; source-derived exact-duration bounds. Existing client reused. |
| `backend/app/api/v1.py` | Existing-state-machine pause/resume/end routes and audit GET. |
| `backend/app/schemas/__init__.py`, `backend/app/schemas/v1.py` | Actions, audit/retention contract, PAUSED/REVIEW/ENDED snapshots. |
| `backend/app/services/conversation.py` | Restore question/proposal/review; correction/help; bounded evidence after transaction commit. Preserve revision/retry/acceptance and immutable accepted history. |
| `backend/app/services/retrieval.py` | Preserve actual snippet sheet/row/method. Ranking/filtering unchanged. |
| `frontend/src/App.tsx` | Support/restoration/end text; truthful SQLite and start-control wording. |
| `frontend/src/api/client.ts`, `frontend/src/api/contracts.ts`, `frontend/src/components/Panels.tsx` | Separate evidence errors from session loss; render provenance/retention. Receipt export retained. |
| `backend/tests/test_api_v1.py`, `backend/tests/test_omlx.py`, `frontend/tests/adapter.test.ts` | Focused transition/stale-ID/retry/retention/guard/duration/error regressions. |
| `docs/ai-context/STATUS.md`, `docs/ai-context/DECISIONS.md`, `docs/ai-context/OVERNIGHT_PROGRESS.md` | Registry, decisions and morning handoff. |

## Verification — separate evidence types

### Source inspection

Approved Q3 D/C and EX04/EX05 were correct before edits. Original full payload
returned Q3_C directly from model JSON before frontend/backend transformation.
oMLX advertised context 2,000; prompt/payload simplification improved results.
Truncation was not proven as the sole cause.

Finance formulas, points, catalog/approval/version, question-scoped retrieval,
SQLite schema and accepted-profile immutability remain unchanged. No Q7/scoring
rules added to model context. Browser calls /api via Vite, never oMLX directly.

### Stub/mock and contract checks actually performed

From repository root, except npm commands from frontend:

- `backend/.venv/bin/python -m pytest backend/tests/test_api_v1.py backend/tests/test_conversation.py backend/tests/test_omlx.py -q`
  — first coherent service/API fix: **94 passed**.
- `backend/.venv/bin/python -m pytest backend/tests/test_api_v1.py backend/tests/test_omlx.py -q`
  — after compatibility/duration regressions: **89 passed**.
- `backend/.venv/bin/python -m pytest backend/tests/test_omlx.py -q`
  — final adapter regression code: **40 passed**.
- `npm test -- tests/adapter.test.ts` — **16 passed** before added evidence-error case.
- `npm test -- tests/adapter.test.ts -t "does not treat unavailable evidence"`
  — new assertion **1 passed, 16 skipped**.
- `npm run check` — passed, including final start-screen wording change.
- `git diff --check` — passed; staged diff empty.
- Required context files and all AGENTS/context Markdown relative links — passed.
- Final reachability: local frontend, backend `/ready` and existing public URL
  returned 200; `/ready` reports configured, demo false, financeScoring true.
  Reachability supplements the actual journey evidence, not a substitute for it.

Covered question/proposal/review pause, stale IDs, correction/yes/save retries,
accepted history, older V1 drafts, support/end, audit restart/expiry/no durable raw
reply, malformed output/semantic guard and exact/ambiguous/negated/age durations.
Starlette deprecation warning observed; no dependency changes. No broad suite,
production build or usability study.

### Actual Qwen and live API

Listed model and actual completion metadata: **Qwen3.5-9B-4bit**.
Real approved catalog-v2 / WorkbookFinancePolicy; demo flags false; existing oMLX.

Final real-model matrix passed maximum-loss Q1_D, wealth-only clarification,
conflicting loss amounts clarification, exact Q3_D, missing-plans clarification,
contradictory-plans clarification, distress support and five-year Q6_E.
Actual boundary check passed three=D, five=E, ten=F, seven=E.
These are observed examples, not general accuracy.

`PYTHONPATH="$PWD" backend/.venv/bin/python /private/tmp/vesper-live-verification.py`
exited 0 against final backend PID 31621. Verified Q1/Q3 cases, Q1 Unsure through
Q2 Pause/Resume, Q4 D/Q5 D/Q6 E, real EX04/EX05 audit, identical request replay
with unchanged snapshot/events, typed yes unsaved, Q3 edit/reconfirmation, stale
finalize 422, explicit acceptance and receipt/SQLite equality. Distress without
an explicit support request paused and resumed safely.

Unsure profile `fb6c49c1-38d7-4250-b26d-bc5d6b95bb96`;
session `9824c6cd-2c78-408e-83be-34d5d2aeabc8`.
Q1_U/Q3_U: attitude/capacity unresolved, horizon 80, no overall, **Not assigned**.
Temporary artifact: /private/tmp/vesper-live-unsure.json.

### Actual Safari browser through existing public URL

Fresh final-runtime flow: Q1 £1,000=C; Q2 hold=C; exact reported Q3=D;
Q4 twelve months accessible savings=D; Q5 mortgage only=D; Q6 seven years=E.
Checked each displayed proposal; safety questions required checkbox confirmation.
Help kept review unsaved; Pause/Resume restored six confirmations/review.
Edited Q6 to “Actually, I may need it in three years.” → D; explicitly reconfirmed.

Evidence displayed exact Q3 reply, EX04/EX05 from Explanations rows 5/6,
proposal Q3_D, ASKING→AWAITING_CONFIRMATION, model ID, **3,299.68 ms total turn**.
Clicked **Accept and save these answers**. Display: attitude 67, capacity 100,
horizon 60, overall 60, **Medium**.

Downloaded /Users/harry/Downloads/accepted-profile-4.json.
Profile `837c9001-8c17-49ed-9ad5-1a1bcb7b1667`;
session `fbbf06fe-a622-4cab-a5da-09df572af43e`.
Read-only comparison passed: export exactly equals live SAVED receipt; canonical
answers and score equal SQLite profile; limiting dimension horizon; no unresolved
dimensions; simulated false. 20 actual audit events ended with acceptance.

Separate fresh browser tested exact human-support request. PAUSED with Resume/End,
honest support wording, actual support evidence (model, **2,244.52 ms total turn**),
Resume to Q1 with zero confirmations, explicit End → ENDED.
Final wording change was type-checked and observed through HMR; current tab is at start.

## Failed approaches and truthful limits

- Extra prompt prose with duplicate options/clarification still misclassified Q3;
  reasoning mode returned invalid JSON. These are failures, not accuracy evidence.
- Nullable schema biased/added option fields; final literal allowed objects plus
  strict backend validation used. Runtime grammar enforcement not established.
- Guarding all questions rejected valid Q1 bands/extremes; final semantic support
  check uses existing safety metadata only. It rejects unsupported meanings,
  chooses no replacement and adds a second call on those questions.
- Generic clarification guidance changed a clear Q1 result; final payload includes
  short guidance only when exact-duration filtering applies. Numeric prompt examples
  alone still failed boundaries. Authored-bound filtering only handles unambiguous
  exact duration; wider semantic accuracy remains unproven.
- Audit: successful committed turns only; last 100 turns/session, 100 sessions,
  one process; expires with session and disappears on restart/end/eviction.
  SQLite drafts/retries/profiles remain durable. End is not physical purge.
- Browser reload/HMR loses in-memory session handle. UI reload recovery is deferred;
  avoid refreshing during a presentation conversation.
- Older profiles are not rescored; selection/profile lookup remain outside scope.
  Wider access control/security and model-server cache/log retention not audited.
- No staffed support, five-person usability findings, general accuracy, regulatory
  compliance or full judging-document compliance claimed.

## Running services and exact startup commands

Final inspected services serve this checkout, listening on loopback:

| Service | PID / port | Working directory |
| --- | --- | --- |
| Frontend | 30040 / 5173 | repository frontend/ |
| Backend | 31621 / 8001 | repository root |
| Existing oMLX | 28025 / 8000 | / (untouched) |
| Existing cloudflared | 29105 → 5173 | existing tunnel, no duplicate |

Local: http://127.0.0.1:5173
Public: https://pray-proved-bacterial-rochester.trycloudflare.com
Public frontend/proxied API used for actual browser checks.

Already running. If the application needs restarting, use separate terminals.
Existing ignored server .env supplies credentials/model; no key belongs in browser:

```sh
cd /Users/harry/GitHub/Vesper-Financial-Tech-Ltd-Conversational-AI
VESPER_MODEL_BACKEND=omlx VESPER_DEMO=0 VESPER_DEMO_CATALOG=0 VESPER_SERVE_FRONTEND=0 \
  backend/.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001 --no-access-log
```

```sh
cd /Users/harry/GitHub/Vesper-Financial-Tech-Ltd-Conversational-AI/frontend
VITE_API_MODE=http /opt/homebrew/bin/npm run dev
```

No need to restart oMLX or start another tunnel. Quick-tunnel URL is temporary.

## Seven-minute fictional presentation

1. Start; explain Qwen proposes canonical answers and the user confirms.
2. Reply £1,000 comfortable loss; hold investment; exact no-impact Q3;
   twelve months accessible savings; mortgage only; seven-year horizon.
3. Show Q3 safety checkbox and evidence (reply, EX04/EX05, action/option).
4. Pause/Resume. At review, Edit Q6 to three years and reconfirm.
5. Explicitly accept/save; show Medium 60 and export receipt JSON.
6. If time permits, separate support example; explain Unsure means unresolved/
   Not assigned, never zero.

## Integration requirements and next action

Review/apply the uncommitted branch diff together: Python routes/action/snapshot/
evidence schemas match TypeScript contract/UI. No dependency, DB migration, catalog
release or Finance policy changes. Restart backend after integration; frontend
HTTP mode/proxy required. Recheck relevant journeys if integration changes their code.

No unfinished implementation or blocked code. VP-001 reservations retained until
Harry reviews/integrates or releases. Next action: **review diff and present using
running product**. No automatic commit/push/merge. Reload recovery and wider model
evaluation remain deferred.
