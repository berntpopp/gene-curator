"""A review round is open while the curation is IN_REVIEW and starts at its latest submission.

The review status enum has no "cancelled" value (and no migration is allowed here), so a
review counts only when its curation is IN_REVIEW and it was assigned at or after the
curation's latest `submitted_at`. Reviews left PENDING by request_changes/reject, or by
an earlier round, are therefore ignored by every pending count and check. Use this one rule.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import CurationNew, CurationStatus, Review, ReviewStatus

_submitted_at = (
    select(CurationNew.submitted_at)
    .where(CurationNew.id == Review.curation_id)
    .scalar_subquery()
)
_in_review = (
    select(CurationNew.status)
    .where(CurationNew.id == Review.curation_id)
    .scalar_subquery()
    == CurationStatus.IN_REVIEW
)

# SQL condition on Review rows (correlated to the review's curation).
in_current_round: Any = and_(
    _in_review, or_(_submitted_at.is_(None), Review.assigned_at >= _submitted_at)
)


def check_review_open(db: Session, review: Review) -> None:
    """Raise ValueError unless the review belongs to the curation's open round."""
    curation = db.get(CurationNew, review.curation_id)
    if curation is None or curation.status != CurationStatus.IN_REVIEW:
        raise ValueError("Curation is not in review")
    if curation.submitted_at is not None and review.assigned_at < curation.submitted_at:
        raise ValueError("Review belongs to a previous review round")


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
