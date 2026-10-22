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
    "answered": {"type": "boolean", "required": True, "default": False},
    "parent": {
        "type": "object",
        "required": True,
        "properties": {"child": {"type": "text", "required": True}},
    },
    "detail": {"type": "text", "required_when": {"kind": "other"}},
    "rows": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "detail": {"type": "text", "required_when": {"kind": "other"}},
            },
        },
    },
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
    curation_schema: str = ""
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
            "INSERT INTO curation_schemas (name, version, schema_type, field_definitions, "
            "validation_rules, scoring_configuration, workflow_states, ui_configuration, "
            "schema_hash, created_by) SELECT %s, version, 'curation', %s, %s, "
            "'{}', '{}', ui_configuration, schema_hash, %s "
            "FROM curation_schemas WHERE id = %s RETURNING id",
            (f"rc-{tag}", json.dumps(FIELDS), json.dumps(RULES), str(x.alice), seeded),
        )
        x.curation_schema = str(cur.fetchone()[0])
        cur.execute(
            "INSERT INTO workflow_pairs (name, version, precuration_schema_id, "
            "curation_schema_id) VALUES (%s, '1.0', %s, %s) RETURNING id",
            (f"rw-{tag}", x.schema, x.curation_schema),
        )
        x.pair = str(cur.fetchone()[0])
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
        cur.execute("DELETE FROM workflow_pairs WHERE id = %s", (x.pair,))
        cur.execute(
            "DELETE FROM curation_schemas WHERE id IN (%s, %s)",
            (x.schema, x.curation_schema),
        )
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
            "evidence_data": {
                "kind": "other",
                "answered": False,
                "parent": {"child": "yes"},
                "rows": [{"kind": "case"}],
            },
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
    assert sorted(refused.json()["detail"]["fields"]) == [
        "detail",
        "extra.why",
        "note",
        "rows.0.detail",
    ]
    assert _state(pid) == before  # a refused submit changes nothing

    # kind AD: detail is not required, extra (and its required child) is hidden;
    # rows.0.kind no longer "case": note is not required
    saved = client.patch(
        f"/api/v1/precurations/{pid}/draft",
        json={
            "evidence_data": {
                "kind": "AD",
                "answered": False,
                "parent": {"child": "yes"},
                "rows": [{"kind": "other"}],
            },
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


def _item_state(item_type: str, item_id: str) -> tuple[object, ...]:
    from psycopg2 import sql

    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            sql.SQL(
                "SELECT status, workflow_stage, lock_version, evidence_data, "
                "is_draft FROM {} WHERE id = %s"
            ).format(sql.Identifier(f"{item_type}s")),
            (item_id,),
        )
        row = cur.fetchone()
        assert row
        return row


def _enter_review(
    client: TestClient,
    headers: dict[str, str],
    item_type: str,
    item_id: str,
    route: str,
    lock_version: int,
):
    if route == "bulk":
        return client.post(
            "/api/v1/workflow/bulk-transition",
            json={
                "item_ids": [item_id],
                "item_type": item_type,
                "target_stage": "review",
            },
            headers=headers,
        )
    if route == "direct":
        return client.post(
            f"/api/v1/workflow/{item_type}/{item_id}/transition",
            json={"target_stage": "review"},
            headers=headers,
        )
    return client.post(
        f"/api/v1/{item_type}s/{item_id}/{route}",
        json={"lock_version": lock_version} if route == "submit" else None,
        headers=headers,
    )


@pytest.mark.parametrize(
    ("item_type", "route"),
    [
        ("curation", "submit"),
        ("curation", "direct"),
        ("curation", "bulk"),
        ("precuration", "submit"),
        ("precuration", "direct"),
        ("precuration", "bulk"),
        ("precuration", "complete"),
    ],
)
def test_every_route_checks_pinned_required_fields_without_mutating_a_refusal(
    client: TestClient,
    w: W,
    item_type: str,
    route: str,
) -> None:
    h = {"Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"}
    if route == "bulk":
        # Platform admin still needs the accepted scope membership and content checks.
        with _owner() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET role = 'admin' WHERE id = %s", (str(w.alice),)
            )
    if item_type == "curation":
        with _owner() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO precurations (gene_id, scope_id, precuration_schema_id, "
                "status, workflow_stage, is_draft, created_by) VALUES "
                "(%s, %s, %s, 'approved', 'curation', false, %s)",
                (str(w.gene), str(w.scope), w.schema, str(w.alice)),
            )
    made = client.post(
        f"/api/v1/{item_type}s/",
        json={
            "gene_id": str(w.gene),
            "scope_id": str(w.scope),
            **(
                {"workflow_pair_id": w.pair}
                if item_type == "curation"
                else {"precuration_schema_id": w.schema}
            ),
            "evidence_data": {
                "kind": "other",
                "answered": False,
                "parent": {"other": "present"},
                "rows": [{"kind": "case"}],
            },
        },
        headers=h,
    )
    assert made.status_code == 201, made.text
    item_id = made.json()["id"]
    assert made.json()["methodology_version_id"]
    # The pinned definition must win over edits to the working schema.
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE curation_schemas SET field_definitions = '{}', validation_rules = '{}' "
            "WHERE id = %s",
            (w.curation_schema if item_type == "curation" else w.schema,),
        )
    before = _item_state(item_type, item_id)
    refused = _enter_review(client, h, item_type, item_id, route, int(before[2]))
    if route == "bulk":
        assert refused.status_code == 200, refused.text
        assert refused.json()["total_failed"] == 1
        error = refused.json()["failed_transitions"][0]["error"]
    else:
        assert refused.status_code == (
            422
            if item_type == "precuration" and route in ("submit", "complete")
            else 400
        ), refused.text
        error = str(refused.json()["detail"])
    for path in ("detail", "extra.why", "note", "parent.child", "rows.0.detail"):
        assert path in error
    assert _item_state(item_type, item_id) == before
    saved = client.patch(
        f"/api/v1/{item_type}s/{item_id}/draft",
        json={
            "evidence_data": {
                "kind": "AD",
                "answered": False,
                "parent": {"child": "yes"},
                "rows": [{"kind": "other"}],
            },
            "lock_version": before[2],
        },
        headers=h,
    )
    assert saved.status_code == 200, saved.text
    accepted = _enter_review(
        client, h, item_type, item_id, route, saved.json()["lock_version"]
    )
    assert accepted.status_code == 200, accepted.text
    if route == "bulk":
        assert accepted.json()["total_successful"] == 1, accepted.text
    assert _item_state(item_type, item_id)[1] == "review"


