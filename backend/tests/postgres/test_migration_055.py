"""055 / #486: the seeded demo memberships are accepted (accepted_at set), on a fresh database
and, through the backfill, on an existing one; real pending invitations stay pending."""

import os
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest

pytestmark = pytest.mark.postgres

MIGRATION = Path(__file__).parents[3] / "database/sql/055_seed_memberships_accepted.sql"
SEEDED = "SELECT u.email FROM scope_memberships m JOIN users u ON u.id = m.user_id"
ALICE = "(SELECT id FROM users WHERE email = 'alice.smith@genecurator.org')"
DEMO = (
    "u.email IN ('admin@genecurator.org', 'alice.smith@genecurator.org', "
    "'bob.jones@genecurator.org', 'carol.williams@genecurator.org')"
)


def test_seeded_memberships_are_accepted_and_055_backfills_only_them() -> None:
    other = uuid4()
    with (
        psycopg2.connect(os.environ["OWNER_DATABASE_URL"]) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(f"{SEEDED} WHERE {DEMO}")
        assert {r[0] for r in cur.fetchall()} >= {
            "alice.smith@genecurator.org",
            "bob.jones@genecurator.org",
        }
        cur.execute(f"{SEEDED} WHERE {DEMO} AND m.accepted_at IS NULL")
        assert cur.fetchall() == []

        # An existing database: seeded rows still pending, plus a real pending invitation
        cur.execute(
            f"UPDATE scope_memberships SET accepted_at = NULL WHERE user_id = {ALICE}"
        )
        cur.execute(
            "INSERT INTO users (id, email, hashed_password, name, role) "
            "VALUES (%s, %s, 'x', 'o', 'user')",
            (str(other), f"{other}@m055.org"),
        )
        cur.execute(
            "INSERT INTO scope_memberships (scope_id, user_id, role, invitation_status) "
            "SELECT id, %s, 'curator', 'accepted' FROM scopes LIMIT 1",
            (str(other),),
        )
        for _ in range(2):  # idempotent
            cur.execute(MIGRATION.read_text())
        cur.execute(
            f"{SEEDED} WHERE ({DEMO} OR u.id = %s) AND m.accepted_at IS NULL",
            (str(other),),
        )
        assert cur.fetchall() == [(f"{other}@m055.org",)]
        conn.rollback()
