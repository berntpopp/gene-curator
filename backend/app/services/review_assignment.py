"""Route a submitted precuration to a peer reviewer (MCP study round 1, finding 1).

A precuration has no Review row (reviews.curation_id references curations); routing it
notifies the reviewer, who approves or rejects it via /precurations/{id}/approve|reject.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.capabilities import EDIT, require
from app.core.workflow_errors import ReviewForbiddenError, WorkflowConflictError
from app.crud.review_round import (
    CORRECTED_OWN,
    REVIEW_ROLES,
    corrected_by,
    correctors,
    has_pending_review,
    holds_review_capability,
)
from app.mcp.audit import request_channel
from app.models import (
    CurationNew,
    CurationStatus,
    NotificationNew,
    NotificationType,
    PrecurationNew,
    Review,
    ReviewStatus,
    Scope,
    ScopeMembership,
    UserNew,
    WorkflowStage,
)
from app.schemas.curation import CurationSubmit
from app.schemas.precuration import PrecurationSubmit
from app.schemas.workflow_engine import AssignedReviewer, PeerReviewRequest

APPROVERS = "an accepted reviewer or admin of its scope, never its author, approves it"


def check_reviewer(
    db: Session,
    kind: str,
    item_id: UUID,
    author: UUID | None,
    reviewer: UUID,
    scope: UUID,
) -> None:
    """Same reviewer rules for curations and precurations (D1: never the author, nor
    who corrected a curation's disease entity)."""
    if reviewer == author:
        raise ReviewForbiddenError(
            f"4-eyes principle violation: the author of {kind} {item_id} cannot review it; "
            f"{APPROVERS}"
        )
    if kind == "curation" and corrected_by(db, item_id, reviewer):
        raise ReviewForbiddenError(f"{CORRECTED_OWN}; {APPROVERS}")
    if not holds_review_capability(db, reviewer, scope):
        raise ReviewForbiddenError(
            f"User {reviewer} is not allowed to review {kind} {item_id}: {APPROVERS}"
        )


def _reviewers(db: Session, scope_id: UUID) -> Any:
    """The scope's accepted reviewers and admins; agent accounts only where the
    review_policy lets them review (#639)."""
    return (
        select(UserNew.id, UserNew.email)
        .join(ScopeMembership, ScopeMembership.user_id == UserNew.id)
        .join(Scope, Scope.id == ScopeMembership.scope_id)
        .where(
            ScopeMembership.scope_id == scope_id,
            ScopeMembership.is_active,
            ScopeMembership.accepted_at.isnot(None),
            ScopeMembership.role.in_(REVIEW_ROLES),
            or_(UserNew.is_agent == False, Scope.review_policy != "human"),  # noqa: E712
        )
    )


def missing_reviewer(db: Session, scope_id: UUID, author: UUID | None) -> list[str]:
    """Warned at create (#640): submit will 409 when nobody but the author may review."""
    others = _reviewers(db, scope_id).where(UserNew.id != author, UserNew.is_active)
    if db.execute(others.limit(1)).first():
        return []
    return [
        "There is no eligible reviewer in this scope besides you; submit will be "
        "refused until another reviewer or admin accepts an invitation"
    ]


def submit_reviewer(
    db: Session,
    scope_id: UUID,
    data: CurationSubmit | PrecurationSubmit,
    author: UUID | None,
    *,
    item_id: UUID | None = None,
    submitter: UUID | None = None,
) -> UUID | None:
    """The reviewer a submit names: reviewer_id, or reviewer_email matched only against the
    scope's accepted reviewers and admins (so it never reveals other accounts). Over MCP,
    naming none picks the only eligible reviewer besides the author and refuses when there
    are several (KGDB QA: nothing reaches review unassigned); the web UI submits first
    and routes after."""
    if data.reviewer_id:
        return data.reviewer_id
    if not data.reviewer_email and _over_mcp():
        # D1: never the author, the submitter or who corrected the item
        others = db.execute(
            _reviewers(db, scope_id).where(
                UserNew.id.not_in([u for u in (author, submitter) if u]),
                UserNew.id.not_in(correctors(item_id)),
                UserNew.is_active,
            )
        ).all()
        if len(others) > 1:
            raise ValueError(
                "Several reviewers can review this; name one with reviewer_email: "
                + ", ".join(sorted(row.email for row in others))
            )
        if not others:  # reviewers cannot self-assign: unrouted, it would be stuck
            raise WorkflowConflictError(
                "There is no eligible reviewer in this scope: everyone who may review "
                "has written, submitted or corrected this item; invite another reviewer"
            )
        picked: UUID = others[0].id
        return picked
    if not data.reviewer_email:
        return None
    found: UUID | None = db.scalar(
        _reviewers(db, scope_id)
        .with_only_columns(UserNew.id)
        .where(func.lower(UserNew.email) == data.reviewer_email.strip().lower())
    )
    if found is None:
        raise ValueError(
            f"No reviewer of this scope has the email {data.reviewer_email}: {APPROVERS}"
        )
    return found


def _over_mcp() -> bool:
    found = request_channel.get()
    return found is not None and found[0] == "mcp"


def assigned_reviewer(db: Session, reviewer_id: UUID | None) -> AssignedReviewer | None:
    """The echo for a submit that named a reviewer."""
    if reviewer_id is None:
        return None
    return AssignedReviewer(
        id=reviewer_id,
        name=db.scalar(select(UserNew.name).where(UserNew.id == reviewer_id)),
    )


def stage_reviewer(
    db: Session,
    item: CurationNew | PrecurationNew,
    reviewer_id: UUID,
    assigned_by: UUID,
    *,
    on_submit: bool = False,
) -> Review | None:
    """Check the reviewer and add the review row (curations) and notification, uncommitted,
    so a submit can route its item in the same transaction. None for a precuration."""
    kind = "curation" if isinstance(item, CurationNew) else "precuration"
    if not (
        item.workflow_stage == WorkflowStage.REVIEW
        if isinstance(item, CurationNew)
        else item.status == CurationStatus.SUBMITTED
    ):
        raise WorkflowConflictError(
            f"{kind.capitalize()} {item.id} is {item.status.value}; only an item in review "
            f"is routed to a reviewer: {APPROVERS}"
        )
    check_reviewer(db, kind, item.id, item.created_by, reviewer_id, item.scope_id)
    review = None
    if isinstance(item, CurationNew):
        if has_pending_review(db, item.id, reviewer_id):
            if on_submit:  # a resubmit already reassigned this earlier reviewer
                return None
            raise WorkflowConflictError("Reviewer already has a pending review")
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
        raise WorkflowConflictError(
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
