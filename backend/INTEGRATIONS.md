# Proposed handoff to Harry/CS3 and Finance

Status: existing Python integration interfaces, preserved in the shared team baseline. The target HTTP contract is now [../API.md](../API.md), using `/api/v1`. The backend still implements `/api/conversation`; CS2 will adapt it in later work. No external agreement or teammate contact has occurred.
Harry/CS3's catalog is not available yet. The opt-in demo exists only to exercise the backend.
Replace it through dependency injection. A separate thin `app/adapters/omlx.py` client was added
for the user's supplied OpenAI-compatible server and model; the scripted adapter remains separate.
Harry/CS3 retain the real importer, retrieval and final model adapter integration.

## Harry/CS3 interfaces

The proposed Python contracts are in `app/interfaces.py` and the Pydantic shapes are in
`app/schemas/__init__.py`. Calls are synchronous because the route runs in FastAPI's worker thread.
Use a synchronous wrapper if the underlying adapter is async. Do not block the event loop.
Raise on unavailable integrations and enforce connection/request timeouts in adapters.

| Interface | Input | Output | Owner |
| --- | --- | --- | --- |
| `CatalogProvider.load()` | None | `Catalog` | Harry/CS3 importer; Finance approves content |
| `Retriever.retrieve(...)` | `text`, pinned `question`, pinned `catalog` | At most 10 `RetrievedContext` items | Harry/CS3 |
| `ModelAdapter.interpret(...)` | `text`, pinned `question`, pinned `catalog`, `confirmed_answers`, `context` | `Interpretation` | Harry/CS3 |
| `FinancePolicy.evaluate(...)` | Complete canonical `answers`, pinned `catalog` | Versioned `ScoreResult` | Finance |

Catalog fields: `version`, `financeApproved`, `demo`, `questions`. Each ordered question has
`id`, `label`, `prompt`, `clarification`, `requiresExplicitConfirmation` and ordered `options`.
Each option has `id` and its canonical `answer` wording. Question and option IDs must be stable
and unique in their scopes; changes to wording, meanings or options require a new catalog version.
Live mode rejects unapproved catalogs and demo catalogs. Approval must come from the trusted
import/configuration path; it is not a model output or user-supplied request flag.

Retrieval items contain `sourceId` and bounded `text`. Retrieve context relevant to the pinned
catalog version, and treat retrieved/model text as untrusted input. No importer, vector store
or Finance formulas are implemented here. The optional oMLX client contains
a constrained interpretation prompt and reads credentials only from backend settings.

The model returns only one of:

```python
Interpretation(kind="proposal", optionId="an-existing-option-id")
Interpretation(kind="clarification")
Interpretation(kind="pause")
Interpretation(kind="support")
```

The backend resolves answer wording and the safety requirement from the pinned catalog. Model
output cannot confirm answers, calculate scores, create arbitrary answer wording, select another
question or persist a profile. Unknown option IDs and malformed integration output return 503
without advancing the revision. Adapter exceptions return a generic availability error, with no
silent demo fallback. Clarification wording comes from the catalog. This initial interface does
not accept arbitrary model assistant text, extracted findings or a full transcript; agree any
contract expansion before implementation.

## Finance handoff

Please provide approved catalog meanings and safety requirements plus a versioned policy for
points, formulas, completeness constraints and classifications. The scoring boundary passes
canonical confirmed answers and the pinned catalog to `FinancePolicy.evaluate()`. Results must
declare `status="scored"`, `policyVersion`, the matching `catalogVersion`, finite Decimal `values`
and an optional `classification`. No scoring formula is chosen by the backend.

With no policy, `ScoringService` returns `status="not_configured"`, empty values and no
classification. The user sees that limitation before saving; accepted answers can still be
stored. A policy failure or catalog mismatch prevents saving and rolls back the transaction.
If Finance requires a score before any save, agree that policy before live integration.

## Composition example (placeholder imports to be supplied by the owners)

```python
from backend.app.main import create_app

# Import these concrete adapters from the Harry/CS3 and Finance packages once available.
app = create_app(
    catalog=catalog_provider,
    model=model_adapter,
    retrieval=retriever,          # Optional: absent retrieval means empty context.
    finance_policy=finance_policy,
    serve_frontend=True,
)
```

Contract review topics: exact IDs/schema, question ordering and safety metadata, catalog/policy
version matching, retrieval provenance, model timeout/error behaviour, and Finance's save gate.
