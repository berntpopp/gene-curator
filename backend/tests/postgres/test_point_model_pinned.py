"""Saves score with the row's pinned point model, as app_user through the API (#266).

A new curation scores with the latest version; a later publish never re-scores an older
row with the new model.
"""

import json
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from tests.postgres.test_methodology_versions import W, _h, _owner, client, w
from tests.unit.test_point_model import CUSTOM_EVIDENCE, _custom_model

pytestmark = pytest.mark.postgres
__all__ = ["client", "w"]  # fixtures shared with the methodology version tests


def _create(client: TestClient, w: W, gene: UUID) -> dict[str, Any]:
    r = client.post(
        "/api/v1/curations/",
        json={
            "gene_id": str(gene),
            "scope_id": str(w.scope),
            "workflow_pair_id": w.pair,
            "evidence_data": CUSTOM_EVIDENCE,
        },
        headers=_h(w.alice),
    )
    assert r.status_code == 201, r.text
    body: dict[str, Any] = r.json()
    return body


def test_saves_score_with_the_pinned_point_model(client: TestClient, w: W) -> None:
    old = _create(client, w, w.genes[0])  # v1: the ClinGen template
    assert old["computed_scores"]["total_score"] == 2

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

    new = _create(client, w, w.genes[1])  # latest version on create
    assert new["methodology_version_id"] == r.json()["id"]
    assert new["computed_scores"]["total_score"] == 1.5
    assert new["computed_scores"]["trace"]["total"] == 1.5

    saved = client.patch(
        f"/api/v1/curations/{old['id']}/draft",
        json={"evidence_data": CUSTOM_EVIDENCE, "lock_version": old["lock_version"]},
        headers=_h(w.alice),
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["computed_scores"]["total_score"] == 2  # still pinned to v1

    # Stored/detail and live preview use the same pinned model and selected rule, as app_user.
    for row in (saved.json(), new):
        preview = client.post(
            "/api/v1/validation/validate-evidence",
            json={
                "evidence_data": CUSTOM_EVIDENCE,
                "methodology_version_id": row["methodology_version_id"],
            },
            headers=_h(w.alice),
        )
        assert preview.status_code == 200, preview.text
        detail = client.get(f"/api/v1/curations/{row['id']}", headers=_h(w.alice))
        assert detail.status_code == 200, detail.text
        trace = row["computed_scores"]["trace"]
        assert trace["classification_rule"]["class"] == trace["class"]
        assert preview.json()["score_calculations"]["trace"] == trace
        assert detail.json()["computed_scores"]["trace"] == trace
