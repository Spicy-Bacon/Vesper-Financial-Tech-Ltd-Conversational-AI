"""Construction-time release validation and mutation-isolated CatalogProvider."""

from pathlib import Path

from ..schemas import Catalog, Question
from .release import load_release


class JsonCatalogProvider:
    def __init__(self, release_directory: str | Path):
        release, explanations = load_release(release_directory)
        self._release = release.model_copy(deep=True)
        self._explanations = explanations.model_copy(deep=True)

    def load(self) -> Catalog:
        return self._release.catalog.model_copy(deep=True)

    @property
    def review(self) -> Question:
        """Q7 metadata for CS2's final-review UI; never send to interpretation."""
        return self._release.review.model_copy(deep=True)

    @property
    def question_help(self) -> dict[str, str]:
        return dict(self._release.question_help)

    @property
    def provenance(self):
        return self._release.provenance.model_copy(deep=True)

    @property
    def review_explanations(self):
        return [r.model_copy(deep=True) for r in self._explanations.records if r.question_id == "Q7"]
