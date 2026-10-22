"""Checks every route into review runs (#267, #433): /submit, /workflow transitions, bulk."""

from typing import Any

from sqlalchemy.orm import Session

from app.crud.precuration_required import (
    MissingRequiredFieldsError,
    missing_required_fields,
)
from app.models import CurationNew, CurationSchema, PrecurationNew, WorkflowPair
from app.models.methodology import MethodologyVersion

LS_DECISIONS = ("LUMP", "NOT_APPLICABLE", "SPLIT")


def item_definition(db: Session, item: CurationNew | PrecurationNew) -> dict[str, Any]:
    """The pinned methodology version's snapshot; the live schema only while unpinned
    (a curation's via its workflow pair). A pin that cannot be read fails."""
    if item.methodology_version_id:
        version = db.get(MethodologyVersion, item.methodology_version_id)
        if version is None or not isinstance(version.snapshot, dict):
            raise ValueError(
                f"Pinned methodology version {item.methodology_version_id} is unreadable"
            )
        return version.snapshot
    if isinstance(item, CurationNew):
        pair = db.get(WorkflowPair, item.workflow_pair_id)
        schema_id = pair.curation_schema_id if pair else None
    else:
        schema_id = item.precuration_schema_id
    schema = db.get(CurationSchema, schema_id) if schema_id else None
    if schema is None:
        return {}
    return {
        "field_definitions": schema.field_definitions,
        "validation_rules": schema.validation_rules,
    }


def check_review_content(db: Session, item: CurationNew | PrecurationNew) -> None:
    """Network-free content checks before an item enters review, on every route there.

    Raises MissingRequiredFieldsError (dotted paths) or ValueError.
    """
    evidence = item.evidence_data or {}
    if isinstance(item, CurationNew) and not evidence:
        raise ValueError("Evidence data is required before review")
    definition = item_definition(db, item)
    if missing := missing_required_fields(
        definition.get("field_definitions"),
        evidence,
        definition.get("validation_rules"),
    ):
        raise MissingRequiredFieldsError(missing)
    if isinstance(item, PrecurationNew) and evidence.get(
        "lumping_splitting_applicable"
    ):
        decision = evidence.get("lumping_splitting_decision")
        if not decision or decision == "UNDECIDED":
            raise ValueError(
                "Lumping/splitting is marked as applicable but no decision "
                "has been made. Please select LUMP, SPLIT, or NOT_APPLICABLE "
                "before submitting."
            )
        if decision not in LS_DECISIONS:
            raise ValueError(
                f"Invalid lumping/splitting decision '{decision}'. "
                f"Must be one of: {', '.join(LS_DECISIONS)}."
            )