@pytest.mark.parametrize("route", ["submit", "direct", "bulk", "complete"])
def test_lumping_decision_cannot_bypass_review_validation(
    client: TestClient,
    w: W,
    route: str,
) -> None:
    headers = {
        "Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"
    }
    if route == "bulk":
        with _owner() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET role = 'admin' WHERE id = %s", (str(w.alice),)
            )
    evidence = {
        "kind": "AD",
        "answered": False,
        "parent": {"child": "yes"},
        "lumping_splitting_applicable": True,
        "lumping_splitting_decision": "UNDECIDED",
    }
    made = client.post(
        "/api/v1/precurations/",
        headers=headers,
        json={
            "gene_id": str(w.gene),
            "scope_id": str(w.scope),
            "precuration_schema_id": w.schema,
            "evidence_data": evidence,
        },
    )
    assert made.status_code == 201, made.text
    item_id = made.json()["id"]
    before = _item_state("precuration", item_id)
    refused = _enter_review(
        client, headers, "precuration", item_id, route, int(before[2])
    )
    assert "no decision" in refused.text
    if route == "bulk":
        assert refused.status_code == 200, refused.text
        assert refused.json()["total_failed"] == 1
    else:
        assert refused.status_code == 400, refused.text
    assert _item_state("precuration", item_id) == before
    evidence["lumping_splitting_decision"] = "LUMP"
    saved = client.patch(
        f"/api/v1/precurations/{item_id}/draft",
        headers=headers,
        json={"evidence_data": evidence, "lock_version": before[2]},
    )
    assert saved.status_code == 200, saved.text
    accepted = _enter_review(
        client, headers, "precuration", item_id, route, saved.json()["lock_version"]
    )
    assert accepted.status_code == 200, accepted.text
    assert _item_state("precuration", item_id)[1] == "review"


