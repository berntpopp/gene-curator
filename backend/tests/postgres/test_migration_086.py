"""086 as app_user: a scope whose curation uses a second (non-default) pair gets 422 on new
work with that pair until the backfill allows it; then the precuration is created."""

import os
from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient

from app.core import database
from app.core.security import create_access_token, get_password_hash
from app.main import app

pytestmark = pytest.mark.postgres
MIGRATION = (
    Path(__file__).parents[3] / "database/sql/086_backfill_allowed_workflow_pairs.sql"
)


@dataclass
class W:
    scope: UUID = field(default_factory=uuid4)
    alice: UUID = field(default_factory=uuid4)  # curator
    gene: UUID = field(default_factory=uuid4)
    pair_x: UUID = field(default_factory=uuid4)  # the second pair, in use
    pre_x: str = ""


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.scope)[:8]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, precuration_schema_id, curation_schema_id FROM workflow_pairs "
            "WHERE is_active AND precuration_schema_id IS NOT NULL LIMIT 1"
        )
        default, pre, cur_schema = cur.fetchone()
        cur.execute(  # a second precuration schema, so only pair X uses it
            "INSERT INTO curation_schemas (name, version, schema_type, field_definitions, "
            "validation_rules, scoring_configuration, workflow_states, ui_configuration, "
            "schema_hash) SELECT %s, version, schema_type, field_definitions, "
            "validation_rules, scoring_configuration, workflow_states, "
            "ui_configuration, schema_hash FROM curation_schemas WHERE id = %s "
            "RETURNING id",
            (f"m086-{tag}", str(pre)),
        )
        x.pre_x = str(cur.fetchone()[0])
        cur.execute(
            "INSERT INTO workflow_pairs (id, name, version, precuration_schema_id, "
            "curation_schema_id, is_active) VALUES (%s, %s, '1.0', %s, %s, true)",
            (str(x.pair_x), f"X-{tag}", x.pre_x, str(cur_schema)),
        )
        cur.execute(
            "INSERT INTO users (id, email, hashed_password, name, role) "
            "VALUES (%s, %s, %s, 'alice', 'user')",
            (str(x.alice), f"alice-{tag}@m086.org", get_password_hash("pw")),
        )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by, "
            "default_workflow_pair_id) VALUES (%s, %s, 'M', false, %s, %s)",
            (str(x.scope), f"m086-{x.scope}", str(x.alice), str(default)),
        )
        cur.execute(
            "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
            "accepted_at) VALUES (%s, %s, 'curator', %s, now())",
            (str(x.scope), str(x.alice), str(x.alice)),
        )
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (%s, %s, %s, %s)",
            (str(x.gene), f"HGNC:{x.gene.int % 10**9}", f"M{tag}", x.gene.hex * 2),
        )
        cur.execute(  # pre-082 work on pair X (another gene's entity would do too)
            "INSERT INTO curations (gene_id, scope_id, workflow_pair_id, status, "
            "workflow_stage, is_draft, evidence_data, created_by) VALUES "
            "(%s, %s, %s, 'draft', 'curation', true, '{}', %s)",
            (str(x.gene), str(x.scope), str(x.pair_x), str(x.alice)),
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
        cur.execute("DELETE FROM workflow_pairs WHERE id = %s", (str(x.pair_x),))
        cur.execute("DELETE FROM curation_schemas WHERE id = %s", (x.pre_x,))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def test_backfill_allows_the_pair_a_scope_already_uses(
    client: TestClient, w: W
) -> None:
    h = {"Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"}
    body = {
        "gene_id": str(w.gene),
        "scope_id": str(w.scope),
        "precuration_schema_id": w.pre_x,
        "evidence_data": {},
    }
    refused = client.post("/api/v1/precurations/", json=body, headers=h)
    assert refused.status_code == 422, refused.text
    for _ in range(2):  # idempotent
        with _owner() as conn, conn.cursor() as cur:
            cur.execute(MIGRATION.read_text())
    r = client.post("/api/v1/precurations/", json=body, headers=h)
    assert r.status_code == 201, r.text
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM schema_migrations WHERE filename = %s",
            ("086_backfill_allowed_workflow_pairs.sql",),
        )
        assert cur.fetchone()[0] == 1
