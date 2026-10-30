"""GET /curations/{id}/score returns the scorer's warnings (monkey L1)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CurationNew

pytestmark = pytest.mark.unit


def test_score_returns_the_scorer_warnings(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    test_curation: CurationNew,
) -> None:
    test_curation.evidence_data = {"evidence_summary": "total of 99 points"}
    db_session.commit()
    response = client.get(
        f"/api/v1/curations/{test_curation.id}/score",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, response.text
    assert any("claims a total of 99" in w for w in response.json()["warnings"])
