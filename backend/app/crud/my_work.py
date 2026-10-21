"""Aggregate the current user's work, grouped by next action."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from app.models import (
    CurationNew,
    CurationStatus,
    Gene,
    GeneScopeAssignment,
    PrecurationNew,
    Review,
    ReviewStatus,
    Scope,
    ScopeMembership,
    UserNew,
)
from app.schemas.my_work import WorkItem, WorkKind, WorkTab

DONE_WINDOW = timedelta(days=7)
_S = CurationStatus


def _item(row: Any, kind: WorkKind, tab: WorkTab, verb: str, link: str) -> WorkItem:
    obj, symbol, scope_name, item_type = row
    return WorkItem(
        kind=kind,
        tab=tab,
        verb=verb,
        item_type=item_type,
        item_id=obj.id,
        gene_id=obj.gene_id,
        gene_symbol=symbol,
        scope_id=obj.scope_id,
        scope_name=scope_name,
        link=link.format(s=obj.scope_id, i=obj.id, g=obj.gene_id),
        updated_at=getattr(obj, "updated_at", None) or obj.assigned_at,
    )


def _rows(
    db: Session, scopes: list[UUID], model: Any, kind: str, *where: Any
) -> list[Any]:
    stmt = (
        select(model, Gene.approved_symbol, Scope.name)
        .join(Gene, Gene.id == model.gene_id)
        .join(Scope, Scope.id == model.scope_id)
        .where(model.scope_id.in_(scopes), *where)
    )
    return [(o, g, s, kind) for o, g, s in db.execute(stmt)]


def _member_scopes(
    db: Session, user: UserNew, roles: tuple[str, ...] | None = None
) -> list[UUID]:
    """Accepted, active memberships only; platform admins get no implicit scopes."""
    stmt = (
        select(ScopeMembership.scope_id)
        .join(Scope, Scope.id == ScopeMembership.scope_id)
        .where(
            ScopeMembership.user_id == user.id,
            ScopeMembership.is_active,
            ScopeMembership.accepted_at.isnot(None),
            Scope.is_active,
        )
    )
    if roles:
        stmt = stmt.where(ScopeMembership.role.in_(roles))
    return list(db.execute(stmt).scalars())


def get_my_work(db: Session, user: UserNew) -> list[WorkItem]:
    scopes = _member_scopes(db, user)
    items = _needs_you(db, user, scopes)
    items += _reviews_waiting_done(
        db, user, scopes, _member_scopes(db, user, ("admin", "reviewer"))
    )
    return items


# Newest review decides: a later approval or new round clears "changes requested".
_latest_review = (
    select(Review.status)
    .where(Review.curation_id == CurationNew.id)
    .order_by(Review.assigned_at.desc())
    .limit(1)
    .scalar_subquery()
)
_changes_requested = _latest_review == ReviewStatus.NEEDS_REVISION
# NULL-safe negation: a curation with no review at all is not 'changes requested'
_not_changes_requested = _latest_review.is_distinct_from(ReviewStatus.NEEDS_REVISION)


def _needs_you(db: Session, user: UserNew, scopes: list[UUID]) -> list[WorkItem]:
    items: list[WorkItem] = []
    rows = lambda *a: _rows(db, scopes, *a)  # noqa: E731

    # Assigned genes nobody has started yet.
    started = lambda m: exists().where(  # noqa: E731
        m.gene_id == GeneScopeAssignment.gene_id,
        m.scope_id == GeneScopeAssignment.scope_id,
        m.created_by == user.id,
    )
    for r in rows(
        GeneScopeAssignment,
        "assignment",
        GeneScopeAssignment.assigned_curator_id == user.id,
        GeneScopeAssignment.is_active,
        ~started(PrecurationNew),
        ~started(CurationNew),
    ):
        items.append(
            _item(
                r,
                "assignment",
                "needs_you",
                "Start precuration",
                "/scopes/{s}/genes/{g}/precuration/new",
            )
        )

    mine = [CurationNew.created_by == user.id]
    pmine = [PrecurationNew.created_by == user.id]
    cedit = "/scopes/{s}/curations/{i}/edit"
    pview = "/scopes/{s}/precurations/{i}"

    open_states = CurationNew.status.in_((_S.DRAFT, _S.IN_REVIEW))
    for r in rows(CurationNew, "curation", *mine, open_states, _changes_requested):
        items.append(
            _item(
                r, "changes_requested", "needs_you", "Address requested changes", cedit
            )
        )
    for r in rows(
        CurationNew,
        "curation",
        *mine,
        CurationNew.status == _S.DRAFT,
        _not_changes_requested,
    ):
        items.append(_item(r, "draft", "needs_you", "Continue curation draft", cedit))
    for r in rows(
        PrecurationNew, "precuration", *pmine, PrecurationNew.status == _S.DRAFT
    ):
        items.append(
            _item(r, "draft", "needs_you", "Continue precuration draft", pview)
        )

    return items


def _assignment_filters(user: UserNew) -> list[Any]:
    """Skip items assigned to another reviewer, or that I already decided."""

    def has(*cond: Any) -> Any:
        return exists().where(Review.curation_id == CurationNew.id, *cond)

    pending = ReviewStatus.PENDING
    mine_open = has(Review.reviewer_id == user.id, Review.status == pending)
    others = has(Review.reviewer_id != user.id, Review.status == pending)
    decided = has(Review.reviewer_id == user.id, Review.status != pending)
    return [~decided, or_(~others, mine_open)]


def _reviews_waiting_done(
    db: Session, user: UserNew, scopes: list[UUID], reviewer_scopes: list[UUID]
) -> list[WorkItem]:
    items: list[WorkItem] = []
    rows = lambda *a: _rows(db, scopes, *a)  # noqa: E731
    cview = "/scopes/{s}/curations/{i}"
    pview = "/scopes/{s}/precurations/{i}"
    cutoff = datetime.now(UTC) - DONE_WINDOW
    # Same definition as the pending_review list filter: reviewer scopes, not my own.
    for model, kind, status, link in (
        (CurationNew, "curation", _S.IN_REVIEW, cview),
        (PrecurationNew, "precuration", _S.SUBMITTED, pview),
    ):
        extra = _assignment_filters(user) if model is CurationNew else []
        for r in rows(
            model,
            kind,
            model.status == status,
            model.created_by != user.id,
            model.scope_id.in_(reviewer_scopes),
            *extra,
        ):
            items.append(_item(r, "review", "needs_you", f"Review {kind}", link))

    for model, kind, link, waiting, done in (
        (
            CurationNew,
            "curation",
            cview,
            (_S.SUBMITTED, _S.IN_REVIEW),
            (_S.APPROVED, _S.ACTIVE),
        ),
        (
            PrecurationNew,
            "precuration",
            pview,
            (_S.SUBMITTED,),
            (_S.APPROVED, _S.ACTIVE),
        ),
    ):
        mm = [model.created_by == user.id]
        if model is CurationNew:
            mm.append(_not_changes_requested)
        for r in rows(model, kind, *mm, model.status.in_(waiting)):
            items.append(_item(r, "waiting", "waiting", "Waiting for review", link))
        for r in rows(
            model, kind, *mm, model.status.in_(done), model.updated_at >= cutoff
        ):
            items.append(_item(r, "done", "done", f"Finished {kind}", link))

    return items
