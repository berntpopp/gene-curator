"""Personal access tokens: create/list/revoke own tokens and authenticate with them (#462)."""

import logging
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.deps import PAT_BLOCKED_OPERATIONS
from app.core.security import hash_personal_access_token
from app.models import PersonalAccessToken, UserNew

pytestmark = pytest.mark.unit

URL = "/api/v1/me/tokens/"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _future(days: int = 30) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def _create(client: TestClient, jwt: str, **body: object) -> dict:
    r = client.post(
        URL, json={"name": "cli", "expires_at": _future(), **body}, headers=_bearer(jwt)
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_plaintext_is_shown_once_stored_hashed_and_never_logged(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    created = _create(client, admin_token)
    token = created["token"]

    assert token.startswith("gc_pat_") and len(token) > 40
    assert created["token_prefix"] == token[:12]
    row = db_session.get(PersonalAccessToken, created["id"])
    assert row is not None and row.token_hash == hash_personal_access_token(token)
    listed = client.get(URL, headers=_bearer(admin_token))
    assert listed.status_code == 200
    assert token not in listed.text and row.token_hash not in listed.text
    assert [t["id"] for t in listed.json()] == [created["id"]]
    assert "Personal access token created" in caplog.text
    assert token not in caplog.text


def test_pat_authenticates_as_owner_and_stamps_last_used(
    client: TestClient, admin_token: str, test_user_admin: UserNew
) -> None:
    token = _create(client, admin_token)["token"]

    me = client.get("/api/v1/auth/me", headers=_bearer(token))

    assert me.status_code == 200, me.text
    assert me.json()["id"] == str(test_user_admin.id)
    assert client.get(URL, headers=_bearer(admin_token)).json()[0]["last_used_at"]


def test_pat_cannot_create_tokens(client: TestClient, admin_token: str) -> None:
    token = _create(client, admin_token)["token"]

    r = client.post(
        URL, json={"name": "x", "expires_at": _future()}, headers=_bearer(token)
    )

    assert r.status_code == 403


def test_read_only_pat_cannot_write(client: TestClient, admin_token: str) -> None:
    created = _create(client, admin_token, scopes=["read"])

    assert client.get(URL, headers=_bearer(created["token"])).status_code == 200
    r = client.delete(f"{URL}{created['id']}", headers=_bearer(created["token"]))
    assert r.status_code == 403


def test_revoked_and_expired_tokens_are_rejected(
    client: TestClient, admin_token: str, db_session: Session
) -> None:
    revoked = _create(client, admin_token)
    assert (
        client.delete(f"{URL}{revoked['id']}", headers=_bearer(admin_token)).status_code
        == 204
    )
    assert (
        client.get("/api/v1/auth/me", headers=_bearer(revoked["token"])).status_code
        == 401
    )
    # revoking again is a no-op
    assert (
        client.delete(f"{URL}{revoked['id']}", headers=_bearer(admin_token)).status_code
        == 204
    )

    expired = _create(client, admin_token)
    row = db_session.get(PersonalAccessToken, expired["id"])
    assert row is not None
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()
    assert (
        client.get("/api/v1/auth/me", headers=_bearer(expired["token"])).status_code
        == 401
    )
    assert (
        client.get("/api/v1/auth/me", headers=_bearer("gc_pat_unknown")).status_code
        == 401
    )


def test_users_cannot_see_or_revoke_each_others_tokens(
    client: TestClient, admin_token: str, curator_token: str
) -> None:
    mine = _create(client, admin_token)

    assert client.get(URL, headers=_bearer(curator_token)).json() == []
    r = client.delete(f"{URL}{mine['id']}", headers=_bearer(curator_token))
    assert r.status_code == 404
    assert (
        client.get("/api/v1/auth/me", headers=_bearer(mine["token"])).status_code == 200
    )


@pytest.mark.parametrize(
    "body",
    [
        {"name": "x"},
        {
            "name": "x",
            "expires_at": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        },
        {"name": "x", "expires_at": "2099-01-01T00:00:00"},
        {"name": "x", "expires_at": "2099-01-01T00:00:00Z", "scopes": ["admin"]},
        {"name": "x", "expires_at": "2099-01-01T00:00:00Z", "scopes": []},
        {"name": "", "expires_at": "2099-01-01T00:00:00Z"},
    ],
)
def test_create_validates_input(
    client: TestClient, admin_token: str, body: dict
) -> None:
    assert client.post(URL, json=body, headers=_bearer(admin_token)).status_code == 422


def _guarded_routes() -> set[tuple[str, str]]:
    # app.routes includes routers lazily, so read the routers that hold the guard
    from fastapi.routing import APIRoute

    from app.api.v1.endpoints import auth, personal_access_tokens, users
    from app.core.deps import reject_personal_access_token

    routers = {
        "/api/v1/auth": auth.router,
        "/api/v1/users": users.router,
        "/api/v1/me/tokens": personal_access_tokens.router,
    }
    return {
        (method, prefix + route.path)
        for prefix, router in routers.items()
        for route in router.routes
        if isinstance(route, APIRoute)
        and any(
            d.call is reject_personal_access_token for d in route.dependant.dependencies
        )
        for method in route.methods
    }


def test_blocked_operations_list_matches_the_guarded_routes() -> None:
    assert _guarded_routes() == set(PAT_BLOCKED_OPERATIONS)


@pytest.mark.parametrize(("method", "path"), PAT_BLOCKED_OPERATIONS)
def test_admin_pat_cannot_take_over_accounts(
    client: TestClient,
    admin_token: str,
    test_user_curator: UserNew,
    method: str,
    path: str,
) -> None:
    pat = _create(client, admin_token)["token"]
    url = path.replace("{user_id}", str(test_user_curator.id))

    r = client.request(method, url, json={}, headers=_bearer(pat))

    assert r.status_code == 403, r.text


def test_admin_pat_keeps_ordinary_admin_rights(
    client: TestClient, admin_token: str, test_user_curator: UserNew
) -> None:
    pat = _create(client, admin_token)["token"]
    url = f"/api/v1/users/{test_user_curator.id}"

    assert client.get("/api/v1/users/", headers=_bearer(pat)).status_code == 200
    r = client.put(
        f"{url}/password", json={"new_password": "x" * 12}, headers=_bearer(pat)
    )
    assert r.status_code == 403
    assert (
        client.put(url, json={"role": "admin"}, headers=_bearer(pat)).status_code == 403
    )
    assert client.get(url, headers=_bearer(pat)).json()["role"] == "user"
