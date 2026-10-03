# Session decisions

Updated 4 October 2026, Europe/London. Inspected commit `38fcf21` on `main`.
Proposed keeper: Harry, integration coordinator; team confirmation is pending.
Teammate supplies decision suggestions through [handoffs](HANDOFF_TEMPLATE.md).
Do not change this record from a teammate implementation task.

| ID | Decision | Basis and status |
| --- | --- | --- |
| D-01 | Presentation is Sunday 4 October 2026; optimise tonight for small demo fixes. | User's session brief; confirmed requirement. |
| D-02 | Harry handles model/RAG/catalog/backend and integration; teammate handles frontend wording/layout/interaction/export presentation. Harry alone edits shared status/decisions. | Proposed split; not yet team-confirmed. Areas do not reserve files. |
| D-03 | One exact-path task per person, separate branches and local checkouts; cross-boundary changes require an owner handoff. | User's working rules. No implementation claims exist yet. |
| D-04 | Prioritise broken journeys, wrong mappings, confirmation and save/export, then confusing wording and obvious UI problems. Defer low-value cosmetics/new features. | User's priority order. Do not auto-expand scope or redesign/refactor broadly. |
| D-05 | Preserve model proposals, deterministic validation/scoring/save, explicit answer confirmation and exact final acceptance. | User requirement and inspected architecture. Finance rules remain workbook-authoritative; no LLM bucket choice. |
| D-06 | Use repository sources as context-package fallback. Record static gaps separately from new reproductions and keep tasks unassigned. | No matching Downloads package or existing ai-context/AGENTS files found. Source inspected at `38fcf21`; no app verification in this task. |
| D-07 | This package setup changes documentation only; no application tests, commit, push or merge. | Explicit user instruction overrides the earlier standing stage-and-commit preference for this task. |
| D-08 | Future verification is targeted and proportionate; protect confirmation, persistence and scoring; distinguish mocks/stubs from actual Qwen/browser observations. | User's verification rules. A green health endpoint is insufficient evidence of a working journey. |
| D-09 | Commit the completed context package locally; no push or merge. | User's subsequent “commit” instruction on 4 October 2026 supersedes D-07's no-commit constraint only. Documentation-only scope and no application tests remain. |

Record later decisions with date, deciding person(s), task ID, rationale and concrete
integration impact. Do not turn an adjacent issue or an unconfirmed role proposal
into an agreed feature, file reservation or completed task.
