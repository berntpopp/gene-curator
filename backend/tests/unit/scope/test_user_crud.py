"""Unit tests for user_crud (credentials, role checks, scope membership helpers)."""

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.crud.user import user_crud
from app.models.models import ScopeMembership, UserRoleNew
from app.schemas.auth import UserCreate, UserUpdate
from tests.api.scopes.factories import PASSWORD, make_member, make_scope, make_user

pytestmark = pytest.mark.unit


def _user_create(email: str | None = None) -> UserCreate:
    return UserCreate(
        email=email or f"crud-{uuid4().hex[:8]}@test.com",
        name="Created",
        password="secret-password",
        role="user",
        institution="Lab",
        expertise_areas=["cardiology"],
    )


# -----------------------------------------------------------------------------
# Creation and credentials
# -----------------------------------------------------------------------------


def test_create_hashes_password_and_stores_profile(db_session: Session) -> None:
    created = user_crud.create(db_session, obj_in=_user_create())

    assert created.hashed_password != "secret-password"  # noqa: S105
    assert verify_password("secret-password", created.hashed_password)
    assert created.institution == "Lab"
    assert created.expertise_areas == ["cardiology"]
    assert created.is_active is True


def test_get_by_email(db_session: Session) -> None:
    user = make_user(db_session)

    assert user_crud.get_by_email(db_session, email=user.email).id == user.id
    assert user_crud.get_by_email(db_session, email="nobody@test.com") is None


def test_authenticate_success_and_failures(db_session: Session) -> None:
    user = make_user(db_session)

    assert (
        user_crud.authenticate(db_session, email=user.email, password=PASSWORD).id
        == user.id
    )
    assert user_crud.authenticate(db_session, email=user.email, password="nope") is None
    assert (
        user_crud.authenticate(db_session, email="ghost@test.com", password=PASSWORD)
        is None
    )


def test_update_user_changes_profile_fields(db_session: Session) -> None:
    user = make_user(db_session)

    updated = user_crud.update_user(
        db_session,
        user_id=str(user.id),
        user_update=UserUpdate(name="Renamed", is_active=False),
    )

    assert updated is not None
    assert updated.name == "Renamed"
    assert updated.is_active is False


def test_update_user_unknown_returns_none(db_session: Session) -> None:
    assert (
        user_crud.update_user(
            db_session, user_id=str(uuid4()), user_update=UserUpdate(name="x")
        )
        is None
    )


def test_update_password_true_and_false(db_session: Session) -> None:
    user = make_user(db_session)

    assert (
        user_crud.update_password(
            db_session, user_id=str(user.id), new_password="p-new-1"
        )
        is True
    )
    db_session.refresh(user)
    assert verify_password("p-new-1", user.hashed_password)
    assert (
        user_crud.update_password(db_session, user_id=str(uuid4()), new_password="x")
        is False
    )


def test_update_last_login(db_session: Session) -> None:
    user = make_user(db_session)

    assert user_crud.update_last_login(db_session, str(user.id)) is True
    db_session.refresh(user)
    assert user.last_login is not None
    assert user_crud.update_last_login(db_session, str(uuid4())) is False


# -----------------------------------------------------------------------------
# Role helpers
# -----------------------------------------------------------------------------


def test_role_predicates(db_session: Session) -> None:
    admin = make_user(db_session, role="admin")
    plain = make_user(db_session, role="user", is_active=False)

    assert user_crud.is_admin(admin) is True
    assert user_crud.is_admin(plain) is False
    assert user_crud.is_active(plain) is False
    assert user_crud.has_role(admin, UserRoleNew.ADMIN) is True
    assert user_crud.has_any_role(plain, [UserRoleNew.ADMIN]) is False
    assert user_crud.has_any_role(plain, [UserRoleNew.USER, UserRoleNew.ADMIN]) is True


def test_get_by_role_only_active(db_session: Session) -> None:
    active_admin = make_user(db_session, role="admin")
    make_user(db_session, role="admin", is_active=False)

    ids = {u.id for u in user_crud.get_by_role(db_session, role=UserRoleNew.ADMIN)}

    assert active_admin.id in ids
    assert all(
        u.is_active for u in user_crud.get_by_role(db_session, role=UserRoleNew.ADMIN)
    )


