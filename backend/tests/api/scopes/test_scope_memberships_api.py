"""API tests for scope membership management (invite, accept, list, update, remove)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import Scope, ScopeMembership, UserNew
from tests.api.scopes.factories import auth_headers, make_member, make_scope, make_user

pytestmark = pytest.mark.unit

BASE = "/api/v1/scopes"


def _invite(
    client: TestClient,
    scope: Scope,
    actor: UserNew,
    invitee: UserNew,
    role: str = "curator",
) -> dict[str, object]:
    response = client.post(
        f"{BASE}/{scope.id}/invitations",
        json={"user_id": str(invitee.id), "role": role},
        headers=auth_headers(actor),
    )
    assert response.status_code == 201, response.text
    return response.json()


# -----------------------------------------------------------------------------
# Invite
# -----------------------------------------------------------------------------


def test_invite_creates_pending_membership(
    client: TestClient,
    db_session: Session,
    owner: UserNew,
    scope_with_admin: Scope,
) -> None:
    invitee = make_user(db_session)

    body = _invite(client, scope_with_admin, owner, invitee, role="reviewer")

    assert body["is_pending"] is True
    assert body["accepted_at"] is None
    assert body["role"] == "reviewer"
    membership = (
        db_session.query(ScopeMembership).filter(ScopeMembership.id == body["id"]).one()
    )
    assert membership.accepted_at is None
    assert membership.expires_at is not None


def test_invite_existing_member_is_rejected(
    client: TestClient, owner: UserNew, scope_with_admin: Scope, curator: UserNew
) -> None:
    response = client.post(
        f"{BASE}/{scope_with_admin.id}/invitations",
        json={"user_id": str(curator.id), "role": "viewer"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 400
    assert "already a member" in response.json()["detail"]


def test_invite_unknown_user_is_rejected(
    client: TestClient, owner: UserNew, scope_with_admin: Scope
) -> None:
    response = client.post(
        f"{BASE}/{scope_with_admin.id}/invitations",
        json={"user_id": str(uuid4()), "role": "viewer"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "User not found"


def test_invite_requires_user_id_or_email(
    client: TestClient, owner: UserNew, scope_with_admin: Scope
) -> None:
    response = client.post(
        f"{BASE}/{scope_with_admin.id}/invitations",
        json={"role": "viewer"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 422


def test_invite_forbidden_for_curator(
    client: TestClient, db_session: Session, curator: UserNew, scope_with_admin: Scope
) -> None:
    response = client.post(
        f"{BASE}/{scope_with_admin.id}/invitations",
        json={"user_id": str(make_user(db_session).id), "role": "viewer"},
        headers=auth_headers(curator),
    )

    assert response.status_code == 403


def test_invite_rejects_unknown_role(
    client: TestClient, db_session: Session, owner: UserNew, scope_with_admin: Scope
) -> None:
    response = client.post(
        f"{BASE}/{scope_with_admin.id}/invitations",
        json={"user_id": str(make_user(db_session).id), "role": "superuser"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 422


# -----------------------------------------------------------------------------
# Accept
# -----------------------------------------------------------------------------


def test_invitee_accepts_pending_invitation(
    client: TestClient,
    db_session: Session,
    owner: UserNew,
    scope_with_admin: Scope,
) -> None:
    invitee = make_user(db_session)
    invitation = _invite(client, scope_with_admin, owner, invitee)

    response = client.post(
        f"{BASE}/{scope_with_admin.id}/invitations/{invitation['id']}/accept",
        json={},
        headers=auth_headers(invitee),
    )

    assert response.status_code == 200
    assert response.json()["is_pending"] is False
    db_session.expire_all()
    membership = db_session.get(ScopeMembership, invitation["id"])
    assert membership is not None
    assert membership.accepted_at is not None


def test_accept_by_other_user_is_rejected(
    client: TestClient,
    db_session: Session,
    owner: UserNew,
    scope_with_admin: Scope,
) -> None:
    invitee = make_user(db_session)
    intruder = make_user(db_session)
    invitation = _invite(client, scope_with_admin, owner, invitee)

    response = client.post(
        f"{BASE}/{scope_with_admin.id}/invitations/{invitation['id']}/accept",
        json={},
        headers=auth_headers(intruder),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invitation is not for this user"


def test_accept_twice_is_rejected(
    client: TestClient,
    db_session: Session,
    owner: UserNew,
    scope_with_admin: Scope,
) -> None:
    invitee = make_user(db_session)
    invitation = _invite(client, scope_with_admin, owner, invitee)
    url = f"{BASE}/{scope_with_admin.id}/invitations/{invitation['id']}/accept"
    client.post(url, json={}, headers=auth_headers(invitee))

    response = client.post(url, json={}, headers=auth_headers(invitee))

    assert response.status_code == 400
    assert response.json()["detail"] == "Invitation already accepted"


def test_accept_unknown_invitation_returns_404(
    client: TestClient, db_session: Session, owner: UserNew, scope_with_admin: Scope
) -> None:
    response = client.post(
        f"{BASE}/{scope_with_admin.id}/invitations/{uuid4()}/accept",
        json={},
        headers=auth_headers(make_user(db_session)),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Invitation not found"


def test_accept_under_another_scope_is_404_and_accepts_nothing(
    client: TestClient, db_session: Session, owner: UserNew, scope_with_admin: Scope
) -> None:
    invitee = make_user(db_session)
    invitation = _invite(client, scope_with_admin, owner, invitee)
    other = make_scope(db_session, created_by=owner.id)

    response = client.post(
        f"{BASE}/{other.id}/invitations/{invitation['id']}/accept",
        json={},
        headers=auth_headers(invitee),
    )

    assert response.status_code == 404
    db_session.expire_all()
    membership = db_session.get(ScopeMembership, invitation["id"])
    assert membership is not None and membership.accepted_at is None


def test_expired_invitation_cannot_be_accepted(
    client: TestClient,
    db_session: Session,
    owner: UserNew,
    scope_with_admin: Scope,
) -> None:
    """Invitations expire after 7 days and must not be accepted afterwards."""
    invitee = make_user(db_session)
    expired = make_member(
        db_session,
        scope_with_admin,
        invitee,
        "viewer",
        accepted=False,
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )

    response = client.post(
        f"{BASE}/{scope_with_admin.id}/invitations/{expired.id}/accept",
        json={},
        headers=auth_headers(invitee),
    )

    assert response.status_code == 400
    db_session.expire_all()
    assert db_session.get(ScopeMembership, expired.id).accepted_at is None


# -----------------------------------------------------------------------------
# List members
# -----------------------------------------------------------------------------


def test_list_members_hides_pending_by_default(
    client: TestClient,
    db_session: Session,
    owner: UserNew,
    scope_with_admin: Scope,
) -> None:
    _invite(client, scope_with_admin, owner, make_user(db_session))

    active = client.get(
        f"{BASE}/{scope_with_admin.id}/members", headers=auth_headers(owner)
    ).json()
    everyone = client.get(
        f"{BASE}/{scope_with_admin.id}/members",
        params={"include_pending": True},
        headers=auth_headers(owner),
    ).json()

    assert active["total"] == 1
    assert active["pending_count"] == 0
    assert everyone["total"] == 2
    assert everyone["pending_count"] == 1
    assert active["role_counts"]["admin"] == 1


def test_list_members_visible_to_viewer(
    client: TestClient, viewer: UserNew, scope_with_admin: Scope
) -> None:
    response = client.get(
        f"{BASE}/{scope_with_admin.id}/members", headers=auth_headers(viewer)
    )

    assert response.status_code == 200


def test_list_members_forbidden_for_non_member(
    client: TestClient, outsider: UserNew, scope_with_admin: Scope
) -> None:
    response = client.get(
        f"{BASE}/{scope_with_admin.id}/members", headers=auth_headers(outsider)
    )

    assert response.status_code == 403


# -----------------------------------------------------------------------------
# Update member
# -----------------------------------------------------------------------------


def test_update_member_role_and_notes(
    client: TestClient, owner: UserNew, scope_with_admin: Scope, curator: UserNew
) -> None:
    response = client.patch(
        f"{BASE}/{scope_with_admin.id}/members/{curator.id}",
        json={"role": "reviewer", "notes": "promoted"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert response.json()["role"] == "reviewer"
    assert response.json()["notes"] == "promoted"


def test_update_unknown_member_returns_404(
    client: TestClient, owner: UserNew, scope_with_admin: Scope
) -> None:
    response = client.patch(
        f"{BASE}/{scope_with_admin.id}/members/{uuid4()}",
        json={"role": "viewer"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 404


def test_update_member_forbidden_for_curator(
    client: TestClient, curator: UserNew, viewer: UserNew, scope_with_admin: Scope
) -> None:
    response = client.patch(
        f"{BASE}/{scope_with_admin.id}/members/{viewer.id}",
        json={"role": "admin"},
        headers=auth_headers(curator),
    )

    assert response.status_code == 403


def test_deactivating_last_admin_is_rejected(
    client: TestClient, db_session: Session, owner: UserNew, scope_with_admin: Scope
) -> None:
    """The last active admin must not be deactivated (docstring: 400)."""
    response = client.patch(
        f"{BASE}/{scope_with_admin.id}/members/{owner.id}",
        json={"is_active": False},
        headers=auth_headers(owner),
    )

    assert response.status_code == 400
    db_session.expire_all()
    membership = (
        db_session.query(ScopeMembership)
        .filter_by(scope_id=scope_with_admin.id, user_id=owner.id)
        .one()
    )
    assert membership.is_active is True


def test_demoting_last_admin_is_rejected(
    client: TestClient, db_session: Session, owner: UserNew, scope_with_admin: Scope
) -> None:
    response = client.patch(
        f"{BASE}/{scope_with_admin.id}/members/{owner.id}",
        json={"role": "viewer"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 400
    db_session.expire_all()
    membership = (
        db_session.query(ScopeMembership)
        .filter_by(scope_id=scope_with_admin.id, user_id=owner.id)
        .one()
    )
    assert membership.role == "admin"


def test_demoting_admin_allowed_when_another_admin_exists(
    client: TestClient, db_session: Session, owner: UserNew, scope_with_admin: Scope
) -> None:
    second = make_user(db_session)
    make_member(db_session, scope_with_admin, second, "admin")

    response = client.patch(
        f"{BASE}/{scope_with_admin.id}/members/{owner.id}",
        json={"role": "viewer"},
        headers=auth_headers(second),
    )

    assert response.status_code == 200
    assert response.json()["role"] == "viewer"


# -----------------------------------------------------------------------------
# Remove member
# -----------------------------------------------------------------------------


def test_remove_member_soft_deletes(
    client: TestClient,
    db_session: Session,
    owner: UserNew,
    scope_with_admin: Scope,
    curator: UserNew,
) -> None:
    response = client.delete(
        f"{BASE}/{scope_with_admin.id}/members/{curator.id}",
        headers=auth_headers(owner),
    )

    assert response.status_code == 204
    db_session.expire_all()
    membership = (
        db_session.query(ScopeMembership)
        .filter_by(scope_id=scope_with_admin.id, user_id=curator.id)
        .one()
    )
    assert membership.is_active is False


def test_removed_member_is_not_listed(
    client: TestClient,
    owner: UserNew,
    scope_with_admin: Scope,
    curator: UserNew,
) -> None:
    """A removed (inactive) membership grants nothing, so the list must not show it."""
    url = f"{BASE}/{scope_with_admin.id}/members"
    assert (
        client.delete(f"{url}/{curator.id}", headers=auth_headers(owner)).status_code
        == 204
    )
    for params in ({}, {"include_pending": True}):
        listed = client.get(url, params=params, headers=auth_headers(owner)).json()
        assert curator.id not in {UUID(m["user_id"]) for m in listed["members"]}


def test_remove_last_admin_is_rejected(
    client: TestClient, owner: UserNew, scope_with_admin: Scope
) -> None:
    response = client.delete(
        f"{BASE}/{scope_with_admin.id}/members/{owner.id}",
        headers=auth_headers(owner),
    )

    assert response.status_code == 400
    assert "last admin" in response.json()["detail"]


def test_remove_unknown_member_returns_404(
    client: TestClient, owner: UserNew, scope_with_admin: Scope
) -> None:
    response = client.delete(
        f"{BASE}/{scope_with_admin.id}/members/{uuid4()}",
        headers=auth_headers(owner),
    )

    assert response.status_code == 404


def test_remove_member_forbidden_for_reviewer(
    client: TestClient, reviewer: UserNew, curator: UserNew, scope_with_admin: Scope
) -> None:
    response = client.delete(
        f"{BASE}/{scope_with_admin.id}/members/{curator.id}",
        headers=auth_headers(reviewer),
    )

    assert response.status_code == 403


# -----------------------------------------------------------------------------
# User search for invitations
# -----------------------------------------------------------------------------


def test_user_search_excludes_existing_members(
    client: TestClient,
    db_session: Session,
    owner: UserNew,
    scope_with_admin: Scope,
) -> None:
    tag = uuid4().hex[:6]
    member = make_user(db_session, name=f"Member {tag}")
    make_member(db_session, scope_with_admin, member, "viewer")
    outsider_match = make_user(db_session, name=f"Candidate {tag}")
    make_user(db_session, name=f"Inactive {tag}", is_active=False)

    response = client.get(
        f"{BASE}/{scope_with_admin.id}/users/search",
        params={"q": tag},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    names = [u["name"] for u in response.json()]
    assert f"Candidate {tag}" in names
    assert f"Member {tag}" not in names
    assert f"Inactive {tag}" not in names
    assert str(outsider_match.id) in [u["id"] for u in response.json()]


def test_user_search_forbidden_for_curator(
    client: TestClient, curator: UserNew, scope_with_admin: Scope
) -> None:
    response = client.get(
        f"{BASE}/{scope_with_admin.id}/users/search",
        params={"q": "a"},
        headers=auth_headers(curator),
    )

    assert response.status_code == 403
