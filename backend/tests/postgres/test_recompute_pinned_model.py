"""Score recompute as app_user over rows created and saved through the API, pinned to a
custom point model: its custom categories are scored, not skipped (#434)."""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import database
from app.services import recompute_scores
from tests.postgres.test_methodology_versions import W, _h, _owner, client, w
from tests.postgres.test_point_model_pinned import _create
from tests.unit.test_point_model import CUSTOM_EVIDENCE, _custom_model

pytestmark = pytest.mark.postgres
__all__ = ["client", "w"]  # fixtures shared with the methodology version tests


def test_recompute_scores_api_saved_custom_evidence(
    client: TestClient, w: W, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _owner() as conn, conn.cursor() as cur:
        config = {"engine": "clingen_sop_v11", "point_model": _custom_model()}
        cur.execute(
            "UPDATE curation_schemas SET scoring_configuration = %s WHERE id = %s",
            (json.dumps(config), w.schema),
        )
    r = client.post(
        f"/api/v1/schemas/curation-schemas/{w.schema}/versions", headers=_h(w.admin)
    )
    assert r.status_code == 201, r.text
    created = _create(client, w, w.genes[0])  # curator alice, pinned to the latest
    assert created["methodology_version_id"] == r.json()["id"]
    saved = client.patch(
        f"/api/v1/curations/{created['id']}/draft",
        json={
            "evidence_data": CUSTOM_EVIDENCE,
            "lock_version": created["lock_version"],
        },
        headers=_h(w.alice),
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["computed_scores"]["total_score"] == 1.5

    stale = (
        "UPDATE curations SET computed_scores = %s, computed_verdict = %s WHERE id = %s"
    )
    with _owner() as conn, conn.cursor() as cur:  # e.g. scored before the custom model
        cur.execute(stale, ('{"total_score": 0}', "no_known", created["id"]))
    summaries: list[dict[str, Any]] = []
    monkeypatch.setattr(
        recompute_scores.logger, "info", lambda msg, **kw: summaries.append(kw)
    )
    with Session(database.engine) as db:  # app_user: RLS applies, no BYPASSRLS
        assert db.scalar(
            text(
                "SELECT NOT rolsuper AND NOT rolbypassrls FROM pg_roles "
                "WHERE rolname = current_user"
            )
        )
        recompute_scores.recompute_all_scores(db)
    (summary,) = summaries
    assert "genetic_evidence.patient_registry_cohort" in summary["custom_categories"]
    assert created["id"] not in summary["unscored"]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT computed_scores->'total_score', computed_verdict, "
            "computed_scores->'trace'->'total' FROM curations WHERE id = %s",
            (created["id"],),
        )
        assert cur.fetchone() == (1.5, "limited", 1.5)