@pytest.mark.parametrize("route", ["submit", "direct", "bulk"])
@pytest.mark.parametrize("source", ["flat", "nested", "missing"])
def test_linked_disease_is_validated_without_copying_it_into_curation(
    client: TestClient, w: W, route: str, source: str
) -> None:
    disease = {
        "disease_name": "Linked disease",
        "mondo_id": "MONDO:0000001",
        "mode_of_inheritance": "AD",
    }
    entity = {
        "type": "object",
        "readonly": True,
        "properties": {
            key: {"type": "text", "required": True, "readonly": True} for key in disease
        },
    }
    pre_evidence = (
        {"entity_definition": disease}
        if source == "nested"
        else disease
        if source == "flat"
        else {}
    )
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE curation_schemas SET field_definitions = %s, validation_rules = '{}' "
            "WHERE id = %s",
            (json.dumps({"entity_definition": entity}), w.curation_schema),
        )
        cur.execute(
            "INSERT INTO methodology_versions (schema_id, version, snapshot, created_by) "
            "SELECT id, 2, methodology_snapshot(s), created_by FROM curation_schemas s "
            "WHERE id = %s",
            (w.curation_schema,),
        )
        if route == "bulk":
            cur.execute(
                "UPDATE users SET role = 'admin' WHERE id = %s", (str(w.alice),)
            )
        cur.execute(
            "INSERT INTO precurations (gene_id, scope_id, precuration_schema_id, "
            "status, workflow_stage, is_draft, created_by, evidence_data) VALUES "
            "(%s, %s, %s, 'approved', 'curation', false, %s, %s) RETURNING id",
            (
                str(w.gene),
                str(w.scope),
                w.schema,
                str(w.alice),
                json.dumps(pre_evidence),
            ),
        )
        pre_id = str(cur.fetchone()[0])
    headers = {
        "Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"
    }
    evidence = {"summary": "Evidence reviewed"}
    made = client.post(
        "/api/v1/curations/",
        headers=headers,
        json={
            "gene_id": str(w.gene),
            "scope_id": str(w.scope),
            "workflow_pair_id": w.pair,
            "precuration_id": pre_id,
            "evidence_data": evidence,
        },
    )
    assert made.status_code == 201, made.text
    item_id = made.json()["id"]
    assert made.json()["methodology_version_id"]
    before = _item_state("curation", item_id)
    result = _enter_review(client, headers, "curation", item_id, route, int(before[2]))
    after = _item_state("curation", item_id)
    if source == "missing":
        assert result.status_code == (200 if route == "bulk" else 400), result.text
        if route == "bulk":
            assert result.json()["total_failed"] == 1
        for key in disease:
            assert f"entity_definition.{key}" in result.text
        assert after == before
    else:
        assert result.status_code == 200, result.text
        if route == "bulk":
            assert result.json()["total_successful"] == 1, result.text
        assert after[1] == "review"
    assert after[3] == evidence
    assert _item_state("precuration", pre_id)[3] == pre_evidence


def test_active_curation_cannot_reenter_review_with_missing_content(
    client: TestClient, w: W
) -> None:
    headers = {
        "Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"
    }
    # Seed a historical active record; the transition itself must run through app_user.
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE scope_memberships SET role = 'admin' WHERE scope_id = %s AND user_id = %s",
            (str(w.scope), str(w.alice)),
        )
        cur.execute(
            "INSERT INTO curations (gene_id, scope_id, workflow_pair_id, status, "
            "workflow_stage, is_draft, created_by, evidence_data) VALUES "
            "(%s, %s, %s, 'active', 'active', false, %s, %s) RETURNING id",
            (
                str(w.gene),
                str(w.scope),
                w.pair,
                str(w.alice),
                json.dumps({"kind": "AD", "answered": False}),
            ),
        )
        item_id = str(cur.fetchone()[0])
    before = _item_state("curation", item_id)
    refused = _enter_review(
        client, headers, "curation", item_id, "direct", int(before[2])
    )
    assert refused.status_code == 400, refused.text
    assert "parent.child" in refused.text
    assert _item_state("curation", item_id) == before
