"""Per-item review comments and the evidence diff for a curation (#279).

Capability checks go through core.capabilities.require (VIEW to read, REVIEW or, for the
curation's own curator, EDIT to write). The database enforces the same rules with RLS, which
has no platform-admin bypass; a write it refuses becomes a 403 here.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.core.capabilities import EDIT, REVIEW, VIEW, require, require_active_scope
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.logging import api_endpoint
from app.models import (
    ActiveCuration,
    AuditLogNew,
    CurationNew,
    Review,
    ReviewItemComment,
    Scope,
    UserNew,
)
from app.schemas.review_comment import (
    CurationDiff,
    ReviewComment,
    ReviewCommentCreate,
    ReviewCommentUpdate,
)
from app.services.evidence_diff import diff_evidence, snapshot_at, submitted_snapshots

router = APIRouter()
# ?baseline= name: index into the submissions, newest first
_SUBMISSION = {"submitted": 0, "previous_submission": 1}

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
    # VIEW holds in an inactive scope too: its comments are read-only (409)
    require_active_scope(db.get(Scope, curation.scope_id))
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
            # only the accepting reviewer withdraws or restores an accept
            if comment.author_id != current_user.id:
                raise _DENIED
        else:
            _require_writer(db, current_user, curation)
        comment.status = payload.status
    _commit(db)
    db.refresh(comment)
    return comment


def _baseline(
    db: Session, curation_id: UUID, user_id: UUID, current: dict[str, Any]
) -> tuple[AuditLogNew, str, datetime] | None:
    """The version the requester last saw. The audit trigger stores the row after each update, so
    the last submission equals the current evidence; the useful baseline is the state at the
    requester's own last review decision, else anyone's latest decision unless it saw the
    current evidence, else the submission before the latest one."""
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
        row = snapshot_at(db, curation_id, decided)
        seen = ((row.changes or {}).get("evidence_data") or {}) if row else None
        # MUI-17: another reviewer's decision on this very evidence shows nothing new
        if row is not None and not (source == "any_review" and seen == current):
            return row, source, decided
    submissions = submitted_snapshots(db, curation_id)
    if len(submissions) >= 2:
        return submissions[1], "previous_submission", submissions[1].timestamp
    return None


def _active(
    db: Session, curation: CurationNew, *, others_only: bool
) -> ActiveCuration | None:
    """The active curation of the curation's gene and scope (others_only: not itself)."""
    query = select(ActiveCuration).where(
        ActiveCuration.gene_id == curation.gene_id,
        ActiveCuration.scope_id == curation.scope_id,
        ActiveCuration.archived_at.is_(None),
    )
    if others_only:
        query = query.where(ActiveCuration.curation_id != curation.id)
    return db.scalars(query).first()


def _requested(
    db: Session, curation: CurationNew, baseline: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """(baseline info, evidence snapshot) for an explicit ?baseline=; 404 when there is none."""
    if baseline == "active":
        active = _active(db, curation, others_only=False)
        if active is None:
            raise HTTPException(404, "No active curation for this gene and scope")
        info = {"audit_id": None, "as_of": active.activated_at}
        return {
            **info,
            "source": "active_curation",
        }, active.curation.evidence_data or {}
    rows = submitted_snapshots(db, curation.id)
    if baseline in _SUBMISSION:
        index = _SUBMISSION[baseline]
        row = rows[index] if len(rows) > index else None
    else:
        row = db.get(AuditLogNew, int(baseline))
        if row is not None and (row.entity_type, row.entity_id) != (
            "curations",
            curation.id,
        ):
            row = None
    if row is None:
        raise HTTPException(404, f"No {baseline} snapshot of this curation")
    source = baseline if baseline in _SUBMISSION else "audit"
    snapshot = (row.changes or {}).get("evidence_data") or {}
    found: dict[str, Any] = {
        "audit_id": row.id,
        "as_of": row.timestamp,
        "source": source,
    }
    current = curation.evidence_data or {}
    if source == "submitted" and len(rows) > 1 and snapshot == current:
        found["note"] = (
            f"The latest submission (audit {row.id}) is the current evidence; "
            f"baseline=previous_submission compares with audit {rows[1].id}"
        )
    return found, snapshot


@router.get("/{curation_id}/diff", response_model=CurationDiff)
@api_endpoint()
def curation_diff(
    curation_id: UUID,
    baseline: str | None = Query(
        None,
        pattern=r"^(submitted|previous_submission|active|\d{1,18})$",
        description="submitted (last submission), previous_submission (the one before "
        "it), active (the active curation) or an audit id (get_workflow_audit_trail "
        "entries carry them); default: the version the caller last reviewed",
    ),
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> CurationDiff:
    """Current evidence versus the version the reviewer last saw, else the active curation it
    replaces (none of either: all items added). Long text changes come as word_diff
    ([-removed-]{+added+}), not the whole before and after."""
    curation = _curation(db, curation_id)
    require(db, current_user, curation.scope_id, VIEW)
    current = curation.evidence_data or {}
    if baseline is not None:
        info, snapshot = _requested(db, curation, baseline)
        return CurationDiff.model_validate(
            {"baseline": info, "items": diff_evidence(snapshot, current)}
        )
    found = _baseline(db, curation_id, current_user.id, current)
    if found is None:
        # A re-curation's first review compares against the active curation it replaces
        active = _active(db, curation, others_only=True)
        if active is None:
            return CurationDiff.model_validate(
                {"baseline": None, "items": diff_evidence({}, current)}
            )
        return CurationDiff.model_validate(
            {
                "baseline": {
                    "audit_id": None,
                    "as_of": active.activated_at,
                    "source": "active_curation",
                },
                "items": diff_evidence(active.curation.evidence_data or {}, current),
            }
        )
    row, source, as_of = found
    snapshot = (row.changes or {}).get("evidence_data") or {}
    return CurationDiff.model_validate(
        {
            "baseline": {"audit_id": row.id, "as_of": as_of, "source": source},
            "items": diff_evidence(snapshot, current),
        }
    )
