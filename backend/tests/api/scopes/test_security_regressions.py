"""Regression tests for access-control findings (tokens, pending invitations, scope visibility)."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_refresh_token
from app.models.models import GeneScopeAssignment, Scope, UserNew
from app.services.scope_permissions import ScopePermissionService
from tests.api.scopes.factories import (
    auth_headers,
    make_gene,
    make_member,
    make_scope,
    make_workflow_pair,
)

pytestmark = pytest.mark.unit

GA = "/api/v1/gene-assignments"


def _assignment(
    db: Session, scope: Scope, *, active: bool = True, **kw: object
) -> GeneScopeAssignment:
    row = GeneScopeAssignment(
        gene_id=make_gene(db).id, scope_id=scope.id, is_active=active, **kw
    )
    db.add(row)
    db.commit()
    return row


def _ids(client: TestClient, user: UserNew, query: str = "") -> set[str]:
    response = client.get(f"{GA}/?{query}", headers=auth_headers(user))
    assert response.status_code == 200
    return {a["id"] for a in response.json()["assignments"]}


def test_refresh_token_is_rejected_as_access_token(
    client: TestClient, owner: UserNew
) -> None:
    token = create_refresh_token({"sub": str(owner.id)})
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


def test_pending_invitation_grants_no_scope_access(
    db_session: Session, scope_with_admin: Scope, outsider: UserNew
) -> None:
    make_member(db_session, scope_with_admin, outsider, "curator", accepted=False)
    assert not ScopePermissionService.has_scope_access(
        db_session, outsider, scope_with_admin.id
    )
    assert ScopePermissionService.get_user_scope_ids(db_session, outsider) == []
    assert not ScopePermissionService.can_view_scope(
        db_session, outsider, scope_with_admin
    )


def test_scope_details_hidden_from_non_members(
    client: TestClient, scope_with_admin: Scope, outsider: UserNew, owner: UserNew
) -> None:
    url = f"/api/v1/scopes/{scope_with_admin.id}"
    assert client.get(url, headers=auth_headers(outsider)).status_code == 404
    # Statistics need PostgreSQL: stub them and assert the member got past the gate.
    with patch("app.api.v1.endpoints.scopes.scope_crud.get_with_statistics") as stats:
        stats.return_value = None
        client.get(url, headers=auth_headers(owner))
    stats.assert_called_once()


def test_assignment_list_is_limited_to_member_scopes(
    client: TestClient,
    db_session: Session,
    scope_with_admin: Scope,
    viewer: UserNew,
) -> None:
    other = make_scope(db_session)
    mine = _assignment(db_session, scope_with_admin)
    _assignment(db_session, other)
    _assignment(db_session, other, active=False)
    _assignment(db_session, scope_with_admin, active=False)

    assert _ids(client, viewer) == {str(mine.id)}
    # is_active=false applies the same restriction (only the member scope's row)
    assert len(_ids(client, viewer, "is_active=false")) == 1


def test_assignment_list_filters_priority_and_curator(
    client: TestClient,
    db_session: Session,
    scope_with_admin: Scope,
    viewer: UserNew,
    curator: UserNew,
) -> None:
    high = _assignment(db_session, scope_with_admin, priority="high")
    low = _assignment(
        db_session, scope_with_admin, priority="low", assigned_curator_id=curator.id
    )
    assert _ids(client, viewer, "priority_level=high") == {str(high.id)}
    assert _ids(client, viewer, "has_curator=true") == {str(low.id)}
    assert _ids(client, viewer, "has_curator=false") == {str(high.id)}


def test_update_assignment_requires_scope_admin_and_ignores_curator_id(
    client: TestClient,
    db_session: Session,
    scope_with_admin: Scope,
    viewer: UserNew,
    curator: UserNew,
    outsider: UserNew,
    owner: UserNew,
) -> None:
    row = _assignment(db_session, scope_with_admin)
    url = f"{GA}/{row.id}"
    for user in (viewer, curator):
        denied = client.put(
            url, json={"assignment_notes": "x"}, headers=auth_headers(user)
        )
        assert denied.status_code == 403

    response = client.put(
        url,
        json={"assignment_notes": "x", "assigned_curator_id": str(outsider.id)},
        headers=auth_headers(owner),
    )
    assert response.status_code == 200
    db_session.refresh(row)
    assert row.assignment_notes == "x"
    assert row.assigned_curator_id is None


def test_admin_password_reset_takes_json_body(
    client: TestClient, app_admin: UserNew, owner: UserNew
) -> None:
    url = f"/api/v1/users/{owner.id}/password"
    h = auth_headers(app_admin)
    assert client.put(f"{url}?new_password=longenough1", headers=h).status_code == 422
    assert client.put(url, json={"new_password": "short"}, headers=h).status_code == 422
    ok = client.put(url, json={"new_password": "longenough1"}, headers=h)
    assert ok.status_code == 200


def test_create_scope_rolls_back_when_owner_membership_fails(
    client: TestClient, db_session: Session, owner: UserNew
) -> None:
    name = f"ownerless-{uuid4().hex[:6]}"
    with (
        patch(
            "app.api.v1.endpoints.scopes.scope_membership_crud.create_owner_membership",
            side_effect=RuntimeError("boom"),
        ),
        pytest.raises(RuntimeError),
    ):
        client.post(
            "/api/v1/scopes/",
            json={
                "name": name,
                "display_name": "X",
                "description": "y",
                "default_workflow_pair_id": str(make_workflow_pair(db_session).id),
            },
            headers=auth_headers(owner),
        )
    assert db_session.query(Scope).filter(Scope.name == name).count() == 0
