"""SYNTHETIC interface tests. MockTransport tests do not measure Qwen quality.

No question wording, finance meaning or expected mapping is copied from the older
Handoff workbook. Synthetic approval flags only exercise the existing gate.
"""

import copy
import hashlib
import json
import os
from pathlib import Path
from time import perf_counter

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.adapters.omlx import OmlxAdapter
from backend.app.catalog import JsonCatalogProvider
from backend.app.catalog.release import (
    WORKBOOK_NAME, deterministic_json, load_release, read_document,
    source_provenance, validate_documents,
)
from backend.app.errors import IntegrationUnavailable
from backend.app.interfaces import CatalogProvider, ModelAdapter, Retriever
from backend.app.main import create_app
from backend.app.schemas import Catalog
from backend.app.services.retrieval import CatalogRetriever
from backend.scripts.import_finance_workbook import main as import_main
from backend.tests.conftest import Journey

VERSION = "SYNTHETIC-CATALOG-INTERFACE-v1"


@pytest.fixture
def documents():
    provenance = {"workbook_filename": WORKBOOK_NAME, "workbook_sha256": "a" * 64}
    def question(qid, options, safety=False):
        return {"id": qid, "label": f"SYNTHETIC {qid}", "prompt": "SYNTHETIC choose a token.",
                "clarification": "SYNTHETIC please clarify the token.",
                "requiresExplicitConfirmation": safety,
                "options": [{"id": f"{qid}_{token}", "answer": f"SYNTHETIC playback {token}."}
                            for token in options]}
    # Deliberate non-alphabetical order proves the provider preserves array order.
    questions = [question("Q4", ["BLUE", "RED", "UNSURE"], True), question("Q3", ["GREEN"])]
    catalog = {
        "schema_version": "finance-catalog-release-v1", "provenance": provenance,
        "approval": {"approved": True, "basis": "SYNTHETIC fixture only; no Finance approval."},
        "catalog": {"version": VERSION, "financeApproved": True, "demo": False, "questions": questions},
        "question_help": {qid: f"SYNTHETIC help for {qid}." for qid in ["Q4", "Q3", "Q7"]},
        "review": question("Q7", ["CONFIRM", "CORRECT", "UNSURE"]),
    }
    records = [{"content_id": f"SYN_EX_{i}", "question_id": "Q4",
                "text": f"SYNTHETIC token glossary entry {i}.", "source_sheet": "Explanations",
                "source_row": i + 2, "catalog_version": VERSION,
                "approval_status": "approved", "retrievable": True} for i in range(5)]
    records += [{**records[0], "content_id": "SYN_OTHER", "question_id": "Q3", "source_row": 8},
                {**records[0], "content_id": "SYN_REVIEW", "question_id": "Q7",
                 "retrievable": False, "source_row": 9}]
    explanations = {"schema_version": "finance-explanations-release-v1", "provenance": provenance,
                    "catalog_version": VERSION, "records": records}
    return catalog, explanations


def write_fixture(tmp_path, documents):
    release, explanations = validate_documents(*documents)
    directory = tmp_path / release.catalog.version
    directory.mkdir()
    (directory / "catalog.json").write_bytes(deterministic_json(release))
    (directory / "explanations.json").write_bytes(deterministic_json(explanations))
    return directory


@pytest.fixture
def release_dir(tmp_path, documents):
    return write_fixture(tmp_path, documents)


def test_release_determinism_and_canonical_order(documents, release_dir):
    first = validate_documents(*documents)
    second = load_release(release_dir)
    assert [deterministic_json(d) for d in first] == [deterministic_json(d) for d in second]
    provider: CatalogProvider = JsonCatalogProvider(release_dir)
    catalog = provider.load()
    assert isinstance(catalog, Catalog)
    assert [q.id for q in catalog.questions] == ["Q4", "Q3"]
    assert [o.id for o in catalog.questions[0].options] == ["Q4_BLUE", "Q4_RED", "Q4_UNSURE"]
    assert catalog.questions[0].options[0].answer == "SYNTHETIC playback BLUE."
    assert catalog.questions[0].requiresExplicitConfirmation is True
    assert provider.review.id == "Q7"
    assert provider.question_help["Q4"] == "SYNTHETIC help for Q4."
    assert [r.content_id for r in provider.review_explanations] == ["SYN_REVIEW"]
    assert "Q7" not in catalog.model_dump_json()


