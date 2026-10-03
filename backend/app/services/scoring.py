"""Do not invent points or formulas here: Finance supplies the policy."""
from ..errors import IntegrationUnavailable
from ..interfaces import FinancePolicy
from ..schemas import Answer, Catalog, ScoreResult
from .rules import require_complete


class ScoringService:
    def __init__(self, policy: FinancePolicy | None = None):
        self.policy = policy

    def score(self, answers: list[Answer], catalog: Catalog) -> ScoreResult:
        require_complete(catalog, answers)
        if self.policy is None:
            return ScoreResult(catalogVersion=catalog.version)
        try:
            result = ScoreResult.model_validate(self.policy.evaluate(
                answers=[a.model_copy(deep=True) for a in answers], catalog=catalog.model_copy(deep=True),
            ))
            if result.status != "scored" or result.catalogVersion != catalog.version:
                raise ValueError("Finance policy/catalog mismatch.")
            return result
        except Exception as exc:
            raise IntegrationUnavailable() from exc
