"""Precuration disease entities (#530): the key, the author's open draft per entity, saves
the open-draft index refuses, and curation saves that would move the entity (#539)."""

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, exists, literal, literal_column, or_, select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db_types import compatible_jsonb
from app.crud.optimistic_lock import update_if_version
from app.models import CurationNew, CurationStatus, PrecurationNew
from app.models.curation import ENTITY_KEY_SQL
from app.schemas.curation import disease_fields, relationship_type, risk_allele


def conflict(message: str, **ids: UUID) -> HTTPException:
    """409 naming the existing record a unique entity index protects (#530)."""
    return HTTPException(
        409, {"message": message, **{k: str(v) for k, v in ids.items()}}
    )


def entity_key_of(db: Session, evidence: dict[str, Any]) -> str:
    """The entity_key the precurations column derives from this evidence (same SQL)."""
    row = select(
        literal(evidence, compatible_jsonb()).label("evidence_data")
    ).subquery()
    return db.scalar(select(literal_column(ENTITY_KEY_SQL)).select_from(row)) or ""


def curation_entity_key(
    db: Session, evidence: dict[str, Any], precuration: dict[str, Any] | None
) -> str:
    """The key a curation's evidence names, the precuration filling what it leaves out."""
    fields = disease_fields(evidence, precuration)
    fields["relationship_type"] = relationship_type(evidence, precuration)
    fields["risk_allele"] = risk_allele(evidence, precuration)
    return entity_key_of(db, fields)


def refuse_entity_change(
    db: Session, curation: CurationNew, evidence: dict[str, Any]
) -> None:
    """409 when a curation save names another disease entity than the curation's: its
    entity_key is copied once at creation, so a changed MONDO id or MOI would drift from it
    (#539). Saves that leave the named entity as it was (already drifted rows) pass, and
    an unkeyed ('' = lumped or legacy) curation covers the whole gene as before."""
    pre = curation.precuration.evidence_data if curation.precuration else None
    refuse_other_entity(
        db,
        curation.entity_key,
        evidence,
        pre,
        {"curation_id": curation.id},
        allowed=curation_entity_key(db, curation.evidence_data or {}, pre),
    )


def refuse_other_entity(
    db: Session,
    entity_key: str,
    evidence: dict[str, Any],
    precuration: dict[str, Any] | None,
    ids: dict[str, UUID],
    allowed: str = "",
) -> None:
    """409 naming `ids` when the evidence names another entity than `entity_key` (or
    `allowed`); '' on either side names none."""
    new = curation_entity_key(db, evidence, precuration)
    if entity_key and new and new not in (entity_key, allowed):
        raise conflict(
            "This curation is for another disease entity (MONDO id, inheritance and "
            "relationship type); start a precuration to curate this one",
            **ids,
        )


def open_draft(
    db: Session, gene_id: UUID, scope_id: UUID, user_id: UUID, entity_key: str
) -> PrecurationNew | None:
    """The author's draft for this gene, scope and disease entity ('' = none yet)."""
    return db.scalars(
        select(PrecurationNew)
        .where(
            PrecurationNew.gene_id == gene_id,
            PrecurationNew.scope_id == scope_id,
            PrecurationNew.created_by == user_id,
            PrecurationNew.entity_key == entity_key,
            PrecurationNew.status == CurationStatus.DRAFT,
        )
        .order_by(PrecurationNew.created_at)
        .limit(1)
    ).first()


# Statuses a precuration can still move on from to approval (rejected ones are revised)
_OPEN = (
    CurationStatus.DRAFT,
    CurationStatus.SUBMITTED,
    CurationStatus.IN_REVIEW,
    CurationStatus.REJECTED,
)


def refuse_open_entity(
    db: Session,
    gene_id: UUID,
    scope_id: UUID,
    entity_key: str,
    author: UUID | None,
    exclude: UUID | None = None,
) -> None:
    """409 naming the scope's open or approved-unused precuration of this gene and entity
    (#567); the author's own drafts are left to the open-draft index, '' names none."""
    if not entity_key:
        return
    # concurrent creates that both pass meet uq_precurations_open_entity (077)
    curated = exists().where(CurationNew.precuration_id == PrecurationNew.id)
    other = db.scalar(
        select(PrecurationNew.id)
        .where(
            PrecurationNew.gene_id == gene_id,
            PrecurationNew.scope_id == scope_id,
            PrecurationNew.entity_key == entity_key,
            PrecurationNew.id != exclude if exclude else true(),
            or_(  # NULL-safe: a creatorless legacy draft still blocks
                PrecurationNew.created_by.is_distinct_from(author),
                PrecurationNew.status != CurationStatus.DRAFT,
            ),
            or_(
                PrecurationNew.status.in_(_OPEN),
                and_(PrecurationNew.status == CurationStatus.APPROVED, ~curated),
            ),
        )
        .order_by(PrecurationNew.created_at)
        .limit(1)
    )
    if other:
        raise conflict(
            "This disease entity already has an open or approved precuration in this "
            "scope",
            precuration_id=other,
        )


def write_draft(
    db: Session, db_obj: PrecurationNew, lock_version: int, values: dict[str, Any]
) -> bool:
    """update_if_version; 409 naming the author's draft when the new disease entity is one
    they already have a draft for (the open-draft index). Other errors propagate."""
    gene_id, scope_id, author = db_obj.gene_id, db_obj.scope_id, db_obj.created_by
    if "evidence_data" in values:
        key = entity_key_of(db, values["evidence_data"])
        if key != db_obj.entity_key:  # unchanged: the row already holds this entity
            refuse_open_entity(db, gene_id, scope_id, key, author, db_obj.id)
    try:
        return update_if_version(db, PrecurationNew, db_obj.id, lock_version, values)
    except IntegrityError:
        db.rollback()
        other = (
            open_draft(
                db,
                gene_id,
                scope_id,
                author,
                entity_key_of(db, values["evidence_data"]),
            )
            if author and "evidence_data" in values
            else None
        )
        if other is None:
            if "evidence_data" in values:  # a concurrent precuration took the entity
                key = entity_key_of(db, values["evidence_data"])
                refuse_open_entity(db, gene_id, scope_id, key, author, db_obj.id)
            raise
        raise conflict(
            "You already have an open precuration draft for this disease and inheritance",
            precuration_id=other.id,
        ) from None
