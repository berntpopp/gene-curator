"""Split disease entities through the API as app_user (#530).

One gene, two MONDO ids: each approval opens its own draft, both become active, a
re-curation of A archives only A, and the same MONDO+MOI cannot be opened twice.
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

A = {"mondo_id": "MONDO:0000001", "disease_name": "a", "mode_of_inheritance": "AD"}
B = {"mondo_id": "MONDO:0000002", "disease_name": "b", "mode_of_inheritance": "AR"}


@dataclass
class W:
    scope: UUID = field(default_factory=uuid4)
    alice: UUID = field(default_factory=uuid4)  # curator, author
    bob: UUID = field(default_factory=uuid4)  # independent reviewer
    gene: UUID = field(default_factory=uuid4)
    pair: str = ""
    schema: str = ""


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


def _rows(sql: str, *params: object) -> list[tuple[object, ...]]:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.scope)[:8]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, precuration_schema_id FROM workflow_pairs "
            "WHERE is_active AND precuration_schema_id IS NOT NULL ORDER BY name LIMIT 1"
        )
        pair, schema = cur.fetchone()
        x.pair, x.schema = str(pair), str(schema)
        for uid, name in ((x.alice, "alice"), (x.bob, "bob")):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, 'user')",
                (str(uid), f"{name}-{tag}@split.org", get_password_hash("pw"), name),
            )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by, "
            "default_workflow_pair_id) VALUES (%s, %s, 'Split', false, %s, %s)",
            (str(x.scope), f"split-{x.scope}", str(x.alice), x.pair),
        )
        for uid, role in ((x.alice, "curator"), (x.bob, "reviewer")):
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, %s, %s, now())",
                (str(x.scope), str(uid), role, str(x.alice)),
            )
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (%s, %s, %s, %s)",
            (str(x.gene), f"HGNC:{x.gene.int % 10**9}", f"SP{tag}", x.gene.hex * 2),
        )
    yield x
    users = [str(x.alice), str(x.bob)]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(x.scope),))
        cur.execute("DELETE FROM genes WHERE id = %s", (str(x.gene),))
        cur.execute(
            "DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[]) OR scope_id = %s",
            (users, str(x.scope)),
        )
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (users,))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _h(uid: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(uid)})}"}


def _submitted(w: W, disease: dict[str, str]) -> str:
    """A precuration of this entity, submitted for review."""
    pid = str(uuid4())
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO precurations (id, gene_id, scope_id, precuration_schema_id, "
            "status, workflow_stage, is_draft, created_by, evidence_data) VALUES "
            "(%s, %s, %s, %s, 'submitted', 'review', false, %s, %s)",
            (
                pid,
                str(w.gene),
                str(w.scope),
                w.schema,
                str(w.alice),
                json.dumps(disease),
            ),
        )
    return pid


def _approve(client: TestClient, w: W, pid: str) -> str | None:
    r = client.post(f"/api/v1/precurations/{pid}/approve", headers=_h(w.bob))
    assert r.status_code == 200, r.text
    cid: str | None = r.json()["curation_id"]
    return cid


def _submit(client: TestClient, w: W, cid: str, disease: dict[str, str]) -> None:
    # Passes the seeded ClinGen required-content check (as in test_workflow_config)
    evidence = {"summary": "ok", "entity_definition": disease}
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE curations SET evidence_data = %s WHERE id = %s",
            (json.dumps(evidence), cid),
        )
    lock = client.get(f"/api/v1/curations/{cid}", headers=_h(w.alice)).json()
    sub = client.post(
        f"/api/v1/curations/{cid}/submit",
        json={"lock_version": lock["lock_version"]},
        headers=_h(w.alice),
    )
    assert sub.status_code == 200, sub.text


def _activate(client: TestClient, w: W, cid: str, disease: dict[str, str]) -> None:
    _submit(client, w, cid, disease)
    r = client.post(
        f"/api/v1/workflow/curation/{cid}/transition",
        json={"target_stage": "active", "notes": "ok"},
        headers=_h(w.bob),
    )
    assert r.json()["to_stage"] == "active", r.text


def _create(client: TestClient, w: W, **extra: str) -> tuple[int, dict]:
    body = {
        "gene_id": str(w.gene),
        "scope_id": str(w.scope),
        "workflow_pair_id": w.pair,
        "evidence_data": {},
        **extra,
    }
    r = client.post("/api/v1/curations/", json=body, headers=_h(w.alice))
    return r.status_code, r.json()


def _active(w: W) -> set[tuple[str, str]]:
    rows = _rows(
        "SELECT c.id::text, ac.entity_key FROM active_curations ac "
        "JOIN curations c ON c.id = ac.curation_id AND c.status = 'active' "
        "WHERE ac.gene_id = %s AND ac.archived_at IS NULL",
        str(w.gene),
    )
    return {(str(r[0]), str(r[1])) for r in rows}


def test_split_entities_are_curated_and_activated_on_their_own(
    client: TestClient, w: W
) -> None:
    pre_a, pre_b = _submitted(w, A), _submitted(w, B)
    a, b = _approve(client, w, pre_a), _approve(client, w, pre_b)
    assert a and b and a != b  # the second approval opens its own draft
    _activate(client, w, a, A)
    _activate(client, w, b, B)
    key_a, key_b = "MONDO:0000001|AD", "MONDO:0000002|AR"
    assert _active(w) == {(a, key_a), (b, key_b)}

    # The same MONDO+MOI again: its approval opens nothing while A is being re-curated
    code, _ = _create(client, w)
    assert code == 422  # two entities: which one?
    code, body = _create(client, w, precuration_id=pre_a)
    assert code == 201, body
    recuration = body["id"]
    dup = _submitted(w, {**A, "mondo_id": " mondo:0000001 "})
    assert _approve(client, w, dup) == recuration  # creates nothing, names the open one
    code, body = _create(client, w, precuration_id=dup)
    assert code == 409 and body["detail"]["curation_id"] == recuration

    # Re-curating A archives only A
    _activate(client, w, recuration, A)
    assert _active(w) == {(recuration, key_a), (b, key_b)}
    assert _rows("SELECT status::text FROM curations WHERE id = %s", a) == [
        ("archived",)
    ]


def test_author_drafts_one_precuration_per_entity(client: TestClient, w: W) -> None:
    def create(disease: dict[str, str]) -> tuple[int, str]:
        r = client.post(
            "/api/v1/precurations/",
            json={
                "gene_id": str(w.gene),
                "scope_id": str(w.scope),
                "precuration_schema_id": w.schema,
                "evidence_data": disease,
            },
            headers=_h(w.alice),
        )
        assert r.status_code in (200, 201), r.text
        return r.status_code, r.json()["id"]

    (_, a), (_, b) = create(A), create(B)
    assert a != b
    assert create(A)[1] == a  # the open-draft index holds per entity
    keys = _rows(
        "SELECT entity_key FROM precurations WHERE id = ANY(%s::uuid[]) ORDER BY 1",
        [a, b],
    )
    assert keys == [("MONDO:0000001|AD",), ("MONDO:0000002|AR",)]


def test_reviewer_cannot_change_a_curations_entity(client: TestClient, w: W) -> None:
    """067's guard lets precurations' generated key through, never a curation's."""
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.orm import Session

    from app.core.deps import set_rls_context
    from app.models import UserNew

    cid = _approve(client, w, _submitted(w, A))
    assert cid
    _submit(client, w, cid, A)  # under review: the reviewer may move it, nothing else
    with Session(database.engine) as db:
        set_rls_context(db, db.get_one(UserNew, w.bob))
        with pytest.raises(DBAPIError) as err:
            db.execute(
                text("UPDATE curations SET entity_key = 'MONDO:9|AD' WHERE id = :i"),
                {"i": cid},
            )
        assert isinstance(err.value.orig, psycopg2.errors.InsufficientPrivilege)
