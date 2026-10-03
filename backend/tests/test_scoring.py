from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.app.errors import ConversationError, IntegrationUnavailable
from backend.app.schemas import Answer, Catalog, ScoreResult
from backend.app.services.scoring import ScoringService
from backend.tests.conftest import TestCatalogProvider


def complete_answers(catalog):
    return [Answer(questionId=q.id, optionId=q.options[0].id, label=q.label, answer=q.options[0].answer)
            for q in catalog.questions]


def test_scoring_delegates_to_versioned_finance_policy():
    catalog = TestCatalogProvider().load()
    answers = complete_answers(catalog)
    class SyntheticPolicy:
        def evaluate(self, *, answers, catalog):
            assert len(answers) == 2
            # Tests interface plumbing only; this value is not a financial score/formula.
            return ScoreResult(status="scored", policyVersion="test-policy", catalogVersion=catalog.version,
                               values={"fixture_value": Decimal("1.25")}, classification="Synthetic test label")
    result = ScoringService(SyntheticPolicy()).score(answers, catalog)
    assert result.values["fixture_value"] == Decimal("1.25")


def test_unconfigured_scoring_has_no_invented_values():
    catalog = TestCatalogProvider().load()
    result = ScoringService().score(complete_answers(catalog), catalog)
    assert result.status == "not_configured" and result.values == {} and result.classification is None


@pytest.mark.parametrize("variant", ["incomplete", "duplicate", "tampered"])
def test_incomplete_duplicate_or_noncanonical_answers_cannot_score(variant):
    catalog = TestCatalogProvider().load()
    answers = complete_answers(catalog)
    if variant == "incomplete":
        answers.pop()
    elif variant == "duplicate":
        answers[1] = answers[0]
    else:
        answers[0].answer = "Injected meaning"
    with pytest.raises(ConversationError):
        ScoringService().score(answers, catalog)


def test_policy_catalog_mismatch_is_rejected():
    catalog = TestCatalogProvider().load()
    class WrongPolicy:
        def evaluate(self, **kwargs):
            return ScoreResult(status="scored", policyVersion="test", catalogVersion="wrong")
    with pytest.raises(IntegrationUnavailable):
        ScoringService(WrongPolicy()).score(complete_answers(catalog), catalog)


@pytest.mark.parametrize("extra", [
    {"status": "scored"}, {"values": {"x": Decimal("1")}},
    {"status": "scored", "policyVersion": "test", "values": {"x": Decimal("NaN")}},
])
def test_score_schema_rejects_unversioned_or_invalid_outputs(extra):
    with pytest.raises(ValidationError):
        ScoreResult(catalogVersion="test-v1", **extra)


def test_catalog_rejects_duplicate_identifiers():
    catalog = TestCatalogProvider().load().model_dump()
    catalog["questions"].append(catalog["questions"][0])
    with pytest.raises(ValidationError):
        Catalog.model_validate(catalog)
