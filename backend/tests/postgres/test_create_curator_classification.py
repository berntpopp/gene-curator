"""W9 monkey: a new curation (re-curation prefill) stores the curator's call on create,
through the real API as app_user."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from tests.postgres.test_submit_unknown_pmids import W, client, w

pytestmark = pytest.mark.postgres
__all__ = ["client", "w"]


def test_create_stores_the_curator_classification(client: TestClient, w: W) -> None:
    h = {"Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"}
    r = client.post(
        "/api/v1/curations/",
        json={
            "gene_id": str(w.gene),
            "scope_id": str(w.scope),
            "workflow_pair_id": w.pair,
            "precuration_id": str(w.pre),
            "evidence_data": {},
            "curator_classification": "Strong",
            "curator_classification_rationale": "Expert panel call",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = client.get(f"/api/v1/curations/{r.json()['id']}", headers=h).json()
    assert body["curator_classification"] == "strong"
    assert body["curator_classification_rationale"] == "Expert panel call"
    assert body["final_classification"] == "strong"
