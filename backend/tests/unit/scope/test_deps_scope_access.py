"""Unit tests for app.core.deps: authentication chain and scope role gates.

The scope gates are called directly (they are plain functions with injected
arguments). set_rls_context is patched because app.current_user_id is
PostgreSQL-only; the real one is tested against a mocked PostgreSQL connection.
"""

from collections.abc import Iterator
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core import deps
from app.core.enums import ScopeRole
from app.core.security import create_access_token
from app.models.models import Scope, UserNew
from tests.api.scopes.factories import make_member, make_scope, make_user, token_for

pytestmark = pytest.mark.unit

# Captured at import time, before the autouse fixture replaces the module attribute.
_REAL_SET_RLS_CONTEXT = deps.set_rls_context


@pytest.fixture(autouse=True)
def _no_rls() -> Iterator[None]:
    with patch("app.core.deps.set_rls_context"):
        yield


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _gate(role: ScopeRole, db: Session, user: UserNew, scope: Scope) -> Scope:
    checker = deps.require_scope_role(role)
    return checker(scope_id=scope.id, db=db, current_user=user)  # type: ignore[no-any-return]


@pytest.fixture
def scope(db_session: Session) -> Scope:
    return make_scope(db_session)


@pytest.fixture
def members(db_session: Session, scope: Scope) -> dict[str, UserNew]:
    result = {}
    for role in ("admin", "curator", "reviewer", "viewer"):
        user = make_user(db_session, role="user", name=role)
        make_member(db_session, scope, user, role)
        result[role] = user
    return result


# -----------------------------------------------------------------------------
# Scope role gates
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("required", "allowed", "denied"),
    [
        (ScopeRole.VIEWER, ["admin", "curator", "reviewer", "viewer"], []),
        (ScopeRole.REVIEWER, ["admin", "reviewer"], ["curator", "viewer"]),
        (ScopeRole.CURATOR, ["admin", "curator"], ["reviewer", "viewer"]),
        (ScopeRole.ADMIN, ["admin"], ["curator", "reviewer", "viewer"]),
    ],
)
def test_scope_role_hierarchy(
    db_session: Session,
    scope: Scope,
    members: dict[str, UserNew],
    required: ScopeRole,
    allowed: list[str],
    denied: list[str],
) -> None:
    for role in allowed:
        assert _gate(required, db_session, members[role], scope).id == scope.id
    for role in denied:
        with pytest.raises(HTTPException) as exc:
            _gate(required, db_session, members[role], scope)
        assert exc.value.status_code == 403


def test_non_member_is_forbidden(db_session: Session, scope: Scope) -> None:
    stranger = make_user(db_session)

    with pytest.raises(HTTPException) as exc:
        _gate(ScopeRole.VIEWER, db_session, stranger, scope)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Not a member of this scope"


def test_pending_invitation_does_not_pass_gate(
    db_session: Session, scope: Scope
) -> None:
    invitee = make_user(db_session)
    make_member(db_session, scope, invitee, "admin", accepted=False)

    with pytest.raises(HTTPException) as exc:
        _gate(ScopeRole.VIEWER, db_session, invitee, scope)

    assert exc.value.status_code == 403


def test_deactivated_membership_does_not_pass_gate(
    db_session: Session, scope: Scope
) -> None:
    former = make_user(db_session)
    make_member(db_session, scope, former, "admin", is_active=False)

    with pytest.raises(HTTPException):
        _gate(ScopeRole.VIEWER, db_session, former, scope)


def test_application_admin_bypasses_membership(
    db_session: Session, scope: Scope
) -> None:
    app_admin = make_user(db_session, role="admin")

    assert _gate(ScopeRole.ADMIN, db_session, app_admin, scope).id == scope.id


def test_gate_for_unknown_scope_is_404_for_admin(db_session: Session) -> None:
    app_admin = make_user(db_session, role="admin")
    checker = deps.require_scope_role(ScopeRole.VIEWER)

    with pytest.raises(HTTPException) as exc:
        checker(scope_id=uuid4(), db=db_session, current_user=app_admin)

    assert exc.value.status_code == 404


# -----------------------------------------------------------------------------
# Authentication chain
# -----------------------------------------------------------------------------


def test_get_current_user_resolves_token_subject(db_session: Session) -> None:
    user = make_user(db_session)

    resolved = deps.get_current_user(db=db_session, credentials=_creds(token_for(user)))

    assert resolved.id == user.id


def test_get_current_user_rejects_bad_tokens(db_session: Session) -> None:
    creds = _creds(create_access_token(data={"email": "no-subject@test.com"}))
    garbage = _creds("garbage")

    with pytest.raises(HTTPException) as exc:
        deps.get_current_user(db=db_session, credentials=creds)
    with pytest.raises(HTTPException):
        deps.get_current_user(db=db_session, credentials=garbage)

    assert exc.value.status_code == 401


def test_get_current_user_rejects_unknown_subject(db_session: Session) -> None:
    token = create_access_token(data={"sub": str(uuid4())})

    with pytest.raises(HTTPException) as exc:
        deps.get_current_user(db=db_session, credentials=_creds(token))

    assert exc.value.status_code == 401


def test_get_current_active_user_rejects_inactive(db_session: Session) -> None:
    inactive = make_user(db_session, is_active=False)

    with pytest.raises(HTTPException) as exc:
        deps.get_current_active_user(current_user=inactive)

    assert exc.value.status_code == 401


def test_get_current_admin_user_requires_application_admin(db_session: Session) -> None:
    plain = make_user(db_session)
    admin = make_user(db_session, role="admin")

    assert deps.get_current_admin_user(current_user=admin).id == admin.id
    with pytest.raises(HTTPException) as exc:
        deps.get_current_admin_user(current_user=plain)
    assert exc.value.status_code == 403


def test_optional_user_is_none_without_or_with_bad_credentials(
    db_session: Session,
) -> None:
    user = make_user(db_session)

    assert deps.get_current_user_optional(db=db_session, credentials=None) is None
    assert (
        deps.get_current_user_optional(db=db_session, credentials=_creds("junk"))
        is None
    )
    assert (
        deps.get_current_user_optional(
            db=db_session, credentials=_creds(token_for(user))
        )
        is not None
    )


def test_optional_user_hides_inactive_accounts(db_session: Session) -> None:
    inactive = make_user(db_session, is_active=False)

    result = deps.get_current_user_optional(
        db=db_session, credentials=_creds(token_for(inactive))
    )

    assert result is None


# -----------------------------------------------------------------------------
# RLS context (the real implementation, captured before patching)
# -----------------------------------------------------------------------------


def test_set_rls_context_is_transaction_local_and_reapplied() -> None:
    user = UserNew(id=uuid4(), email="rls@test.com", name="RLS", role="user")
    db = MagicMock()
    db.info = {}
    db.connection.return_value.dialect.name = "postgresql"

    _REAL_SET_RLS_CONTEXT(db, user)

    # Remembered on the session, so after_begin re-applies it after each commit.
    assert db.info["rls_user_id"] == str(user.id)
    statement, params = db.connection.return_value.execute.call_args.args
    assert "set_config('app.current_user_id', :uid, true)" in str(statement)
    assert params == {"uid": str(user.id)}
