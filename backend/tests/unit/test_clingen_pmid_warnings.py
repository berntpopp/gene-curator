"""PMID warnings of the ClinGen engine: scored rows need a PMID, blank rows stay quiet."""

import pytest

from app.scoring.clingen import ClinGenEngine, _positive

pytestmark = pytest.mark.unit


def _case_rows(*rows: dict) -> dict:
    return {
        "case_level": {
            "autosomal_dominant_or_x_linked": {"predicted_or_proven_null": list(rows)}
        }
    }


def test_rows_without_pmid_warn_when_scored_or_filled() -> None:
    evidence = {
        "genetic_evidence": _case_rows(
            {"id": "r0", "pmid": "", "proband_counted_points": 0, "notes": None},
            {"id": "r1", "pmid": "", "proband_counted_points": 1.5},  # preset, scores
            {"id": "r2", "pmid": None, "proband_counted_points": "2"},
            {"id": "r3", "pmid": None, "proband_label": "Proband 1"},
        )
    }

    assert ClinGenEngine().calculate_scores(evidence, {}).warnings == [
        "2 scored row(s) have no PMID",
        "1 evidence item(s) with invalid or missing PMID",
    ]


@pytest.mark.parametrize("value", [True, "n/a", None, "-1", 0])
def test_non_positive_points_do_not_score(value: object) -> None:
    assert _positive(value) is False
