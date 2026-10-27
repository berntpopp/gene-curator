"""Route a submitted precuration to a peer reviewer (MCP study round 1, finding 1).

A precuration has no Review row (reviews.curation_id references curations); routing it
notifies the reviewer, who approves or rejects it via /precurations/{id}/approve|reject.
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.capabilities import EDIT, require
from app.crud.review_round import holds_review_capability
from app.models import (
    CurationStatus,
    NotificationNew,
    NotificationType,
    PrecurationNew,
    ReviewStatus,
    UserNew,
)
from app.schemas.workflow_engine import PeerReviewRequest

APPROVERS = "an accepted reviewer or admin of its scope, never its author, approves it"


def check_reviewer(
    db: Session,
    kind: str,
    item_id: UUID,
    author: UUID | None,
    reviewer: UUID,
    scope: UUID,
) -> None:
    """Same reviewer rules for curations and precurations (D1: never the author)."""
    if reviewer == author:
        raise ValueError(
            f"4-eyes principle violation: the author of {kind} {item_id} cannot review it; "
            f"{APPROVERS}"
        )
    if not holds_review_capability(db, reviewer, scope):
        raise ValueError(
            f"User {reviewer} is not allowed to review {kind} {item_id}: {APPROVERS}"
        )


def assign_precuration_reviewer(
    db: Session, precuration_id: UUID, reviewer_id: UUID, user: UserNew
) -> PeerReviewRequest:
    p = db.get(PrecurationNew, precuration_id)
    if p is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Precuration {precuration_id} not found"
        )
    if p.created_by != user.id:
        require(db, user, p.scope_id, EDIT)
    if p.status != CurationStatus.SUBMITTED:
        raise ValueError(
            f"Precuration {p.id} is {p.status.value}; submit it before routing it to a "
            f"reviewer: {APPROVERS}"
        )
    check_reviewer(db, "precuration", p.id, p.created_by, reviewer_id, p.scope_id)
    db.add(
        NotificationNew(
            user_id=reviewer_id,
            type=NotificationType.REVIEW_ASSIGNED,
            title="New review assigned",
            message=f"Precuration to review: {p.gene.approved_symbol}",
            link=f"/scopes/{p.scope_id}/precurations/{p.id}",
        )
    )
    db.commit()
    return PeerReviewRequest(
        review_id=None,
        item_id=p.id,
        item_type="precuration",
        reviewer_id=reviewer_id,
        assigned_by=user.id,
        review_type="peer_review",
        assigned_at=datetime.now(UTC),
        status=ReviewStatus.PENDING,
    )
