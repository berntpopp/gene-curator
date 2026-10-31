"""KGDB QA run fixes as app_user on PostgreSQL: the bundle's own lump decision submits
(#610), a viewer is told the role approval needs (#612), and a draft save warns on a
cell submit would refuse while still saving it (#611)."""

import pytest
from fastapi.testclient import TestClient

from tests.postgres.test_kgdb_bundle_import import BUNDLE, ENTITY, W, _ok, client, w
from tests.postgres.test_methodology_versions import _h

pytestmark = pytest.mark.postgres
__all__ = ["client", "w"]

LUMPED = {
    **ENTITY,
    "lumping_splitting_applicable": True,
    "lumping_splitting_decision": "lump",
    "lumping_splitting_rationale": "one disease spectrum",
}


def test_kgdb_lump_submits_roles_are_named_and_drafts_warn(
    client: TestClient, w: W
) -> None:
    url = "/api/v1/schemas/methodologies/import"
    items = _ok(client.post(url, json=BUNDLE, headers=_h(w.admin)))["items"]
    schema = next(i["id"] for i in items if i["name"] == "KGDB Mendelian Precuration")
    pre = _ok(
        client.post(
            "/api/v1/precurations/",
            json={
                "gene_id": str(w.gene),
                "scope_id": w.scope,
                "precuration_schema_id": schema,
                "evidence_data": LUMPED,
            },
            headers=_h(w.alice),
        )
    )
    denied = client.post(
        f"/api/v1/precurations/{pre['id']}/approve", headers=_h(w.carol)
    )
    assert denied.status_code == 403
    assert denied.json()["detail"] == (
        "Your scope role viewer cannot do curation.review; it needs the admin or "
        "reviewer role"
    )
    _ok(
        client.post(
            f"/api/v1/precurations/{pre['id']}/submit",
            json={"lock_version": pre["lock_version"], "reviewer_id": str(w.bob)},
            headers=_h(w.alice),
        )
    )
    cid = _ok(
        client.post(f"/api/v1/precurations/{pre['id']}/approve", headers=_h(w.bob))
    )["curation_id"]

    curation = f"/api/v1/curations/{cid}"
    lock = _ok(client.get(curation, headers=_h(w.alice)))["lock_version"]
    bad = {"diagnostics": {"resources": [{"type": "patient_organization"}]}}
    saved = _ok(
        client.patch(
            f"{curation}/draft?detail=true",
            json={"evidence_data": bad, "lock_version": lock},
            headers=_h(w.alice),
        )
    )
    paths = {x["path"] for x in saved["warnings"]}
    assert "diagnostics.resources[0].type" in paths
    stored = _ok(client.get(f"{curation}?fields=evidence_data", headers=_h(w.alice)))
    assert stored["evidence_data"] == bad
