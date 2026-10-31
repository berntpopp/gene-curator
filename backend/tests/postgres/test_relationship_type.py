"""Relationship type (#539) on real PostgreSQL: 072 keeps every Mendelian entity_key
byte-identical and suffixes susceptibility ones; both entities of one gene, MONDO id and
MOI coexist; a curation save that moves the entity is refused (409) as app_user."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import Scope, UserNew, WorkflowPair
from tests.postgres.test_submit_unknown_pmids import W, _owner, client, w

pytestmark = pytest.mark.postgres
__all__ = ["client", "w"]
SQL = Path(__file__).parents[3] / "database/sql"
ENTITY = {"mondo_id": "MONDO:0011037", "mode_of_inheritance": "AD"}
KEY = "MONDO:0011037|AD"


def test_072_keeps_mendelian_keys_and_suffixes_susceptibility(
    owner_session: Session,
) -> None:
    # Back to the 067 column: the index on it goes with it, 067 recreates both
    owner_session.execute(
        text(
            "DROP INDEX uq_precurations_open_draft; "
            "ALTER TABLE precurations DROP COLUMN entity_key"
        )
    )
    owner_session.execute(text((SQL / "067_split_disease_entities.sql").read_text()))
    scope = owner_session.scalars(select(Scope)).first()
    user = owner_session.scalars(select(UserNew)).first()
    pair = owner_session.scalars(select(WorkflowPair)).first()
    assert scope and user and pair and pair.precuration_schema_id
    gene = uuid4()
    owner_session.execute(
        text(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (:g, 'HGNC:999072', 'REL072', :h)"
        ),
        {"g": gene, "h": "7" * 64},
    )
    evidence = {
        "mendelian": {**ENTITY, "relationship_type": "mendelian"},
        "absent": {"entity_definition": ENTITY},
        "susceptibility": {**ENTITY, "relationship_type": "Susceptibility"},
    }
    ids = {
        name: owner_session.scalar(
            text(
                "INSERT INTO precurations (gene_id, scope_id, precuration_schema_id, "
                "status, evidence_data, created_by) VALUES "
                "(:g, :s, :ps, 'approved', CAST(:e AS jsonb), :u) RETURNING id"
            ),
            {
                "g": gene,
                "s": scope.id,
                "ps": pair.precuration_schema_id,
                "e": json.dumps(e),
                "u": user.id,
            },
        )
        for name, e in evidence.items()
    }

    def keys() -> dict[str, str]:
        return {
            name: owner_session.scalar(
                text("SELECT entity_key FROM precurations WHERE id = :i"), {"i": i}
            )
            for name, i in ids.items()
        }

    # A 067-era copy of the susceptibility precuration's key follows it
    copy = owner_session.scalar(
        text(
            "INSERT INTO curations (gene_id, scope_id, workflow_pair_id, status, "
            "workflow_stage, evidence_data, created_by, precuration_id, entity_key) "
            "VALUES (:g, :s, :p, 'active', 'curation', '{}', :u, :pre, :k) RETURNING id"
        ),
        {
            "g": gene,
            "s": scope.id,
            "p": pair.id,
            "u": user.id,
            "pre": ids["susceptibility"],
            "k": KEY,
        },
    )
    owner_session.execute(
        text(
            "INSERT INTO active_curations (gene_id, scope_id, curation_id, entity_key) "
            "VALUES (:g, :s, :c, :k)"
        ),
        {"g": gene, "s": scope.id, "c": copy, "k": KEY},
    )
    before = keys()
    assert set(before.values()) == {KEY}  # 067 knows no relationship type
    for _ in range(2):
        owner_session.execute(text((SQL / "072_relationship_type.sql").read_text()))
    after = keys()
    assert after["mendelian"] == after["absent"] == before["mendelian"] == KEY
    assert after["susceptibility"] == f"{KEY}|SUSCEPTIBILITY"
    for table, col in (("curations", "id"), ("active_curations", "curation_id")):
        assert (
            owner_session.scalar(
                text(f"SELECT entity_key FROM {table} WHERE {col} = :c"),
                {"c": copy},
            )
            == f"{KEY}|SUSCEPTIBILITY"
        )
    index = owner_session.scalar(
        text(
            "SELECT indexdef FROM pg_indexes WHERE indexname = 'uq_precurations_open_draft'"
        )
    )
    assert "entity_key" in (index or "")
    assert owner_session.scalar(
        text(
            "SELECT count(*) FROM schema_migrations WHERE filename = '072_relationship_type.sql'"
        )
    )


def test_clingen_precuration_offers_relationship_type(client: TestClient, w: W) -> None:
    h = {"Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"}
    r = client.get(
        "/api/v1/schemas/curation-schemas/e8f9a0b1-c2d3-4e5f-6a7b-8c9d0e1f2a3b/versions",
        headers=h,
    )
    assert r.status_code == 200, r.text
    fields = [
        f["id"]
        for s in r.json()[0]["snapshot"]["field_definitions"]["sections"]
        for f in s["fields"]
    ]
    assert fields[fields.index("mode_of_inheritance") + 1] == "relationship_type"


def test_entities_coexist_and_a_save_cannot_move_the_entity(
    client: TestClient, w: W
) -> None:
    sus = uuid4()
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE precurations SET evidence_data = %s WHERE id = %s",
            (json.dumps(ENTITY), str(w.pre)),
        )
        cur.execute(
            "INSERT INTO precurations (id, gene_id, scope_id, precuration_schema_id, "
            "status, workflow_stage, is_draft, created_by, evidence_data) "
            "SELECT %s, gene_id, scope_id, precuration_schema_id, status, "
            "workflow_stage, false, created_by, %s FROM precurations WHERE id = %s",
            (
                str(sus),
                json.dumps({**ENTITY, "relationship_type": "susceptibility"}),
                str(w.pre),
            ),
        )
    h = {"Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"}
    made = {}
    for pre in (w.pre, sus):
        r = client.post(
            "/api/v1/curations/",
            json={
                "gene_id": str(w.gene),
                "scope_id": str(w.scope),
                "workflow_pair_id": w.pair,
                "precuration_id": str(pre),
                "evidence_data": {"entity_definition": ENTITY},
            },
            headers=h,
        )
        assert r.status_code == 201, r.text
        made[pre] = r.json()
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT entity_key FROM curations WHERE id = %s", (made[sus]["id"],)
        )
        assert cur.fetchone() == (f"{KEY}|SUSCEPTIBILITY",)

    cid, version = made[sus]["id"], made[sus]["lock_version"]
    moved = {"entity_definition": {**ENTITY, "mondo_id": "MONDO:0000001"}}
    r = client.patch(
        f"/api/v1/curations/{cid}/draft",
        json={"evidence_data": moved, "lock_version": version},
        headers=h,
    )
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["curation_id"] == cid
    r = client.patch(
        f"/api/v1/curations/{cid}/draft",
        json={"evidence_data": {"entity_definition": ENTITY}, "lock_version": version},
        headers=h,
    )
    assert r.status_code == 200, r.text
    r = client.get(f"/api/v1/curations/{cid}", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["relationship_type"] == "susceptibility"


def test_two_risk_alleles_are_two_curations(client: TestClient, w: W) -> None:
    """#614: as app_user, a second risk allele of one gene, disease and MOI opens its
    own curation instead of colliding with the first."""
    sus = {**ENTITY, "relationship_type": "susceptibility"}
    other = uuid4()
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE precurations SET evidence_data = %s WHERE id = %s",
            (json.dumps({**sus, "risk_allele": "rs4664308"}), str(w.pre)),
        )
        cur.execute(
            "INSERT INTO precurations (id, gene_id, scope_id, precuration_schema_id, "
            "status, workflow_stage, is_draft, created_by, evidence_data) "
            "SELECT %s, gene_id, scope_id, precuration_schema_id, status, "
            "workflow_stage, false, created_by, %s FROM precurations WHERE id = %s",
            (str(other), json.dumps({**sus, "risk_allele": "rs17831251"}), str(w.pre)),
        )
    h = {"Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"}
    keys = set()
    for pre in (w.pre, other):
        r = client.post(
            "/api/v1/curations/",
            json={
                "gene_id": str(w.gene),
                "scope_id": str(w.scope),
                "workflow_pair_id": w.pair,
                "precuration_id": str(pre),
                "evidence_data": {},
            },
            headers=h,
        )
        assert r.status_code == 201, r.text
        with _owner() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT entity_key FROM curations WHERE id = %s", (r.json()["id"],)
            )
            keys.add(cur.fetchone()[0])
    assert keys == {
        f"{KEY}|SUSCEPTIBILITY|RS4664308",
        f"{KEY}|SUSCEPTIBILITY|RS17831251",
    }


def test_088_keys_susceptibility_by_risk_allele(owner_session: Session) -> None:
    """#614: back on the 072 column, 088 adds the allele to susceptibility keys, makes
    HP:0000005 UNDETERMINED, leaves Mendelian keys alone and re-keys curation copies; twice is once."""
    owner_session.execute(
        text(
            "DROP INDEX uq_precurations_open_draft; DROP INDEX uq_precurations_open_entity; "
            "ALTER TABLE precurations DROP COLUMN entity_key"
        )
    )
    owner_session.execute(text((SQL / "067_split_disease_entities.sql").read_text()))
    owner_session.execute(text((SQL / "072_relationship_type.sql").read_text()))
    scope = owner_session.scalars(select(Scope)).first()
    user = owner_session.scalars(select(UserNew)).first()
    pair = owner_session.scalars(select(WorkflowPair)).first()
    assert scope and user and pair and pair.precuration_schema_id
    gene = uuid4()
    owner_session.execute(
        text(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (:g, 'HGNC:999088', 'REL088', :h)"
        ),
        {"g": gene, "h": "8" * 64},
    )
    sus = {**ENTITY, "relationship_type": "susceptibility"}
    evidence = {
        "mendelian": {**ENTITY, "risk_allele": "rs1"},
        "a1": {**sus, "risk_allele": "rs4664308"},
        "ud": {**sus, "mode_of_inheritance": "HP:0000005", "risk_allele": "rs2"},
    }
    ids = {
        name: owner_session.scalar(
            text(
                "INSERT INTO precurations (gene_id, scope_id, precuration_schema_id, "
                "status, evidence_data, created_by) VALUES "
                "(:g, :s, :ps, 'approved', CAST(:e AS jsonb), :u) RETURNING id"
            ),
            {
                "g": gene,
                "s": scope.id,
                "ps": pair.precuration_schema_id,
                "e": json.dumps(e),
                "u": user.id,
            },
        )
        for name, e in evidence.items()
    }
    old = f"{KEY}|SUSCEPTIBILITY"
    copy = owner_session.scalar(
        text(
            "INSERT INTO curations (gene_id, scope_id, workflow_pair_id, status, "
            "workflow_stage, evidence_data, created_by, precuration_id, entity_key) "
            "VALUES (:g, :s, :p, 'active', 'curation', '{}', :u, :pre, :k) RETURNING id"
        ),
        {
            "g": gene,
            "s": scope.id,
            "p": pair.id,
            "u": user.id,
            "pre": ids["a1"],
            "k": old,
        },
    )
    owner_session.execute(
        text(
            "INSERT INTO active_curations (gene_id, scope_id, curation_id, entity_key) "
            "VALUES (:g, :s, :c, :k)"
        ),
        {"g": gene, "s": scope.id, "c": copy, "k": old},
    )
    for _ in range(2):
        owner_session.execute(
            text((SQL / "088_susceptibility_allele_key.sql").read_text())
        )
    keys = {
        name: owner_session.scalar(
            text("SELECT entity_key FROM precurations WHERE id = :i"), {"i": i}
        )
        for name, i in ids.items()
    }
    assert keys == {
        "mendelian": KEY,
        "a1": f"{old}|RS4664308",
        "ud": "MONDO:0011037|UNDETERMINED|SUSCEPTIBILITY|RS2",
    }
    for table, col in (("curations", "id"), ("active_curations", "curation_id")):
        assert (
            owner_session.scalar(
                text(f"SELECT entity_key FROM {table} WHERE {col} = :c"), {"c": copy}
            )
            == f"{old}|RS4664308"
        )
    indexes = owner_session.scalars(
        text(
            "SELECT indexname FROM pg_indexes WHERE indexname IN "
            "('uq_precurations_open_draft', 'uq_precurations_open_entity')"
        )
    ).all()
    assert sorted(indexes) == [
        "uq_precurations_open_draft",
        "uq_precurations_open_entity",
    ]
    assert owner_session.scalar(
        text(
            "SELECT count(*) FROM schema_migrations "
            "WHERE filename = '088_susceptibility_allele_key.sql'"
        )
    )


def test_088_stops_on_open_precurations_the_new_key_merges(
    owner_session: Session,
) -> None:
    """Review of #619: 'Undetermined' and HP:0000005 were two keys before 088 and are one
    after; two open precurations of them stop the migration with both ids."""
    owner_session.execute(
        text(
            "DROP INDEX uq_precurations_open_draft; DROP INDEX uq_precurations_open_entity; "
            "ALTER TABLE precurations DROP COLUMN entity_key"
        )
    )
    owner_session.execute(text((SQL / "067_split_disease_entities.sql").read_text()))
    owner_session.execute(text((SQL / "072_relationship_type.sql").read_text()))
    scope = owner_session.scalars(select(Scope)).first()
    user = owner_session.scalars(select(UserNew)).first()
    pair = owner_session.scalars(select(WorkflowPair)).first()
    assert scope and user and pair and pair.precuration_schema_id
    gene = uuid4()
    owner_session.execute(
        text(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (:g, 'HGNC:999089', 'DUP088', :h)"
        ),
        {"g": gene, "h": "9" * 64},
    )
    ids = [
        owner_session.scalar(
            text(
                "INSERT INTO precurations (gene_id, scope_id, precuration_schema_id, "
                "status, evidence_data, created_by) VALUES "
                "(:g, :s, :ps, 'submitted', CAST(:e AS jsonb), :u) RETURNING id"
            ),
            {
                "g": gene,
                "s": scope.id,
                "ps": pair.precuration_schema_id,
                "e": json.dumps({**ENTITY, "mode_of_inheritance": moi}),
                "u": user.id,
            },
        )
        for moi in ("Undetermined", "HP:0000005")
    ]
    with pytest.raises(DBAPIError) as refused:
        owner_session.execute(
            text((SQL / "088_susceptibility_allele_key.sql").read_text())
        )
    message = str(refused.value)
    assert "088: open precurations would share a disease entity" in message
    assert all(str(i) in message for i in ids)
