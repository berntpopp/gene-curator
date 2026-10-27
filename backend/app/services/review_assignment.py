"""Route a submitted precuration to a peer reviewer (MCP study round 1, finding 1).

A precuration has no Review row (reviews.curation_id references curations); routing it
notifies the reviewer, who approves or rejects it via /precurations/{id}/approve|reject.
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.capabilities import EDIT, require
from app.crud.review_round import has_pending_review, holds_review_capability
from app.models import (
    CurationNew,
    CurationStatus,
    NotificationNew,
    NotificationType,
    PrecurationNew,
    Review,
    ReviewStatus,
    UserNew,
    WorkflowStage,
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


def stage_reviewer(
    db: Session,
    item: CurationNew | PrecurationNew,
    reviewer_id: UUID,
    assigned_by: UUID,
) -> Review | None:
    """Check the reviewer and add the review row (curations) and notification, uncommitted,
    so a submit can route its item in the same transaction. None for a precuration."""
    kind = "curation" if isinstance(item, CurationNew) else "precuration"
    if not (
        item.workflow_stage == WorkflowStage.REVIEW
        if isinstance(item, CurationNew)
        else item.status == CurationStatus.SUBMITTED
    ):
        raise ValueError(
            f"{kind.capitalize()} {item.id} is {item.status.value}; only an item in review "
            f"is routed to a reviewer: {APPROVERS}"
        )
    check_reviewer(db, kind, item.id, item.created_by, reviewer_id, item.scope_id)
    review = None
    if isinstance(item, CurationNew):
        if has_pending_review(db, item.id, reviewer_id):
            raise ValueError("Reviewer already has a pending review")
        review = Review(
            curation_id=item.id,
            reviewer_id=reviewer_id,
            assigned_by=assigned_by,
            status=ReviewStatus.PENDING,
            assigned_at=datetime.now(UTC),
        )
        db.add(review)
        db.flush()
    link = f"/scopes/{item.scope_id}/{kind}s/{item.id}"
    already = db.scalar(
        select(NotificationNew.id).where(
            NotificationNew.user_id == reviewer_id,
            NotificationNew.type == NotificationType.REVIEW_ASSIGNED,
            NotificationNew.link == link,
            ~NotificationNew.is_read,
        )
    )
    if already is None:  # routing again must not spam an unread duplicate
        symbol = getattr(item.gene, "approved_symbol", "Unknown")
        db.add(
            NotificationNew(
                user_id=reviewer_id,
                type=NotificationType.REVIEW_ASSIGNED,
                title="New review assigned",
                message=f"{kind.capitalize()} to review: {symbol}",
                link=link,
            )
        )
    return review


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
    stage_reviewer(db, p, reviewer_id, user.id)
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
