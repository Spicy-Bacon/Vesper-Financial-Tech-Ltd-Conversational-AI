"""Deterministic transcription of Finance-approved team-scoring-v2, SR01–SR09.

Source: data/source/212d7a0a7649f6add4706d683539822f3d518e625164ce6e8379eef06c4fdf57/
CC_Question_Set_Scored_v2_Judge_Ready.xlsx, Answer_Options and Scoring_Rules.
No workbook formulas or points are inferred from user text or option wording.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from ..schemas import Answer, Catalog, ScoreResult
from .rules import require_complete


class WorkbookFinancePolicy:
    policy_version = "team-scoring-v2"
    catalog_version = "catalog-v2"
    # Exact authored points. Unsure has no points, rather than zero.
    points = {
        "Q1_A": 1, "Q1_B": 2, "Q1_C": 3, "Q1_D": 4, "Q1_U": None,
        "Q2_A": 1, "Q2_B": 2, "Q2_C": 3, "Q2_D": 4, "Q2_U": None,
        "Q3_A": 1, "Q3_B": 2, "Q3_C": 3, "Q3_D": 4, "Q3_U": None,
        "Q4_A": 1, "Q4_B": 2, "Q4_C": 3, "Q4_D": 4, "Q4_U": None,
        "Q5_A": 1, "Q5_B": 2, "Q5_C": 3, "Q5_D": 4, "Q5_U": None,
        "Q6_A": 1, "Q6_B": 2, "Q6_C": 3, "Q6_D": 4, "Q6_E": 5, "Q6_F": 6, "Q6_U": None,
    }
    dimensions = {
        "attitude": (("Q1", "Q2"), 2, 8),
        "capacity": (("Q3", "Q4", "Q5"), 3, 12),
        "horizon": (("Q6",), 1, 6),
    }

    def __init__(self, catalog: Catalog):
        if catalog.version != self.catalog_version or catalog.demo or not catalog.financeApproved:
            raise ValueError("WorkbookFinancePolicy requires the approved non-demo catalog-v2 release.")
        options = {o.id: o for q in catalog.questions for o in q.options}
        if {q.id for q in catalog.questions} != {"Q1", "Q2", "Q3", "Q4", "Q5", "Q6"}:
            raise ValueError("Finance policy question IDs do not match the catalog.")
        if set(options) != set(self.points) or any(
            options[oid].is_unsure != (points is None) for oid, points in self.points.items()
        ):
            raise ValueError("Finance policy option IDs or Unsure metadata do not match the catalog.")
        if any(not o.id.startswith(q.id + "_") for q in catalog.questions for o in q.options):
            raise ValueError("Finance policy options must belong to their authored questions.")
        self._catalog = catalog.model_copy(deep=True)

    @staticmethod
    def category(overall: Decimal | None) -> str:
        if overall is None:
            return "Not assigned"
        if not overall.is_finite() or overall != overall.to_integral_value() or not 0 <= overall <= 100:
            raise ValueError("Overall score must be a whole number between 0 and 100.")
        return "Low" if overall <= 39 else "Medium" if overall <= 69 else "High"

    def evaluate(self, *, answers: Sequence[Answer], catalog: Catalog) -> ScoreResult:
        if catalog != self._catalog:
            raise ValueError("Finance policy/catalog mismatch.")
        # Also protects direct callers: complete, unique, canonical confirmed records only.
        require_complete(catalog, answers)
        selected = {a.questionId: self.points[a.optionId] for a in answers}
        values, unresolved = {}, []
        for dimension, (questions, minimum, maximum) in self.dimensions.items():
            points = [selected[qid] for qid in questions]
            if any(point is None for point in points):
                unresolved.append(dimension)
                continue
            raw = Decimal(sum(points))
            values[dimension + "_raw"] = raw
            values[dimension] = ((raw - minimum) / (maximum - minimum) * 100).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP,
            )
        overall = None if unresolved else min(values[d] for d in self.dimensions)
        limiting = []
        if overall is not None:
            values["overall"] = overall
            limiting = [d for d in self.dimensions if values[d] == overall]
        return ScoreResult(
            status="scored", policyVersion=self.policy_version, catalogVersion=catalog.version,
            values=values, classification=self.category(overall),
            limitingDimensions=limiting, unresolvedDimensions=unresolved,
        )
