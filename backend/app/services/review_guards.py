"""Checks every route into review runs (#267, #433): /submit, /workflow transitions, bulk."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.precuration_required import (
    MissingRequiredFieldsError,
    missing_required_fields,
)
from app.models import CurationNew, CurationSchema, PrecurationNew, WorkflowPair
from app.models.methodology import MethodologyVersion
from app.schemas.curation import EvidenceWarning, disease_fields
from app.scoring.point_limits import scoring_configuration
from app.scoring.registry import engine_for
from app.services.evidence_ids import InvalidEvidenceError, evidence_errors

LS_DECISIONS = ("LUMP", "NOT_APPLICABLE", "SPLIT")
# Why a row with points scores 0 (scoring/evidence_items.uncited): refused on review entry
_UNCITED = {
    "no_pmid": "Scored row needs a PMID",
    "no_variant": "Scored case-level row needs a variant",
    "placeholder_variant": "Scored case-level row needs a real variant: HGVS (c./p./g.), "
    "an rsID or a genomic coordinate",
    "missing_status": "Case-level row with points needs a score_status: score, review "
    "or contradicts",
}


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


def _curation_review_evidence(db: Session, item: CurationNew) -> dict[str, Any]:
    """Validate inherited disease fields without writing them into saved evidence."""
    evidence = item.evidence_data or {}
    entity = evidence.get("entity_definition", {})
    if not item.precuration_id or not isinstance(entity, dict):
        return evidence
    precuration = db.scalar(
        select(PrecurationNew).where(
            PrecurationNew.id == item.precuration_id,
            PrecurationNew.scope_id == item.scope_id,
            PrecurationNew.gene_id == item.gene_id,
        )
    )
    disease = disease_fields(
        evidence, precuration.evidence_data if precuration else None
    )
    # Display falls back on empty values; validation must retain explicit empty answers.
    entity = {
        **disease,
        **entity,
        **{key: evidence[key] for key in disease if key in evidence},
    }
    return {**evidence, "entity_definition": entity}


def _uncited_rows(
    db: Session, item: CurationNew, evidence: dict[str, Any]
) -> list[EvidenceWarning]:
    """Rows the pinned engine scores 0 for a missing citation or variant, by field path."""
    config = scoring_configuration(
        db, item.workflow_pair_id, item.methodology_version_id
    )
    excluded = engine_for(config).calculate_scores(evidence, config).evidence_breakdown
    return [
        EvidenceWarning(path=f"{e['path']}.{e['field']}", message=_UNCITED[e["reason"]])
        for e in excluded.get("excluded", [])
        if e.get("reason") in _UNCITED
    ]


def check_review_content(db: Session, item: CurationNew | PrecurationNew) -> None:
    """Network-free content checks before an item enters review, on every route there.

    Raises MissingRequiredFieldsError (dotted paths), InvalidEvidenceError (schema and
    ID-format errors by path) or ValueError.
    """
    evidence = item.evidence_data or {}
    if isinstance(item, CurationNew) and not evidence:
        raise ValueError("Evidence data is required before review")
    if isinstance(item, CurationNew):
        evidence = _curation_review_evidence(db, item)
    definition = item_definition(db, item)
    if missing := missing_required_fields(
        definition.get("field_definitions"),
        evidence,
        definition.get("validation_rules"),
    ):
        raise MissingRequiredFieldsError(missing)
    if errors := evidence_errors(evidence, definition):
        raise InvalidEvidenceError(errors)
    if isinstance(item, CurationNew) and (uncited := _uncited_rows(db, item, evidence)):
        raise InvalidEvidenceError(uncited)
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
