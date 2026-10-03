# Model + question-scoped RAG

This module ends at the inference boundary. It retrieves reviewed explanation
snippets, calls a local OpenAI-compatible model, validates the result, and returns
an `InferenceOutcome`. It has no routes, session state, confirmation, persistence,
scoring, importer, or frontend code.

The intended connection is browser → FastAPI **:8001** → this module → oMLX
**:8000**. Keep the model endpoint and credentials on the backend. The frontend
branch uses `/api/v1`; these are internal Python interfaces, not new HTTP routes.

## Setup and tests

Python **3.11+**. From the repository root, using [uv](https://docs.astral.sh/uv/):

```sh
uv sync --project backend --locked
backend/.venv/bin/python -m pytest -q backend/tests
git diff --check
```

`backend/uv.lock` pins the dependencies. `pyproject.toml` contains only Pydantic,
HTTPX and pytest; there is no application framework setup. Tests use scripted
responses and `httpx.MockTransport`, and need no running server. Run pytest from
the backend directory with `.venv/bin/python -m pytest -q` if preferred.

## Configuration and manual probe

Export environment variables in your shell. `.env.example` is a reference;
neither the module nor the probe automatically reads `.env` files.

| Variable | Behavior |
| --- | --- |
| `MODEL_BASE_URL` | Defaults to `http://127.0.0.1:8000/v1`; include `/v1`. No URL credentials, query or fragment. |
| `MODEL_ID` | No executable default. Use the exact ID returned by `GET /v1/models`. |
| `MODEL_API_KEY` | Optional bearer key; excluded from config serialization and repr. |
| `MODEL_TIMEOUT_SECONDS` | Defaults to 30; positive and at most 120 seconds per attempt. |
| `MODEL_JSON_MODE` | Defaults to `false`. Set `true` only after verifying `response_format: {"type":"json_object"}` support. |

First discover your model IDs:

```sh
MODEL_BASE_URL=http://127.0.0.1:8000/v1 MODEL_ID= \
  backend/.venv/bin/python backend/scripts/probe_model.py
```

Then run the probe with the actual discovered ID:

```sh
MODEL_BASE_URL=http://127.0.0.1:8000/v1 MODEL_ID='EXACT_ID_FROM_DISCOVERY' \
  backend/.venv/bin/python backend/scripts/probe_model.py
```

The second command contains a placeholder to replace, not a suggested model.
Set `MODEL_API_KEY` separately if your server requires it. The probe lists available
IDs, requires an exact match, then sends **one** synthetic completion request with
no retry. It uses the production parser, including option and evidence checks.
Output includes base URL, model ID, success/failure, total discovery/completion
latency and parsed action. It does not print keys, raw responses, replies or hidden
reasoning. Exit codes: 0 success, 1 model/output failure, 2 configuration/discovery
selection required. No live oMLX verification is implied by unit test results.

## Public contracts and backend integration

Contracts are in `app.schemas.inference`; services are in `app.services`.

```python
from app.services.retrieval import QuestionScopedRetriever
from app.services.model_client import Interpreter, LocalModelClient, ModelConfig

# explanation_records: iterable[ExplanationRecord], from the catalog owner.
# question: InferenceQuestion, from the session's pinned catalog version.
retriever = QuestionScopedRetriever(explanation_records)
retrieval = retriever.retrieve(
    catalog_version=question.catalog_version,
    question_id=question.question_id,
    user_reply=text,
)

# In async backend code. Reuse the client across calls and close at shutdown.
async with LocalModelClient(ModelConfig.from_env()) as client:
    interpreter = Interpreter(client)
    outcome = await interpreter.interpret(
        question=question,
        options=question.options,
        user_reply=text,
        retrieval=retrieval,
    )
```

The example is an integration fragment; the caller supplies `question`, `text`
and records. No runtime catalog loader or synthetic fallback catalog is installed.
Import `app` with `backend/` on Python's module path (or run from `backend/`).

### Catalog projection

- `InferenceQuestion(catalog_version, question_id, text, options, help_text=None)`:
  use a direct catalog lookup. Question text is capped at 1,200 characters.
- `AllowedOption(question_id, option_id, label, playback=None, is_unsure=False)`:
  pass **every** allowed option, including Unsure. The explicit `question_id`
  establishes ownership; IDs are opaque and no ID prefix is guessed. The frontend's
  option shape has no `question_id`; the backend adds it from the owning catalog
  question. Supply approved playback/help when available; missing text stays null.
- `ExplanationRecord(content_id, text, source_sheet, source_row, catalog_version,
  question_id, approval_status, retrievable)`: the catalog owner supplies approval
  metadata. Status is `approved`, `draft`, `unapproved` or `retired`. Keep unreviewed
  content unapproved and do not set approval merely to make retrieval return data.
  The source must be exactly `Explanations` to be retrievable.

Identifiers are nonblank, contain no whitespace and are capped at 160 characters.
Snippet/help/label/playback/evidence fields are capped at 600 characters. Catalog
records exceeding the cap are rejected, not silently truncated: the catalog owner
must provide suitably short reviewed content. Replies are capped at 4,000
characters; 1–20 options are supported. All Pydantic contracts forbid extra fields
and coercion. Project explicitly from catalog/API models rather than passing their
unrelated fields. The input enforces the exact question/version and complete,
unchanged option set; invalid caller data raises `ValidationError` before any model
call. This is a caller integration error, distinct from a model fallback.

The caller is responsible for supplying trusted catalog metadata and the result
from this retriever. An arbitrary object marked `approved`, or a hand-built snippet
with false provenance, is not evidence of approval. There is no approval authority
or manifest verification in this slice.

### Retrieval and decisions

`QuestionScopedRetriever.retrieve(*, catalog_version, question_id, user_reply)`
returns `RetrievalResult(catalog_version, question_id, snippets, retrieval_method)`.
Every snippet retains `content_id`, `text`, `source_sheet` and positive `source_row`.
Hard filters require exact version, question, approved status, `retrievable=True`
and the `Explanations` source sheet. Evaluation/persona/issue/mapping sheets are
excluded even if their flags incorrectly say approved. Duplicate content IDs in
one question/version are rejected.

After filtering, retrieval ranks by case-insensitive overlap of non-stopword
tokens; ties use source row then content ID. With no meaningful match it uses that
same source order. At most three snippets are returned; an empty set stays empty.
Methods are `question_scoped_lexical`, `question_scoped_order`, and
`question_scoped_empty`. Retrieval never chooses a question or changes options.
The small question-scoped explanation set needs no embeddings or vector database.

`Interpreter.interpret(...)` is async and returns:

```text
InferenceOutcome:
  retrieval: RetrievalResult
  decision: ModelDecision | None
  model_id: str | None
  latency_ms: int                 # full inference time, including any retry
  fallback_reason: str | None
  retry_count: 0 | 1
```

`ModelDecision` requires all six JSON fields: `action`, `option_id`,
`evidence_quote`, `clarification_question`, `explanation_content_ids`,
`support_reason`. Only five actions exist:

| Action | Required payload |
| --- | --- |
| `propose_option` | Active/supplied option ID and nonblank evidence that is a literal substring of this reply. |
| `clarify` | One exact neutral question from `CLARIFICATION_QUESTIONS` in the contract module. |
| `explain` | One to three unique IDs from the actual retrieved snippet set. Render source text. |
| `offer_pause` | Support code `user_requested_pause`, `user_declined`, or `user_distress`. |
| `out_of_scope` | Support code `outside_questionnaire`. |

Non-applicable fields must be null (or `[]` for IDs). Support codes carry no
generated reasoning or advice. Clarifications use a small, explicit set of generic
neutral templates so deterministic validation can rule out hidden proposals,
confirmations and save claims. Arbitrary model-written follow-ups are rejected.
Question-specific templates can be added with catalog review later.

The versioned prompt treats replies and retrieved text as data, separates attitude
from capacity, rejects demographic inference and rule bypasses, and distinguishes
uncertainty from refusal. It receives only the active question, complete options,
available help/playback, retrieved snippets and current reply; no history or profile
is sent. Literal evidence validation proves the quote exists, **not** that the
financial interpretation is correct. Model quality and ambiguity handling require
separate evaluation against a reviewed catalog.

`parse_decision(raw, *, context: InterpretationInput)` is shared by the interpreter
and probe. JSON mode never bypasses Pydantic or semantic validation. Duplicate JSON
keys, unknown/forbidden actions, extra fields, fabricated evidence and foreign IDs
fail validation. The HTTP adapter rejects tool calls, refusals, missing content and
truncated completions; it never forwards hidden reasoning.

### Failures and backend ownership

The adapter uses temperature 0, a 512-token output cap, no streaming, a 64 KiB HTTP
response limit, and both HTTP operation and total-attempt timeouts. Redirects,
environment proxies and automatic transport retries are disabled. Malformed or
semantically invalid output may retry **once** with a generic instruction, without
echoing the failed response. Transport failure does not retry. With default config,
two model attempts take at most approximately 60 seconds plus local validation.
Backend request timeout configuration must allow for this or cancel inference.
Cancellation propagates; it is not converted into a new answer.

Fallback codes are `model_not_configured`, `model_unavailable`, `model_timeout` and
`invalid_model_output`. Each has `decision=None`; success has no fallback reason.
No fallback chooses an option. The backend must:

1. Check session state/revision before inference and again before using its result.
2. Decide whether a valid decision can create an **unconfirmed** proposal, ask the
   allowed clarification, show retrieved text, or offer pause/out-of-scope UI.
3. Translate fallback into fixed-option buttons; use catalog playback for proposals.
4. Own confirmation, advancement, review, persistence, and catalog release gates.

The inference code does not mutate the caller's session or inputs and knows
nothing about whether a profile can be saved. It logs no financial conversation,
credentials or reasoning. Avoid enabling HTTP debug logging with sensitive data;
runtime/server logging and retention settings remain outside this module.

For deterministic tests, `MockModelClient([json_string, ModelCallError(...)])`
implements the same async `ModelClient.complete(messages)` protocol. Its ID is
`mock-synthetic`; it records only a call count. Do not present mock outcomes as live
inference. `LocalModelClient.list_models()` supports probe discovery, and
`aclose()`/the async context manager owns HTTP resource cleanup.

## Finance handoff still required

There is no approved catalog in the inspected branches. The test-only Q4 fixtures
are labelled `SYNTHETIC / PROVISIONAL` and use a non-release catalog version.
Their status flags simulate approval gate inputs solely to test filters; they make
no claim of finance approval. They are never loaded by runtime code. Probe data is
also visibly synthetic, has namespaced option IDs, and retrieves no explanations.

Finance/catalog owners still need to provide the released version, exact question
and option semantics, approved playback/help, reviewed explanation provenance and
approval/retrievable metadata. Q4 boundary/qualifier expectations and other financial
policy decisions remain theirs. This module does not invent thresholds or decide
whether a catalog release is approved.

Implementation references: [Pydantic strict configuration](https://pydantic.dev/docs/validation/latest/api/pydantic/config/),
[HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/), and
[HTTPX test transports](https://www.python-httpx.org/advanced/transports/).
