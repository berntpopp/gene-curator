"""Sticky form actions retain the real app_user save/reload/version contract (#437)."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from tests.postgres.test_recovery_save_conflict import W, client as client, w as w

pytestmark = pytest.mark.postgres


@pytest.mark.parametrize("kind", ["curations", "precurations"])
def test_form_save_round_trips_long_text_false_and_zero(
    client: TestClient, w: W, kind: str
) -> None:
    headers = {
        "Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"
    }
    target = (
        {"gene_id": str(w.gene), "workflow_pair_id": w.pair}
        if kind == "curations"
        else {"gene_id": str(w.gene2), "precuration_schema_id": w.schema}
    )
    created = client.post(
        f"/api/v1/{kind}/",
        json={"scope_id": str(w.scope), "evidence_data": {}, **target},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    loaded = created.json()
    url = f"/api/v1/{kind}/{loaded['id']}"
    evidence = {
        "notes": "HGVS NM_000000.1:c.1234_5678del\n" * 30,
        "reviewed": False,
        "points": 0,
    }
    saved = client.patch(
        f"{url}/draft",
        json={"evidence_data": evidence, "lock_version": loaded["lock_version"]},
        headers=headers,
    )
    assert saved.status_code == 200, saved.text
    reloaded = client.get(url, headers=headers).json()
    assert reloaded["evidence_data"] == evidence
    assert reloaded["lock_version"] == loaded["lock_version"] + 1
    stale = client.patch(
        f"{url}/draft",
        json={
            "evidence_data": {"notes": "stale click"},
            "lock_version": loaded["lock_version"],
        },
        headers=headers,
    )
    assert stale.status_code == 409, stale.text
    assert client.get(url, headers=headers).json()["evidence_data"] == evidence
