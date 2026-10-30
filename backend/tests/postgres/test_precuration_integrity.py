"""Precuration integrity through the API as app_user: one open precuration per disease
entity (#567)."""

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from tests.postgres.test_split_entities import A, W, _h, _rows, _submitted, client, w

pytestmark = pytest.mark.postgres
__all__ = ["client", "w"]  # fixtures


def _create(client: TestClient, w: W, evidence: dict, user: UUID) -> tuple[int, dict]:
    r = client.post(
        "/api/v1/precurations/",
        json={
            "gene_id": str(w.gene),
            "scope_id": str(w.scope),
            "precuration_schema_id": w.schema,
            "evidence_data": evidence,
        },
        headers=_h(user),
    )
    return r.status_code, r.json()


def test_an_entity_in_review_refuses_a_second_precuration(
    client: TestClient, w: W
) -> None:
    first = _submitted(w, A)
    code, body = _create(client, w, {**A, "mondo_id": " mondo:0000001 "}, w.alice)
    assert code == 409, body
    assert body["detail"]["precuration_id"] == first

    code, sus = _create(
        client, w, {**A, "relationship_type": "susceptibility"}, w.alice
    )
    assert code == 201, sus

    # A blank draft cannot be saved onto the entity in review either
    code, blank = _create(client, w, {}, w.alice)
    assert code == 201, blank
    r = client.patch(
        f"/api/v1/precurations/{blank['id']}/draft",
        json={"evidence_data": A, "lock_version": blank["lock_version"]},
        headers=_h(w.alice),
    )
    assert r.status_code == 409 and r.json()["detail"]["precuration_id"] == first
    assert _rows(
        "SELECT entity_key, lock_version FROM precurations WHERE id = %s", blank["id"]
    ) == [("", blank["lock_version"])]
    assert _rows(
        "SELECT count(*) FROM precurations WHERE gene_id = %s AND entity_key = %s",
        str(w.gene),
        "MONDO:0000001|AD",
    ) == [(1,)]
