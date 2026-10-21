"""GET /search under real RLS (app_user): other scopes' drafts and private scopes never leak (#273)."""

import os
from collections.abc import Generator
from dataclasses import dataclass
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient

from app.core import database
from app.core.security import create_access_token, get_password_hash
from app.main import app

pytestmark = pytest.mark.postgres


@dataclass
class World:
    alice: UUID  # curator in scope A
    carol: UUID  # pending invitation to scope A
    scope_a: UUID
    scope_b: UUID  # nobody here but bob
    cur_a: UUID
    cur_b: UUID
    tag: str


@pytest.fixture
def world() -> Generator[World, None, None]:
    w = World(uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), uuid4().hex[:6])
    bob, gene = uuid4(), uuid4()
    symbol = f"ZQ{w.tag.upper()}"
    with (
        psycopg2.connect(os.environ["OWNER_DATABASE_URL"]) as conn,
        conn.cursor() as cur,
    ):
        for uid, name in ((w.alice, "alice"), (w.carol, "carol"), (bob, "bob")):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, 'user')",
                (
                    str(uid),
                    f"{name}-{w.tag}@search-test.org",
                    get_password_hash("pw"),
                    name,
                ),
            )
        for sid in (w.scope_a, w.scope_b):
            cur.execute(
                "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
                "VALUES (%s, %s, %s, false, %s)",
                (str(sid), f"srch-{sid}", f"Search {sid}", str(bob)),
            )
        for sid, uid, role, accepted in (
            (w.scope_a, w.alice, "curator", True),
            (w.scope_a, w.carol, "viewer", False),
            (w.scope_b, bob, "curator", True),
        ):
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, %s, %s, CASE WHEN %s THEN now() END)",
                (str(sid), str(uid), role, str(bob), accepted),
            )
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (%s, %s, %s, %s)",
            (str(gene), f"HGNC:8{int(w.tag, 16)}", symbol, uuid4().hex * 2),
        )
        cur.execute("SELECT id FROM workflow_pairs LIMIT 1")
        pair = cur.fetchone()[0]
        for cid, sid in ((w.cur_a, w.scope_a), (w.cur_b, w.scope_b)):
            cur.execute(
                "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, created_by) "
                "VALUES (%s, %s, %s, %s, %s)",
                (str(cid), str(gene), str(sid), str(pair), str(bob)),
            )
    w.symbol = symbol  # type: ignore[attr-defined]
    yield w
    with (
        psycopg2.connect(os.environ["OWNER_DATABASE_URL"]) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            "DELETE FROM curations WHERE id IN (%s, %s)", (str(w.cur_a), str(w.cur_b))
        )
        cur.execute("DELETE FROM genes WHERE id = %s", (str(gene),))
        cur.execute(
            "DELETE FROM scopes WHERE id IN (%s, %s)", (str(w.scope_a), str(w.scope_b))
        )
        users = [str(w.alice), str(w.carol), str(bob)]
        cur.execute("DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[])", (users,))
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (users,))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as test_client:
        yield test_client
    database.engine.dispose()


def _get(client: TestClient, user: UUID, q: str) -> dict:
    token = create_access_token(data={"sub": str(user)})
    response = client.get(
        "/api/v1/search", params={"q": q}, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_member_sees_only_own_scope_curation(client: TestClient, world: World) -> None:
    got = _get(client, world.alice, world.symbol)  # type: ignore[attr-defined]
    assert [c["id"] for c in got["curations"]] == [str(world.cur_a)]
    assert [g["symbol"] for g in got["genes"]] == [world.symbol]  # type: ignore[attr-defined]


def test_non_member_scope_never_appears(client: TestClient, world: World) -> None:
    got = _get(client, world.alice, "srch-")
    assert [s["id"] for s in got["scopes"]] == [str(world.scope_a)]


def test_pending_invitation_sees_nothing(client: TestClient, world: World) -> None:
    got = _get(client, world.carol, world.symbol)  # type: ignore[attr-defined]
    assert got["curations"] == []
    assert _get(client, world.carol, "srch-")["scopes"] == []