def test_provider_copies_and_initialization_only_io(release_dir):
    provider = JsonCatalogProvider(release_dir)
    retriever: Retriever = CatalogRetriever(release_dir)
    original = provider.load()
    changed = provider.load()
    changed.questions[0].options[0].answer = "changed"
    changed.questions.clear()
    provider.review.options.clear()
    provider.question_help.clear()
    (release_dir / "catalog.json").unlink()
    (release_dir / "explanations.json").unlink()
    assert provider.load() == original
    assert provider.review.options
    assert provider.question_help
    assert len(retriever.retrieve(text="glossary", catalog=original, question=original.questions[0])) == 3


def test_bridge_filters_caps_and_preserves_ids(release_dir):
    provider = JsonCatalogProvider(release_dir)
    catalog = provider.load()
    retriever = CatalogRetriever(release_dir)
    result = retriever.retrieve(text="glossary", catalog=catalog, question=catalog.questions[0])
    assert [r.sourceId for r in result] == ["SYN_EX_0", "SYN_EX_1", "SYN_EX_2"]
    assert retriever.retrieve(text="glossary", catalog=catalog, question=catalog.questions[0]) == result
    assert [r.sourceId for r in retriever.retrieve(text="glossary", catalog=catalog,
                                                question=catalog.questions[1])] == ["SYN_OTHER"]
    _, explanations = load_release(release_dir)
    assert explanations.records[0].source_sheet == "Explanations"
    assert explanations.records[0].source_row == 2
    with pytest.raises(ValueError, match="question"):
        retriever.retrieve(text="glossary", catalog=catalog, question=provider.review)


@pytest.mark.parametrize("mutation", ["version", "wording", "options", "approval", "unknown_question"])
def test_bridge_rejects_incompatible_inputs(release_dir, mutation):
    catalog = JsonCatalogProvider(release_dir).load()
    question = catalog.questions[0].model_copy(deep=True)
    if mutation == "version":
        catalog.version = "wrong-version"
    elif mutation == "wording":
        question.prompt = "different wording"
    elif mutation == "options":
        question.options.pop()
    elif mutation == "approval":
        catalog.financeApproved = False
    else:
        question.id = "unknown"
    with pytest.raises(ValueError):
        CatalogRetriever(release_dir).retrieve(text="token", catalog=catalog, question=question)


@pytest.mark.parametrize("field,value", [
    ("question_id", "unknown"), ("catalog_version", "wrong-version"),
    ("approval_status", "draft"), ("approval_status", "unapproved"),
    ("source_sheet", "Test_Cases"), ("source_sheet", "Scoring_Rules"),
    ("source_sheet", "Score_Test_Cases"), ("source_sheet", "Personas"),
    ("source_sheet", "Change_Log"), ("source_sheet", "Judge_Readiness"),
    ("source_sheet", "Integration_Map"), ("source_sheet", "Demo_Cases"),
    ("source_row", 1), ("source_row", True), ("text", "x" * 601),
])
def test_release_rejects_unapproved_or_incompatible_records(documents, field, value):
    documents[1]["records"][0][field] = value
    with pytest.raises(ValueError):
        validate_documents(*documents)


@pytest.mark.parametrize("case", ["duplicate_question", "duplicate_option", "duplicate_explanation",
                                  "safety", "version", "provenance", "approval", "basis", "help",
                                  "q7", "review_retrievable", "score", "expectation", "whitespace"])
def test_bad_release_fails_before_use(documents, case):
    c, e = documents
    q = c["catalog"]["questions"][0]
    if case == "duplicate_question": c["catalog"]["questions"].append(copy.deepcopy(q))
    elif case == "duplicate_option": q["options"].append(copy.deepcopy(q["options"][0]))
    elif case == "duplicate_explanation": e["records"].append(copy.deepcopy(e["records"][0]))
    elif case == "safety": q["requiresExplicitConfirmation"] = "true"
    elif case == "version": e["catalog_version"] = "wrong"
    elif case == "provenance": e["provenance"] = {**e["provenance"], "workbook_sha256": "b" * 64}
    elif case == "approval": c["catalog"]["financeApproved"] = False
    elif case == "basis": c["approval"]["basis"] = None
    elif case == "help": del c["question_help"]["Q4"]
    elif case == "q7": c["catalog"]["questions"].append(copy.deepcopy(c["review"]))
    elif case == "review_retrievable": e["records"][-1]["retrievable"] = True
    elif case == "score": q["options"][0]["score"] = 4
    elif case == "expectation": e["records"][0]["expected_option_id"] = "Q4_BLUE"
    elif case == "whitespace": q["prompt"] = " " + q["prompt"]
    with pytest.raises(ValueError):
        validate_documents(c, e)


