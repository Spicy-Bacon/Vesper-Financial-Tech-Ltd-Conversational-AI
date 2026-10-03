# Session status and task registry

Date: 4 October 2026, Europe/London. Presentation: Sunday 4 October 2026.
Inspected branch/base: `main` at `38fcf212f12c675da18cacb8794a259bc862a88f`.
Initial working tree: clean. Setup scope: documentation only.
No branch switch, application test, model call or browser reproduction was performed.
After setup, the user authorized a local documentation commit on 4 October 2026.
No push or merge was authorized. The inspected application baseline remains `38fcf21`.

## Proposed working split — awaiting team confirmation

- Harry: model/RAG/catalog and backend behaviour; integration coordinator.
- Teammate: frontend wording, layout, interaction and export presentation.
- Harry: sole writer of this file and [DECISIONS](DECISIONS.md). Teammate sends
  [handoffs](HANDOFF_TEMPLATE.md); Harry records accepted claims and evidence.

Team confirmation: **pending**. This is not an automatic claim on any directory.
Active implementation tasks: **none**. Reserved application files: **none**.
Each person may hold one task at a time, using a separate branch and local checkout.
Once confirmed, each person reads the other person's current reservations before edits.

## Task registry

Tasks remain unassigned until explicitly claimed and recorded. Begin exploration
read-only. Assign an ID such as `VP-001` only when recording a concrete task;
date the observation and distinguish runtime reproduction from source suspicion.

| Task ID | Observed problem | Reproduction | Expected behaviour | Owner | Branch/base commit | Exact reserved files | Acceptance criteria | Verification evidence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

The registry is intentionally empty. No implementation task has been claimed.
Use statuses `Unassigned`, `Claimed`, `In progress`, `Blocked`, `Ready for integration`,
`Integrated` or `Deferred`. A blocked task keeps its reservation until explicitly
released. Record releases and completed claims; do not silently overwrite the other
person's reservation. Claims must list each file, including relevant tests/config;
directory names and ownership areas are not exact reservations.

## Dated known gaps — source inspection, not newly reproduced bugs

Observed from source on 4 October 2026 at `38fcf21`. These are context and follow-up
suggestions, not assigned tasks. Promote one only after observing a specific problem
and defining a bounded scope and acceptance criteria.

| Gap | Source finding | Next observation to consider |
| --- | --- | --- |
| KG-01 | V1 has no audit or profile lookup endpoint. The audit panel requests a missing endpoint. Accepted-profile export already uses the receipt directly and does not need lookup. | Check the evidence panel separately from accepted-profile export. Do not reopen the repaired export path merely because profile lookup is absent. |
| KG-02 | Pending-proposal correction is implemented; corrections of confirmed answers at final REVIEW are not advertised or accepted. REVIEW allows only finalize. | Inspect whether final-review Edit controls are disabled or confusing; propose a bounded owner handoff if behaviour must change. |
| KG-03 | Frontend/legacy/demo code has pause, resume, end, selections and review explanation features, but V1 does not expose those routes/actions. PAUSED snapshots advertise no resume action. | Check a specific visible control or model pause response; do not infer V1 completeness from the scripted demo. |
| KG-04 | Model paraphrases and numeric/qualitative matching depend on actual inference. Source guards valid IDs but cannot prove semantic accuracy. | Check a reported example plus a relevant ambiguous reply on the actual configured Qwen model. Do not announce a bug or accuracy result from source alone. |
| KG-05 | Root README and historical spec/demo documents describe older baseline or target behaviour, including demo defaults and missing Finance integration. This new context records the current source. | Treat broad documentation cleanup as a separate task; only the requested START_HERE link is added now. |
| KG-06 | Browser conversation state is in memory; existing saved profiles with unconfigured scoring are not automatically rescored. `/ready` does not probe inference. | Confirm actual session recovery and which profile is being inspected before claiming lost data, missing score or model readiness. |

## Newly reproduced bugs

None recorded in this documentation setup. Record exact mode, reply/click sequence,
observed result, expected result and branch/commit when a teammate actually reproduces one.

## Verification evidence for this setup

- Read Git state, current implementation and existing repository context docs.
- Package discovery: no matching ZIP/extracted package found in Downloads; no prior
  AGENTS.md or docs/ai-context content to merge. Used repository sources as fallback.
- Required files and local relative links are checked as documentation checks.
- Application checks deliberately not run. No new Qwen or browser evidence claimed.

## Integration queue

No application changes queued. The user authorized committing these context files
locally after setup. Harry must share that local commit or the files with the
teammate's separate checkout/ChatGPT session before relying on them; a clone of
`38fcf21` alone does not contain this package. No remote publication is authorized.
Integration/commit/push/merge actions require user authorization for that task.
