"""#447 as app_user on PostgreSQL: the new ClinGen bundle version scores segregation by
family and method, save, preview and reload agree, and an older pin keeps its points."""

import json

import pytest

from tests.postgres.test_clingen_successor import create, publish
from tests.postgres.test_methodology_versions import W, _h, _owner, client, w
from tests.unit.test_clingen_successor import successor_model
from tests.unit.test_segregation_sop11 import ASSERTED, BUNDLE, CANDIDATE, ad, adjusted

pytestmark = pytest.mark.postgres
__all__ = ["client", "w"]


def publish_bundle(client, w: W) -> str:
    schema = next(
        s
        for s in json.loads(BUNDLE.read_text())["schemas"]
        if s["schema_type"] == "curation"
    )
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE curation_schemas SET field_definitions=%s, scoring_configuration=%s "
            "WHERE id=%s",
            (
                json.dumps(schema["field_definitions"]),
                json.dumps(schema["scoring_configuration"]),
                w.schema,
            ),
        )
    response = client.post(
        f"/api/v1/schemas/curation-schemas/{w.schema}/versions", headers=_h(w.admin)
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def test_app_user_save_preview_reload_agree_and_old_pin_is_not_rescored(
    client, w: W
) -> None:
    families = [adjusted(3.1, points=1), ad(4, CANDIDATE)]
    evidence = {
        "genetic_evidence": {
            "segregation": families,
            "segregation_assessment": ASSERTED,
        }
    }
    old_pin = publish(client, w, successor_model())
    old = create(client, w, w.genes[0], evidence)
    assert old["computed_scores"]["total_score"] == 1  # explicit points only
    new_pin = publish_bundle(client, w)
    new = create(client, w, w.genes[1], evidence)
    assert new["methodology_version_id"] == new_pin
    assert new["computed_scores"]["total_score"] == 2  # SOP v11 p.35
    for current, pin in ((old, old_pin), (new, new_pin)):
        saved = client.patch(
            f"/api/v1/curations/{current['id']}/draft?detail=true",
            json={"evidence_data": evidence, "lock_version": current["lock_version"]},
            headers=_h(w.alice),
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["methodology_version_id"] == pin
        preview = client.post(
            "/api/v1/validation/validate-evidence",
            json={"evidence_data": evidence, "methodology_version_id": pin},
            headers=_h(w.alice),
        )
        assert preview.status_code == 200, preview.text
        detail = client.get(
            f"/api/v1/curations/{current['id']}?detail=true", headers=_h(w.alice)
        )
        assert detail.status_code == 200, detail.text
        trace = current["computed_scores"]["trace"]
        assert saved.json()["computed_scores"]["trace"] == trace
        assert preview.json()["score_calculations"]["trace"] == trace
        assert detail.json()["computed_scores"]["trace"] == trace
    applied = new["computed_scores"]["trace"]["rules_applied"]
    rule = next(r for r in applied if r["rule"] == "segregation_sop11")
    assert [f["status"] for f in rule["families"]] == ["included", "omitted_lower"]
