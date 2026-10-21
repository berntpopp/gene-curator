"""047 on real PostgreSQL: contradictory evidence disputes only by impact. ClinGen v1 snapshots
and working copies carry the new model, custom models are untouched, versions stay immutable
and a re-run is a no-op; validate-evidence on a seeded v1 scores it that way (as app_user)."""

import json
import os
from collections.abc import Generator
from pathlib import Path
from typing import Any

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core import database
from app.core.security import create_access_token
from app.main import app
from app.scoring.point_model import template
from tests.unit.test_clingen_v1_correction import _evidence
from tests.unit.test_migration_047_literals import literal

pytestmark = pytest.mark.postgres

MIGRATION = Path(__file__).parents[3] / "database/sql/047_contradictory_by_impact.sql"
OLD = literal("047_contradictory_by_impact.sql", "old")
NEW = template("clingen_sop_v11")
CLINGEN_V1 = (
    "SELECT id FROM methodology_versions WHERE version = 1 "
    "AND snapshot->'scoring_configuration'->>'engine' = 'clingen_sop_v11' ORDER BY id"
)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def test_note_only_row_keeps_the_class_disputing_row_disputes(
    client: TestClient,
) -> None:
    with (
        psycopg2.connect(os.environ["OWNER_DATABASE_URL"]) as conn,
        conn.cursor() as cur,
    ):
        cur.execute("SELECT id FROM users WHERE email = 'alice.smith@genecurator.org'")
        alice = str(cur.fetchone()[0])
        cur.execute(CLINGEN_V1)
        versions = [str(row[0]) for row in cur.fetchall()]
    assert versions
    token = create_access_token(data={"sub": alice})

    def verdict(version: str, impact: str) -> str:
        data = _evidence()
        data["contradictory_evidence"][0].update(
            pmid="23456789", description="Common in gnomAD", impact=impact
        )
        response = client.post(
            "/api/v1/validation/validate-evidence",
            json={"evidence_data": data, "methodology_version_id": version},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        return str(response.json()["score_calculations"]["verdict"])

    for version in versions:
        assert verdict(version, "note") == verdict(version, "requires_review")
        assert verdict(version, "note") != "disputed"
        assert verdict(version, "disputed") == "disputed"


def _state(s: Session) -> Any:
    return s.execute(
        text(
            "SELECT (SELECT jsonb_agg(snapshot ORDER BY id) FROM methodology_versions),"
            " (SELECT jsonb_agg(scoring_configuration ORDER BY id) FROM curation_schemas),"
            " (SELECT count(*) FROM schema_migrations"
            "  WHERE filename = '047_contradictory_by_impact.sql')"
        )
    ).one()


def test_seeded_working_copies_match_their_v1(owner_session: Session) -> None:
    rows = owner_session.execute(
        text(
            "SELECT c.field_definitions, c.ui_configuration, c.scoring_configuration,"
            " mv.snapshot FROM curation_schemas c JOIN methodology_versions mv"
            " ON mv.schema_id = c.id AND mv.version = 1"
            " WHERE c.schema_type = 'curation'"
            " AND c.scoring_configuration->>'engine' = 'clingen_sop_v11'"
        )
    ).all()
    assert len(rows) == 2  # ClinGen_SOP_v11 and the legacy-seeded ClinGen schema
    for fields, ui, scoring, snapshot in rows:
        assert scoring["point_model"] == NEW
        assert snapshot["scoring_configuration"]["point_model"] == NEW
        assert fields == snapshot["field_definitions"]
        assert ui == snapshot["ui_configuration"]


def test_rerun_is_a_noop_and_versions_stay_immutable(owner_session: Session) -> None:
    s = owner_session
    before = _state(s)
    assert before[-1] == 1
    s.execute(text(MIGRATION.read_text()))
    assert _state(s) == before
    vid = s.scalar(text(CLINGEN_V1))
    with pytest.raises(DBAPIError, match="immutable"), s.begin_nested():
        s.execute(
            text("UPDATE methodology_versions SET snapshot = '{}' WHERE id = :v"),
            {"v": vid},
        )


def test_replaces_only_the_046_model(owner_session: Session) -> None:
    s = owner_session
    custom = {**OLD, "overrides": []}
    ids = {}
    for name, model in (("w4k-046", OLD), ("w4k-custom", custom)):
        scoring = {"engine": "clingen_sop_v11", "point_model": model}
        ids[name] = s.scalar(
            text(
                "INSERT INTO curation_schemas (name, version, schema_type,"
                " field_definitions, workflow_states, ui_configuration,"
                " scoring_configuration, schema_hash) VALUES (:n, '1', 'curation',"
                " '{}', '{}', '{}', CAST(:sc AS jsonb), repeat('7', 64)) RETURNING id"
            ),
            {"n": name, "sc": json.dumps(scoring)},
        )
    s.execute(text(MIGRATION.read_text()))

    def models(schema_id: Any) -> Any:
        return s.execute(
            text(
                "SELECT c.scoring_configuration->'point_model',"
                " mv.snapshot->'scoring_configuration'->'point_model'"
                " FROM curation_schemas c JOIN methodology_versions mv"
                " ON mv.schema_id = c.id AND mv.version = 1 WHERE c.id = :id"
            ),
            {"id": schema_id},
        ).one()

    assert tuple(models(ids["w4k-046"])) == (NEW, NEW)
    assert tuple(models(ids["w4k-custom"])) == (custom, custom)