def test_duplicate_json_keys_and_wrong_directory_rejected(release_dir):
    path = release_dir / "duplicate.json"
    path.write_text('{"version":1,"version":2}')
    with pytest.raises(ValueError, match="duplicate"):
        read_document(path)
    moved = release_dir.rename(release_dir.with_name("wrong-version"))
    with pytest.raises(ValueError, match="directory"):
        JsonCatalogProvider(moved)


def test_import_scaffold_does_not_substitute_or_publish(tmp_path, capsys):
    missing = tmp_path / WORKBOOK_NAME
    assert import_main([str(missing)]) == 2
    assert "unavailable" in capsys.readouterr().err
    older = tmp_path / "CC_Question_Set_Scored_v2_Handoff.xlsx"
    older.write_bytes(b"SYNTHETIC placeholder, not a workbook")
    assert import_main([str(older)]) == 2
    assert "exact source required" in capsys.readouterr().err
    # Presence/name alone never authorizes publication or approval.
    missing.write_bytes(b"SYNTHETIC bytes used only to test source hashing")
    assert source_provenance(missing).workbook_sha256 == hashlib.sha256(missing.read_bytes()).hexdigest()
    assert import_main([str(missing)]) == 2
    assert "No files written" in capsys.readouterr().err
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([WORKBOOK_NAME, older.name])


def mocked_adapter(handler):
    return OmlxAdapter(base_url="http://synthetic.test/v1", model="SYNTHETIC-model",
                       api_key="SYNTHETIC-key", transport=httpx.MockTransport(handler))


def complete(kind="proposal", option="Q4_BLUE"):
    decision = {"kind": kind}
    if option is not None:
        decision["optionId"] = option
    return httpx.Response(200, json={"choices": [{"finish_reason": "stop",
        "message": {"role": "assistant", "content": json.dumps(decision)}}]})


def test_mocked_adapter_gets_all_options_and_question_only_context(release_dir):
    catalog = JsonCatalogProvider(release_dir).load()
    q4 = catalog.questions[0]
    context = CatalogRetriever(release_dir).retrieve(text="token", question=q4, catalog=catalog)
    def handler(request):
        prompt = json.loads(json.loads(request.content)["messages"][1]["content"])
        assert prompt["question"]["options"] == [o.model_dump() for o in q4.options]
        assert prompt["question"]["requiresExplicitConfirmation"] is True
        assert [r["sourceId"] for r in prompt["context"]] == ["SYN_EX_0", "SYN_EX_1", "SYN_EX_2"]
        assert "SYN_OTHER" not in request.content.decode() and "Q7" not in request.content.decode()
        assert "score" not in prompt["question"]
        return complete()
    model: ModelAdapter = mocked_adapter(handler)
    assert model.interpret(text="token", question=q4, catalog=catalog,
                           confirmed_answers=[], context=context).optionId == "Q4_BLUE"


def test_mocked_conversation_keeps_proposal_confirmation_and_acceptance_separate(release_dir, repository):
    def handler(request):
        qid = json.loads(json.loads(request.content)["messages"][1]["content"])["question"]["id"]
        return complete(option="Q4_BLUE" if qid == "Q4" else "Q3_GREEN")
    with TestClient(create_app(repository=repository, catalog=JsonCatalogProvider(release_dir),
                              retrieval=CatalogRetriever(release_dir), model=mocked_adapter(handler))) as client:
        journey = Journey(client)
        journey.send("start")
        proposal = journey.send("message", message={"role": "user", "text": "SYNTHETIC token"})
        assert proposal["confirmedAnswers"] == [] and proposal["proposal"]["safety"] is True
        assert repository.list_for_session(journey.session_id) == []
        assert journey.post(journey.body("save")).status_code == 422
        assert journey.post(journey.body("confirm", questionId="Q4", optionId="Q4_BLUE")).status_code == 422
        journey.send("confirm", questionId="Q4", optionId="Q4_BLUE", explicitConfirmation=True)
        journey.send("message", message={"role": "user", "text": "SYNTHETIC other token"})
        review = journey.send("confirm", questionId="Q3", optionId="Q3_GREEN")
        assert review["type"] == "final_playback"
        assert repository.list_for_session(journey.session_id) == []
        assert journey.send("save")["saveStatus"] == "saved"
        assert len(repository.list_for_session(journey.session_id)) == 1


