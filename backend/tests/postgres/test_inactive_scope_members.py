"""A1 as app_user: in an inactive scope a member's write gets the 409 read-only reason,
a non-member still the 403 (require() used to count active scopes only)."""

import os
from collections.abc import Generator
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient

from app.core import database
from app.core.security import create_access_token, get_password_hash
from app.main import app

pytestmark = pytest.mark.postgres


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def ids() -> Generator[tuple[UUID, UUID, UUID], None, None]:
    scope, cur, stranger = uuid4(), uuid4(), uuid4()
    users = [str(cur), str(stranger)]
    with _owner() as conn, conn.cursor() as c:
        for uid in users:
            c.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, 'u', 'user')",
                (uid, f"{uid}@inact.org", get_password_hash("pw")),
            )
        c.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, is_active, "
            "created_by) VALUES (%s, %s, 'IN', false, false, %s)",
            (str(scope), f"inact-{scope}", str(cur)),
        )
        c.execute(
            "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
            "accepted_at) VALUES (%s, %s, 'curator', %s, now())",
            (str(scope), str(cur), str(cur)),
        )
    yield scope, cur, stranger
    with _owner() as conn, conn.cursor() as c:
        c.execute("DELETE FROM scopes WHERE id = %s", (str(scope),))
        c.execute("DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[])", (users,))
        c.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (users,))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _h(uid: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(uid)})}"}


def test_member_gets_read_only_reason_stranger_403(
    client: TestClient, ids: tuple[UUID, UUID, UUID]
) -> None:
    scope, cur, stranger = ids
    calls = (
        ("/api/v1/scopes/genes", {"scope_id": str(scope), "symbols": ["TULP3"]}),
        ("/api/v1/precurations/", {"gene_id": str(uuid4()), "scope_id": str(scope)}),
    )
    for url, body in calls:
        r = client.post(url, json=body, headers=_h(cur))
        assert r.status_code == 409, r.text
        assert "inactive" in r.json()["detail"]
        assert client.post(url, json=body, headers=_h(stranger)).status_code == 403
