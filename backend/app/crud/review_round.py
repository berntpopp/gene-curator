"""A review round is open while the curation is IN_REVIEW and starts at its latest submission.

The review status enum has no "cancelled" value (and no migration is allowed here), so a
review counts only when its curation is IN_REVIEW and it was assigned at or after the
curation's latest `submitted_at`. Reviews left PENDING by request_changes/reject, or by
an earlier round, are therefore ignored by every pending count and check. Use this one rule.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select, true
from sqlalchemy.orm import Session

from app.core.capabilities import REVIEW, ROLE_CAPABILITIES
from app.core.enums import ScopeRole
from app.core.workflow_errors import ReviewForbiddenError, WorkflowConflictError
from app.models import (
    AuditLogNew,
    CurationNew,
    CurationStatus,
    Review,
    ReviewItemComment,
    ReviewStatus,
    ScopeMembership,
    UserNew,
    WorkflowStage,
)

_submitted_at = (
    select(CurationNew.submitted_at)
    .where(CurationNew.id == Review.curation_id)
    .correlate(Review)
    .scalar_subquery()
)
_in_review = (
    select(CurationNew.status)
    .where(CurationNew.id == Review.curation_id)
    .correlate(Review)
    .scalar_subquery()
    == CurationStatus.IN_REVIEW
)

# SQL condition on Review rows (correlated to the review's curation).
in_current_round: Any = and_(
    _in_review, or_(_submitted_at.is_(None), Review.assigned_at >= _submitted_at)
)


CORRECTED_OWN = (
    "4-eyes principle violation: you corrected this curation's disease entity "
    "or moved it to a new methodology version"
)


def correctors(curation_id: Any) -> Any:
    """Who corrected the disease (#453) or moved the curation to a new methodology
    version (#591): their work too (D1)."""
    return select(AuditLogNew.user_id).where(
        AuditLogNew.entity_id == curation_id,
        AuditLogNew.change_type.in_(("disease_correction", "version_move")),
        AuditLogNew.user_id.isnot(None),
    )


def corrected_by(db: Session, curation_id: UUID, user_id: UUID) -> bool:
    return (
        db.scalar(correctors(curation_id).where(AuditLogNew.user_id == user_id))
        is not None
    )


def check_review_open(db: Session, review: Review) -> None:
    """Raise ValueError unless the review is in the open round and its reviewer may review."""
    curation = db.get(CurationNew, review.curation_id)
    if curation is None or curation.status != CurationStatus.IN_REVIEW:
        raise WorkflowConflictError("Curation is not in review")
    if not holds_review_capability(db, review.reviewer_id, curation.scope_id):
        raise ReviewForbiddenError("User is not allowed to review in this scope")
    if curation.submitted_at is not None and review.assigned_at < curation.submitted_at:
        raise WorkflowConflictError("Review belongs to a previous review round")
    if corrected_by(db, curation.id, review.reviewer_id):
        raise ReviewForbiddenError(CORRECTED_OWN)


def all_reviews_approved(db: Session, curation_id: UUID) -> bool:
    """No pending review left in the open round and every decision there is approve."""
    base = select(func.count()).select_from(Review)
    open_round = and_(Review.curation_id == curation_id, in_current_round)
    pending = db.execute(
        base.where(open_round, Review.status == ReviewStatus.PENDING)
    ).scalar()
    if pending:
        return False
    # Legacy rows: APPROVED status with a non-approve recommendation still blocks.
    blocked = db.execute(
        base.where(
            open_round,
            Review.status != ReviewStatus.PENDING,
            Review.recommendation != "approve",
        )
    ).scalar()
    return not blocked


def approving_reviewers(db: Session, curation: CurationNew) -> int:
    """Distinct reviewers who approved in the open round; the author and a disease
    corrector never count (D1)."""
    return (
        db.scalar(
            select(func.count(func.distinct(Review.reviewer_id))).where(
                Review.curation_id == curation.id,
                # this round by submitted_at only: legacy 'submitted' rows are in review too
                Review.assigned_at >= curation.submitted_at
                if curation.submitted_at
                else true(),
                Review.status == ReviewStatus.APPROVED,
                Review.recommendation == "approve",
                Review.reviewer_id != curation.created_by,
                Review.reviewer_id.notin_(correctors(curation.id)),
            )
        )
        or 0
    )


def reviewers_required(workflow_states: dict[str, Any]) -> int:
    """`workflow_states.review.reviewers_required` (1-5); anything else means 1."""
    review = workflow_states.get("review")
    n = review.get("reviewers_required") if isinstance(review, dict) else None
    return n if type(n) is int and 1 <= n <= 5 else 1


def reassign_earlier_reviewers(
    db: Session, curation: CurationNew, assigned_by: UUID, source_id: UUID | None = None
) -> list[UUID]:
    """On resubmit, give each earlier reviewer a new PENDING review in the new round.

    Never the curation's own curator (4-eyes, admins included). ``source_id``: whose
    reviews are the earlier ones, for a copy of an active curation (#591); default its own.
    """
    if curation.submitted_at is None:
        return []
    earlier = db.scalars(
        select(Review.reviewer_id)
        .where(
            Review.curation_id == (source_id or curation.id),
            Review.assigned_at < curation.submitted_at,
            Review.reviewer_id != curation.created_by,
            Review.reviewer_id.notin_(correctors(curation.id)),
            # same condition as holds_review_capability: still a reviewer here
            Review.reviewer_id.in_(
                select(ScopeMembership.user_id).where(
                    ScopeMembership.scope_id == curation.scope_id,
                    ScopeMembership.is_active,
                    ScopeMembership.accepted_at.isnot(None),
                    ScopeMembership.role.in_(REVIEW_ROLES),
                )
            ),
        )
        .distinct()
    ).all()
    for reviewer_id in earlier:
        db.add(
            Review(
                curation_id=curation.id,
                reviewer_id=reviewer_id,
                assigned_by=assigned_by,
                status=ReviewStatus.PENDING,
                assigned_at=datetime.now(UTC),
            )
        )
    db.flush()
    return list(earlier)


def pending_reviews(db: Session, curation_id: UUID) -> list[dict[str, Any]]:
    """Pending reviews in the open round."""
    rows = db.scalars(
        select(Review).where(
            Review.curation_id == curation_id,
            Review.status == ReviewStatus.PENDING,
            in_current_round,
        )
    )
    return [
        {"review_id": r.id, "reviewer_id": r.reviewer_id, "assigned_at": r.assigned_at}
        for r in rows
    ]


REVIEW_ROLES = [r.value for r in ScopeRole if REVIEW in ROLE_CAPABILITIES[r]]


def holds_review_capability(db: Session, user_id: UUID, scope_id: UUID) -> bool:
    """REVIEW via an accepted, active membership. Platform admins get no bypass."""
    return (
        db.scalar(
            select(ScopeMembership.id).where(
                ScopeMembership.user_id == user_id,
                ScopeMembership.scope_id == scope_id,
                ScopeMembership.is_active,
                ScopeMembership.accepted_at.isnot(None),
                ScopeMembership.role.in_(REVIEW_ROLES),
            )
        )
        is not None
    )


def has_pending_review(db: Session, curation_id: UUID, reviewer_id: UUID) -> bool:
    """The reviewer already has a PENDING review in the open round."""
    return (
        db.scalar(
            select(Review.id).where(
                Review.curation_id == curation_id,
                Review.reviewer_id == reviewer_id,
                Review.status == ReviewStatus.PENDING,
                in_current_round,
            )
        )
        is not None
    )


_DECISIONS = {
    WorkflowStage.ACTIVE: (ReviewStatus.APPROVED, "approve"),
    WorkflowStage.CURATION: (ReviewStatus.NEEDS_REVISION, "request_changes"),
}


def record_review_decision(
    db: Session,
    curation: CurationNew,
    reviewer_id: UUID,
    target: WorkflowStage,
    notes: str | None,
) -> None:
    """Store a review -> active/curation transition as the reviewer's decision with its notes.

    Call while the round is still open. Fills the reviewer's pending review of the round, else adds
    one; a same decision already submitted this round (auto-activation) is kept as it is.
    """
    if target not in _DECISIONS:
        return
    status, recommendation = _DECISIONS[target]
    review = db.scalars(
        select(Review)
        .where(
            Review.curation_id == curation.id,
            Review.reviewer_id == reviewer_id,
            in_current_round,
            Review.status.in_((ReviewStatus.PENDING, status)),
        )
        .order_by(Review.status == status)  # a pending one first
    ).first()
    if review is not None and review.status == status:
        return
    if review is None:
        review = Review(
            curation_id=curation.id,
            reviewer_id=reviewer_id,
            assigned_by=reviewer_id,
            created_by=reviewer_id,
            assigned_at=datetime.now(UTC),  # same clock as submitted_at (round start)
        )
        db.add(review)
    review.status = status
    review.recommendation = recommendation
    review.comments = notes
    review.reviewed_at = func.now()  # DB clock, like audit timestamps
    review.updated_by = reviewer_id
    db.flush()


def eligible_peer_reviewers(
    db: Session,
    scope_id: UUID | None = None,
    exclude_user_id: UUID | None = None,
) -> list[dict[str, Any]]:
    """
    Get eligible peer reviewers for assignment.

    Filters:
    - Active users only
    - If scope_id provided, must be member of that scope with reviewer-capable role
    - Excludes exclude_user_id (4-eyes principle)

    Returns users with pending review count.
    """
    # Eligible roles within a scope for reviewing
    eligible_scope_roles = REVIEW_ROLES

    # Base query for active users
    query = db.query(UserNew).filter(UserNew.is_active == True)  # noqa: E712

    # Exclude current user (4-eyes principle)
    if exclude_user_id:
        query = query.filter(UserNew.id != exclude_user_id)

    # Filter by scope membership if scope_id provided
    if scope_id:
        # Subquery to get user IDs with eligible roles in the scope
        scope_member_ids = (
            db.query(ScopeMembership.user_id)
            .filter(
                ScopeMembership.scope_id == scope_id,
                ScopeMembership.is_active == True,  # noqa: E712
                ScopeMembership.accepted_at.isnot(None),
                ScopeMembership.role.in_(eligible_scope_roles),
            )
            .subquery()
        )
        query = query.filter(UserNew.id.in_(select(scope_member_ids)))

    users = query.order_by(UserNew.name).all()

    # Get pending review counts and scope roles
    result = []
    for user in users:
        pending_count = (
            db.query(func.count(Review.id))
            .filter(
                Review.reviewer_id == user.id,
                Review.status == ReviewStatus.PENDING,
                in_current_round,
            )
            .scalar()
            or 0
        )

        # Get scope roles for this user
        scope_roles_query = db.query(ScopeMembership.role).filter(
            ScopeMembership.user_id == user.id,
            ScopeMembership.is_active == True,  # noqa: E712
        )
        if scope_id:
            scope_roles_query = scope_roles_query.filter(
                ScopeMembership.scope_id == scope_id
            )

        scope_roles = list({r[0] for r in scope_roles_query.all()})

        result.append(
            {
                "id": user.id,
                "name": user.name or user.email.split("@")[0],
                "email": user.email,
                "role": user.role.value if hasattr(user.role, "value") else user.role,
                "institution": user.institution,
                "expertise_areas": user.expertise_areas or [],
                "is_active": user.is_active,
                "pending_review_count": pending_count,
                "scope_roles": scope_roles,
            }
        )

    return result


def earlier_feedback(
    db: Session, curation: CurationNew
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(decided reviews, item comments still open) the curator was asked to act on: from
    before the latest submission while it is in review again, else every round so far
    (after a request for changes the latest decision is the feedback)."""
    if curation.submitted_at is None:
        return [], []
    # far future: no cut-off while the curation is back with its curator
    cutoff = (
        curation.submitted_at
        if curation.status == CurationStatus.IN_REVIEW
        else datetime.max.replace(tzinfo=UTC)
    )
    reviews = db.execute(
        select(
            UserNew.name,
            Review.status,
            Review.comments,
            Review.feedback_data,
            Review.reviewed_at,
        )
        .join(UserNew, UserNew.id == Review.reviewer_id)
        .where(
            Review.curation_id == curation.id,
            Review.reviewed_at.isnot(None),
            Review.reviewed_at < cutoff,
        )
        .order_by(Review.reviewed_at.desc())
    ).all()
    comments = db.execute(
        select(
            ReviewItemComment.id,
            ReviewItemComment.item_path,
            ReviewItemComment.kind,
            ReviewItemComment.body,
        ).where(
            ReviewItemComment.curation_id == curation.id,
            ReviewItemComment.status == "open",
            ReviewItemComment.created_at < cutoff,
        )
    ).all()
    return (
        [
            {
                "reviewer": r.name,
                "decision": r.status,
                "comments": r.comments,
                "feedback_data": r.feedback_data,
                "reviewed_at": r.reviewed_at,
            }
            for r in reviews
        ],
        [dict(c._mapping) for c in comments],
    )
