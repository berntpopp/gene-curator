"""Approval pins the curation to the scope's default pair, as the API runs (app_user, RLS) (#448).

Two active pairs share one precuration schema P (A: P -> C1, B: P -> C2, C2 a copy of C1
with `review.reviewers_required: 2`). An independent reviewer approves through the API; the
curation must use the scope default B, pin C2, and need two approvals to activate. Without an
applicable default the approval refuses and changes nothing. D1 stays intact.
"""

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


@dataclass
class W:
    scope: UUID = field(default_factory=uuid4)
    alice: UUID = field(default_factory=uuid4)  # curator, author
    bob: UUID = field(default_factory=uuid4)  # independent reviewer
    carol: UUID = field(default_factory=uuid4)  # second reviewer
    gene: UUID = field(default_factory=uuid4)
    pre: UUID = field(default_factory=uuid4)
    pair_b: UUID = field(default_factory=uuid4)
    c2: str = ""


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


def _scalar(sql: str, *params: object) -> object:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return row[0] if row else None


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.scope)[:8]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT precuration_schema_id, curation_schema_id FROM workflow_pairs "
            "WHERE is_active AND precuration_schema_id IS NOT NULL LIMIT 1"
        )
        p, c1 = cur.fetchone()
        # C2: C1 needing two reviewers; its initial methodology version is published on insert
        cur.execute(
            "INSERT INTO curation_schemas (name, version, schema_type, field_definitions, "
            "validation_rules, scoring_configuration, workflow_states, ui_configuration, "
            "schema_hash) SELECT %s, version, schema_type, field_definitions, "
            "validation_rules, scoring_configuration, workflow_states || %s::jsonb, "
            "ui_configuration, schema_hash FROM curation_schemas WHERE id = %s RETURNING id",
            (f"ps-{tag}", json.dumps({"review": {"reviewers_required": 2}}), str(c1)),
        )
        x.c2 = str(cur.fetchone()[0])
        cur.execute(
            "INSERT INTO workflow_pairs (id, name, version, precuration_schema_id, "
            "curation_schema_id, is_active) VALUES (%s, %s, '1.0', %s, %s, true)",
            (str(x.pair_b), f"pairB-{tag}", str(p), x.c2),
        )
        for uid, name in ((x.alice, "alice"), (x.bob, "bob"), (x.carol, "carol")):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, 'user')",
                (str(uid), f"{name}-{tag}@pairsel.org", get_password_hash("pw"), name),
            )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by, "
            "default_workflow_pair_id) VALUES (%s, %s, 'PS', false, %s, %s)",
            (str(x.scope), f"ps-{x.scope}", str(x.alice), str(x.pair_b)),
        )
        for uid, role in (
            (x.alice, "curator"),
            (x.bob, "reviewer"),
            (x.carol, "reviewer"),
        ):
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, %s, %s, now())",
                (str(x.scope), str(uid), role, str(x.alice)),
            )
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (%s, %s, %s, %s)",
            (str(x.gene), f"HGNC:{x.gene.int % 10**9}", f"PS{tag}", x.gene.hex * 2),
        )
        cur.execute(
            "INSERT INTO precurations (id, gene_id, scope_id, precuration_schema_id, "
            "status, workflow_stage, is_draft, created_by) VALUES "
            "(%s, %s, %s, %s, 'submitted', 'review', false, %s)",
            (str(x.pre), str(x.gene), str(x.scope), str(p), str(x.alice)),
        )
    yield x
    users = [str(x.alice), str(x.bob), str(x.carol)]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(x.scope),))
        cur.execute("DELETE FROM genes WHERE id = %s", (str(x.gene),))
        cur.execute(
            "DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[]) OR scope_id = %s "
            "OR workflow_pair_id = %s OR schema_id = %s",
            (users, str(x.scope), str(x.pair_b), x.c2),
        )
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (users,))
        cur.execute("DELETE FROM workflow_pairs WHERE id = %s", (str(x.pair_b),))
        cur.execute("DELETE FROM curation_schemas WHERE id = %s", (x.c2,))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


# Passes the seeded ClinGen required-content check (as in test_workflow_config)
_EVIDENCE = {
    "summary": "ok",
    "entity_definition": {
        "mondo_id": "MONDO:0000001",
        "disease_name": "disease",
        "mode_of_inheritance": "AD",
    },
}


def _h(uid: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(uid)})}"}


