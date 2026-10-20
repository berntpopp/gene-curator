"""Unit tests for scope_crud (scope lifecycle, roster helpers, workflow defaults)."""

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.crud.scope import scope_crud
from app.models.models import Scope, ScopeMembership, WorkflowPair
from app.schemas.scope import ScopeCreate, ScopeUpdate
from tests.api.scopes.factories import (
    make_gene,
    make_member,
    make_scope,
    make_user,
)

pytestmark = pytest.mark.unit

PG_ONLY = pytest.mark.skip(reason="uses PostgreSQL EXTRACT(); not runnable on SQLite")


def _scope_create(name: str) -> ScopeCreate:
    return ScopeCreate(name=name, display_name="Display", description="d")


# -----------------------------------------------------------------------------
# Creation and lookup
# -----------------------------------------------------------------------------


def test_create_with_owner_records_creator(db_session: Session) -> None:
    owner = make_user(db_session)
    name = f"crud-{uuid4().hex[:8]}"

    scope = scope_crud.create_with_owner(
        db_session, obj_in=_scope_create(name), owner_id=owner.id
    )

    assert scope.created_by == owner.id
    assert scope.name == name
    assert scope.is_active is True


def test_create_scope_wrapper_and_lookup_by_name(db_session: Session) -> None:
    owner = make_user(db_session)
    name = f"wrap-{uuid4().hex[:8]}"

    created = scope_crud.create_scope(
        db_session, obj_in=_scope_create(name), owner_id=owner.id
    )

    assert scope_crud.get_scope_by_name(db_session, name=name).id == created.id
    assert scope_crud.get_scope(db_session, scope_id=created.id).id == created.id
    assert scope_crud.get_scope(db_session, scope_id=uuid4()) is None
    assert scope_crud.get_by_name(db_session, name="missing-name") is None


# -----------------------------------------------------------------------------
# Listing
# -----------------------------------------------------------------------------


def test_get_multi_filters_active_and_institution(db_session: Session) -> None:
    tag = uuid4().hex[:6]
    active = make_scope(db_session, name=f"act-{tag}")
    inactive = make_scope(db_session, is_active=False, name=f"off-{tag}")
    active.institution = f"Inst-{tag}"
    db_session.commit()

    only_active = {s.id for s in scope_crud.get_multi(db_session, limit=1000)}
    everything = {
        s.id for s in scope_crud.get_multi(db_session, limit=1000, active_only=False)
    }
    by_institution = scope_crud.get_scopes_by_institution(db_session, f"Inst-{tag}")

    assert active.id in only_active
    assert inactive.id not in only_active
    assert inactive.id in everything
    assert [s.id for s in by_institution] == [active.id]


def test_get_multi_with_counts_reports_genes_and_accepted_members(
    db_session: Session,
) -> None:
    from app.models.models import GeneScopeAssignment

    scope = make_scope(db_session)
    member = make_user(db_session)
    pending = make_user(db_session)
    make_member(db_session, scope, member, "viewer")
    make_member(db_session, scope, pending, "viewer", accepted=False)
    gene = make_gene(db_session)
    db_session.add(
        GeneScopeAssignment(gene_id=gene.id, scope_id=scope.id, is_active=True)
    )
    db_session.commit()

    rows = scope_crud.get_multi_with_counts(db_session, limit=1000)
    row = next(r for r in rows if r["id"] == scope.id)

    assert row["gene_count"] == 1
    assert row["member_count"] == 1


def test_get_user_scopes_by_ids(db_session: Session) -> None:
    keep = make_scope(db_session)
    skip = make_scope(db_session)
    off = make_scope(db_session, is_active=False)

    found = scope_crud.get_user_scopes(
        db_session, user_scope_ids=[keep.id, skip.id, off.id]
    )
    found_all = scope_crud.get_user_scopes(
        db_session, user_scope_ids=[keep.id, off.id], active_only=False
    )

    assert {s.id for s in found} == {keep.id, skip.id}
    assert {s.id for s in found_all} == {keep.id, off.id}


# -----------------------------------------------------------------------------
# Update and deletion
# -----------------------------------------------------------------------------


def test_update_scope_by_id_and_missing(db_session: Session) -> None:
    scope = make_scope(db_session)

    updated = scope_crud.update_scope(
        db_session, scope.id, ScopeUpdate(display_name="New Name")
    )

    assert updated is not None
    assert updated.display_name == "New Name"
    assert scope_crud.update_scope(db_session, uuid4(), {"display_name": "x"}) is None


def test_soft_delete_deactivates_scope(db_session: Session) -> None:
    scope = make_scope(db_session)

    assert scope_crud.delete_scope(db_session, scope.id) is True

    db_session.refresh(scope)
    assert scope.is_active is False
    assert db_session.get(Scope, scope.id) is not None


