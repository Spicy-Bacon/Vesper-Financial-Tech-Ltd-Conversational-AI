# Vesper demo-polish working instructions

Session: Sunday 4 October 2026, Europe/London. Presentation: Sunday 4 October 2026.
Context inspected at `38fcf212f12c675da18cacb8794a259bc862a88f` on `main`.

Read [START_HERE](docs/ai-context/START_HERE.md), [TEAM_CONTEXT](docs/ai-context/TEAM_CONTEXT.md),
[STATUS](docs/ai-context/STATUS.md) and [DECISIONS](docs/ai-context/DECISIONS.md) before work.
Current user instructions take precedence over these defaults. Recheck the checkout;
the inspected commit and task reservations can change during the session.

## Two-person agreement

The proposed split is **not yet confirmed**:

- Harry: model/RAG/catalog and backend behaviour; integration coordinator.
- Teammate: frontend wording, layout, interaction and export presentation.
- Harry: sole writer of shared status and decisions; teammate sends handoffs.

Areas are routing guidance, not reservations. Claim one task per person at a time,
with exact repository-relative file paths, a branch/base commit and observable
acceptance criteria. Tasks begin unassigned. Confirm the split and record accepted
claims through the integrator before implementation. Use separate branches and
separate local checkouts; do not switch the user's branch automatically.

Never edit another person's reserved files. A cross-boundary dependency needs a
concrete handoff to its owner: proposed interface/behaviour, exact paths, acceptance
criteria and integration requirements. The teammate supplies updates using the
[handoff template](docs/ai-context/HANDOFF_TEMPLATE.md); the integrator edits the
shared context files. Announce planned files before edits and preserve uncommitted work.

## Scope and safety

- Prioritise broken journeys, wrong mappings, confirmation and save/export, then
  confusing wording and obvious UI problems. Defer new features and low-value cosmetics.
- No automatic scope expansion, new architecture, dependencies or broad refactoring.
  Record adjacent issues as follow-up suggestions. Stop at the claimed acceptance criteria.
- The model proposes an existing option; backend code validates canonical IDs and
  wording. The user explicitly confirms each answer, including Unsure, and accepts
  the exact final review before deterministic backend scoring and persistence.
- Never ask the model to score, choose Low/Medium/High, confirm or save. Do not invent
  Finance wording, points, formulas, thresholds or missing answers. Preserve catalog
  approval, provenance, version and overwrite rules. Unsure is not a middle score.
- Preserve revision/proposal/review checks, idempotency, transaction boundaries and
  accepted-only persistence. A browser abort does not prove server work was undone.
- Credentials stay server-side and out of commits, handoffs and browser configuration.
  Use fictional demo circumstances. Do not claim investment advice, suitability
  validation, regulatory approval or verified retention/usability.

## Verification and handoff

Reproduce the reported bug and verify the same journey after the fix. Run relevant
existing checks where useful. For mapping, check the target reply and a relevant
ambiguous case. For save/export, verify explicit acceptance and matching receipt,
stored records and exported data, including scoring when affected.

Do not run broad suites by default, write redundant tests or repeat successful
checks without a new reason. Do not skip checks needed to protect confirmation,
persistence or scoring. Label source inspection, mocks/stubs, actual Qwen calls and
actual browser observations separately; record only checks actually performed.

Every implementation prompt includes role, task ID/scope, branch/base, exact reserved
files, the other person's reserved files and observable acceptance criteria.
Every handoff includes branch and commit (or `uncommitted`), changed files, fixed
behaviour, actual checks, limitations and exact integration requirements.

Follow the current task's commit/push/merge instructions. The original documentation
setup required no application tests, commit, push or merge. On 4 October 2026,
the user subsequently authorized a local documentation commit only; no push or merge.
