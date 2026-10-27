"""Async endpoints run with the caller's RLS user, as app_user (#386).

The async session (asyncpg) must set app.current_user_id at every transaction begin,
like the sync session; before #386 publications and logs ran without it.
"""

import os
from collections.abc import Generator
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, event, text
from sqlalchemy.orm import Session, SessionTransaction

from app.core.security import create_access_token, get_password_hash
from app.main import app

pytestmark = pytest.mark.postgres


@pytest.fixture
def user_id() -> Generator[UUID, None, None]:
    uid = uuid4()
    with (
        psycopg2.connect(os.environ["OWNER_DATABASE_URL"]) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            "INSERT INTO users (id, email, hashed_password, name, role) "
            "VALUES (%s, %s, %s, 'async', 'user')",
            (str(uid), f"async-{uid}@rls-test.org", get_password_hash("pw")),
        )
    yield uid
    with (
        psycopg2.connect(os.environ["OWNER_DATABASE_URL"]) as conn,
        conn.cursor() as cur,
    ):
        cur.execute("DELETE FROM audit_log WHERE user_id = %s", (str(uid),))
        cur.execute("DELETE FROM users WHERE id = %s", (str(uid),))


def test_async_endpoint_transactions_carry_the_rls_user(user_id: UUID) -> None:
    seen: list[tuple[str, str | None]] = []

    def record(
        session: Session, transaction: SessionTransaction, connection: Connection
    ) -> None:
        seen.append(
            (
                connection.dialect.driver,
                connection.execute(
                    text("SELECT current_setting('app.current_user_id', true)")
                ).scalar(),
            )
        )

    # registered after core.database's listener, so it sees what that one set
    event.listen(Session, "after_begin", record)
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/publications/stats/count",
                headers={
                    "Authorization": "Bearer "
                    + create_access_token(data={"sub": str(user_id)})
                },
            )
    finally:
        event.remove(Session, "after_begin", record)

    assert response.status_code == 200
    async_begins = [value for driver, value in seen if driver == "asyncpg"]
    assert async_begins and set(async_begins) == {str(user_id)}
