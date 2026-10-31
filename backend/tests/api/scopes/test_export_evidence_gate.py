"""export_evidence_public (#558): only a signed-in scope admin turns it on; a token or MCP
call may leave it as is or turn it off."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import Scope, UserNew
from app.schemas.scope import ScopeCreate
from tests.api.scopes.factories import auth_headers
from tests.api.scopes.test_approvals_require_session import _pat

pytestmark = pytest.mark.unit


def test_only_a_signed_in_scope_admin_turns_it_on(
    client: TestClient, owner: UserNew, scope_with_admin: Scope
) -> None:
    url = f"/api/v1/scopes/{scope_with_admin.id}"
    on, off = {"export_evidence_public": True}, {"export_evidence_public": False}
    token = _pat(client, owner)
    assert client.patch(url, json=on, headers=token).status_code == 403
    r = client.patch(url, json=on, headers=auth_headers(owner))
    assert r.status_code == 200 and r.json()["export_evidence_public"] is True
    assert client.patch(url, json=on, headers=token).status_code == 200  # unchanged
    r = client.patch(url, json=off, headers=token)
    assert r.status_code == 200 and r.json()["export_evidence_public"] is False


def test_making_the_scope_public_with_it_on_needs_a_session(
    client: TestClient, db_session: Session, owner: UserNew, scope_with_admin: Scope
) -> None:
    """Monkey M1: on while private, then is_public true by token exposed evidence."""
    url = f"/api/v1/scopes/{scope_with_admin.id}"
    token = _pat(client, owner)
    for body in ({"is_public": False}, {"export_evidence_public": True}):
        r = client.patch(url, json=body, headers=auth_headers(owner))
        assert r.status_code == 200, r.text
    r = client.patch(url, json={"is_public": True}, headers=token)
    assert r.status_code == 403, r.text
    db_session.refresh(scope_with_admin)
    assert scope_with_admin.is_public is False
    r = client.patch(url, json={"is_public": True}, headers=auth_headers(owner))
    assert r.status_code == 200 and r.json()["is_public"] is True
    assert (
        client.patch(url, json={"is_public": False}, headers=token).status_code == 200
    )


def test_a_new_scope_cannot_start_with_it_on() -> None:
    """Create takes no export_evidence_public: a new scope starts with it off."""
    body = {"name": "m1", "display_name": "M1", "is_public": True}
    body["export_evidence_public"] = True
    assert "export_evidence_public" not in ScopeCreate(**body).model_dump()
