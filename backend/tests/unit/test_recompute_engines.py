"""Recompute scores GenCC and qualitative curations through their own engine (#496)."""

import pytest
from sqlalchemy.orm import Session

from app.models.models import CurationNew
from app.scoring.registry import engine_for

pytestmark = pytest.mark.unit

EVIDENCE = {
    "genetic_evidence": {"case_level_data": [{"pmid": "12345678", "points": 3}]},
    "experimental_evidence": {},
}


@pytest.mark.parametrize("engine", ["gencc_based", "qualitative_assessment"])
def test_recompute_scores_non_clingen_curations_with_their_engine(
    db_session: Session,
    test_curation: CurationNew,
    test_user_admin: object,
    monkeypatch: pytest.MonkeyPatch,
    engine: str,
) -> None:
    from app.services import recompute_scores
    from tests.unit.test_point_model import _version

    summaries: list[dict] = []
    monkeypatch.setattr(
        recompute_scores.logger, "info", lambda msg, **kw: summaries.append(kw)
    )
    config = {"engine": engine}
    test_curation.methodology_version_id = _version(
        db_session, test_curation, 1, config
    ).id
    test_curation.evidence_data = EVIDENCE
    test_curation.computed_scores = {"total_score": -1.0}
    test_curation.computed_verdict = "keep"
    db_session.commit()

    recompute_scores.recompute_all_scores(db_session)
    db_session.refresh(test_curation)
    expected = engine_for(config).calculate_scores(EVIDENCE, config)
    assert test_curation.computed_verdict == expected.verdict
    assert {k: test_curation.computed_scores[k] for k in expected.scores} == (
        expected.scores
    )
    assert str(test_curation.id) not in summaries[-1]["skipped_ids"]
    assert summaries[-1]["updated"] == 1

    recompute_scores.recompute_all_scores(db_session)  # idempotent
    assert summaries[-1]["unchanged"] == 1


def test_recompute_leaves_an_adoption_unscored(
    db_session: Session, test_curation: CurationNew, test_user_admin: object
) -> None:
    """#613: ClinGen's class, never points of ours, after a recompute too."""
    from app.services import recompute_scores
    from tests.unit.test_point_model import _version

    config = {"engine": "gencc_based"}  # would score it, as the test above shows
    test_curation.methodology_version_id = _version(
        db_session, test_curation, 1, config
    ).id
    test_curation.evidence_data = EVIDENCE
    test_curation.clingen_adoption = {"cggv_id": "CGGV:assertion_x"}
    test_curation.computed_scores, test_curation.computed_verdict = {}, None
    db_session.commit()
    recompute_scores.recompute_all_scores(db_session)
    db_session.refresh(test_curation)
    assert (test_curation.computed_verdict, test_curation.computed_scores) == (None, {})
