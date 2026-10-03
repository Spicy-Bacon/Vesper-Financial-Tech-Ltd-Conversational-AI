"""Deterministic retrieval over a caller-supplied, versioned explanation set."""

import re
from collections.abc import Iterable

from pydantic import TypeAdapter

from ..schemas.inference import (
    ExplanationRecord, Identifier, RetrievalResult, RetrievalSnippet, UserReply,
)

_STOP_WORDS = frozenset(
    "a an and are as at be been but by can could do does for from had has have how i "
    "if in is it its me my of on or our please so some that the their them there these "
    "they this those to us was we were what when which who why will with would you your".split()
)


def _tokens(text: str) -> set[str]:
    return {word for word in re.findall(r"[^\W_]+", text.casefold())
            if len(word) > 2 and word not in _STOP_WORDS}


class QuestionScopedRetriever:
    def __init__(self, records: Iterable[ExplanationRecord]) -> None:
        # Copy and validate so the source collection cannot change under retrieval.
        self._records = tuple(ExplanationRecord.model_validate(r) for r in records)
        keys = [(r.catalog_version, r.question_id, r.content_id) for r in self._records]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate explanation record in a question/version")

    def retrieve(self, *, catalog_version: str, question_id: str,
                 user_reply: str) -> RetrievalResult:
        TypeAdapter(Identifier).validate_python(catalog_version, strict=True)
        TypeAdapter(Identifier).validate_python(question_id, strict=True)
        TypeAdapter(UserReply).validate_python(user_reply, strict=True)
        # Filter before ranking. In particular, approval cannot admit other sheets.
        candidates = [r for r in self._records
                      if r.catalog_version == catalog_version
                      and r.question_id == question_id
                      and r.approval_status == "approved"
                      and r.retrievable
                      and r.source_sheet == "Explanations"]
        query = _tokens(user_reply)
        scores = {r.content_id: len(query & _tokens(r.text)) for r in candidates}
        candidates.sort(key=lambda r: (-scores[r.content_id], r.source_row, r.content_id))
        method = "question_scoped_empty"
        if candidates:
            method = ("question_scoped_lexical" if any(scores.values())
                      else "question_scoped_order")
        return RetrievalResult(
            catalog_version=catalog_version, question_id=question_id,
            snippets=[RetrievalSnippet(
                content_id=r.content_id, text=r.text,
                source_sheet=r.source_sheet, source_row=r.source_row,
            ) for r in candidates[:3]],
            retrieval_method=method,
        )


class CatalogRetriever:
    """Thin backend Retriever bridge over a validated, pinned release.

    Files are read once at initialization. The original QuestionScopedRetriever
    API and ranking are unchanged; only its validated snippets cross the bridge.
    """

    def __init__(self, release_directory):
        from ..catalog.release import load_release

        release, explanations = load_release(release_directory)
        self._catalog = release.catalog.model_copy(deep=True)
        self._retriever = QuestionScopedRetriever(
            record for record in explanations.records if record.question_id != "Q7"
        )

    def retrieve(self, *, text, question, catalog):
        from ..schemas import Catalog, Question, RetrievedContext

        # Revalidate dumps: Pydantic's mutable backend models can be changed by
        # callers after construction. Equality also rejects same-version drift.
        if not isinstance(catalog, Catalog) or not isinstance(question, Question):
            raise ValueError("expected backend Catalog and Question")
        supplied = Catalog.model_validate(catalog.model_dump(), strict=True)
        active = Question.model_validate(question.model_dump(), strict=True)
        if supplied != self._catalog:
            raise ValueError("catalog does not match pinned release")
        expected = next((q for q in self._catalog.questions if q.id == active.id), None)
        if expected is None or active != expected or active.id == "Q7":
            raise ValueError("question does not match pinned answer catalog")
        result = self._retriever.retrieve(
            catalog_version=self._catalog.version, question_id=active.id, user_reply=text,
        )
        return [RetrievedContext(sourceId=snippet.content_id, text=snippet.text)
                for snippet in result.snippets]
