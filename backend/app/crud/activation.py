"""Activation of an approved curation: supersede the previous one, stamp approval, point."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import ActiveCuration, CurationNew, CurationStatus, WorkflowStage


def activate_item(db: Session, item: Any, user_id: UUID) -> None:
    # Update workflow stage and status on the item
    if hasattr(item, "workflow_stage"):
        item.workflow_stage = WorkflowStage.ACTIVE
    if isinstance(item, CurationNew):
        item.approved_at = datetime.now(UTC)
        item.approved_by = user_id
        # One active curation per gene+scope: supersede any other (same transaction)
        for old in db.query(CurationNew).filter(
            CurationNew.gene_id == item.gene_id,
            CurationNew.scope_id == item.scope_id,
            CurationNew.status == CurationStatus.ACTIVE,
            CurationNew.id != item.id,
        ):
            old.status = CurationStatus.ARCHIVED
            old.updated_by = user_id
        db.flush()
    if hasattr(item, "status"):  # after the flush: partial unique index on active
        item.status = CurationStatus.ACTIVE

    # Create active curation record
    if hasattr(item, "gene_id") and hasattr(item, "scope_id"):
        # Check for existing active curation for this gene-scope pair
        existing_active = (
            db.query(ActiveCuration)
            .filter(
                ActiveCuration.gene_id == item.gene_id,
                ActiveCuration.scope_id == item.scope_id,
                ActiveCuration.archived_at.is_(None),
            )
            .first()
        )

        replaced_curation_id = None
        if existing_active:
            existing_active.archived_at = datetime.now(UTC)
            existing_active.archived_by = user_id
            existing_active.archive_reason = "Replaced by new active curation"
            replaced_curation_id = existing_active.curation_id
            db.flush()  # archive UPDATE must precede the new row's INSERT

        # Create new active curation record
        active_curation = ActiveCuration(
            gene_id=item.gene_id,
            scope_id=item.scope_id,
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
