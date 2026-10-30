"""export_evidence_public (#558): only a signed-in scope admin turns it on; a token or MCP
call may leave it as is or turn it off."""

import pytest
from fastapi.testclient import TestClient

from app.models.models import Scope, UserNew
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
