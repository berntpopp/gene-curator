"""Saved catalogue view through the real API as app_user under RLS (084, #276)."""

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

URL = "/api/v1/me/views/catalogue"


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def users() -> Generator[tuple[UUID, UUID], None, None]:
    alice, bob = uuid4(), uuid4()
    tag = str(alice)[:8]
    with _owner() as conn, conn.cursor() as cur:
        for uid, name in ((alice, "alice"), (bob, "bob")):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, 'user')",
                (str(uid), f"{name}-{tag}@views.org", get_password_hash("pw"), name),
            )
    yield alice, bob
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM users WHERE id IN (%s, %s)", (str(alice), str(bob)))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _jwt(uid: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(uid)})}"}


def test_each_user_saves_and_reads_only_their_own_view(
    client: TestClient, users: tuple[UUID, UUID]
) -> None:
    alice, bob = users
    first, second = [str(uuid4())], [str(uuid4()), str(uuid4())]
    assert (
        client.put(URL, json={"scope_ids": first}, headers=_jwt(alice)).status_code
        == 200
    )
    assert (
        client.put(URL, json={"scope_ids": second}, headers=_jwt(alice)).status_code
        == 200
    )
    assert client.get(URL, headers=_jwt(alice)).json()["scope_ids"] == second
    assert client.get(URL, headers=_jwt(bob)).json()["scope_ids"] == []
    assert (
        client.put(URL, json={"scope_ids": first}, headers=_jwt(bob)).status_code == 200
    )
    assert client.get(URL, headers=_jwt(alice)).json()["scope_ids"] == second


def test_rls_hides_and_protects_other_users_rows(users: tuple[UUID, UUID]) -> None:
    alice, bob = users
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO user_view_preferences (user_id, view, value) "
            "VALUES (%s, 'catalogue', '{\"scope_ids\": []}')",
            (str(alice),),
        )
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        cur.execute("SELECT set_config('app.current_user_id', %s, true)", (str(bob),))
        cur.execute("SELECT count(*) FROM user_view_preferences")
        assert cur.fetchone()[0] == 0
        cur.execute("UPDATE user_view_preferences SET value = '{}'")
        assert cur.rowcount == 0
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute(
                "INSERT INTO user_view_preferences (user_id, view) "
                "VALUES (%s, 'other')",
                (str(alice),),
            )