def test_mocked_unknown_model_option_does_not_advance_or_save(release_dir, repository):
    with TestClient(create_app(repository=repository, catalog=JsonCatalogProvider(release_dir),
                              retrieval=CatalogRetriever(release_dir),
                              model=mocked_adapter(lambda request: complete(option="Q7_CONFIRM")))) as client:
        journey = Journey(client)
        journey.send("start")
        assert journey.post(journey.body("message", message={"role": "user", "text": "token"})).status_code == 503
        assert repository.list_for_session(journey.session_id) == []
        with repository.transaction() as db:
            state = repository.load_session(db, journey.session_id)
        assert state["revision"] == journey.revision and state["answers"] == [] and state["proposal"] is None


def test_unapproved_provider_keeps_existing_gate(documents, tmp_path, repository):
    documents[0]["approval"] = {"approved": False, "basis": None}
    documents[0]["catalog"]["financeApproved"] = False
    directory = write_fixture(tmp_path, documents)
    provider = JsonCatalogProvider(directory)
    assert provider.load().financeApproved is False
    with TestClient(create_app(repository=repository, catalog=provider,
                              model=mocked_adapter(lambda request: complete()))) as client:
        assert client.get("/api/catalog").status_code == 503


def test_real_judge_ready_import_is_blocked_until_source_is_inspected():
    pytest.skip("BLOCKED: exact Judge_Ready workbook unavailable; header mapping and real import not implemented")


@pytest.mark.parametrize("reply,kind,option", [
    ("I keep six months of expenses in an easy-access account.", "proposal", "Q4_D"),
    ("About three months' worth.", "clarification", None),
    ("I've got £2,000 in a savings account.", "clarification", None),
    ("I honestly don't know.", "proposal", "Q4_U"),
])
def test_live_q4_opt_in(reply, kind, option):
    if os.environ.get("VESPER_LIVE_Q4") != "1":
        pytest.skip("live Qwen test requires VESPER_LIVE_Q4=1")
    directory = os.environ.get("VESPER_CATALOG_RELEASE")
    if not directory or not Path(directory).is_dir():
        pytest.skip("BLOCKED: real imported Judge_Ready release not available")
    provider = JsonCatalogProvider(directory)
    catalog = provider.load()
    if catalog.version.startswith("SYNTHETIC") or not catalog.financeApproved:
        pytest.fail("live Q4 evaluation requires a trusted approved real release")
    source = Path("data/source") / provider.provenance.workbook_sha256 / WORKBOOK_NAME
    if not source.is_file():
        pytest.skip("BLOCKED: original Judge_Ready workbook not archived")
    assert source_provenance(source) == provider.provenance
    from backend.app.settings import Settings
    settings = Settings.load()
    if not settings.OMLX_API_KEY or not settings.OMLX_MODEL:
        pytest.skip("BLOCKED: oMLX server-side settings incomplete")
    model = OmlxAdapter(base_url=settings.OMLX_BASE_URL, model=settings.OMLX_MODEL,
                        api_key=settings.OMLX_API_KEY.get_secret_value())
    try:
        model.check_model()
    except IntegrationUnavailable:
        pytest.skip("BLOCKED: endpoint unavailable or exact configured model not listed")
    q4 = next(q for q in catalog.questions if q.id == "Q4")
    context = CatalogRetriever(directory).retrieve(text=reply, question=q4, catalog=catalog)
    started = perf_counter()
    try:
        actual = model.interpret(text=reply, question=q4, catalog=catalog, confirmed_answers=[], context=context)
    except IntegrationUnavailable as error:
        if isinstance(error.__cause__, (httpx.RequestError, httpx.HTTPStatusError)):
            pytest.skip("BLOCKED: model inference unavailable")
        pytest.fail("Model returned invalid output; coordinate OmlxAdapter validation/prompt with CS2")
    print(json.dumps({"case": reply, "observed_kind": actual.kind, "observed_option_id": actual.optionId,
                      "latency_ms": round((perf_counter() - started) * 1000)}))
    assert (actual.kind, actual.optionId) == (kind, option), (
        "Q4 mapping failed: coordinate OmlxAdapter.SYSTEM_PROMPT with CS2 to clarify approximate "
        "boundary values and missing expense denominators, preserve explicit Unsure, and never default. "
        "Do not hard-code utterances; rerun all four cases after any coordinated prompt change."
    )
