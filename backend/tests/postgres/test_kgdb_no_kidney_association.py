"""KGDB #535 as app_user on PostgreSQL: a gene-only precuration is approved on submit, the
judge reviews the assessment once, the export says no_association, an approved disease
entity archives it, and a new assessment cannot hide that entity (409)."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.postgres.test_kgdb_bundle_import import CLDN16, ENTITY, SCOPE, W, _ok, w
from tests.postgres.test_methodology_versions import _h, client
from tests.unit.test_kgdb_methodology import BUNDLE

pytestmark = pytest.mark.postgres
__all__ = ["client", "w"]

ASSESSMENT = {
    "rationale": "Kidney HPO terms come from the MODY group record, not INS",
    "sources_checked": [
        {"source": "gencc", "finding": "Diabetes entities only"},
        {"source": "hpo", "finding": "Kidney terms via the group record", "pmid": "31000080"},
    ],
    "non_kidney_entities": [
        {"disease_name": "MODY", "kidney_phenotype_via": "group record", "note": "x"}
    ],
}  # fmt: skip


def _precurate(client: TestClient, w: W, schema: str, evidence: dict[str, Any]) -> Any:
    return _ok(
        client.post(
            "/api/v1/precurations/",
            json={
                "gene_id": str(w.gene), "scope_id": w.scope,
                "precuration_schema_id": schema, "evidence_data": evidence,
            },
            headers=_h(w.alice),
        )
    )  # fmt: skip


def _review(client: TestClient, w: W, cid: str, evidence: dict[str, Any]) -> Any:
    """Alice fills and submits the curation, Bob approves it: the approval response."""
    url = f"/api/v1/curations/{cid}"
    lock = _ok(client.get(url, headers=_h(w.alice)))["lock_version"]
    saved = _ok(
        client.patch(
            f"{url}/draft",
            json={"evidence_data": evidence, "lock_version": lock},
            headers=_h(w.alice),
        )
    )
    _ok(
        client.post(
            f"{url}/submit",
            json={"lock_version": saved["lock_version"], "reviewer_id": str(w.bob)},
            headers=_h(w.alice),
        )
    )
    reviews = client.get(
        "/api/v1/workflow/reviews/my-assignments", headers=_h(w.bob)
    ).json()
    [review] = [r for r in reviews if r["item_id"] == cid]
    return client.post(
        f"/api/v1/workflow/reviews/{review['review_id']}/submit",
        json={"decision": "approve"},
        headers=_h(w.bob),
    )


def _assess(client: TestClient, w: W, schema: str) -> str:
    """Gene-only precuration, submitted: approved at once, its draft curation's id."""
    pre = _precurate(client, w, schema, {"relationship_type": "no_association"})
    submitted = _ok(
        client.post(
            f"/api/v1/precurations/{pre['id']}/submit",
            json={"lock_version": pre["lock_version"]},
            headers=_h(w.alice),
        )
    )
    assert submitted["status"] == "approved"
    return str(submitted["curation_id"])


def _exported(client: TestClient, w: W, cid: str) -> dict[str, Any]:
    page = _ok(
        client.get(
            "/api/v1/export/curations",
            params={"scope_name": SCOPE},
            headers=_h(w.carol),
        )
    )
    [item] = [i for i in page["items"] if i["curation_id"] == cid]
    return item  # type: ignore[no-any-return]


def test_no_kidney_association_is_reviewed_once_exported_and_never_hides_an_entity(
    client: TestClient, w: W
) -> None:
    url = "/api/v1/schemas/methodologies/import"
    items = _ok(client.post(url, json=BUNDLE, headers=_h(w.admin)))["items"]
    ids = {i["name"]: i["id"] for i in items}
    schema = ids["KGDB No Kidney Association Precuration"]

    first = _assess(client, w, schema)
    assert _review(client, w, first, ASSESSMENT).status_code == 200
    item = _exported(client, w, first)
    assert (item["status"], item["relationship_type"], item["entity_key"]) == (
        "active",
        "no_association",
        "",
    )
    assert (item["mondo_id"], item["mode_of_inheritance"]) == (None, None)
    assert item["computed_verdict"] == "no_primary_kidney_association"
    assert item["evidence"]["non_kidney_entities"][0]["kidney_phenotype_via"]

    # a disease entity approved later archives the assessment
    pre = _precurate(client, w, ids["KGDB Mendelian Precuration"], ENTITY)
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
    assert _review(client, w, cid, CLDN16).status_code == 200
    assert _exported(client, w, first)["status"] == "archived"

    # and a new assessment cannot hide that active entity
    again = _review(client, w, _assess(client, w, schema), ASSESSMENT)
    assert again.status_code == 409, again.text
    assert cid in again.text
    assert _exported(client, w, cid)["status"] == "active"
