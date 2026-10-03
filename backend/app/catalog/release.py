"""Validated file envelopes around the existing backend Catalog, not a new catalog API.

Only trusted import/configuration code may set approval and its recorded basis.
"""

import hashlib
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from ..schemas import Catalog, Identifier, Question
from ..schemas.inference import ExplanationRecord, StrictContract

WORKBOOK_NAME = "CC_Question_Set_Scored_v2_Judge_Ready.xlsx"
Nonblank = Annotated[str, StringConstraints(min_length=1, max_length=8000, pattern=r"\S")]


class Provenance(StrictContract):
    workbook_filename: Literal["CC_Question_Set_Scored_v2_Judge_Ready.xlsx"]
    workbook_sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class Approval(StrictContract):
    approved: bool = False
    basis: Nonblank | None = None

    @model_validator(mode="after")
    def explicit_basis(self):
        if self.approved and self.basis is None:
            raise ValueError("finance approval requires an explicit trusted basis")
        return self


class CatalogRelease(StrictContract):
    schema_version: Literal["finance-catalog-release-v1"]
    provenance: Provenance
    approval: Approval
    catalog: Catalog
    # Exact help text is retained separately because backend Question has no help_text.
    question_help: dict[Identifier, Nonblank]
    # Q7 has the existing Question shape, but is never returned by load().
    review: Question

    @model_validator(mode="before")
    @classmethod
    def prevent_implicit_rewriting(cls, value):
        if isinstance(value, dict):
            for field, schema in (("catalog", Catalog), ("review", Question)):
                raw = value.get(field)
                if isinstance(raw, dict):
                    parsed = schema.model_validate(raw, strict=True)
                    # Reject stripped whitespace or coercion rather than changing Finance wording.
                    def check(source, target):
                        if isinstance(source, dict):
                            return all(check(v, target[k]) for k, v in source.items())
                        if isinstance(source, list):
                            return len(source) == len(target) and all(check(a, b) for a, b in zip(source, target))
                        return type(source) is type(target) and source == target
                    if not check(raw, parsed.model_dump()):
                        raise ValueError(f"{field} would rewrite supplied values")
        return value

    @model_validator(mode="after")
    def validate_scope(self):
        catalog = self.catalog
        if catalog.version in {".", ".."}:
            raise ValueError("catalog version must name one release directory")
        if catalog.financeApproved != self.approval.approved or catalog.demo:
            raise ValueError("catalog approval must match trusted release approval; demo is not a finance release")
        ids = {q.id for q in catalog.questions}
        if len(catalog.questions) != 6:
            raise ValueError("finance runtime requires six answer questions")
        for question in [*catalog.questions, self.review]:
            if any(o.label is None or o.is_unsure is None for o in question.options):
                raise ValueError("release options require authored labels and explicit unsure metadata")
            if sum(o.is_unsure is True for o in question.options) != 1:
                raise ValueError("each question requires exactly one explicit unsure option")
        if self.review.id != "Q7" or "Q7" in ids:
            raise ValueError("Q7 must be a separate review control")
        if set(self.question_help) != ids | {"Q7"}:
            raise ValueError("help text must cover exactly the answer questions and Q7")
        option_ids = [o.id for q in [*catalog.questions, self.review] for o in q.options]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("duplicate option IDs across the release")
        return self


class ExplanationsRelease(StrictContract):
    schema_version: Literal["finance-explanations-release-v1"]
    provenance: Provenance
    catalog_version: Identifier
    records: Annotated[list[ExplanationRecord], Field(max_length=1000)]

    @model_validator(mode="after")
    def validate_records(self):
        ids = [r.content_id for r in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate explanation content IDs")
        for record in self.records:
            if record.text != record.text.strip():
                raise ValueError("explanation text would be stripped by backend context validation")
            if record.catalog_version != self.catalog_version:
                raise ValueError("explanation catalog version mismatch")
            if record.source_sheet != "Explanations" or record.source_row < 2:
                raise ValueError("explanations must originate in Explanations data rows")
            if record.approval_status != "approved":
                raise ValueError("runtime release must contain only Approved explanations")
            if record.retrievable != (record.question_id != "Q7"):
                raise ValueError("Q7 explanations are review-only; answer explanations must be retrievable")
        return self


def validate_documents(catalog_data: dict, explanations_data: dict):
    """Validate both documents, references and provenance before use or writing."""
    catalog = CatalogRelease.model_validate(catalog_data, strict=True)
    explanations = ExplanationsRelease.model_validate(explanations_data, strict=True)
    if explanations.catalog_version != catalog.catalog.version:
        raise ValueError("release catalog versions differ")
    if explanations.provenance != catalog.provenance:
        raise ValueError("release workbook provenance differs")
    known = {q.id for q in catalog.catalog.questions} | {"Q7"}
    if any(r.question_id not in known for r in explanations.records):
        raise ValueError("explanation references an unknown question")
    return catalog, explanations


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("non-finite JSON number")


def read_document(path: Path):
    with path.open("rb") as stream:
        raw = stream.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("release document exceeds 2 MB")
    return json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)


def load_release(directory: str | Path):
    directory = Path(directory)
    release = validate_documents(read_document(directory / "catalog.json"),
                                 read_document(directory / "explanations.json"))
    if directory.name != release[0].catalog.version:
        raise ValueError("release directory must match catalog version")
    return release


def deterministic_json(document) -> bytes:
    data = document.model_dump(mode="json")
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def source_provenance(path: str | Path) -> Provenance:
    path = Path(path)
    if path.name != WORKBOOK_NAME:
        raise ValueError(f"exact source required: {WORKBOOK_NAME}")
    if not path.is_file():
        raise FileNotFoundError(f"required source is unavailable: {WORKBOOK_NAME}")
    return Provenance(workbook_filename=WORKBOOK_NAME,
                      workbook_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
