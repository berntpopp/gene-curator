"""Per-item review comments and the evidence diff for a curation (#279).

Capability checks go through core.capabilities.require (VIEW to read, REVIEW or, for the
curation's own curator, EDIT to write). The database enforces the same rules with RLS, which
has no platform-admin bypass; a write it refuses becomes a 403 here.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.core.capabilities import EDIT, REVIEW, VIEW, require
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.logging import api_endpoint
from app.models import AuditLogNew, CurationNew, Review, ReviewItemComment, UserNew
from app.schemas.review_comment import (
    CurationDiff,
    ReviewComment,
    ReviewCommentCreate,
    ReviewCommentUpdate,
)
from app.services.evidence_diff import diff_evidence

router = APIRouter()

_DENIED = HTTPException(
    status.HTTP_403_FORBIDDEN, "Not authorized to comment on this item"
)


def _curation(db: Session, curation_id: UUID) -> CurationNew:
    curation = db.get(CurationNew, curation_id)
    if curation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Curation not found")
    return curation


def _require_writer(db: Session, user: UserNew, curation: CurationNew) -> None:
    """Reviewers and scope admins, or the curation's own curator (replies)."""
    try:
        require(db, user, curation.scope_id, REVIEW)
    except HTTPException:
        require(db, user, curation.scope_id, EDIT)
        if curation.created_by != user.id:
            raise _DENIED from None


def _require_accepter(db: Session, user: UserNew, curation: CurationNew) -> None:
    """Accepting (or withdrawing an accept) is a review decision: REVIEW capability, and never on
    one's own curation (4-eyes, D1; scope admins get no exception)."""
    require(db, user, curation.scope_id, REVIEW)
    if curation.created_by == user.id:
        raise _DENIED


def _commit(db: Session) -> None:
    try:
        db.commit()
    except (DBAPIError, StaleDataError):
        db.rollback()
        raise _DENIED from None


@router.get("/{curation_id}/review-comments", response_model=list[ReviewComment])
@api_endpoint()
def list_review_comments(
    curation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> list[ReviewItemComment]:
    curation = _curation(db, curation_id)
    require(db, current_user, curation.scope_id, VIEW)
    return list(
        db.scalars(
            select(ReviewItemComment)
            .where(ReviewItemComment.curation_id == curation_id)
            .order_by(ReviewItemComment.created_at, ReviewItemComment.id)
        )
    )


@router.post(
    "/{curation_id}/review-comments",
    response_model=ReviewComment,
    status_code=status.HTTP_201_CREATED,
)
@api_endpoint()
def create_review_comment(
    curation_id: UUID,
    payload: ReviewCommentCreate,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> ReviewItemComment:
    curation = _curation(db, curation_id)
    if payload.kind == "accepted":
        _require_accepter(db, current_user, curation)
    else:
        _require_writer(db, current_user, curation)
    if payload.review_id is not None:
        review = db.get(Review, payload.review_id)
        if review is None or review.curation_id != curation_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown review")
    comment = ReviewItemComment(
        curation_id=curation_id, author_id=current_user.id, **payload.model_dump()
    )
    db.add(comment)
    _commit(db)
    db.refresh(comment)
    return comment


@router.patch(
    "/{curation_id}/review-comments/{comment_id}", response_model=ReviewComment
)
@api_endpoint()
def update_review_comment(
    curation_id: UUID,
    comment_id: UUID,
    payload: ReviewCommentUpdate,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> ReviewItemComment:
    curation = _curation(db, curation_id)
    require(db, current_user, curation.scope_id, VIEW)
    comment = db.get(ReviewItemComment, comment_id)
    if comment is None or comment.curation_id != curation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comment not found")
    if payload.body is not None:
        if comment.author_id != current_user.id:
            raise _DENIED
        comment.body = payload.body
    if payload.status is not None:
        if comment.kind == "accepted":
            _require_accepter(db, current_user, curation)
        else:
            _require_writer(db, current_user, curation)
        comment.status = payload.status
    _commit(db)
    db.refresh(comment)
    return comment


def _submissions(db: Session, curation_id: UUID) -> list[AuditLogNew]:
    """Audit rows of status transitions into submitted/in_review, newest first (an edit made while
    already submitted is not a submission)."""
    return list(
        db.scalars(
            select(AuditLogNew)
            .where(
                AuditLogNew.entity_type == "curations",
                AuditLogNew.entity_id == curation_id,
                AuditLogNew.new_status.in_(("submitted", "in_review")),
                or_(
                    AuditLogNew.previous_status.is_(None),
                    AuditLogNew.previous_status != AuditLogNew.new_status,
                ),
            )
            .order_by(AuditLogNew.timestamp.desc(), AuditLogNew.id.desc())
        )
    )


def _baseline(
    db: Session, curation_id: UUID, user_id: UUID
) -> tuple[AuditLogNew, str, datetime] | None:
    """The version the requester last saw. The audit trigger stores the row after each update, so
    the last submission equals the current evidence; the useful baseline is the state at the
    requester's own last review decision, else anyone's latest decision, else the submission
    before the latest one."""
    decided_q = (
        select(Review.reviewed_at)
        .where(Review.curation_id == curation_id, Review.reviewed_at.isnot(None))
        .order_by(Review.reviewed_at.desc())
        .limit(1)
    )
    for source, query in (
        ("review", decided_q.where(Review.reviewer_id == user_id)),
        ("any_review", decided_q),
    ):
        decided = db.scalars(query).first()
        if decided is None:
            continue
        row = db.scalars(
            select(AuditLogNew)
            .where(
                AuditLogNew.entity_type == "curations",
                AuditLogNew.entity_id == curation_id,
                AuditLogNew.timestamp <= decided,
            )
            .order_by(AuditLogNew.timestamp.desc(), AuditLogNew.id.desc())
            .limit(1)
        ).first()
        if row is not None:
            return row, source, decided
    submissions = _submissions(db, curation_id)
    if len(submissions) >= 2:
        return submissions[1], "previous_submission", submissions[1].timestamp
    return None


@router.get("/{curation_id}/diff", response_model=CurationDiff)
@api_endpoint()
def curation_diff(
    curation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> CurationDiff:
    """Current evidence versus the version the reviewer last saw (none yet: all items added)."""
    curation = _curation(db, curation_id)
    require(db, current_user, curation.scope_id, VIEW)
    current = curation.evidence_data or {}
    found = _baseline(db, curation_id, current_user.id)
    if found is None:
        return CurationDiff.model_validate(
            {"baseline": None, "items": diff_evidence({}, current)}
        )
    row, source, as_of = found
    snapshot = (row.changes or {}).get("evidence_data") or {}
    return CurationDiff.model_validate(
        {
            "baseline": {"audit_id": row.id, "as_of": as_of, "source": source},
            "items": diff_evidence(snapshot, current),
        }
    )