def test_search_matches_name_email_or_institution(db_session: Session) -> None:
    tag = uuid4().hex[:8]
    by_name = make_user(db_session, name=f"Ada {tag}")
    by_institution = make_user(db_session, name="Other")
    by_institution.institution = f"Institute {tag}"
    db_session.commit()

    hits = {u.id for u in user_crud.search(db_session, query=tag)}

    assert by_name.id in hits
    assert by_institution.id in hits


def test_search_without_query_returns_page(db_session: Session) -> None:
    make_user(db_session)

    page = user_crud.search(db_session, query="", skip=0, limit=1)

    assert len(page) == 1


def test_statistics_counts_active_and_roles(db_session: Session) -> None:
    make_user(db_session, role="admin")
    make_user(db_session, role="user", is_active=False)

    stats = user_crud.get_statistics(db_session)

    assert stats["total_users"] == stats["active_users"] + stats["inactive_users"]
    assert set(stats["role_distribution"]) == {"admin", "user"}
    assert stats["role_distribution"]["admin"] >= 1


def test_user_activity_summary(db_session: Session) -> None:
    user = make_user(db_session)
    scope = make_scope(db_session)
    make_member(db_session, scope, user, "viewer")

    activity = user_crud.get_user_activity(db_session, user_id=str(user.id))

    assert activity["scope_count"] == 1
    assert activity["role"] == "user"
    assert activity["expertise_areas"] == 0
    assert user_crud.get_user_activity(db_session, user_id=str(uuid4())) == {}


# -----------------------------------------------------------------------------
# Scope helpers
# -----------------------------------------------------------------------------


def test_users_by_scope_only_active_members(db_session: Session) -> None:
    scope = make_scope(db_session)
    member = make_user(db_session)
    lapsed = make_user(db_session)
    make_member(db_session, scope, member, "viewer")
    make_member(db_session, scope, lapsed, "viewer", is_active=False)

    ids = {u.id for u in user_crud.get_users_by_scope(db_session, scope_id=scope.id)}

    assert ids == {member.id}


def test_assign_to_scope_creates_then_reuses_membership(db_session: Session) -> None:
    scope = make_scope(db_session)
    user = make_user(db_session)

    assert user_crud.assign_to_scope(
        db_session, user_id=user.id, scope_id=scope.id, role="curator"
    )
    assert user_crud.assign_to_scope(
        db_session, user_id=user.id, scope_id=scope.id, role="curator"
    )

    rows = (
        db_session.query(ScopeMembership)
        .filter_by(scope_id=scope.id, user_id=user.id)
        .all()
    )
    assert len(rows) == 1
    assert rows[0].role == "curator"


def test_assign_to_scope_reactivates_with_new_role(db_session: Session) -> None:
    scope = make_scope(db_session)
    user = make_user(db_session)
    make_member(db_session, scope, user, "viewer", is_active=False)

    user_crud.assign_to_scope(
        db_session, user_id=user.id, scope_id=scope.id, role="reviewer"
    )

    membership = (
        db_session.query(ScopeMembership)
        .filter_by(scope_id=scope.id, user_id=user.id)
        .one()
    )
    assert membership.is_active is True
    assert membership.role == "reviewer"


def test_assign_to_scope_unknown_user_returns_none(db_session: Session) -> None:
    scope = make_scope(db_session)

    assert (
        user_crud.assign_to_scope(db_session, user_id=uuid4(), scope_id=scope.id)
        is None
    )


def test_remove_from_scope_soft_deletes(db_session: Session) -> None:
    scope = make_scope(db_session)
    user = make_user(db_session)
    make_member(db_session, scope, user, "viewer")

    assert (
        user_crud.remove_from_scope(db_session, user_id=user.id, scope_id=scope.id).id
        == user.id
    )
    membership = (
        db_session.query(ScopeMembership)
        .filter_by(scope_id=scope.id, user_id=user.id)
        .one()
    )
    assert membership.is_active is False
    assert (
        user_crud.remove_from_scope(db_session, user_id=uuid4(), scope_id=scope.id)
        is None
    )
