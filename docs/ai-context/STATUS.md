# Session status and task registry

Date: 4 October 2026, Europe/London. Presentation: Sunday 4 October 2026.
Morning authorization update: the user subsequently requested **commit and push**
of VP-001 on `feature/harry-demo-polish`. This supersedes the overnight prohibition
on those actions. No merge is authorized. Uncommitted references below describe
the overnight handoff snapshot; use Git history for the resulting commit.
Current inspected branch/base: `feature/harry-demo-polish` at
`d3de1acd2e0ff0db4d8c1a915c597efa9a77e60e`. Initially clean; VP-001 changes are
uncommitted and unstaged. User authorized cross-component presentation fixes;
explicitly no commit, push, merge or publication. The original documentation setup
inspected `main` at `38fcf21`; that evidence remains historical below.
See [current handoff and exact evidence](OVERNIGHT_PROGRESS.md).

## Proposed working split — awaiting team confirmation

- Harry: model/RAG/catalog and backend behaviour; integration coordinator.
- Teammate: frontend wording, layout, interaction and export presentation.
- Harry: sole writer of this file and [DECISIONS](DECISIONS.md). Teammate sends
  [handoffs](HANDOFF_TEMPLATE.md); Harry records accepted claims and evidence.

Team confirmation: **pending**. This is not an automatic claim on any directory.
Current task: **VP-001 ready for integration**, owned by Harry's authorized
integration session. Exact reservations below; no other reservations/newer handoffs
were found. User's cross-component authorization applies to this task only.
Each person may hold one task at a time, using a separate branch and local checkout.
Once confirmed, each person reads the other person's current reservations before edits.

## Task registry

Tasks remain unassigned until explicitly claimed and recorded. Begin exploration
read-only. Assign an ID such as `VP-001` only when recording a concrete task;
date the observation and distinguish runtime reproduction from source suspicion.

| Task ID | Observed problem | Reproduction | Expected behaviour | Owner | Branch/base commit | Exact reserved files | Acceptance criteria | Verification evidence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VP-001 | Wrong Q3 mapping; support/Pause dead ends; disabled review corrections/help; missing evidence | Exact replies/clicks and final results in [handoff](OVERNIGHT_PROGRESS.md) | Correct canonical proposal or clarification; resumable state; renewed confirmation/acceptance; actual evidence; matching export/profile | Harry integration session (user-authorized) | feature/harry-demo-polish / d3de1acd | backend/app/adapters/omlx.py; backend/app/api/v1.py; backend/app/schemas/__init__.py; backend/app/schemas/v1.py; backend/app/services/conversation.py; backend/app/services/retrieval.py; backend/tests/test_api_v1.py; backend/tests/test_omlx.py; frontend/src/App.tsx; frontend/src/api/client.ts; frontend/src/api/contracts.ts; frontend/src/components/Panels.tsx; frontend/tests/adapter.test.ts; docs/ai-context/STATUS.md; docs/ai-context/DECISIONS.md; docs/ai-context/OVERNIGHT_PROGRESS.md | All five reported journeys fixed; ambiguous/contradictory mapping clarifies; explicit confirmations/final save preserved; stale IDs rejected; replay adds no evidence; numeric and Unsure scores agree with persisted receipts | Targeted mocks/contracts; actual Qwen3.5-9B-4bit API; fresh Safari flow; Medium 60 exported JSON equals live receipt/SQLite; live Unsure Not assigned. Exact checks in handoff | Ready for integration; uncommitted; reservations retained |

Use statuses `Unassigned`, `Claimed`, `In progress`, `Blocked`, `Ready for integration`,
`Integrated` or `Deferred`. A blocked task keeps its reservation until explicitly
released. Record releases and completed claims; do not silently overwrite the other
person's reservation. Claims must list each file, including relevant tests/config;
directory names and ownership areas are not exact reservations.

## Dated known gaps — source inspection, not newly reproduced bugs

Observed from source on 4 October 2026 at `38fcf21`. These are context and follow-up
suggestions, not assigned tasks. Promote one only after observing a specific problem
and defining a bounded scope and acceptance criteria.
KG-01 audit, KG-02 review correction and KG-03 pause/resume/end/review help are
superseded by VP-001's implemented and verified flow. Profile lookup/selections
remain outside scope. KG-04 general model accuracy and KG-06 reload recovery
remain limitations; verified examples do not establish general readiness.

| Gap | Source finding | Next observation to consider |
| --- | --- | --- |
| KG-01 | V1 has no audit or profile lookup endpoint. The audit panel requests a missing endpoint. Accepted-profile export already uses the receipt directly and does not need lookup. | Check the evidence panel separately from accepted-profile export. Do not reopen the repaired export path merely because profile lookup is absent. |
| KG-02 | Pending-proposal correction is implemented; corrections of confirmed answers at final REVIEW are not advertised or accepted. REVIEW allows only finalize. | Inspect whether final-review Edit controls are disabled or confusing; propose a bounded owner handoff if behaviour must change. |
| KG-03 | Frontend/legacy/demo code has pause, resume, end, selections and review explanation features, but V1 does not expose those routes/actions. PAUSED snapshots advertise no resume action. | Check a specific visible control or model pause response; do not infer V1 completeness from the scripted demo. |
| KG-04 | Model paraphrases and numeric/qualitative matching depend on actual inference. Source guards valid IDs but cannot prove semantic accuracy. | Check a reported example plus a relevant ambiguous reply on the actual configured Qwen model. Do not announce a bug or accuracy result from source alone. |
| KG-05 | Root README and historical spec/demo documents describe older baseline or target behaviour, including demo defaults and missing Finance integration. This new context records the current source. | Treat broad documentation cleanup as a separate task; only the requested START_HERE link is added now. |
| KG-06 | Browser conversation state is in memory; existing saved profiles with unconfigured scoring are not automatically rescored. `/ready` does not probe inference. | Confirm actual session recovery and which profile is being inspected before claiming lost data, missing score or model readiness. |

## Newly reproduced bugs

VP-001 reproduced Q3 model-output error and final-review numeric horizon error,
and completed the reported broken control/evidence journeys. Source diagnosis,
failed experiments, final actual-Qwen/API/browser evidence and exact reproductions
are recorded separately in [OVERNIGHT_PROGRESS](OVERNIGHT_PROGRESS.md).

## Historical verification evidence for the documentation setup

- Read Git state, current implementation and existing repository context docs.
- Package discovery: no matching ZIP/extracted package found in Downloads; no prior
  AGENTS.md or docs/ai-context content to merge. Used repository sources as fallback.
- Required files and local relative links are checked as documentation checks.
- Application checks deliberately not run. No new Qwen or browser evidence claimed.

## Integration queue

VP-001 is an uncommitted diff on the current branch; preserve/apply its backend and
frontend contracts together. No dependencies, database migration, catalog release
or Finance policy changes. Product remains running from this checkout. Exact files,
checks, commands, limitations and presentation script are in the handoff.
Do not assume another checkout contains these changes. No staging/commit/push/merge
authorized for this task. Reservations remain until Harry reviews/integrates or
explicitly releases them. Reload recovery and general model evaluation are deferred.
