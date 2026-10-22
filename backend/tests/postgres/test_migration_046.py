"""046 on real PostgreSQL: ClinGen v1 snapshots corrected in place, still immutable, re-run is a
no-op, pins unchanged, and validate-evidence on a seeded v1 accepts real form data (as app_user)."""

import json
import os
import re
from collections.abc import Generator
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core import database
from app.core.security import create_access_token
from app.main import app
from app.scoring.clingen import ClinGenEngine
from app.scoring.point_model import template
from tests.postgres.conftest import set_test_user_context
from tests.unit.test_clingen_v1_correction import NULL_AD, _at, _evidence
from tests.unit.test_point_model import _custom_model

pytestmark = pytest.mark.postgres

ENGINE = "clingen_sop_v11"
MIGRATION = Path(__file__).parents[3] / "database/sql/046_clingen_v1_correction.sql"
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


def test_seeded_clingen_v1_validates_real_form_data(client: TestClient) -> None:
    with (
        psycopg2.connect(os.environ["OWNER_DATABASE_URL"]) as conn,
        conn.cursor() as cur,
    ):
        cur.execute("SELECT id FROM users WHERE email = 'alice.smith@genecurator.org'")
        alice = str(cur.fetchone()[0])
        cur.execute(CLINGEN_V1)
        versions = [str(row[0]) for row in cur.fetchall()]
    assert len(versions) == 2  # ClinGen_SOP_v11 and the legacy-seeded ClinGen schema
    token = create_access_token(data={"sub": alice})

    def validate(version: str, data: dict[str, Any]) -> dict[str, Any]:
        response = client.post(
            "/api/v1/validation/validate-evidence",
            json={"evidence_data": data, "methodology_version_id": version},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        return body

    bad = _evidence()
    _at(bad, NULL_AD)[0]["proband_counted_points"] = 99
    for version in versions:
        ok = validate(version, _evidence())
        assert ok["is_valid"] is True, ok["errors"]
        live = ok["score_calculations"]  # the forms' live score, pinned point model
        saved = ClinGenEngine().calculate_scores(
            _evidence(), {}
        )  # embedded == template
        assert (live["verdict"], live["total_score"]) == (
            saved.verdict,
            saved.total_score,
        )
        assert live["trace"] == saved.evidence_breakdown["trace"]
        errors = validate(version, bad)["errors"]
        assert [e["field"].rsplit(".", 1)[-1] for e in errors] == [
            "proband_counted_points"
        ]


def _state(s: Session) -> Any:
    return s.execute(
        text(
            "SELECT (SELECT jsonb_agg(snapshot ORDER BY id) FROM methodology_versions),"
            " (SELECT jsonb_agg(field_definitions ORDER BY id) FROM curation_schemas),"
            " (SELECT jsonb_agg(methodology_version_id ORDER BY id) FROM curations),"
            " (SELECT jsonb_agg(methodology_version_id ORDER BY id) FROM precurations),"
            " (SELECT count(*) FROM schema_migrations"
            "  WHERE filename = '046_clingen_v1_correction.sql')"
        )
    ).one()


def restore_046_working_copies(s: Session) -> None:
    """Replay 046 against its historical working copies, before successor publication."""
    s.execute(
        text(
            "UPDATE curation_schemas c SET field_definitions=mv.snapshot->'field_definitions', scoring_configuration=mv.snapshot->'scoring_configuration' FROM methodology_versions mv WHERE mv.schema_id=c.id AND mv.version=1 AND c.scoring_configuration->>'engine'='clingen_sop_v11'"
        )
    )


def test_rerun_is_a_noop_and_versions_stay_immutable(owner_session: Session) -> None:
    s = owner_session
    restore_046_working_copies(s)
    before = _state(s)
    assert before[-1] == 1
    s.execute(text(MIGRATION.read_text()))
    assert _state(s) == before  # nothing changed, pins included
    vid = s.scalar(text(CLINGEN_V1))
    with pytest.raises(DBAPIError, match="immutable"), s.begin_nested():
        s.execute(
            text("UPDATE methodology_versions SET snapshot = '{}' WHERE id = :v"),
            {"v": vid},
        )


def test_corrected_version_is_immutable_for_app_user(db: Session) -> None:
    admin = db.scalar(
        text("SELECT id FROM users WHERE role = 'admin' AND is_active LIMIT 1")
    )
    set_test_user_context(db, str(admin))
    update = "UPDATE methodology_versions SET snapshot = '{}' WHERE id = :v"
    for vid in db.scalars(text(CLINGEN_V1)):
        # no UPDATE policy: app_user changes nothing, not even as platform admin
        assert db.execute(text(update), {"v": vid}).rowcount == 0  # type: ignore[attr-defined]
        snapshot = db.scalar(
            text("SELECT snapshot FROM methodology_versions WHERE id = :v"),
            {"v": vid},
        )
        fields = snapshot["field_definitions"]
        assert fields["genetic_evidence"]["type"] == "object"
        assert fields["replicated_over_time"]["type"] == "boolean"
        contradictory = fields["contradictory_evidence"]["items"]["properties"]
        assert contradictory["pmid"]["order"] == 2
        case_level = fields["genetic_evidence"]["properties"]["case_level"]
        assert case_level["order"] == 1
        model = snapshot["scoring_configuration"]["point_model"]
        assert model == template("clingen_sop_v11")


def test_046_replaces_only_the_old_template_model(owner_session: Session) -> None:
    """The real 046 on fresh v1 snapshots and its pg_temp helper: the pre-046 template is
    replaced, a custom point model kept, re-runs change nothing, versions stay immutable."""
    s = owner_session
    restore_046_working_copies(s)
    sql = MIGRATION.read_text()

    def literal(tag: str) -> Any:  # 046's own models; 047 changed the template since
        match = re.search(rf"\${tag}\$(.*?)\${tag}\$", sql, re.S)
        assert match
        return json.loads(match[1])

    old, custom, new = literal("old"), _custom_model(), literal("model")
    assert old != new != custom
    seeded = s.scalar(
        text(
            "SELECT id FROM curation_schemas WHERE schema_type = 'curation' "
            "AND scoring_configuration->>'engine' = :e LIMIT 1"
        ),
        {"e": ENGINE},
    )
    snapshot = "SELECT snapshot FROM methodology_versions WHERE id = :v"
    versions, before = {}, {}
    for name, model in (("old", old), ("custom", custom)):
        schema = s.scalar(
            text(
                "INSERT INTO curation_schemas (name, version, schema_type, "
                "field_definitions, validation_rules, scoring_configuration, "
                "workflow_states, ui_configuration, schema_hash) SELECT :n, version, "
                "schema_type, field_definitions, validation_rules, CAST(:c AS jsonb), "
                "workflow_states, ui_configuration, schema_hash FROM curation_schemas "
                "WHERE id = :s RETURNING id"
            ),
            {
                "n": f"046-{name}-{uuid4()}",
                "c": json.dumps({"engine": ENGINE, "point_model": model}),
                "s": seeded,
            },
        )  # publishes v1 with this point model
        versions[name] = s.scalar(
            text(
                "SELECT id FROM methodology_versions WHERE schema_id = :s AND version = 1"
            ),
            {"s": schema},
        )
        before[name] = s.scalar(text(snapshot), {"v": versions[name]})
        assert before[name]["scoring_configuration"]["point_model"] == model

    s.execute(text(sql))
    fixed = s.scalar(text(snapshot), {"v": versions["old"]})
    config = {"engine": ENGINE, "point_model": new}
    assert fixed == {**before["old"], "scoring_configuration": config}
    assert s.scalar(text(snapshot), {"v": versions["custom"]}) == before["custom"]
    state = _state(s)
    s.execute(text(sql))
    assert _state(s) == state
    for vid in versions.values():
        with pytest.raises(DBAPIError, match="immutable"), s.begin_nested():
            s.execute(
                text("UPDATE methodology_versions SET snapshot = '{}' WHERE id = :v"),
                {"v": vid},
            )

    def helper(doc: dict[str, Any], with_model: bool = True) -> Any:
        return s.scalar(
            text("SELECT pg_temp.clingen_046(CAST(:d AS jsonb), :m)"),
            {"d": json.dumps(doc), "m": with_model},
        )

    for given, expected in (({"point_model": old}, new), ({}, new), (config, new)):
        doc = {"scoring_configuration": {"engine": ENGINE, **given}}
        out = helper(doc)
        assert out["scoring_configuration"]["point_model"] == expected
        assert helper(out) == out  # idempotent per document
        assert (
            helper(doc, False)["scoring_configuration"] == doc["scoring_configuration"]
        )
    doc = {"scoring_configuration": {"engine": ENGINE, "point_model": custom}}
    assert helper(doc)["scoring_configuration"] == doc["scoring_configuration"]
