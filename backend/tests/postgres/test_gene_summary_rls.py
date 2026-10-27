"""Gene summary under RLS: a non-member never sees another scope's draft or active row."""

import json
import os
from collections.abc import Generator
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import database
from app.core.deps import set_rls_context
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import CurationNew, UserNew

pytestmark = pytest.mark.postgres


@dataclass
class World:
    gene: UUID = field(default_factory=uuid4)
    pair: UUID = field(default_factory=uuid4)
    bob: UUID = field(default_factory=uuid4)  # curator in private scope B
    alice: UUID = field(default_factory=uuid4)  # member of private scope A only
    carol: UUID = field(default_factory=uuid4)  # pending invitation to B
    dave: UUID = field(default_factory=uuid4)  # platform admin, no memberships
    scope_a: UUID = field(default_factory=uuid4)
    scope_b: UUID = field(default_factory=uuid4)
    scope_pub: UUID = field(default_factory=uuid4)
    draft_b: UUID = field(default_factory=uuid4)
    active_b: UUID = field(default_factory=uuid4)
    active_pub: UUID = field(default_factory=uuid4)
    draft_pub: UUID = field(default_factory=uuid4)  # draft inside a PUBLIC scope


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def world() -> Generator[World, None, None]:
    w = World()
    tag = str(w.gene)[:8]
    with _owner() as conn, conn.cursor() as cur:
        for uid, name, role in (
            (w.bob, "bob", "user"),
            (w.alice, "alice", "user"),
            (w.carol, "carol", "user"),
            (w.dave, "dave", "admin"),
        ):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    str(uid),
                    f"{name}-{tag}@gs-test.org",
                    get_password_hash("pw"),
                    name,
                    role,
                ),
            )
        for sid, public in (
            (w.scope_a, False),
            (w.scope_b, False),
            (w.scope_pub, True),
        ):
            cur.execute(
                "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
                "VALUES (%s, %s, %s, %s, %s)",
                (str(sid), f"gs-{sid}", "GS", public, str(w.bob)),
            )
        for sid, uid, accepted in (
            (w.scope_a, w.alice, True),
            (w.scope_b, w.bob, True),
            (w.scope_b, w.carol, False),
            (w.scope_pub, w.bob, True),
        ):
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, 'curator', %s, CASE WHEN %s THEN now() END)",
                (str(sid), str(uid), str(w.bob), accepted),
            )
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (%s, %s, %s, %s)",
            (
                str(w.gene),
                f"HGNC:{w.gene.int % 10**9}",
                f"GS{tag}",
                str(w.gene).replace("-", "") * 2,
            ),
        )
        cur.execute(
            # curations pin a version of the pair's curation schema (042)
            "INSERT INTO workflow_pairs (id, name, version, precuration_schema_id, "
            "curation_schema_id) SELECT %s, %s, '1', precuration_schema_id, "
            "curation_schema_id FROM workflow_pairs WHERE is_active LIMIT 1",
            (str(w.pair), f"gs-{tag}"),
        )
        for cid, sid, status, stage, verdict in (
            (w.draft_b, w.scope_b, "draft", "curation", "limited"),
            (w.active_b, w.scope_b, "active", "active", "definitive"),
            (w.active_pub, w.scope_pub, "active", "active", "refuted"),
            (w.draft_pub, w.scope_pub, "draft", "curation", "limited"),
        ):
            cur.execute(
                "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, status, "
                "workflow_stage, computed_verdict, created_by, evidence_data) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    str(cid),
                    str(w.gene),
                    str(sid),
                    str(w.pair),
                    status,
                    stage,
                    verdict,
                    str(w.bob),
                    json.dumps({"n": str(cid)}),
                ),
            )
        for cid, sid in ((w.active_b, w.scope_b), (w.active_pub, w.scope_pub)):
            cur.execute(
                "INSERT INTO active_curations (gene_id, scope_id, curation_id) "
                "VALUES (%s, %s, %s)",
                (str(w.gene), str(sid), str(cid)),
            )
    yield w
    with _owner() as conn, conn.cursor() as cur:
        users = [str(u) for u in (w.bob, w.alice, w.carol, w.dave)]
        scopes = [str(s) for s in (w.scope_a, w.scope_b, w.scope_pub)]
        cur.execute("DELETE FROM scopes WHERE id = ANY(%s::uuid[])", (scopes,))
        cur.execute("DELETE FROM genes WHERE id = %s", (str(w.gene),))
        cur.execute("DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[])", (users,))
        cur.execute("DELETE FROM audit_log WHERE workflow_pair_id = %s", (str(w.pair),))
        cur.execute("DELETE FROM workflow_pairs WHERE id = %s", (str(w.pair),))
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (users,))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as test_client:
        yield test_client
    database.engine.dispose()


def _full(client: TestClient, w: World, user: UUID) -> dict:
    token = create_access_token(data={"sub": str(user)})
    r = client.get(
        f"/api/v1/genes/{w.gene}/summary/full",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_non_members_never_see_scope_b(client: TestClient, world: World) -> None:
    for user in (world.alice, world.carol, world.dave):
        body = _full(client, world, user)
        assert [r["curation_id"] for r in body["scope_summaries"]] == [
            str(world.active_pub)
        ]
        assert body["classification_summary"] == {"refuted": 1}
        assert body["has_conflicts"] is False


def test_anonymous_sees_only_active_public_row(
    client: TestClient, world: World
) -> None:
    body = client.get(f"/api/v1/genes/{world.gene}/summary").json()
    assert [r["curation_id"] for r in body["scope_summaries"]] == [
        str(world.active_pub)
    ]


def test_member_sees_own_draft_and_active(client: TestClient, world: World) -> None:
    body = _full(client, world, world.bob)
    rows = {r["curation_id"]: r for r in body["scope_summaries"]}
    assert set(rows) == {
        str(world.draft_b),
        str(world.active_b),
        str(world.active_pub),
        str(world.draft_pub),
    }
    assert rows[str(world.draft_b)]["in_progress"] is True
    assert body["has_conflicts"] is True


def test_rls_alone_hides_draft_from_non_member(world: World) -> None:
    """No Python checks: the database decides."""
    with Session(database.engine) as db:
        set_rls_context(db, db.get_one(UserNew, world.alice))
        ids = set(
            db.scalars(select(CurationNew.id).where(CurationNew.gene_id == world.gene))
        )
        assert world.draft_b not in ids
        assert world.active_b not in ids
