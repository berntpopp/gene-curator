"""Precuration submit enforces required_when as app_user (#433); hidden fields never block."""

import json
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

FIELDS = {
    "kind": {"type": "text"},
    "detail": {"type": "text", "required_when": {"kind": "other"}},
    "extra": {
        "type": "object",
        "visible_when": {"kind": "other"},
        "properties": {"why": {"type": "text", "required": True}},
    },
}
RULES = {"conditional_required": {"note": {"when": {"rows.0.kind": "case"}}}}


@dataclass
class W:
    scope: UUID = field(default_factory=uuid4)
    alice: UUID = field(default_factory=uuid4)  # curator
    gene: UUID = field(default_factory=uuid4)
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
            (str(x.alice), f"alice-{tag}@reqwhen.org", get_password_hash("pw")),
        )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, 'RW', false, %s)",
            (str(x.scope), f"rw-{x.scope}", str(x.alice)),
        )
        cur.execute(
            "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
            "accepted_at) VALUES (%s, %s, 'curator', %s, now())",
            (str(x.scope), str(x.alice), str(x.alice)),
        )
        cur.execute(
            "SELECT precuration_schema_id FROM workflow_pairs WHERE is_active LIMIT 1"
        )
        seeded = cur.fetchone()[0]
        # The seeded precuration schema with conditional fields (auto-published as v1)
        cur.execute(
            "INSERT INTO curation_schemas (name, version, schema_type, field_definitions, "
            "validation_rules, scoring_configuration, workflow_states, ui_configuration, "
            "schema_hash, created_by) SELECT %s, version, schema_type, %s, %s, "
            "scoring_configuration, workflow_states, ui_configuration, schema_hash, %s "
            "FROM curation_schemas WHERE id = %s RETURNING id",
            (f"rw-{tag}", json.dumps(FIELDS), json.dumps(RULES), str(x.alice), seeded),
        )
        x.schema = str(cur.fetchone()[0])
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (%s, %s, %s, %s)",
            (str(x.gene), f"HGNC:{x.gene.int % 10**9}", f"RW{tag}", x.gene.hex * 2),
        )
    yield x
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(x.scope),))
        cur.execute(
            "DELETE FROM audit_log WHERE user_id = %s OR scope_id = %s OR schema_id = %s",
            (str(x.alice), str(x.scope), x.schema),
        )
        cur.execute("DELETE FROM curation_schemas WHERE id = %s", (x.schema,))
        cur.execute("DELETE FROM genes WHERE id = %s", (str(x.gene),))
        cur.execute("DELETE FROM users WHERE id = %s", (str(x.alice),))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _state(pid: str) -> tuple[str, int]:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT workflow_stage, lock_version FROM precurations WHERE id = %s",
            (pid,),
        )
        row = cur.fetchone()
        assert row
        return row[0], row[1]


def test_submit_requires_required_when_fields_and_skips_hidden_ones(
    client: TestClient, w: W
) -> None:
    h = {"Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"}
    r = client.post(
        "/api/v1/precurations/",
        json={
            "gene_id": str(w.gene),
            "scope_id": str(w.scope),
            "precuration_schema_id": w.schema,
            "evidence_data": {"kind": "other", "rows": [{"kind": "case"}]},
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    before = _state(pid)

    refused = client.post(
        f"/api/v1/precurations/{pid}/submit",
        json={"lock_version": before[1]},
        headers=h,
    )
    assert refused.status_code == 422, refused.text
    # jsonb keeps no key order
    assert sorted(refused.json()["detail"]["fields"]) == ["detail", "extra.why", "note"]
    assert _state(pid) == before  # a refused submit changes nothing

    # kind AD: detail is not required, extra (and its required child) is hidden;
    # rows.0.kind no longer "case": note is not required
    saved = client.patch(
        f"/api/v1/precurations/{pid}/draft",
        json={
            "evidence_data": {"kind": "AD", "rows": [{"kind": "other"}]},
            "lock_version": before[1],
        },
        headers=h,
    )
    assert saved.status_code == 200, saved.text
    ok = client.post(
        f"/api/v1/precurations/{pid}/submit",
        json={"lock_version": saved.json()["lock_version"]},
        headers=h,
    )
    assert ok.status_code == 200, ok.text
    assert _state(pid)[0] == "review"
