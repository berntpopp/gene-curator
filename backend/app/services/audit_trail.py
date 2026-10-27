"""Review history of a curation for the workflow audit-trail endpoint. Entries carry the
``audit_id`` of the evidence snapshot they refer to, usable as curation_diff ``?baseline=``."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CurationNew, Review, ReviewStatus, WorkflowStage
from app.schemas.workflow_engine import WorkflowAuditEntry
from app.services.evidence_diff import snapshot_at, submitted_snapshots


def audit_entries(
    db: Session, curation: CurationNew, item_type: str
) -> list[WorkflowAuditEntry]:
    """Every submission (its snapshot) and every review decision (the snapshot reviewed),
    oldest first. Without audit rows (no trigger) the latest submission still shows."""
    submissions: list[tuple[int | None, UUID | None, datetime]] = [
        (
            row.id,
            row.user_id or curation.submitted_by or curation.created_by,
            row.timestamp,
        )
        for row in submitted_snapshots(db, curation.id)
    ]
    if not submissions and curation.submitted_at and curation.submitted_by:
        submissions = [(None, curation.submitted_by, curation.submitted_at)]
    entries = [
        WorkflowAuditEntry(
            id=curation.id,
            item_id=curation.id,
            item_type=item_type,
            from_stage=WorkflowStage.CURATION,
            to_stage=WorkflowStage.REVIEW,
            executed_by=by,
            executed_at=at,
            notes=None,
            metadata={},
            audit_id=audit_id,
        )
        for audit_id, by, at in submissions
        if by is not None  # every submission has a user; a deleted one leaves None
    ]
    entries += [
        WorkflowAuditEntry(
            id=r.id,
            item_id=curation.id,
            item_type=item_type,
            from_stage=WorkflowStage.REVIEW,
            to_stage=WorkflowStage.ACTIVE
            if r.status == ReviewStatus.APPROVED
            else WorkflowStage.CURATION,
            executed_by=r.reviewer_id,
            executed_by_name=r.reviewer.name or r.reviewer.email,
            executed_at=r.reviewed_at,
            notes=r.comments,
            metadata={"decision": r.recommendation},
            audit_id=getattr(snapshot_at(db, curation.id, r.reviewed_at), "id", None),
        )
        for r in db.scalars(select(Review).where(Review.curation_id == curation.id))
        if r.reviewed_at is not None
    ]
    return sorted(entries, key=lambda e: e.executed_at)
