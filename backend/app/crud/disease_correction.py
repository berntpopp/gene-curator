"""Audited correction of a legacy curation's disease entity (#453): a scope admin writes
the curation's own disease answers, with a reason, when neither its evidence nor a usable
linked precuration supplies them. Nothing is inherited, backfilled or re-pinned."""

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.curation import open_conflict_message
from app.crud.optimistic_lock import claim_version
from app.crud.precuration_entity import conflict, curation_entity_key
from app.models import AuditLogNew, CurationNew, CurationStatus, UserNew
from app.schemas.curation import disease_fields, relationship_type
from app.schemas.disease_correction import DiseaseCorrection

_FIELDS = ("disease_name", "mondo_id", "mode_of_inheritance", "relationship_type")


def _named(
    evidence: dict[str, Any], precuration: dict[str, Any] | None, key: str
) -> dict[str, Any]:
    """The disease entity the record names: its own answers, else its precuration's."""
    return {
        **disease_fields(evidence, precuration),
        "relationship_type": relationship_type(evidence, precuration),
        "entity_key": key,
    }


def correct_disease(
    db: Session, curation: CurationNew, body: DiseaseCorrection, user: UserNew
) -> bool:
    """Write the corrected disease answers (nested, and flat keys the record already has,
    which take precedence) plus the entity_key they name, and an audit row with the old and
    new values and the reason. False if lock_version is stale."""
    if curation.status not in (CurationStatus.DRAFT, CurationStatus.REJECTED):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only a draft or sent-back curation can have its disease entity corrected",
        )
    evidence = dict(curation.evidence_data or {})
    entity = evidence.get("entity_definition", {})
    if not isinstance(entity, dict):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "entity_definition is malformed; it cannot be corrected here",
        )
    values = body.model_dump(include=set(_FIELDS), exclude_none=True)
    evidence["entity_definition"] = {**entity, **values}
    evidence.update({k: v for k, v in values.items() if k in evidence})
    pre = curation.precuration.evidence_data if curation.precuration else None
    key = curation_entity_key(db, evidence, pre)
    if key != curation.entity_key:
        other = db.scalar(
            select(CurationNew.id).where(
                CurationNew.gene_id == curation.gene_id,
                CurationNew.scope_id == curation.scope_id,
                CurationNew.entity_key == key,
                CurationNew.id != curation.id,
                CurationNew.status.notin_(
                    [CurationStatus.ACTIVE, CurationStatus.ARCHIVED]
                ),
            )
        )
        if other:
            raise conflict(open_conflict_message(db, other), curation_id=other)
    old = _named(curation.evidence_data or {}, pre, curation.entity_key)
    curation_id, scope_id = curation.id, curation.scope_id
    try:
        if not claim_version(
            db,
            CurationNew,
            curation_id,
            body.lock_version,
            evidence_data=evidence,
            entity_key=key,
            updated_by=user.id,
            # ClinGen's record named the old entity
            **({"clingen_reference": None} if key != curation.entity_key else {}),
        ):
            return False
    except IntegrityError:  # a concurrent curation of this entity won the open index
        db.rollback()
        raise conflict(
            "This disease entity already has an open curation in this scope"
        ) from None
    db.add(
        AuditLogNew(
            entity_type="curations",
            entity_id=curation_id,
            operation="UPDATE",
            change_type="disease_correction",
            scope_id=scope_id,
            user_id=user.id,
            old_values=old,
            new_values=_named(evidence, pre, key),
            changes={"reason": body.reason},
        )
    )
    db.commit()
    return True
