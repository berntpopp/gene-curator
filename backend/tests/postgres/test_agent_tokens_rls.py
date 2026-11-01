"""#639 through RLS as app_user: a platform admin issues an agent account's token (094);
it signs the agent in. A person's tokens stay the person's own."""

import os
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
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
def users() -> Generator[dict[str, UUID], None, None]:
    ids = {"admin": uuid4(), "agent": uuid4(), "person": uuid4()}
    with _owner() as conn, conn.cursor() as cur:
        for name, uid in ids.items():
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role, is_agent) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    str(uid),
                    f"{str(uid)[:8]}@agents.org",
                    get_password_hash("pw"),
                    name,
                    "admin" if name == "admin" else "user",
                    name == "agent",
                ),
            )
    yield ids
    with _owner() as conn, conn.cursor() as cur:
        every = [str(u) for u in ids.values()]
        cur.execute(
            "DELETE FROM personal_access_tokens WHERE user_id = ANY(%s::uuid[])",
            (every,),
        )
        cur.execute("DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[])", (every,))
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (every,))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def test_a_platform_admin_issues_an_agent_token(
    client: TestClient, users: dict[str, UUID]
) -> None:
    admin = {
        "Authorization": f"Bearer {create_access_token(data={'sub': str(users['admin'])})}"
    }
    body = {
        "name": "judge",
        "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
    }
    r = client.post(f"/api/v1/users/{users['agent']}/tokens", json=body, headers=admin)
    assert r.status_code == 201, r.text
    me = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {r.json()['token']}"}
    )
    assert me.status_code == 200 and me.json()["id"] == str(users["agent"]), me.text
    person = client.post(
        f"/api/v1/users/{users['person']}/tokens", json=body, headers=admin
    )
    assert person.status_code == 404, person.text
