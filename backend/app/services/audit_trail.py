"""Review history of a curation for the workflow audit-trail endpoint. Entries carry the
``audit_id`` of the evidence snapshot they refer to, usable as curation_diff ``?baseline=``."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CurationNew, Review, ReviewStatus, UserNew, WorkflowStage
from app.schemas.workflow_engine import WorkflowAuditEntry
from app.services.evidence_diff import snapshot_at, submitted_snapshots


def _name(db: Session, user_id: UUID | None) -> str | None:
    user = db.get(UserNew, user_id) if user_id else None
    return (user.name or None) if user else None  # never the email


def audit_entries(
    db: Session, curation: CurationNew, item_type: str
) -> list[WorkflowAuditEntry]:
    """Every submission (its snapshot) and every review decision (the snapshot reviewed),
    oldest first. Without audit rows (no trigger) the latest submission still shows."""
    # #593: the AI agent of an MCP submit (080) is shown with the person it acted for
    submissions: list[tuple[int | None, UUID | None, datetime, dict[str, Any]]] = [
        (
            row.id,
            row.user_id or curation.submitted_by or curation.created_by,
            row.timestamp,
            {"agent": agent}
            if (agent := (row.change_metadata or {}).get("agent"))
            else {},
        )
        for row in submitted_snapshots(db, curation.id)
    ]
    if not submissions and curation.submitted_at and curation.submitted_by:
        submissions = [(None, curation.submitted_by, curation.submitted_at, {})]
    entries = [
        WorkflowAuditEntry(
            id=curation.id,
            item_id=curation.id,
            item_type=item_type,
            from_stage=WorkflowStage.CURATION,
            to_stage=WorkflowStage.REVIEW,
            executed_by=by,
            executed_by_name=_name(db, by),
            executed_at=at,
            notes=None,
            metadata=meta,
            audit_id=audit_id,
        )
        for audit_id, by, at, meta in submissions
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
