# Start here: two-person demo polish

Presentation: Sunday 4 October 2026. Inspected baseline: `main` at `38fcf21`.
Read [AGENTS.md](../../AGENTS.md), [TEAM_CONTEXT](TEAM_CONTEXT.md),
[STATUS](STATUS.md), [DECISIONS](DECISIONS.md) and [HANDOFF_TEMPLATE](HANDOFF_TEMPLATE.md).
Current checkout and explicit task instructions take precedence over a stale baseline.

## Before implementation

1. Inspect branch, HEAD and uncommitted changes; preserve work and do not switch
   branches automatically. Read this package. If it is unavailable in ChatGPT,
   request the files; do not claim to have read inaccessible repository context.
2. Confirm the proposed split with the team. It does not reserve every file in an area.
3. Explore the product read-only first. Prioritise broken journeys, wrong mappings,
   confirmation and save/export, then confusing wording and obvious UI problems.
   Distinguish known gaps from a newly reproduced bug. Defer cosmetics and new features.
4. Propose one bounded task, exact paths and observable acceptance criteria. Harry
   records the accepted task claim and the other person's reservations in STATUS.
   Use separate branches and separate local checkouts. Do not create/switch them
   without authorization; no two people work in one shared checkout.
5. Do only the claimed task. Cross-boundary work needs a concrete owner handoff.
   Adjacent issues become follow-up suggestions. Stop at acceptance criteria.
6. Verify proportionately and deliver the handoff. Teammate does not edit shared
   status/decisions; Harry coordinates integration. Follow explicit commit instructions.

## Common starter prompt for both ChatGPT sessions

Paste this with the context files accessible. Fill in the role after the team
confirms it. `UNCLAIMED` means exploration only; it does not authorize implementation.

```text
Help with Vesper demo polish for Sunday 4 October 2026.
Read AGENTS.md and docs/ai-context/{START_HERE,TEAM_CONTEXT,STATUS,DECISIONS,HANDOFF_TEMPLATE}.md.
If you cannot access these files, ask me to provide them; do not invent their contents.

Role: [Harry: model/RAG/catalog/backend and integration; OR Teammate: frontend wording/layout/interaction/export presentation].
The split is proposed until confirmed. Harry is the proposed sole writer of shared status/decisions.
Task ID: UNCLAIMED.
Scope: read-only exploration and one bounded task proposal; no application edits yet.
Branch/base commit: inspect my checkout first; package baseline is main at 38fcf21.
Reserved files: none until an explicit exact-path claim is recorded by the integrator.
Other person's reserved files: read current STATUS.md; none at package creation, never assume unchanged.
Observable acceptance criteria for this exploration: report current Git state, one concrete observed problem with exact reproduction and expected behaviour, proposed file paths and proportionate verification. Label source-only suspicions separately.

Preserve uncommitted work. Do not switch branches automatically. Use separate branches/checkouts.
Before implementation, get a confirmed task ID, role, scope, branch/base, exact reserved files, other person's reservations and observable acceptance criteria. Announce planned files before editing.
Never edit the other person's reserved files. Send cross-boundary needs as concrete handoffs.
No automatic scope expansion, new architecture/dependencies or broad refactoring. Record adjacent issues as follow-ups and stop when acceptance criteria are met.
The model proposes; deterministic backend code validates, scores and saves. Preserve explicit answer confirmation and final-review acceptance.
Reproduce and verify the target problem. Use relevant existing checks; for mapping include a relevant ambiguous case; for save/export check explicit acceptance and matching exported records. Protect confirmation, persistence and scoring. Separate mocks/stubs from actual Qwen and browser evidence. Do not run broad suites by default or repeat checks without reason.
Finish with HANDOFF_TEMPLATE.md: branch/commit or uncommitted, files, behaviour, checks actually performed, limitations and exact integration requirements. Follow my explicit commit/push/merge instructions.
```

## Required implementation prompt

Use this after a task has been explicitly claimed. Every field must be concrete;
missing role/claim/acceptance information means no implementation authorization.

```text
Role: <confirmed Harry or Teammate role>
Task ID and scope: <registered ID; reproduced problem; explicit inclusions/exclusions>
Branch/base commit: <own branch; exact inspected base SHA; own checkout path>
Reserved files: <each exact repository-relative path>
Other person's reserved files: <each path or explicitly confirmed none; registry date/version>
Observable acceptance criteria: <specific inputs/clicks and expected outputs>
Verification: <target reproduction/fix check; relevant existing checks; real or mock environment>
Commit/push/merge instruction: <explicit authorization or no action>

Read the shared context, inspect and preserve local work, state planned files,
and implement only this claim. Hand off cross-boundary dependencies to their owner.
Preserve Vesper's confirmation, acceptance, deterministic scoring and persistence safeguards.
Stop at acceptance criteria and return the completed handoff template.
```

## Evidence and useful checks

Choose checks that answer the claimed risk; these are references, not a default suite:

- Frontend types: `npm run check`; build when packaging/bundling is affected: `npm run build`.
- Existing frontend checks: `npm run test --workspace frontend -- tests/adapter.test.ts -t '<relevant_case>'`;
  select an existing case that actually covers the change. Browser cases may use stubs.
- Backend: `backend/.venv/bin/python -m pytest backend/tests/<relevant_file>.py -k '<relevant_case>' -q`.
- Mapping: exact target reply and a relevant ambiguous/opposite case, current question,
  catalog/model IDs, expected option IDs and actual outputs. Model discovery is not inference.
- Save/export: no premature save; explicit confirmations and matching review version;
  accepted receipt/storage/export agreement, score/bucket and Unsure behaviour if affected.
- Browser: actual mode, clicks, observed result and limits. Record whether HTTP/model was
  stubbed. Scripted fixture behaviour is not proof of real V1 support.

Do not skip necessary safety checks, write redundant tests, run broad suites by
default or repeat successful checks without new changes, failures or unresolved concerns.
No application tests are run for the documentation setup itself.