def test_hard_delete_removes_scope_and_memberships(db_session: Session) -> None:
    scope = make_scope(db_session)
    member = make_user(db_session)
    membership_id = make_member(db_session, scope, member, "viewer").id

    assert scope_crud.delete_scope(db_session, scope.id, soft_delete=False) is True

    db_session.expire_all()
    assert db_session.get(Scope, scope.id) is None
    assert db_session.get(ScopeMembership, membership_id) is None


def test_delete_missing_scope_returns_false(db_session: Session) -> None:
    assert scope_crud.delete_scope(db_session, uuid4()) is False


def test_has_active_assignments(db_session: Session) -> None:
    from app.models.models import GeneScopeAssignment

    scope = make_scope(db_session)
    assert scope_crud.has_active_assignments(db_session, scope_id=scope.id) is False

    gene = make_gene(db_session)
    db_session.add(
        GeneScopeAssignment(gene_id=gene.id, scope_id=scope.id, is_active=True)
    )
    db_session.commit()

    assert scope_crud.has_active_assignments(db_session, scope_id=scope.id) is True


# -----------------------------------------------------------------------------
# Roster helpers (assign / remove / list)
# -----------------------------------------------------------------------------


def test_assign_users_creates_viewers_and_skips_unknown(db_session: Session) -> None:
    scope = make_scope(db_session)
    newcomer = make_user(db_session)

    count = scope_crud.assign_users(
        db_session, scope_id=scope.id, user_ids=[newcomer.id, uuid4()]
    )

    assert count == 1
    membership = (
        db_session.query(ScopeMembership)
        .filter_by(scope_id=scope.id, user_id=newcomer.id)
        .one()
    )
    assert membership.role == "viewer"
    assert membership.accepted_at is not None


def test_assign_users_reactivates_inactive_but_not_active(db_session: Session) -> None:
    scope = make_scope(db_session)
    former = make_user(db_session)
    active = make_user(db_session)
    make_member(db_session, scope, former, "curator", is_active=False)
    make_member(db_session, scope, active, "curator")

    count = scope_crud.assign_users(
        db_session, scope_id=scope.id, user_ids=[former.id, active.id]
    )

    assert count == 1
    db_session.expire_all()
    reactivated = (
        db_session.query(ScopeMembership)
        .filter_by(scope_id=scope.id, user_id=former.id)
        .one()
    )
    assert reactivated.is_active is True


def test_remove_users_soft_deletes_active_only(db_session: Session) -> None:
    scope = make_scope(db_session)
    member = make_user(db_session)
    make_member(db_session, scope, member, "viewer")

    removed = scope_crud.remove_users(
        db_session, scope_id=scope.id, user_ids=[member.id, uuid4()]
    )

    assert removed == 1
    db_session.expire_all()
    membership = (
        db_session.query(ScopeMembership)
        .filter_by(scope_id=scope.id, user_id=member.id)
        .one()
    )
    assert membership.is_active is False


def test_get_scope_users_lists_accepted_active_members(db_session: Session) -> None:
    scope = make_scope(db_session)
    member = make_user(db_session, name="Listed")
    make_member(db_session, scope, member, "reviewer")
    make_member(db_session, scope, make_user(db_session), "viewer", accepted=False)

    users = scope_crud.get_scope_users(db_session, scope_id=scope.id)

    assert [u["user_id"] for u in users] == [member.id]
    assert users[0]["scope_role"] == "reviewer"
    assert users[0]["user_name"] == "Listed"


def test_set_default_workflow_pair(db_session: Session) -> None:
    scope = make_scope(db_session)
    pair = WorkflowPair(id=uuid4(), name="wp", version="1.0")
    db_session.add(pair)
    db_session.commit()

    updated = scope_crud.set_default_workflow_pair(
        db_session, scope_id=scope.id, workflow_pair_id=pair.id
    )

    assert updated is not None
    assert updated.default_workflow_pair_id == pair.id
    assert (
        scope_crud.set_default_workflow_pair(
            db_session, scope_id=uuid4(), workflow_pair_id=pair.id
        )
        is None
    )


def test_available_workflow_pairs_only_active(db_session: Session) -> None:
    scope = make_scope(db_session)
    live = WorkflowPair(id=uuid4(), name="live", version="1.0", is_active=True)
    dead = WorkflowPair(id=uuid4(), name="dead", version="1.0", is_active=False)
    db_session.add_all([live, dead])
    db_session.commit()

    pairs = scope_crud.get_available_workflow_pairs(db_session, scope_id=scope.id)

    names = {p["name"] for p in pairs}
    assert "live" in names
    assert "dead" not in names


@PG_ONLY
def test_detailed_statistics_counts_members_and_genes(db_session: Session) -> None:
    scope = make_scope(db_session)
    member = make_user(db_session)
    make_member(db_session, scope, member, "viewer")

    stats = scope_crud.get_detailed_statistics(db_session, scope_id=scope.id)

    assert stats["member_count"] == 1


@PG_ONLY
def test_performance_metrics_empty_scope(db_session: Session) -> None:
    scope = make_scope(db_session)

    metrics = scope_crud.get_performance_metrics(db_session, scope_id=scope.id)

    assert metrics["approval_rate"] is None
