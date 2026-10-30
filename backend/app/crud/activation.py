"""Activation of an approved curation: supersede the previous one, stamp approval, point."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import or_, true
from sqlalchemy.orm import Session

from app.models import ActiveCuration, CurationNew, CurationStatus, WorkflowStage


def _same_entity(column: Any, key: str) -> Any:
    """The entity's own rows; '' (lumped or legacy) covers the whole gene, either way."""
    return or_(column == key, column == "") if key else true()


def activate_item(db: Session, item: Any, user_id: UUID) -> None:
    key = getattr(item, "entity_key", "")
    # Update workflow stage and status on the item
    if hasattr(item, "workflow_stage"):
        item.workflow_stage = WorkflowStage.ACTIVE
    if isinstance(item, CurationNew):
        item.approved_at = datetime.now(UTC)
        item.approved_by = user_id
        # One active curation per entity: supersede any other (same transaction)
        for old in db.query(CurationNew).filter(
            CurationNew.gene_id == item.gene_id,
            CurationNew.scope_id == item.scope_id,
            _same_entity(CurationNew.entity_key, key),
            CurationNew.status == CurationStatus.ACTIVE,
            CurationNew.id != item.id,
        ):
            old.status = CurationStatus.ARCHIVED
            old.workflow_stage = WorkflowStage.ARCHIVED
            old.updated_by = user_id
        db.flush()
    if hasattr(item, "status"):  # after the flush: partial unique index on active
        item.status = CurationStatus.ACTIVE

    # Create active curation record
    if hasattr(item, "gene_id") and hasattr(item, "scope_id"):
        # Archive the entity's current pointer(s)
        replaced_curation_id = None
        for existing_active in db.query(ActiveCuration).filter(
            ActiveCuration.gene_id == item.gene_id,
            ActiveCuration.scope_id == item.scope_id,
            _same_entity(ActiveCuration.entity_key, key),
            ActiveCuration.archived_at.is_(None),
        ):
            existing_active.archived_at = datetime.now(UTC)
            existing_active.archived_by = user_id
            existing_active.archive_reason = "Replaced by new active curation"
            if replaced_curation_id is None or existing_active.entity_key == key:
                replaced_curation_id = existing_active.curation_id
        db.flush()  # archive UPDATE must precede the new row's INSERT

        # Create new active curation record
        active_curation = ActiveCuration(
            gene_id=item.gene_id,
            scope_id=item.scope_id,
            entity_key=key,
            curation_id=item.id if hasattr(item, "id") else None,
            activated_by=user_id,
            activated_at=datetime.now(UTC),
            replaced_curation_id=replaced_curation_id,
            # Audit fields required by audit trigger
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(active_curation)

    db.flush()
