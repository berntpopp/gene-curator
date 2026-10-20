"""API tests for /api/v1/users (admin management) and /api/v1/auth (login, tokens, self-service)."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import UserNew
from tests.api.scopes.factories import PASSWORD, auth_headers, make_user

pytestmark = pytest.mark.unit

USERS = "/api/v1/users"
AUTH = "/api/v1/auth"


def _login(client: TestClient, email: str, password: str = PASSWORD) -> object:
    return client.post(f"{AUTH}/login", json={"email": email, "password": password})


# -----------------------------------------------------------------------------
# Users: admin-only collection endpoints
# -----------------------------------------------------------------------------


def test_list_users_admin_only(
    client: TestClient, db_session: Session, app_admin: UserNew, owner: UserNew
) -> None:
    allowed = client.get(f"{USERS}/", headers=auth_headers(app_admin))
    denied = client.get(f"{USERS}/", headers=auth_headers(owner))

    assert allowed.status_code == 200
    assert str(owner.id) in [u["id"] for u in allowed.json()]
    assert denied.status_code == 403


def test_search_users_by_name_admin_only(
    client: TestClient, db_session: Session, app_admin: UserNew, owner: UserNew
) -> None:
    tag = uuid4().hex[:8]
    match = make_user(db_session, name=f"Searchable {tag}")

    response = client.get(
        f"{USERS}/search", params={"q": tag}, headers=auth_headers(app_admin)
    )
    denied = client.get(
        f"{USERS}/search", params={"q": tag}, headers=auth_headers(owner)
    )

    assert response.status_code == 200
    assert [u["id"] for u in response.json()] == [str(match.id)]
    assert denied.status_code == 403


def test_user_statistics_admin_only(
    client: TestClient, app_admin: UserNew, owner: UserNew
) -> None:
    response = client.get(f"{USERS}/statistics", headers=auth_headers(app_admin))
    denied = client.get(f"{USERS}/statistics", headers=auth_headers(owner))

    assert response.status_code == 200
    body = response.json()
    assert body["total_users"] >= 2
    assert "role_distribution" in body
    assert denied.status_code == 403


# -----------------------------------------------------------------------------
# Users: single-user access
# -----------------------------------------------------------------------------


def test_user_can_read_own_profile(client: TestClient, owner: UserNew) -> None:
    response = client.get(f"{USERS}/{owner.id}", headers=auth_headers(owner))

    assert response.status_code == 200
    assert response.json()["email"] == owner.email


def test_user_cannot_read_other_profile(
    client: TestClient, owner: UserNew, outsider: UserNew
) -> None:
    response = client.get(f"{USERS}/{outsider.id}", headers=auth_headers(owner))

    assert response.status_code == 403


def test_admin_reads_any_profile(
    client: TestClient, app_admin: UserNew, outsider: UserNew
) -> None:
    response = client.get(f"{USERS}/{outsider.id}", headers=auth_headers(app_admin))

    assert response.status_code == 200


def test_unknown_user_returns_404_for_admin(
    client: TestClient, app_admin: UserNew
) -> None:
    response = client.get(f"{USERS}/{uuid4()}", headers=auth_headers(app_admin))

    assert response.status_code == 404


def test_user_activity_self_and_admin(
    client: TestClient, app_admin: UserNew, owner: UserNew, outsider: UserNew
) -> None:
    own = client.get(f"{USERS}/{owner.id}/activity", headers=auth_headers(owner))
    admin_view = client.get(
        f"{USERS}/{owner.id}/activity", headers=auth_headers(app_admin)
    )
    other = client.get(f"{USERS}/{outsider.id}/activity", headers=auth_headers(owner))

    assert own.status_code == 200
    assert own.json()["scope_count"] == 0
    assert admin_view.status_code == 200
    assert other.status_code == 403


# -----------------------------------------------------------------------------
# Users: admin create / update / lifecycle
# -----------------------------------------------------------------------------


def _new_user_payload(email: str | None = None) -> dict[str, object]:
    return {
        "email": email or f"new-{uuid4().hex[:8]}@test.com",
        "name": "Created By Admin",
        "password": "longenough1",
        "role": "user",
    }


def test_admin_creates_user(client: TestClient, app_admin: UserNew) -> None:
    payload = _new_user_payload()

    response = client.post(f"{USERS}/", json=payload, headers=auth_headers(app_admin))

    assert response.status_code == 201
    assert response.json()["email"] == payload["email"]
    assert "hashed_password" not in response.json()


def test_admin_create_duplicate_email_rejected(
    client: TestClient, app_admin: UserNew, owner: UserNew
) -> None:
    response = client.post(
        f"{USERS}/",
        json=_new_user_payload(email=owner.email),
        headers=auth_headers(app_admin),
    )

    assert response.status_code == 400


def test_non_admin_cannot_create_user(client: TestClient, owner: UserNew) -> None:
    response = client.post(
        f"{USERS}/", json=_new_user_payload(), headers=auth_headers(owner)
    )

    assert response.status_code == 403


def test_admin_updates_user_name(
    client: TestClient, app_admin: UserNew, outsider: UserNew
) -> None:
    response = client.put(
        f"{USERS}/{outsider.id}",
        json={"name": "Renamed"},
        headers=auth_headers(app_admin),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_admin_update_to_taken_email_rejected(
    client: TestClient, app_admin: UserNew, owner: UserNew, outsider: UserNew
) -> None:
    response = client.put(
        f"{USERS}/{outsider.id}",
        json={"email": owner.email},
        headers=auth_headers(app_admin),
    )

    assert response.status_code == 400


def test_admin_update_unknown_user_returns_404(
    client: TestClient, app_admin: UserNew
) -> None:
    response = client.put(
        f"{USERS}/{uuid4()}", json={"name": "x"}, headers=auth_headers(app_admin)
    )

    assert response.status_code == 404


def test_admin_resets_password_then_user_can_login(
    client: TestClient, app_admin: UserNew, outsider: UserNew
) -> None:
    response = client.put(
        f"{USERS}/{outsider.id}/password",
        params={"new_password": "brand-new-pass"},
        headers=auth_headers(app_admin),
    )

    assert response.status_code == 200
    assert _login(client, outsider.email, "brand-new-pass").status_code == 200
    assert _login(client, outsider.email, PASSWORD).status_code == 401


def test_admin_deactivates_and_reactivates_user(
    client: TestClient, db_session: Session, app_admin: UserNew, outsider: UserNew
) -> None:
    off = client.put(
        f"{USERS}/{outsider.id}/deactivate", headers=auth_headers(app_admin)
    )
    db_session.expire_all()
    deactivated = db_session.get(UserNew, outsider.id).is_active

    on = client.put(f"{USERS}/{outsider.id}/activate", headers=auth_headers(app_admin))
    db_session.expire_all()
    reactivated = db_session.get(UserNew, outsider.id).is_active

    assert off.status_code == 200
    assert deactivated is False
    assert on.status_code == 200
    assert reactivated is True


def test_admin_cannot_deactivate_self(client: TestClient, app_admin: UserNew) -> None:
    response = client.put(
        f"{USERS}/{app_admin.id}/deactivate", headers=auth_headers(app_admin)
    )

    assert response.status_code == 400


def test_lifecycle_endpoints_unknown_user_return_404(
    client: TestClient, app_admin: UserNew
) -> None:
    for action in ("activate", "deactivate"):
        response = client.put(
            f"{USERS}/{uuid4()}/{action}", headers=auth_headers(app_admin)
        )
        assert response.status_code == 404


def test_admin_deletes_user(
    client: TestClient, db_session: Session, app_admin: UserNew
) -> None:
    doomed = make_user(db_session)

    response = client.delete(f"{USERS}/{doomed.id}", headers=auth_headers(app_admin))

    assert response.status_code == 200
    db_session.expire_all()
    assert db_session.get(UserNew, doomed.id) is None


def test_admin_cannot_delete_self(client: TestClient, app_admin: UserNew) -> None:
    response = client.delete(f"{USERS}/{app_admin.id}", headers=auth_headers(app_admin))

    assert response.status_code == 400


def test_delete_unknown_user_returns_404(
    client: TestClient, app_admin: UserNew
) -> None:
    response = client.delete(f"{USERS}/{uuid4()}", headers=auth_headers(app_admin))

    assert response.status_code == 404


# -----------------------------------------------------------------------------
# Auth: login and tokens
# -----------------------------------------------------------------------------


def test_login_returns_access_and_refresh_tokens(
    client: TestClient, owner: UserNew
) -> None:
    response = _login(client, owner.email)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"  # noqa: S105
    assert body["access_token"] and body["refresh_token"]
    assert body["expires_in"] > 0


def test_login_rejects_wrong_password(client: TestClient, owner: UserNew) -> None:
    response = _login(client, owner.email, "wrong-password")

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_rejects_inactive_user(client: TestClient, db_session: Session) -> None:
    inactive = make_user(db_session, is_active=False)

    response = _login(client, inactive.email)

    assert response.status_code == 401
    assert response.json()["detail"] == "Inactive user"


def test_refresh_issues_new_tokens(client: TestClient, owner: UserNew) -> None:
    refresh = _login(client, owner.email).json()["refresh_token"]

    response = client.post(f"{AUTH}/refresh", json={"refresh_token": refresh})

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_refresh_rejects_access_token(client: TestClient, owner: UserNew) -> None:
    access = _login(client, owner.email).json()["access_token"]

    response = client.post(f"{AUTH}/refresh", json={"refresh_token": access})

    assert response.status_code == 401


def test_refresh_rejects_garbage(client: TestClient) -> None:
    response = client.post(f"{AUTH}/refresh", json={"refresh_token": "not-a-jwt"})

    assert response.status_code == 401


def test_me_returns_current_user(client: TestClient, owner: UserNew) -> None:
    response = client.get(f"{AUTH}/me", headers=auth_headers(owner))

    assert response.status_code == 200
    assert response.json()["id"] == str(owner.id)


def test_me_requires_token(client: TestClient) -> None:
    response = client.get(f"{AUTH}/me")

    assert response.status_code in (401, 403)


def test_logout_requires_token_and_succeeds_for_user(
    client: TestClient, owner: UserNew
) -> None:
    ok = client.post(f"{AUTH}/logout", headers=auth_headers(owner))
    anonymous = client.post(f"{AUTH}/logout")

    assert ok.status_code == 200
    assert anonymous.status_code in (401, 403)


def test_auth_info_endpoint(client: TestClient) -> None:
    response = client.get(f"{AUTH}/")

    assert response.status_code == 200
    assert response.json()["status"] == "active"


# -----------------------------------------------------------------------------
# Auth: self-service password change
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/me/password", "/change-password"])
def test_change_password_success_and_login_with_new(
    client: TestClient, owner: UserNew, path: str
) -> None:
    response = client.request(
        "PUT" if path == "/me/password" else "POST",
        f"{AUTH}{path}",
        json={"current_password": PASSWORD, "new_password": "another-pass-1"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert _login(client, owner.email, "another-pass-1").status_code == 200


@pytest.mark.parametrize("path", ["/me/password", "/change-password"])
def test_change_password_rejects_wrong_current(
    client: TestClient, owner: UserNew, path: str
) -> None:
    response = client.request(
        "PUT" if path == "/me/password" else "POST",
        f"{AUTH}{path}",
        json={"current_password": "nope-nope", "new_password": "another-pass-1"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 400
    assert _login(client, owner.email).status_code == 200


def test_change_password_rejects_short_new_password(
    client: TestClient, owner: UserNew
) -> None:
    response = client.put(
        f"{AUTH}/me/password",
        json={"current_password": PASSWORD, "new_password": "short"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 422


# -----------------------------------------------------------------------------
# Auth: public registration
# -----------------------------------------------------------------------------


def test_register_creates_ordinary_active_user(client: TestClient) -> None:
    email = f"reg-{uuid4().hex[:8]}@test.com"

    response = client.post(
        f"{AUTH}/register",
        json={"email": email, "name": "Registrant", "password": "longenough1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == email
    assert body["role"] == "user"
    assert body["is_active"] is True


def test_register_cannot_grant_application_admin(
    client: TestClient, db_session: Session
) -> None:
    """Regression: public registration must not let the client pick its role.

    Otherwise anyone can self-register as a platform administrator.
    """
    email = f"escalate-{uuid4().hex[:8]}@test.com"

    response = client.post(
        f"{AUTH}/register",
        json={
            "email": email,
            "name": "Escalator",
            "password": "longenough1",
            "role": "admin",
        },
    )

    assert response.status_code == 200
    assert response.json()["role"] == "user"
    created = db_session.query(UserNew).filter_by(email=email).one()
    assert created.role.value == "user"


def test_register_rejects_duplicate_email(client: TestClient, owner: UserNew) -> None:
    duplicate = client.post(
        f"{AUTH}/register",
        json={"email": owner.email, "name": "Dup", "password": "longenough1"},
    )

    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Email already registered"
