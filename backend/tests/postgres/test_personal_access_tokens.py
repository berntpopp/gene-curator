"""Personal access tokens through the real API as app_user under RLS (056, #462)."""

import os
from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient

from app.core import database
from app.core.security import create_access_token, get_password_hash
from app.main import app

pytestmark = pytest.mark.postgres

URL = "/api/v1/me/tokens/"


@dataclass
class W:
    alice: UUID = field(default_factory=uuid4)
    bob: UUID = field(default_factory=uuid4)
    scope: UUID = field(default_factory=uuid4)  # private, alice only


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.scope)[:8]
    with _owner() as conn, conn.cursor() as cur:
        for uid, name in ((x.alice, "alice"), (x.bob, "bob")):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, 'user')",
                (str(uid), f"{name}-{tag}@pat.org", get_password_hash("pw"), name),
            )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, 'PAT', false, %s)",
            (str(x.scope), f"pat-{x.scope}", str(x.alice)),
        )
        cur.execute(
            "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
            "accepted_at) VALUES (%s, %s, 'curator', %s, now())",
            (str(x.scope), str(x.alice), str(x.alice)),
        )
    yield x
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(x.scope),))
        cur.execute(
            "DELETE FROM audit_log WHERE user_id IN (%s, %s) OR scope_id = %s",
            (str(x.alice), str(x.bob), str(x.scope)),
        )
        cur.execute(
            "DELETE FROM users WHERE id IN (%s, %s)", (str(x.alice), str(x.bob))
        )


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _jwt(uid: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(uid)})}"}


def test_pat_acts_as_owner_under_rls_and_only_the_owner_can_revoke(
    client: TestClient, w: W
) -> None:
    expires = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    r = client.post(
        URL, json={"name": "mcp", "expires_at": expires}, headers=_jwt(w.alice)
    )
    assert r.status_code == 201, r.text
    token_id, pat = r.json()["id"], {"Authorization": f"Bearer {r.json()['token']}"}

    # The PAT reaches the API as alice: her private scope and her own tokens are visible.
    assert client.get("/api/v1/auth/me", headers=pat).json()["id"] == str(w.alice)
    assert client.get(f"/api/v1/scopes/{w.scope}", headers=pat).status_code == 200
    assert [t["id"] for t in client.get(URL, headers=pat).json()] == [token_id]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT token_hash, last_used_at FROM personal_access_tokens WHERE id = %s",
            (token_id,),
        )
        token_hash, last_used = cur.fetchone()
    assert last_used is not None and r.json()["token"] not in token_hash

    # last_used_at is stamped at most once a minute
    def _last_used() -> datetime:
        with _owner() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT last_used_at FROM personal_access_tokens WHERE id = %s",
                (token_id,),
            )
            return cur.fetchone()[0]

    client.get("/api/v1/auth/me", headers=pat)
    assert _last_used() == last_used
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE personal_access_tokens SET last_used_at = now() - interval '2 minutes' "
            "WHERE id = %s",
            (token_id,),
        )
    client.get("/api/v1/auth/me", headers=pat)
    assert _last_used() >= last_used

    # Bob sees neither the scope nor the token and cannot revoke it.
    assert client.get(f"/api/v1/scopes/{w.scope}", headers=_jwt(w.bob)).status_code in (
        403,
        404,
    )
    assert client.get(URL, headers=_jwt(w.bob)).json() == []
    assert client.delete(f"{URL}{token_id}", headers=_jwt(w.bob)).status_code == 404
    assert client.get("/api/v1/auth/me", headers=pat).status_code == 200

    # A PAT cannot mint PATs; once revoked it is refused.
    assert (
        client.post(
            URL, json={"name": "x", "expires_at": expires}, headers=pat
        ).status_code
        == 403
    )
    assert client.delete(f"{URL}{token_id}", headers=_jwt(w.alice)).status_code == 204
    assert client.get("/api/v1/auth/me", headers=pat).status_code == 401


def test_app_user_can_only_update_revoked_at() -> None:
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT has_column_privilege('personal_access_tokens', c, 'UPDATE') "
            "FROM unnest(ARRAY['revoked_at', 'expires_at', 'scopes', 'user_id', "
            "'last_used_at']) c"
        )
        assert [r[0] for r in cur.fetchall()] == [True, False, False, False, False]
        cur.execute("SELECT has_table_privilege('personal_access_tokens', 'DELETE')")
        assert cur.fetchone()[0] is False
