"""Unit tests for scope_membership_crud (invitations, acceptance, roster queries)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.enums import ScopeRole
from app.crud.scope_membership import (
    INVITATION_VALIDITY_DAYS,
    is_invitation_expired,
    scope_membership_crud,
)
from app.models.models import Scope, ScopeMembership, UserNew
from app.schemas.scope_membership import ScopeMembershipCreate
from tests.api.scopes.factories import make_member, make_scope, make_user

pytestmark = pytest.mark.unit


def _create(
    user_id: UUID | None = None, email: str | None = None
) -> ScopeMembershipCreate:
    return ScopeMembershipCreate(
        user_id=user_id, email=email, team_id=None, role=ScopeRole.CURATOR
    )


# -----------------------------------------------------------------------------
# Expiry helper
# -----------------------------------------------------------------------------


def test_expiry_helper_handles_naive_and_aware_timestamps() -> None:
    now = datetime.now(UTC)

    assert is_invitation_expired(None, now) is False
    assert is_invitation_expired(now - timedelta(seconds=1), now) is True
    assert is_invitation_expired(now + timedelta(days=1), now) is False
    # SQLite hands back naive datetimes; they are interpreted as UTC
    naive_past = (now - timedelta(days=1)).replace(tzinfo=None)
    assert is_invitation_expired(naive_past, now) is True


# -----------------------------------------------------------------------------
# Invitations
# -----------------------------------------------------------------------------


def test_create_invitation_is_pending_with_expiry(db_session: Session) -> None:
    scope = make_scope(db_session)
    invitee = make_user(db_session)
    inviter = make_user(db_session)

    membership = scope_membership_crud.create_invitation(
        db_session,
        scope_id=scope.id,
        invited_by_id=inviter.id,
        obj_in=_create(user_id=invitee.id),
    )

    assert membership.accepted_at is None
    assert membership.is_active is True
    assert membership.invited_by == inviter.id
    expires = membership.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    assert expires - membership.invited_at.replace(tzinfo=UTC) >= timedelta(
        days=INVITATION_VALIDITY_DAYS - 1
    )


def test_email_only_invitation_is_refused_cleanly(db_session: Session) -> None:
    """Regression: email-only invites used to hit a NOT NULL violation (HTTP 500)."""
    scope = make_scope(db_session)

    with pytest.raises(ValueError, match="not supported"):
        scope_membership_crud.create_invitation(
            db_session,
            scope_id=scope.id,
            invited_by_id=make_user(db_session).id,
            obj_in=_create(email="future.member@example.org"),
        )


def test_create_invitation_unknown_user_raises(db_session: Session) -> None:
    scope = make_scope(db_session)

    with pytest.raises(ValueError, match="User not found"):
        scope_membership_crud.create_invitation(
            db_session,
            scope_id=scope.id,
            invited_by_id=uuid4(),
            obj_in=_create(user_id=uuid4()),
        )


def test_create_invitation_for_existing_member_raises(db_session: Session) -> None:
    scope = make_scope(db_session)
    member = make_user(db_session)
    make_member(db_session, scope, member, "viewer")

    with pytest.raises(ValueError, match="already a member"):
        scope_membership_crud.create_invitation(
            db_session,
            scope_id=scope.id,
            invited_by_id=member.id,
            obj_in=_create(user_id=member.id),
        )


# -----------------------------------------------------------------------------
# Acceptance
# -----------------------------------------------------------------------------


def _pending_for(db: Session, scope: Scope, user: UserNew) -> ScopeMembership:
    return scope_membership_crud.create_invitation(
        db,
        scope_id=scope.id,
        invited_by_id=user.id,
        obj_in=_create(user_id=user.id),
    )


def test_accept_sets_accepted_at(db_session: Session) -> None:
    scope = make_scope(db_session)
    invitee = make_user(db_session)
    pending = _pending_for(db_session, scope, invitee)

    accepted = scope_membership_crud.accept_invitation(
        db_session, membership_id=pending.id, user_id=invitee.id
    )

    assert accepted.accepted_at is not None


def test_accept_unknown_membership_raises(db_session: Session) -> None:
    with pytest.raises(ValueError, match="Invitation not found"):
        scope_membership_crud.accept_invitation(
            db_session, membership_id=uuid4(), user_id=uuid4()
        )


def test_accept_expired_invitation_raises_and_stays_pending(
    db_session: Session,
) -> None:
    scope = make_scope(db_session)
    invitee = make_user(db_session)
    pending = _pending_for(db_session, scope, invitee)
    pending.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    with pytest.raises(ValueError, match="expired"):
        scope_membership_crud.accept_invitation(
            db_session, membership_id=pending.id, user_id=invitee.id
        )
    db_session.refresh(pending)
    assert pending.accepted_at is None


def test_create_owner_membership_is_accepted_admin(db_session: Session) -> None:
    """Regression at CRUD level: the owner's membership is active and accepted."""
    scope = make_scope(db_session)
    owner = make_user(db_session)

    membership = scope_membership_crud.create_owner_membership(
        db_session, scope_id=scope.id, owner_id=owner.id
    )

    assert membership.role == "admin"
    assert membership.accepted_at is not None
    assert membership.is_active is True
    assert membership.expires_at is not None
    assert (
        scope_membership_crud.get_user_role_in_scope(
            db_session, user_id=owner.id, scope_id=scope.id
        )
        == ScopeRole.ADMIN
    )


