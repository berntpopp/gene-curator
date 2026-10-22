"""What the server guarantees for local draft recovery (#436), via the real API as app_user.

Two different cases:
- A tab still holding the lock_version it loaded cannot save over a newer save: the stale save
  gets 409 and changes nothing (the form keeps its local copy for the reload).
- After a reload the form holds the new lock_version, so an explicit "Replace with local copy"
  saves by design. Only the frontend guards that case: every save moves lock_version and
  updated_at, the version a local draft is bound to, so the reopened form flags the draft older.
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
    gene: UUID = field(
        default_factory=uuid4
    )  # has an approved precuration: curation target
    gene2: UUID = field(default_factory=uuid4)  # precuration target
    pre: UUID = field(default_factory=uuid4)
    pair: str = ""
    schema: str = ""


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
            (str(x.alice), f"alice-{tag}@recover.org", get_password_hash("pw")),
        )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, 'RC', false, %s)",
            (str(x.scope), f"rc-{x.scope}", str(x.alice)),
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
        x.pair, x.schema = str(pair), str(schema)
        for i, gene in enumerate((x.gene, x.gene2)):
            cur.execute(
                "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
                "VALUES (%s, %s, %s, %s)",
                (str(gene), f"HGNC:{gene.int % 10**9}", f"RC{i}{tag}", gene.hex * 2),
            )
        cur.execute(
            "INSERT INTO precurations (id, gene_id, scope_id, precuration_schema_id, "
            "status, workflow_stage, is_draft, created_by) VALUES "
            "(%s, %s, %s, %s, 'approved', 'curation', false, %s)",
            (str(x.pre), str(x.gene), str(x.scope), x.schema, str(x.alice)),
        )
    yield x
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(x.scope),))
        cur.execute(
            "DELETE FROM genes WHERE id IN (%s, %s)", (str(x.gene), str(x.gene2))
        )
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


@pytest.mark.parametrize("kind", ["curations", "precurations"])
def test_a_stale_loaded_version_gets_409_and_a_reopened_explicit_restore_saves(
    client: TestClient, w: W, kind: str
) -> None:
    h = {"Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"}
    target = (
        {"gene_id": str(w.gene), "workflow_pair_id": w.pair}
        if kind == "curations"
        else {"gene_id": str(w.gene2), "precuration_schema_id": w.schema}
    )
    created = client.post(
        f"/api/v1/{kind}/",
        json={"scope_id": str(w.scope), "evidence_data": {"a": "v1"}, **target},
        headers=h,
    )
    assert created.status_code == 201, created.text
    url = f"/api/v1/{kind}/{created.json()['id']}"
    loaded = client.get(
        url, headers=h
    ).json()  # the form's baseline; local edits start here

    # Another tab saves first
    newer = client.patch(
        f"{url}/draft",
        json={
            "evidence_data": {"a": "their edit"},
            "lock_version": loaded["lock_version"],
        },
        headers=h,
    )
    assert newer.status_code == 200, newer.text
    reopened = client.get(url, headers=h).json()
    # Both parts of the version a local draft is bound to move on: the reopened form flags it
    assert reopened["lock_version"] == loaded["lock_version"] + 1
    assert reopened["updated_at"] != loaded["updated_at"]

    # The tab that loaded before that save still holds the old lock_version: refused
    stale = client.patch(
        f"{url}/draft",
        json={
            "evidence_data": {"a": "my stale edit"},
            "lock_version": loaded["lock_version"],
        },
        headers=h,
    )
    assert stale.status_code == 409, stale.text
    assert client.get(url, headers=h).json()["evidence_data"] == {"a": "their edit"}

    # Reopened, the form holds the new lock_version: replacing the newer save with the flagged
    # local copy is the user's explicit choice in the dialog, and it saves
    replaced = client.patch(
        f"{url}/draft",
        json={
            "evidence_data": {"a": "my stale edit"},
            "lock_version": reopened["lock_version"],
        },
        headers=h,
    )
    assert replaced.status_code == 200, replaced.text
    assert client.get(url, headers=h).json()["evidence_data"] == {"a": "my stale edit"}
