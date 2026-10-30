"""Score recompute as app_user over rows created and saved through the API, pinned to a
custom point model: its custom categories are scored, not skipped (#434)."""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import database
from app.scoring.point_model import template
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
        f"/api/v1/curations/{created['id']}/draft?detail=true",
        json={
            "evidence_data": {"genetic_evidence": CUSTOM_EVIDENCE["genetic_evidence"]},
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


@pytest.mark.parametrize(
    ("evidence", "total", "path"),
    [
        (
            {
                "experimental_evidence": [
                    {"evidence_category": "models", "points": "nan"}
                ]
            },
            0,
            "experimental_evidence[0].points",
        ),
        (
            {
                "experimental_evidence": [
                    {"evidence_category": "rescue", "points": "inf"}
                ]
            },
            0,
            "experimental_evidence[0].points",
        ),
        (
            {"experimental_evidence": [{"evidence_category": "rescue", "points": -3}]},
            0,
            "experimental_evidence[0].points",
        ),
        (
            {"genetic_evidence": {"segregation": [{"lod_score": "nan"}]}},
            0,
            "genetic_evidence.segregation[0].lod_score",
        ),
        (
            {
                "genetic_evidence": [
                    {"evidence_category": "segregation", "lod_score": "inf"}
                ]
            },
            0,
            "genetic_evidence[0].lod_score",
        ),
    ],
)
def test_api_draft_invalid_scores_are_flagged_and_storable(
    client: TestClient,
    w: W,
    monkeypatch: pytest.MonkeyPatch,
    evidence: dict[str, Any],
    total: float,
    path: str,
) -> None:
    # These regression cases exercise the retained v1 LOD fallback, not its successor.
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE curation_schemas SET scoring_configuration = %s WHERE id = %s",
            (
                json.dumps(
                    {
                        "engine": "clingen_sop_v11",
                        "point_model": template("clingen_sop_v11"),
                    }
                ),
                w.schema,
            ),
        )
    version = client.post(
        f"/api/v1/schemas/curation-schemas/{w.schema}/versions", headers=_h(w.admin)
    )
    assert version.status_code == 201, version.text
    created = _create(client, w, w.genes[0])
    assert created["methodology_version_id"] == version.json()["id"]
    url = f"/api/v1/curations/{created['id']}"
    saved = client.patch(
        f"{url}/draft?detail=true",
        json={"evidence_data": evidence, "lock_version": created["lock_version"]},
        headers=_h(w.alice),
    )
    assert saved.status_code == 200, saved.text
    scores = saved.json()["computed_scores"]
    assert scores["total_score"] == total
    assert [f["path"] for f in scores["trace"]["out_of_range"]] == [path]
    json.dumps(scores, allow_nan=False)
    loaded = client.get(f"{url}?detail=true", headers=_h(w.alice))
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["computed_scores"] == scores
    assert loaded.json()["evidence_data"] == evidence

    summaries: list[dict[str, Any]] = []
    monkeypatch.setattr(
        recompute_scores.logger, "info", lambda msg, **kw: summaries.append(kw)
    )
    with Session(database.engine) as db:
        assert db.scalar(text("SELECT current_user")) == "app_user"
        recompute_scores.recompute_all_scores(db)
    assert summaries[-1]["out_of_range"][created["id"]] == [path]


def test_recompute_leaves_active_rows_alone_when_only_warnings_differ(
    client: TestClient, w: W, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An active curation at 12 points whose stored warnings predate new warning text:
    two recomputes as app_user write nothing, so lock_version (008) stays put."""
    from tests.unit.test_curation_score_persistence import _twelve_points

    created = _create(client, w, w.genes[0])
    saved = client.patch(
        f"/api/v1/curations/{created['id']}/draft",
        json={
            "evidence_data": _twelve_points(),
            "lock_version": created["lock_version"],
        },
        headers=_h(w.alice),
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["total_score"] == 12
    with _owner() as conn, conn.cursor() as cur:  # as if approved before the new text
        cur.execute(
            "UPDATE curations SET status = 'active', computed_scores = "
            "computed_scores || '{\"warnings\": []}' WHERE id = %s RETURNING lock_version",
            (created["id"],),
        )
        (before,) = cur.fetchone()
    summaries: list[dict[str, Any]] = []
    monkeypatch.setattr(
        recompute_scores.logger, "info", lambda msg, **kw: summaries.append(kw)
    )
    for _ in range(2):
        with Session(database.engine) as db:
            assert db.scalar(text("SELECT current_user")) == "app_user"
            recompute_scores.recompute_all_scores(db)
        assert created["id"] not in summaries[-1]["kept_uncited_ids"]
        assert summaries[-1]["updated"] == 0
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT lock_version, computed_scores->'warnings' FROM curations "
            "WHERE id = %s",
            (created["id"],),
        )
        assert cur.fetchone() == (before, [])
