"""calculate_score must report and persist the engine's real score keys."""

import pytest
from sqlalchemy.orm import Session

from app.crud.curation import curation_crud
from app.models.models import CurationNew

pytestmark = pytest.mark.unit

_NULL = {"pmid": "12345678", "proband_counted_points": 1.5}


def test_calculate_score_reports_and_persists_genetic_score(
    db_session: Session, test_curation: CurationNew
) -> None:
    test_curation.evidence_data = {
        "genetic_evidence": {
            "case_level": {
                "autosomal_dominant_or_x_linked": {
                    "predicted_or_proven_null": [_NULL, _NULL]
                }
            }
        },
        "experimental_evidence": {},
    }

    result = curation_crud.calculate_score(db_session, test_curation)

    assert result.genetic_score == pytest.approx(3.0)
    assert test_curation.computed_scores["genetic_evidence_total"] == pytest.approx(3.0)
    assert test_curation.computed_scores["total_score"] == pytest.approx(3.0)
