"""#386: publications.added_by is immutable for app_user; the shared cache stays refreshable.

The update policy stays permissive (shared metadata cache); a trigger keeps the adder fixed. Deleting the adder still nulls it (FK SET NULL).
"""

import os
from collections.abc import Generator
from uuid import UUID, uuid4

import psycopg2
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.security import get_password_hash

pytestmark = pytest.mark.postgres


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def pub() -> Generator[tuple[UUID, UUID, UUID], None, None]:
    adder, other, row = uuid4(), uuid4(), uuid4()
    with _owner() as conn, conn.cursor() as cur:
        for uid in (adder, other):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, 'u', 'user')",
                (str(uid), f"{uid}@pub386.org", get_password_hash("pw")),
            )
        cur.execute(
            "INSERT INTO publications (id, pmid, title, journal, added_by) "
            "VALUES (%s, %s, 'T', 'J', %s)",
            (str(row), str(row.int % 10**12), str(adder)),
        )
    yield adder, other, row
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM publications WHERE id = %s", (str(row),))
        cur.execute(
            "DELETE FROM users WHERE id = ANY(%s::uuid[])", ([str(adder), str(other)],)
        )


def _update(db: Session, user: UUID | None, row: UUID, sets: str, **p: str) -> int:
    db.execute(
        text("SELECT set_config('app.current_user_id', :u, true)"),
        {"u": str(user) if user else ""},
    )
    try:
        with db.begin_nested():
            return db.execute(
                text(f"UPDATE publications SET {sets} WHERE id = :i"),
                {"i": str(row), **p},
            ).rowcount
    except DBAPIError:
        return -1


@pytest.mark.parametrize("who", ["adder", "other", None])
def test_nobody_reassigns_added_by(
    pub: tuple[UUID, UUID, UUID], db: Session, who: str | None
) -> None:
    adder, other, row = pub
    user = {"adder": adder, "other": other, None: None}[who]
    assert _update(db, user, row, "added_by = :a", a=str(other)) == -1
    assert _update(db, user, row, "added_by = NULL") == -1


def test_metadata_refresh_still_works_without_a_user_context(
    pub: tuple[UUID, UUID, UUID], db: Session
) -> None:
    _, _, row = pub
    assert _update(db, None, row, "title = 'Refreshed'") == 1


def test_deleting_the_adder_nulls_added_by(pub: tuple[UUID, UUID, UUID]) -> None:
    adder, _, row = pub
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM users WHERE id = %s", (str(adder),))
        cur.execute("SELECT added_by FROM publications WHERE id = %s", (str(row),))
        assert cur.fetchone()[0] is None
