"""API tests for the invitee-facing endpoints (/me/invitations and decline)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import Scope, ScopeMembership, UserNew
from tests.api.scopes.factories import auth_headers, make_member, make_user

pytestmark = pytest.mark.unit


def _pending(
    db: Session,
    scope: Scope,
    invitee: UserNew,
    *,
    expires_in_days: float = 7,
) -> ScopeMembership:
    return make_member(
        db,
        scope,
        invitee,
        "reviewer",
        accepted=False,
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
    )


def test_pending_invitations_list_includes_scope_and_inviter(
    client: TestClient,
    db_session: Session,
    owner: UserNew,
    scope_with_admin: Scope,
) -> None:
    invitee = make_user(db_session)
    invitation = _pending(db_session, scope_with_admin, invitee)
    invitation.invited_by = owner.id
    db_session.commit()

    response = client.get("/api/v1/me/invitations", headers=auth_headers(invitee))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["invitations"][0]
    assert item["id"] == str(invitation.id)
    assert item["scope_name"] == scope_with_admin.name
    assert item["role"] == "reviewer"
    assert item["inviter_email"] == owner.email
    assert item["is_expired"] is False


def test_expired_invitations_hidden_unless_requested(
    client: TestClient,
    db_session: Session,
    scope_with_admin: Scope,
) -> None:
    invitee = make_user(db_session)
    _pending(db_session, scope_with_admin, invitee, expires_in_days=-1)

    hidden = client.get("/api/v1/me/invitations", headers=auth_headers(invitee))

    assert hidden.status_code == 200
    assert hidden.json()["total"] == 0


def test_accepted_memberships_are_not_listed_as_invitations(
    client: TestClient,
    db_session: Session,
    scope_with_admin: Scope,
    viewer: UserNew,
) -> None:
    response = client.get("/api/v1/me/invitations", headers=auth_headers(viewer))

    assert response.json()["total"] == 0


def test_decline_soft_deletes_invitation(
    client: TestClient,
    db_session: Session,
    scope_with_admin: Scope,
) -> None:
    invitee = make_user(db_session)
    invitation = _pending(db_session, scope_with_admin, invitee)

    response = client.post(
        f"/api/v1/invitations/{invitation.id}/decline",
        headers=auth_headers(invitee),
    )

    assert response.status_code == 204
    db_session.expire_all()
    assert db_session.get(ScopeMembership, invitation.id).is_active is False
    listed = client.get("/api/v1/me/invitations", headers=auth_headers(invitee))
    assert listed.json()["total"] == 0


def test_decline_by_other_user_is_forbidden(
    client: TestClient,
    db_session: Session,
    scope_with_admin: Scope,
) -> None:
    invitation = _pending(db_session, scope_with_admin, make_user(db_session))

    response = client.post(
        f"/api/v1/invitations/{invitation.id}/decline",
        headers=auth_headers(make_user(db_session)),
    )

    assert response.status_code == 403


def test_decline_unknown_invitation_returns_404(
    client: TestClient, db_session: Session
) -> None:
    response = client.post(
        f"/api/v1/invitations/{uuid4()}/decline",
        headers=auth_headers(make_user(db_session)),
    )

    assert response.status_code == 404


def test_decline_accepted_membership_is_rejected(
    client: TestClient,
    db_session: Session,
    scope_with_admin: Scope,
    viewer: UserNew,
) -> None:
    membership = db_session.query(ScopeMembership).filter_by(user_id=viewer.id).one()

    response = client.post(
        f"/api/v1/invitations/{membership.id}/decline",
        headers=auth_headers(viewer),
    )

    assert response.status_code == 400
    assert "already accepted" in response.json()["detail"]


def test_decline_twice_is_rejected(
    client: TestClient,
    db_session: Session,
    scope_with_admin: Scope,
) -> None:
    invitee = make_user(db_session)
    invitation = _pending(db_session, scope_with_admin, invitee)
    url = f"/api/v1/invitations/{invitation.id}/decline"
    client.post(url, headers=auth_headers(invitee))

    response = client.post(url, headers=auth_headers(invitee))

    assert response.status_code == 400
    assert "already been declined" in response.json()["detail"]


def test_invitations_require_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/me/invitations")

    assert response.status_code in (401, 403)