def test_reviewer_approval_uses_scope_default_pair_and_its_review_rules(
    client: TestClient, w: W
) -> None:
    # D1: the author cannot approve her own precuration
    own = client.post(f"/api/v1/precurations/{w.pre}/approve", headers=_h(w.alice))
    assert own.status_code == 403, own.text
    r = client.post(f"/api/v1/precurations/{w.pre}/approve", headers=_h(w.bob))
    assert r.status_code == 200, r.text
    cid = r.json()["curation_id"]
    assert _scalar("SELECT workflow_pair_id FROM curations WHERE id = %s", cid) == str(
        w.pair_b
    )
    assert (
        _scalar(
            "SELECT mv.schema_id FROM curations c JOIN methodology_versions mv "
            "ON mv.id = c.methodology_version_id WHERE c.id = %s",
            cid,
        )
        == w.c2
    )

    # The scope pair's rules apply: one approval does not activate (reviewers_required: 2)
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE curations SET evidence_data = %s WHERE id = %s",
            (json.dumps(_EVIDENCE), cid),
        )
    lock = client.get(f"/api/v1/curations/{cid}", headers=_h(w.alice)).json()
    sub = client.post(
        f"/api/v1/curations/{cid}/submit",
        json={"lock_version": lock["lock_version"]},
        headers=_h(w.alice),
    )
    assert sub.status_code == 200, sub.text
    url = f"/api/v1/workflow/curation/{cid}/transition"
    body = {"target_stage": "active", "notes": "ok"}
    assert client.post(url, json=body, headers=_h(w.alice)).status_code == 403  # D1
    first = client.post(url, json=body, headers=_h(w.bob))
    assert first.status_code == 200, first.text
    assert first.json()["to_stage"] == "review"
    stage = "SELECT workflow_stage::text FROM curations WHERE id = %s"
    assert _scalar(stage, cid) == "review"
    second = client.post(url, json=body, headers=_h(w.carol))
    assert second.json()["to_stage"] == "active", second.text
    assert _scalar(stage, cid) == "active"


def test_ambiguous_pairs_without_default_refuse_and_change_nothing(
    client: TestClient, w: W
) -> None:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE scopes SET default_workflow_pair_id = NULL WHERE id = %s",
            (str(w.scope),),
        )
    r = client.post(f"/api/v1/precurations/{w.pre}/approve", headers=_h(w.bob))
    assert r.status_code == 400, r.text
    assert "default workflow pair" in r.json()["detail"]
    assert (
        _scalar(
            "SELECT status::text || '/' || workflow_stage::text FROM precurations "
            "WHERE id = %s",
            str(w.pre),
        )
        == "submitted/review"
    )
    assert (
        _scalar("SELECT count(*) FROM curations WHERE precuration_id = %s", str(w.pre))
        == 0
    )


def test_curation_follows_the_precurations_pair_not_another_default(
    client: TestClient, w: W
) -> None:
    """MUI-03 as app_user: the scope default K belongs to another precuration schema; the
    allowed pair B matches the precuration. Approval and Start curation both use B."""
    pair_k = uuid4()
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO curation_schemas (name, version, schema_type, field_definitions, "
            "validation_rules, scoring_configuration, workflow_states, ui_configuration, "
            "schema_hash) SELECT %s, version, schema_type, field_definitions, "
            "validation_rules, scoring_configuration, workflow_states, "
            "ui_configuration, schema_hash FROM curation_schemas WHERE id = "
            "(SELECT precuration_schema_id FROM workflow_pairs WHERE id = %s) "
            "RETURNING id",
            (f"k-{pair_k}", str(w.pair_b)),
        )
        k_pre = str(cur.fetchone()[0])
        cur.execute(
            "INSERT INTO workflow_pairs (id, name, version, precuration_schema_id, "
            "curation_schema_id, is_active) VALUES (%s, %s, '1.0', %s, %s, true)",
            (str(pair_k), f"K-{pair_k}", k_pre, w.c2),
        )
        cur.execute(
            "UPDATE scopes SET default_workflow_pair_id = %s WHERE id = %s",
            (str(pair_k), str(w.scope)),
        )
        cur.execute(
            "INSERT INTO scope_workflow_pairs (scope_id, workflow_pair_id) "
            "VALUES (%s, %s)",
            (str(w.scope), str(w.pair_b)),
        )
    try:
        r = client.post(f"/api/v1/precurations/{w.pre}/approve", headers=_h(w.bob))
        assert r.status_code == 200, r.text
        cid = r.json()["curation_id"]
        pair_of = "SELECT workflow_pair_id::text FROM curations WHERE id = %s"
        assert _scalar(pair_of, cid) == str(w.pair_b)
        # Start curation sends the scope default; the curation still gets B
        with _owner() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM curations WHERE id = %s", (cid,))
        body = {
            "gene_id": str(w.gene),
            "scope_id": str(w.scope),
            "workflow_pair_id": str(pair_k),
            "precuration_id": str(w.pre),
            "evidence_data": {},
        }
        r = client.post("/api/v1/curations/", json=body, headers=_h(w.alice))
        assert r.status_code == 201, r.text
        assert r.json()["workflow_pair_id"] == str(w.pair_b)
    finally:
        with _owner() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE scopes SET default_workflow_pair_id = NULL WHERE id = %s",
                (str(w.scope),),
            )
            cur.execute("DELETE FROM curations WHERE scope_id = %s", (str(w.scope),))
            cur.execute("DELETE FROM workflow_pairs WHERE id = %s", (str(pair_k),))
            cur.execute("DELETE FROM curation_schemas WHERE id = %s", (k_pre,))
