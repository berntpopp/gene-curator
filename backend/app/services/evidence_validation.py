"""Evidence items are checked against the evidence tables of their curation's schema."""

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.schema_validator import schema_validator
from app.models import CurationNew
from app.scoring.evidence_items import has_content
from app.services.publication_service import evidence_pmids, lookup_pmids
from app.services.review_guards import item_definition


def _tables(node: Any, path: str = "") -> dict[str, dict[str, Any]]:
    """Evidence tables (arrays of row objects) under a schema node, by dotted path."""
    if not isinstance(node, dict):
        return {}
    items = node.get("items")
    if path and isinstance(items, dict) and isinstance(items.get("properties"), dict):
        return {path: items["properties"]}
    found: dict[str, dict[str, Any]] = {}
    for key, child in (node.get("properties") or {}).items():
        found |= _tables(child, f"{path}.{key}" if path else key)
    return found


def _error(loc: list[str], msg: str) -> dict[str, Any]:
    return {"loc": ["body", *loc], "msg": msg, "type": "value_error"}


def evidence_item_errors(
    definition: dict[str, Any], category: str, evidence_type: str, data: Any
) -> list[dict[str, Any]]:
    """FastAPI-shaped errors for an item that does not fit the schema's evidence tables."""
    fields = definition.get("field_definitions") or {}
    groups = {
        key.removesuffix("_evidence"): found
        for key, node in fields.items()
        if key.endswith("_evidence") and (found := _tables(node))
    }
    if not groups:
        return [
            _error(
                ["evidence_category"],
                "This curation's schema defines no evidence tables; record evidence "
                "in the curation's evidence_data (save_draft_curations) instead",
            )
        ]
    tables = groups.get(evidence_type)
    if tables is None:
        return [
            _error(["evidence_type"], f"Expected one of: {', '.join(sorted(groups))}")
        ]
    columns = tables.get(category)
    if columns is None:
        return [
            _error(
                ["evidence_category"],
                f"Unknown category for evidence_type '{evidence_type}'; expected one "
                f"of: {', '.join(sorted(tables))}",
            )
        ]
    expected = f"expected fields: {', '.join(sorted(columns))}"
    if not isinstance(data, dict) or not has_content(data):
        return [_error(["evidence_data"], f"Must not be empty; {expected}")]
    errors = [
        _error(["evidence_data", key], f"Unknown field; {expected}")
        for key in data
        if key not in columns
    ]
    result = schema_validator.validate_evidence_data(
        data, {"field_definitions": columns}
    )
    return errors + [
        _error(["evidence_data", e["field"]], e["message"]) for e in result.errors
    ]


def _pmid_format_errors(data: Any) -> list[dict[str, Any]]:
    pmid = str(data.get("pmid") or "").strip() if isinstance(data, dict) else ""
    if pmid and not evidence_pmids({"pmid": pmid}):
        return [_error(["evidence_data", "pmid"], "Expected 1-9 digits, e.g. 31558469")]
    return []


def validate_evidence_item(
    db: Session,
    curation: CurationNew,
    category: str,
    evidence_type: str,
    data: Any,
    stored: bool = False,
) -> list[str]:
    """422 naming each bad field and the expected format, or a PMID PubMed does not
    know. Returns the PMIDs whose lookup failed (offline): saved, but unverified.
    A stored item whose category is no table path (legacy flat categories) keeps
    only the PMID checks, so it stays editable."""
    definition = item_definition(db, curation)
    errors = evidence_item_errors(definition, category, evidence_type, data)
    if (
        stored
        and errors
        and all(e["loc"][1] in ("evidence_category", "evidence_type") for e in errors)
    ):
        errors = _pmid_format_errors(data)
    unverified: list[str] = []
    if not errors:
        unknown, unverified = lookup_pmids(db, evidence_pmids(data))
        errors = [
            _error(["evidence_data", "pmid"], f"PMID {pmid} not found in PubMed")
            for pmid in unknown
        ]
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=errors
        )
    return unverified
