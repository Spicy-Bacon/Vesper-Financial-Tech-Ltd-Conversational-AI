# Finance catalog integration handoff

The imported release is `catalog-v2`, from `CC_Question_Set_Scored_v2_Judge_Ready.xlsx`.
It contains six answer questions, 32 answer options, and 17 Approved explanations.
Ten explanations are eligible for answer retrieval. Seven Q7 explanations remain available
only through `JsonCatalogProvider.review_explanations` for final review.

## Import and provenance

From the repository root, install the importer dependency in the existing environment:

```sh
backend/.venv/bin/python -m pip install openpyxl==3.1.5
```

Shared dependency manifests were left unchanged. CS2 should coordinate adding this
import/test dependency; production JSON readers do not require openpyxl.

The exact import command used was:

```sh
backend/.venv/bin/python -m backend.scripts.import_finance_workbook \
  /Users/harry/Downloads/CC_Question_Set_Scored_v2_Judge_Ready.xlsx \
  --finance-approved \
  --approval-basis 'User explicitly confirmed Finance approval of the Judge_Ready question and option catalog for runtime use on 2026-10-03. Reviewer name and separate sign-off record not supplied.'
```

The approval basis records the user's explicit confirmation, rather than inferring
approval from the filename or from individual explanation statuses. The default import
sets `financeApproved=false`. An approved import requires an explicit basis.

Generated files:

- `data/catalog/catalog-v2/catalog.json`
- `data/catalog/catalog-v2/explanations.json`
- `data/source/212d7a0a7649f6add4706d683539822f3d518e625164ce6e8379eef06c4fdf57/CC_Question_Set_Scored_v2_Judge_Ready.xlsx`

The archived workbook's SHA-256 is
`212d7a0a7649f6add4706d683539822f3d518e625164ce6e8379eef06c4fdf57`.
Both JSON documents are validated before writing. Repeating the identical import is
idempotent. A different source, content or approval under the same catalog version is
rejected; the source owner must issue a new version for a changed release.

Only `Questions`, `Answer_Options` and `Explanations` are selected. Scores, scoring
policies and evaluation expectations are not exported. Approved Q7 explanation prose
may describe scores, but it is review-only and never reaches answer interpretation.

## CS2 wiring

Use the existing dependency injection entry point. The exact constructor names are:

```python
from pathlib import Path

from backend.app.adapters.omlx import OmlxAdapter
from backend.app.catalog import JsonCatalogProvider
from backend.app.main import create_app
from backend.app.services.retrieval import CatalogRetriever
from backend.app.settings import Settings

settings = Settings.load()
release_dir = Path("data/catalog/catalog-v2")
provider = JsonCatalogProvider(release_dir)
retriever = CatalogRetriever(release_dir)
model = OmlxAdapter(
    base_url=settings.OMLX_BASE_URL,
    model=settings.OMLX_MODEL,
    api_key=settings.OMLX_API_KEY.get_secret_value(),
)
app = create_app(
    catalog=provider,
    retrieval=retriever,
    model=model,
    demo=False,
    demo_catalog=False,
    serve_frontend=False,
)
```

Check the key/model are configured before constructing the adapter. If importing
`backend.app.main` in a script, export `VESPER_SERVE_FRONTEND=0` first: that module
also constructs its default global app on import. The example assumes the repository
root is the working directory; in the existing composition root, resolve the release
directory relative to the repository rather than depending on the working directory.

CS2 must coordinate this wiring in `backend/app/main.py` / `create_configured_app`.
No shared app, settings, adapter or dependency manifest has been edited in this work.
The default app does not automatically select this catalog. Keep the current ports:
FastAPI `127.0.0.1:8001`, oMLX `127.0.0.1:8000`, React/Vite `localhost:5173`.
Use server-side `OMLX_BASE_URL`, `OMLX_MODEL` and `OMLX_API_KEY`; the current local
model setting is `Qwen3.5-9B-4bit`. Disable `VESPER_DEMO`, `VESPER_DEMO_CATALOG`
and `VESPER_SERVE_FRONTEND` when composing the imported catalog flow.

