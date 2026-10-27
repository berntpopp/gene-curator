"""Curations are scored by the engine their schema names, not always ClinGen (#386)."""

import pytest
from pytest import MonkeyPatch
from sqlalchemy.orm import Session

from app.crud import curation as curation_module
from app.crud.curation import _update_computed_scores, curation_crud
from app.models.models import CurationNew

pytestmark = pytest.mark.unit


@pytest.fixture
def qualitative(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        curation_module,
        "scoring_configuration",
        lambda *_args: {"engine": "qualitative_assessment"},
    )


@pytest.mark.usefixtures("qualitative")
def test_save_scores_with_the_schema_engine(
    db_session: Session, test_curation: CurationNew
) -> None:
    _update_computed_scores(db_session, test_curation)
    assert "overall_score" in test_curation.computed_scores
    assert "genetic_evidence_total" not in test_curation.computed_scores


@pytest.mark.usefixtures("qualitative")
def test_score_preview_uses_the_schema_engine(
    db_session: Session, test_curation: CurationNew
) -> None:
    result = curation_crud.calculate_score(db_session, test_curation)
    assert "clinical_assessment" in result.breakdown
    assert result.classification == "Insufficient Evidence"


def test_missing_engine_falls_back_to_clingen(
    db_session: Session, test_curation: CurationNew, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(curation_module, "scoring_configuration", lambda *_args: {})
    _update_computed_scores(db_session, test_curation)
    assert "genetic_evidence_total" in test_curation.computed_scores
