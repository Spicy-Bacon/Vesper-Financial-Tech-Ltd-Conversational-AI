"""Deterministic tests; all approval metadata and content are synthetic."""

import pytest
from pydantic import ValidationError

from app.schemas.inference import ExplanationRecord, RetrievalResult, RetrievalSnippet
from app.services.retrieval import QuestionScopedRetriever
from conftest import SYNTHETIC_VERSION


def retrieve(records, reply="no matching vocabulary"):
    return QuestionScopedRetriever(records).retrieve(
        catalog_version=SYNTHETIC_VERSION, question_id="Q4", user_reply=reply,
    )


@pytest.mark.parametrize("changes", [
    {"question_id": "Q3"}, {"catalog_version": "SYNTHETIC-OLD"},
    {"approval_status": "draft"}, {"approval_status": "unapproved"},
    {"approval_status": "retired"}, {"retrievable": False},
    *[{"source_sheet": sheet} for sheet in [
        "Test_Cases", "Personas", "Open_Issues", "Mapping_Layer", "Questions",
        "Answer_Options", "Change_Log", "Read_Me", "explanations",
    ]],
])
def test_hard_filters_before_ranking(synthetic_record, changes):
    good = synthetic_record()
    excluded = synthetic_record(content_id="SYNTHETIC-EXCLUDED", **changes)
    result = retrieve([excluded, good], excluded.text)
    assert [s.content_id for s in result.snippets] == [good.content_id]
    assert result.catalog_version == SYNTHETIC_VERSION
    assert result.question_id == "Q4"


def test_cap_deterministic_order_and_provenance(synthetic_record):
    records = [synthetic_record(content_id=f"SYNTHETIC-{i}", source_row=i + 2)
               for i in range(6)]
    forward = retrieve(records)
    reverse = retrieve(list(reversed(records)))
    assert forward == reverse
    assert len(forward.snippets) == 3
    assert [s.source_row for s in forward.snippets] == [2, 3, 4]
    assert all(s.source_sheet == "Explanations" for s in forward.snippets)
    assert all(s.text == records[0].text for s in forward.snippets)
    assert forward.retrieval_method == "question_scoped_order"


def test_lexical_ranking_prefers_relevant_explanation(synthetic_record):
    records = [synthetic_record(content_id="SYNTHETIC-A", text="SYNTHETIC ordinary glossary"),
               synthetic_record(content_id="SYNTHETIC-B", source_row=3,
                                text="SYNTHETIC accessibility glossary")]
    result = retrieve(records, "Please explain ACCESSIBILITY?")
    assert result.snippets[0].content_id == "SYNTHETIC-B"
    assert result.retrieval_method == "question_scoped_lexical"


@pytest.mark.parametrize("reply", ["the and a I you", "zebras gallop", "?!"])
def test_no_meaningful_match_uses_question_order(synthetic_record, reply):
    records = [synthetic_record(content_id="SYNTHETIC-B", source_row=2),
               synthetic_record(content_id="SYNTHETIC-A", source_row=2)]
    assert [s.content_id for s in retrieve(records, reply).snippets] == ["SYNTHETIC-A", "SYNTHETIC-B"]
    assert retrieve(records, reply).retrieval_method == "question_scoped_order"


def test_no_eligible_content_is_empty(synthetic_record):
    result = retrieve([synthetic_record(approval_status="draft")])
    assert result.snippets == []
    assert result.retrieval_method == "question_scoped_empty"


def test_duplicate_content_cannot_have_ambiguous_provenance(synthetic_record):
    with pytest.raises(ValueError, match="duplicate"):
        retrieve([synthetic_record(), synthetic_record(source_row=5)])


@pytest.mark.parametrize("field,value", [
    ("source_row", "2"), ("source_row", True), ("source_row", 0),
    ("retrievable", "true"), ("text", " " * 3), ("text", "x" * 601),
    ("unexpected", "metadata"),
])
def test_records_are_strict_and_short(synthetic_record, field, value):
    data = synthetic_record().model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        ExplanationRecord.model_validate(data)


def test_result_and_snippet_forbid_extra_fields(synthetic_record):
    result = retrieve([synthetic_record()])
    with pytest.raises(ValidationError):
        RetrievalResult.model_validate({**result.model_dump(), "extra": 1})
    with pytest.raises(ValidationError):
        RetrievalSnippet.model_validate({**result.snippets[0].model_dump(), "extra": 1})