The provider returns the existing backend `Catalog`, including its approval gate,
and independent copies. The bridge implements the existing backend `Retriever`
signature and reuses `QuestionScopedRetriever` for deterministic ranking and a
maximum of three snippets. Q4 currently retrieves only `EX06` and `EX07`.
Files are read at construction; calls use pinned in-memory content.

## Interface limits to coordinate

The backend `Question` has no separate help field. The exact source question is kept
in `prompt`, exact help is exposed through `provider.question_help`, and `clarification`
contains the authored help followed by the authored option labels in display order.
Canonical `confirmation_text` remains unchanged in each `Option.answer`.
Order is encoded by sorted question/option arrays. CS2 should provide distinct UI labels
if repeated categories such as Capacity for Loss are not sufficient for the review UI.

Q7 is exposed only through `provider.review`, `provider.question_help["Q7"]` and
`provider.review_explanations`. CS2 must render it in the final review state, including
Edit controls, and bind acceptance to the existing explicit save action. Do not pass
Q7 or its options to `OmlxAdapter`, propose its Confirm option, or let typed agreement
trigger persistence. The authored Q7 wording contains a score-display instruction;
scoring integration remains separate and the existing backend reports not configured.

The existing adapter contract remains `proposal`, `clarification`, `pause` or `support`.
The separate `ModelDecision` schema is not used in this backend path. No model client,
state machine or scoring engine was added. The model cannot confirm or save.

The retriever's existing inference contracts accept replies up to 4,000 characters,
while the backend request contract allows 8,000. CS2 should agree a common limit.
Explanation text over the existing 600-character inference limit fails import rather
than being truncated. The supplied explanations fit this limit.

## Verification

The combined backend suite passed with **286 passed, 4 skipped** and one existing
Starlette deprecation warning:

```sh
VESPER_SERVE_FRONTEND=0 backend/.venv/bin/python -m pytest backend/tests -q -rs
```

Tests verify the real workbook's order, canonical text, safety flags, source archive,
deterministic output, approval gate, overwrite rejection, duplicate/unknown IDs,
version consistency, exclusion of unapproved explanations and excluded-sheet data,
provider copy isolation and scoped retrieval. MockTransport integration uses the real
Q4 options and explanations; ConversationService keeps proposals unconfirmed, requires
the Q4 safety confirmation and saves no accepted profile before final acceptance.
Mocked transport results do not prove Qwen interpretation quality.

The explicit live run was attempted with:

```sh
VESPER_SERVE_FRONTEND=0 VESPER_LIVE_Q4=1 \
VESPER_CATALOG_RELEASE=data/catalog/catalog-v2 \
backend/.venv/bin/python -m pytest backend/tests/test_finance_catalog.py \
  -k live_q4_opt_in -q -s -rs
```

All four cases were **skipped/blocked before inference**: no service was listening on
`127.0.0.1:8000`. Reachability verification also failed. No real Qwen result or latency
was observed in this run. Start the existing oMLX server with the configured model,
then rerun that command. It verifies the exact `/v1/models` ID before inference and
prints only the fictional case, observed kind/option ID and latency, never credentials.

Required observations are `Q4_D` for the clear six-month answer, clarification for
the approximate three-month answer, clarification for the amount without an expense
denominator, and `Q4_U` for explicit uncertainty. Expectations live only in evaluation
code, never in prompts or runtime mapping.

If the model guesses on either ambiguous case, coordinate a change to
`backend/app/adapters/omlx.py` / `SYSTEM_PROMPT` with CS2: require clarification when
approximation crosses an option boundary or essential-cost coverage is missing;
preserve explicit uncertainty as the allowed Unsure option. Re-evaluate all four cases
after a prompt change rather than hard-coding the evaluation utterances.

The React `/api/v1` adapter remains a separate CS2 integration task. This change supplies
the Finance catalog and retrieval dependencies to the existing conversation API.
