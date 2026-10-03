# Handoff template

Send this to the owner/integrator. Harry updates [STATUS](STATUS.md) and
[DECISIONS](DECISIONS.md); teammate hands off rather than editing them directly.
Use `not performed`, `unknown` or `uncommitted` where appropriate. Do not report
expected outcomes as observed evidence. No broad suite is required by this template.

```text
Date/time and timezone:
Author and confirmed role:
Task ID and claimed scope:
Acceptance criteria:

Branch:
Base commit:
Commit(s), or "uncommitted":
Local checkout:
Exact reserved files for this task:
Other person's reserved files checked (include registry version/date):

Files changed (exact paths):
Behaviour fixed (before/after):
Original reproduction (mode, question/reply/clicks, observed result):
Fix verification (same steps, actual observed result):

Checks actually performed:
- Command/manual steps:
- Commit/worktree state checked:
- Result:
- Evidence type: source inspection / mock or stub / actual Qwen / actual browser:
- Environment: catalog/model IDs, API mode, browser/ports where relevant:
- Mapping: target example and relevant ambiguous case, expected and actual IDs:
- Save/export: explicit acceptance, receipt/storage/export agreement and score where affected:
Checks not performed and why:

Limitations and remaining risks:
Adjacent issues (follow-up suggestions only; no scope expansion):

Exact integration requirements:
- Commit(s) or uncommitted patch/files to apply; intended target/base:
- Required owner action for any cross-boundary change, with exact paths:
- Interface/request/response/schema change, or "none":
- Configuration/dependency/database changes, or "none" (never include secrets):
- Start/restart/rebuild steps, or "none":
- Relevant checks to perform after integration and why:
- Conflicting reservations/dependent tasks, or "none":
- Commit/push/merge authorization received, or "not authorized":

Status: ready for integration / blocked / deferred
Reservation: retained until integration or explicitly released by integrator
```

For a cross-boundary dependency, provide the smallest concrete request to the
owner before changing files: task ID, observed problem, exact target paths,
proposed contract/behaviour, acceptance criteria, evidence and required ordering.
Do not transfer ownership or reserve another person's files by implication.
