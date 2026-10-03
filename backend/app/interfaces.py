"""Integration contracts; adapter and importer implementations belong to Harry/CS3."""
from typing import Protocol, Sequence

from .schemas import Answer, Catalog, Interpretation, Question, RetrievedContext, ScoreResult


class CatalogProvider(Protocol):
    def load(self) -> Catalog:
        """Return a versioned Finance-approved catalog; raise on unavailability."""
        ...


class Retriever(Protocol):
    def retrieve(self, *, text: str, question: Question, catalog: Catalog) -> Sequence[RetrievedContext]:
        """Return bounded, catalog-version-compatible context. Must enforce a timeout."""
        ...


class ModelAdapter(Protocol):
    def interpret(
        self, *, text: str, question: Question, catalog: Catalog,
        confirmed_answers: Sequence[Answer], context: Sequence[RetrievedContext],
    ) -> Interpretation:
        """Suggest an option ID or clarify/pause/support. Never confirm, score or save."""
        ...


class FinancePolicy(Protocol):
    def evaluate(self, *, answers: Sequence[Answer], catalog: Catalog) -> ScoreResult:
        """Apply only Finance-approved meanings, points and formulas, with a version."""
        ...
