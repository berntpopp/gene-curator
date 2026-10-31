"""Capability matrix (#284 first slice), curation write roles (#196), one 4-eyes rule (#324)."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import capabilities as caps
from app.models.models import CurationNew, CurationStatus, PrecurationNew, Scope
from tests.api.scopes.factories import auth_headers, make_member, make_user

pytestmark = pytest.mark.unit

ALL = [caps.VIEW, caps.EDIT, caps.REVIEW, caps.ASSIGN_GENES, caps.MANAGE_MEMBERS]
GRANTED = {
    "viewer": {caps.VIEW},
    "reviewer": {caps.VIEW, caps.REVIEW},
    "curator": {caps.VIEW, caps.EDIT},
    "admin": set(ALL),
}


@pytest.fixture(autouse=True)
def no_rls_on_sqlite():
    with (
        patch("app.api.v1.endpoints.curations.set_rls_context"),
        patch("app.api.v1.endpoints.precurations.set_rls_context"),
    ):
        yield


@pytest.mark.parametrize("capability", ALL)
@pytest.mark.parametrize("role", [*GRANTED, "platform_admin", "outsider", "pending"])
def test_require_matrix(
    db_session: Session, test_scope: Scope, role: str, capability: str
):
    user = make_user(db_session, role="admin" if role == "platform_admin" else "user")
    if role in GRANTED or role == "pending":
        make_member(
            db_session,
            test_scope,
            user,
            "admin" if role == "pending" else role,
            accepted=role != "pending",
        )
    allowed = role == "platform_admin" or capability in GRANTED.get(role, set())
    if allowed:
        caps.require(db_session, user, test_scope.id, capability)
    else:
        with pytest.raises(HTTPException) as error:
            caps.require(db_session, user, test_scope.id, capability)
        assert error.value.status_code == 403


def test_other_scope_admin_has_no_capability(db_session: Session, test_scope: Scope):
    other = Scope(name="other-scope", display_name="Other", is_active=True)
    db_session.add(other)
    db_session.commit()
    user = make_user(db_session)
    make_member(db_session, other, user, "admin")
    with pytest.raises(HTTPException):
        caps.require(db_session, user, test_scope.id, caps.EDIT)


@pytest.mark.parametrize(
    ("role", "expected"),
    # another curator is not the author (#609 delta review); the author is in test_edits_by_others
    [("curator", 403), ("admin", 200), ("reviewer", 403), ("viewer", 403)],
)
def test_update_curation_by_scope_role(
    client: TestClient,
    db_session: Session,
    test_scope: Scope,
    test_curation: CurationNew,
    role: str,
    expected: int,
):
    user = make_user(db_session)
    make_member(db_session, test_scope, user, role)
    response = client.put(
        f"/api/v1/curations/{test_curation.id}",
        headers=auth_headers(user),
        json={"lock_version": test_curation.lock_version, "evidence_data": {"a": 1}},
    )
    assert response.status_code == expected, response.text


@pytest.mark.parametrize("scope_role", [None, "reviewer", "admin"])
def test_nobody_approves_own_precuration(
    client: TestClient,
    db_session: Session,
    test_scope: Scope,
    test_precuration: PrecurationNew,
    scope_role: str | None,
):
    """Platform admins included (#324)."""
    user = make_user(db_session, role="admin")
    if scope_role:
        make_member(db_session, test_scope, user, scope_role)
    test_precuration.created_by = user.id
    test_precuration.status = CurationStatus.SUBMITTED
    db_session.commit()
    response = client.post(
        f"/api/v1/precurations/{test_precuration.id}/approve",
        headers=auth_headers(user),
    )
    assert response.status_code == 403, response.text


def _creator_with(db_session, scope, curation, role, **kw):
    user = make_user(db_session)
    curation.created_by = user.id
    db_session.commit()
    if role:
        make_member(db_session, scope, user, role, **kw)
    return user


@pytest.mark.parametrize("action", ["delete", "draft", "submit"])
@pytest.mark.parametrize(
    ("role", "kw"),
    [("viewer", {}), ("reviewer", {}), (None, {}), ("curator", {"accepted": False})],
)
def test_creator_without_edit_capability_cannot_write(
    client, db_session, test_scope, test_curation, action, role, kw
):
    """Downgraded, removed or pending creators lose write access."""
    user = _creator_with(db_session, test_scope, test_curation, role, **kw)
    url = f"/api/v1/curations/{test_curation.id}"
    if action == "delete":
        response = client.delete(url, headers=auth_headers(user))
    elif action == "draft":
        response = client.patch(
            url + "/draft",
            headers=auth_headers(user),
            json={"evidence_data": {}, "lock_version": test_curation.lock_version},
        )
    else:
        response = client.post(
            url + "/submit",
            headers=auth_headers(user),
            json={"lock_version": test_curation.lock_version},
        )
    assert response.status_code == 403, response.text


@pytest.mark.parametrize("role", ["viewer", "reviewer"])
def test_read_only_roles_cannot_delete_curators_draft(
    client, db_session, test_scope, test_curation, role
):
    user = make_user(db_session)
    make_member(db_session, test_scope, user, role)
    response = client.delete(
        f"/api/v1/curations/{test_curation.id}", headers=auth_headers(user)
    )
    assert response.status_code == 403


def test_creator_curator_can_delete_own_draft(
    client, db_session, test_scope, test_curation
):
    user = _creator_with(db_session, test_scope, test_curation, "curator")
    response = client.delete(
        f"/api/v1/curations/{test_curation.id}", headers=auth_headers(user)
    )
    assert response.status_code == 204, response.text