# -----------------------------------------------------------------------------
# Roster queries
# -----------------------------------------------------------------------------


def test_list_members_counts_roles_and_pending(db_session: Session) -> None:
    scope = make_scope(db_session)
    admin = make_user(db_session, name="Admin")
    reviewer = make_user(db_session, name="Reviewer")
    pending = make_user(db_session, name="Pending")
    make_member(db_session, scope, admin, "admin")
    make_member(db_session, scope, reviewer, "reviewer")
    make_member(db_session, scope, pending, "viewer", accepted=False)

    active = scope_membership_crud.list_members(db_session, scope_id=scope.id)
    everyone = scope_membership_crud.list_members(
        db_session, scope_id=scope.id, include_pending=True
    )

    assert active.total == 2
    assert active.active_count == 2
    assert active.role_counts == {"admin": 1, "curator": 0, "reviewer": 1, "viewer": 0}
    assert everyone.total == 3
    assert everyone.pending_count == 1
    pending_entry = next(m for m in everyone.members if m.user_email == pending.email)
    assert pending_entry.is_pending is True
    assert pending_entry.user_full_name == "Pending"


def test_get_user_scopes_excludes_pending_inactive_and_filters_role(
    db_session: Session,
) -> None:
    user = make_user(db_session)
    as_curator = make_scope(db_session)
    as_viewer = make_scope(db_session)
    pending_scope = make_scope(db_session)
    inactive_scope = make_scope(db_session)
    make_member(db_session, as_curator, user, "curator")
    make_member(db_session, as_viewer, user, "viewer")
    make_member(db_session, pending_scope, user, "admin", accepted=False)
    make_member(db_session, inactive_scope, user, "admin", is_active=False)

    everything = scope_membership_crud.get_user_scopes(db_session, user_id=user.id)
    curator_only = scope_membership_crud.get_user_scopes(
        db_session, user_id=user.id, role_filter=ScopeRole.CURATOR
    )

    scope_ids = {scope.id for scope, _ in everything}
    assert scope_ids == {as_curator.id, as_viewer.id}
    assert [scope.id for scope, _ in curator_only] == [as_curator.id]


def test_user_role_in_scope_none_for_pending(db_session: Session) -> None:
    scope = make_scope(db_session)
    user = make_user(db_session)
    make_member(db_session, scope, user, "curator", accepted=False)

    assert (
        scope_membership_crud.get_user_role_in_scope(
            db_session, user_id=user.id, scope_id=scope.id
        )
        is None
    )


# -----------------------------------------------------------------------------
# Role change and removal
# -----------------------------------------------------------------------------


def test_update_role_changes_role(db_session: Session) -> None:
    scope = make_scope(db_session)
    user = make_user(db_session)
    membership = make_member(db_session, scope, user, "viewer")

    updated = scope_membership_crud.update_role(
        db_session,
        membership_id=membership.id,
        new_role=ScopeRole.REVIEWER,
        updated_by_id=user.id,
    )

    assert updated.role == "reviewer"


def test_update_role_unknown_membership_raises(db_session: Session) -> None:
    with pytest.raises(ValueError, match="Membership not found"):
        scope_membership_crud.update_role(
            db_session,
            membership_id=uuid4(),
            new_role=ScopeRole.VIEWER,
            updated_by_id=uuid4(),
        )


def test_remove_member_soft_deletes(db_session: Session) -> None:
    scope = make_scope(db_session)
    user = make_user(db_session)
    membership = make_member(db_session, scope, user, "curator")

    removed = scope_membership_crud.remove_member(
        db_session, membership_id=membership.id, removed_by_id=user.id
    )

    assert removed.is_active is False
    assert db_session.get(ScopeMembership, membership.id) is not None


def test_remove_member_unknown_raises(db_session: Session) -> None:
    with pytest.raises(ValueError, match="Membership not found"):
        scope_membership_crud.remove_member(
            db_session, membership_id=uuid4(), removed_by_id=uuid4()
        )


def test_a_removed_member_can_be_invited_again(db_session: Session) -> None:
    scope = make_scope(db_session)
    member = make_user(db_session)
    removed = make_member(db_session, scope, member, "viewer")
    removed.is_active = False
    db_session.commit()

    again = _pending_for(db_session, scope, member)

    assert again.id == removed.id  # the unique (scope, user) row is reused
    assert again.is_active is True
    assert again.accepted_at is None


def test_a_second_invitation_says_it_is_pending(db_session: Session) -> None:
    scope = make_scope(db_session)
    invitee = make_user(db_session)
    _pending_for(db_session, scope, invitee)

    with pytest.raises(ValueError, match="already has a pending invitation"):
        _pending_for(db_session, scope, invitee)


def test_an_expired_invitation_can_be_sent_again(db_session: Session) -> None:
    scope = make_scope(db_session)
    invitee = make_user(db_session)
    old = _pending_for(db_session, scope, invitee)
    old.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    again = _pending_for(db_session, scope, invitee)

    assert again.id == old.id
    assert not is_invitation_expired(again.expires_at, datetime.now(UTC))
