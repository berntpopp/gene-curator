"""Reading a curation never writes it (monkey M2).

GET /curations/{id} showed the gene's approved precuration by assigning the relationship; the
next query flushed `UPDATE curations SET precuration_id`, the version trigger bumped
lock_version, and the client's next save (with the version from create) got a 409.
"""

import os
from collections.abc import Generator
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient

from app.core import database
from app.core.security import create_access_token, get_password_hash
from app.main import app

pytestmark = pytest.mark.postgres


@dataclass
class W:
    scope: UUID = field(default_factory=uuid4)
    alice: UUID = field(default_factory=uuid4)  # curator
    gene: UUID = field(default_factory=uuid4)
    pre: UUID = field(default_factory=uuid4)  # approved precuration of the gene
    pair: str = ""


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.scope)[:8]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (id, email, hashed_password, name, role) "
            "VALUES (%s, %s, %s, 'alice', 'user')",
            (str(x.alice), f"alice-{tag}@getcur.org", get_password_hash("pw")),
        )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, 'GC', false, %s)",
            (str(x.scope), f"gc-{x.scope}", str(x.alice)),
        )
        cur.execute(
            "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
            "accepted_at) VALUES (%s, %s, 'curator', %s, now())",
            (str(x.scope), str(x.alice), str(x.alice)),
        )
        cur.execute(
            "SELECT id, precuration_schema_id FROM workflow_pairs WHERE is_active LIMIT 1"
        )
        pair, schema = cur.fetchone()
        x.pair = str(pair)
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (%s, %s, %s, %s)",
            (str(x.gene), f"HGNC:{x.gene.int % 10**9}", f"GC{tag}", x.gene.hex * 2),
        )
        cur.execute(
            "INSERT INTO precurations (id, gene_id, scope_id, precuration_schema_id, "
            "status, workflow_stage, is_draft, created_by) VALUES "
            "(%s, %s, %s, %s, 'approved', 'curation', false, %s)",
            (str(x.pre), str(x.gene), str(x.scope), str(schema), str(x.alice)),
        )
    yield x
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(x.scope),))
        cur.execute("DELETE FROM genes WHERE id = %s", (str(x.gene),))
        cur.execute(
            "DELETE FROM audit_log WHERE user_id = %s OR scope_id = %s",
            (str(x.alice), str(x.scope)),
        )
        cur.execute("DELETE FROM users WHERE id = %s", (str(x.alice),))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _row(cid: str) -> tuple[int, str | None]:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT lock_version, precuration_id::text FROM curations WHERE id = %s",
            (cid,),
        )
        row = cur.fetchone()
        assert row
        return row[0], row[1]


def test_get_does_not_write_and_a_save_at_the_created_version_succeeds(
    client: TestClient, w: W
) -> None:
    h = {"Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"}
    r = client.post(
        "/api/v1/curations/",
        json={
            "gene_id": str(w.gene),
            "scope_id": str(w.scope),
            "workflow_pair_id": w.pair,
            "evidence_data": {"a": 1},
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    cid, version = r.json()["id"], r.json()["lock_version"]

    got = client.get(f"/api/v1/curations/{cid}", headers=h)
    assert got.status_code == 200, got.text
    # The approved precuration is still shown, but never linked by a read
    assert got.json()["precuration_id"] is None
    assert _row(cid) == (version, None)

    saved = client.patch(
        f"/api/v1/curations/{cid}/draft",
        json={"evidence_data": {"a": 2}, "lock_version": version},
        headers=h,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["lock_version"] == version + 1
