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
    symbol: str
    admin: UUID
    scope_off: UUID  # inactive scope, alice is a member


@pytest.fixture
def world() -> Generator[World, None, None]:
    tag = uuid4().hex[:6]
    symbol = f"ZQ{tag.upper()}"
    w = World(
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        tag,
        symbol,
        uuid4(),
        uuid4(),
    )
    bob, gene = uuid4(), uuid4()
    with (
        psycopg2.connect(os.environ["OWNER_DATABASE_URL"]) as conn,
        conn.cursor() as cur,
    ):
        for uid, name in (
            (w.alice, "alice"),
            (w.carol, "carol"),
            (bob, "bob"),
            (w.admin, "root"),
        ):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    str(uid),
                    f"{name}-{w.tag}@search-test.org",
                    get_password_hash("pw"),
                    name,
                    "admin" if uid == w.admin else "user",
                ),
            )
        for sid in (w.scope_a, w.scope_b, w.scope_off):
            cur.execute(
                "INSERT INTO scopes (id, name, display_name, is_public, is_active, "
                "created_by) VALUES (%s, %s, %s, false, %s, %s)",
                (
                    str(sid),
                    f"srch-{sid}",
                    f"Search {sid}",
                    sid != w.scope_off,
                    str(bob),
                ),
            )
        for sid, uid, role, accepted in (
            (w.scope_a, w.alice, "curator", True),
            (w.scope_a, w.carol, "viewer", False),
            (w.scope_b, bob, "curator", True),
            (w.scope_off, w.alice, "curator", True),
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
            "DELETE FROM scopes WHERE id = ANY(%s::uuid[])",
            ([str(w.scope_a), str(w.scope_b), str(w.scope_off)],),
        )
        users = [str(w.alice), str(w.carol), str(bob), str(w.admin)]
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
    got = _get(client, world.alice, world.symbol)
    assert [c["id"] for c in got["curations"]] == [str(world.cur_a)]
    assert [g["symbol"] for g in got["genes"]] == [world.symbol]


def test_api_connects_as_app_user() -> None:
    database.engine.dispose()
    with database.engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT current_user").scalar() == "app_user"
    database.engine.dispose()


def test_admin_gets_no_bypass(client: TestClient, world: World) -> None:
    """Platform admins follow the shared rule: private scopes of others stay hidden."""
    ids = {s["id"] for s in _get(client, world.admin, "srch-")["scopes"]}
    assert not ids & {str(world.scope_a), str(world.scope_b), str(world.scope_off)}
    got = _get(client, world.admin, world.symbol)
    assert got["curations"] == []


def test_inactive_scope_never_appears(client: TestClient, world: World) -> None:
    for user in (world.alice, world.admin):
        ids = [s["id"] for s in _get(client, user, "srch-")["scopes"]]
        assert str(world.scope_off) not in ids


def test_non_member_scope_never_appears(client: TestClient, world: World) -> None:
    got = _get(client, world.alice, "srch-")
    assert [s["id"] for s in got["scopes"]] == [str(world.scope_a)]


def test_pending_invitation_sees_nothing(client: TestClient, world: World) -> None:
    got = _get(client, world.carol, world.symbol)
    assert got["curations"] == []
    assert _get(client, world.carol, "srch-")["scopes"] == []
