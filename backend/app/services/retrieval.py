"""Deterministic retrieval over a caller-supplied, versioned explanation set."""

import re
from collections.abc import Iterable

from pydantic import TypeAdapter

from app.schemas.inference import (
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
