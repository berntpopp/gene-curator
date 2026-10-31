"""KGDB end-to-end frictions: what agents and the importer read (REST and MCP alike)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CurationNew, PrecurationNew

pytestmark = pytest.mark.unit

KEY = "MONDO:0011308|AR|SUSCEPTIBILITY|G1"
SUSCEPTIBLE = {
    "mondo_id": "MONDO:0011308",
    "mode_of_inheritance": "HP:0000007",
    "relationship_type": "susceptibility",
    "risk_allele": "G1",
}


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def susceptible(db_session: Session, test_curation: CurationNew) -> CurationNew:
    test_curation.entity_key = KEY
    test_curation.evidence_data = dict(SUSCEPTIBLE)
    db_session.commit()
    return test_curation


def test_reads_name_the_entity_key_and_risk_allele(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    susceptible: CurationNew,
    test_precuration: PrecurationNew,
) -> None:
    cid = susceptible.id
    detail = client.get(f"/api/v1/curations/{cid}", headers=_h(curator_token)).json()
    assert (detail["entity_key"], detail["risk_allele"]) == (KEY, "G1")
    review = client.get(f"/api/v1/curations/{cid}/review", headers=_h(curator_token))
    assert review.status_code == 200, review.text
    assert review.json()["curation"]["entity_key"] == KEY
    listed = client.get("/api/v1/curations/", headers=_h(curator_token)).json()
    [row] = [c for c in listed["curations"] if c["id"] == str(cid)]
    assert (row["entity_key"], row["risk_allele"]) == (KEY, "G1")

    test_precuration.evidence_data = dict(SUSCEPTIBLE)
    db_session.commit()
    pre = client.get(
        f"/api/v1/precurations/{test_precuration.id}", headers=_h(curator_token)
    ).json()
    assert pre["risk_allele"] == "G1"
    assert pre["entity_key"] == test_precuration.entity_key
