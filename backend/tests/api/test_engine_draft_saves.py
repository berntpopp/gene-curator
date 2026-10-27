"""Half-filled drafts save under every engine; scoring tolerates empty values (#386)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CurationNew, WorkflowPair
from tests.api.test_evidence_point_ranges import _engine

pytestmark = pytest.mark.unit

QUALITATIVE = {
    "clinical_assessment": {"phenotype_match": None, "inheritance_consistency": ""},
    "literature_review": None,
}
GENCC = {
    "genetic_evidence": {
        "case_level_data": [{"points": ""}, {"points": None}, {"pmid": "1"}, "x"],
        "segregation_data": None,
    },
    "experimental_evidence": {"function": [{"points": "abc"}], "models": None},
    "contradictory_evidence": None,
}


@pytest.mark.parametrize(
    ("engine", "evidence", "verdict"),
    [
        ("qualitative_assessment", QUALITATIVE, "Insufficient Evidence"),
        ("gencc_based", GENCC, "No Known Disease Relationship"),
    ],
)
def test_half_filled_draft_saves_and_scores(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_curation: CurationNew,
    test_workflow_pair: WorkflowPair,
    engine: str,
    evidence: dict[str, object],
    verdict: str,
) -> None:
    _engine(db_session, test_workflow_pair, engine)
    for method, path in (("patch", "/draft"), ("put", "")):
        db_session.refresh(test_curation)
        response = client.request(
            method.upper(),
            f"/api/v1/curations/{test_curation.id}{path}",
            json={
                "evidence_data": evidence,
                "lock_version": test_curation.lock_version,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200, response.text
        db_session.refresh(test_curation)
        assert test_curation.computed_verdict == verdict
