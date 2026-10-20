"""Fixtures for scope, membership, invitation, user/auth and workflow API tests.

PostgreSQL RLS cannot run on SQLite, so set_rls_context is replaced by a no-op.
Scope-level authorization is still enforced by require_scope_role, which is
exercised directly by these tests.
"""

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.models import Scope, UserNew
from tests.api.scopes.factories import make_member, make_scope, make_user


@pytest.fixture(autouse=True)
def _no_rls_on_sqlite() -> Iterator[None]:
    """Make set_rls_context a no-op: SET app.current_user_id is PostgreSQL-only."""
    with patch("app.core.deps.set_rls_context"):
        yield


@pytest.fixture
def app_admin(db_session: Session) -> UserNew:
    return make_user(db_session, role="admin", name="App Admin")


@pytest.fixture
def owner(db_session: Session) -> UserNew:
    """Ordinary user (application role 'user')."""
    return make_user(db_session, role="user", name="Owner")


@pytest.fixture
def scope_with_admin(db_session: Session, owner: UserNew) -> Scope:
    """Scope whose 'owner' is an accepted scope admin."""
    scope = make_scope(db_session, created_by=owner.id)
    make_member(db_session, scope, owner, "admin")
    return scope


@pytest.fixture
def curator(db_session: Session, scope_with_admin: Scope) -> UserNew:
    user = make_user(db_session, role="user", name="Curator")
    make_member(db_session, scope_with_admin, user, "curator")
    return user


@pytest.fixture
def reviewer(db_session: Session, scope_with_admin: Scope) -> UserNew:
    user = make_user(db_session, role="user", name="Reviewer")
    make_member(db_session, scope_with_admin, user, "reviewer")
    return user


@pytest.fixture
def viewer(db_session: Session, scope_with_admin: Scope) -> UserNew:
    user = make_user(db_session, role="user", name="Viewer")
    make_member(db_session, scope_with_admin, user, "viewer")
    return user


@pytest.fixture
def outsider(db_session: Session) -> UserNew:
    """Active user with no membership in any test scope."""
    return make_user(db_session, role="user", name="Outsider")
