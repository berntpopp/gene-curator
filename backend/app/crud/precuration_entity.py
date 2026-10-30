"""Precuration disease entities (#530): the key, the author's open draft per entity, and
saves the open-draft index refuses."""

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import literal, literal_column, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db_types import compatible_jsonb
from app.crud.optimistic_lock import update_if_version
from app.models import CurationStatus, PrecurationNew
from app.models.curation import ENTITY_KEY_SQL


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


def write_draft(
    db: Session, db_obj: PrecurationNew, lock_version: int, values: dict[str, Any]
) -> bool:
    """update_if_version; 409 naming the author's draft when the new disease entity is one
    they already have a draft for (the open-draft index). Other errors propagate."""
    gene_id, scope_id, author = db_obj.gene_id, db_obj.scope_id, db_obj.created_by
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
            raise
        raise conflict(
            "You already have an open precuration draft for this disease and inheritance",
            precuration_id=other.id,
        ) from None
