"""PMID warnings of the ClinGen engine: scored rows need a PMID, blank rows stay quiet."""

import pytest

from app.scoring.clingen import ClinGenEngine, _positive

pytestmark = pytest.mark.unit


def _case_rows(*rows: dict) -> dict:
    return {
        "case_level": {
            "autosomal_dominant_or_x_linked": {
                "predicted_or_proven_null": [
                    {"score_status": "score", **r} for r in rows
                ]
            }
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
        "2 row(s) with points have no PMID and score 0",
        "1 evidence item(s) with invalid or missing PMID",
    ]


def _warnings(evidence: dict) -> list[str]:
    return ClinGenEngine().calculate_scores(evidence, {}).warnings


def test_not_counted_points_are_not_called_scored() -> None:
    """proband_not_counted_points never reach the total (#434)."""
    evidence = {
        "genetic_evidence": _case_rows(
            {"pmid": "", "proband_counted_points": 0, "proband_not_counted_points": 1},
            {"pmid": "", "proband_counted_points": 0, "proband_not_counted_points": 0},
            {"pmid": "", "proband_counted_points": 2, "proband_not_counted_points": 1},
        )
    }
    assert _warnings(evidence) == [
        "1 row(s) with points have no PMID and score 0",
        "1 row(s) with only not-counted points have no PMID",
    ]


def test_nested_experimental_rows() -> None:
    experimental = {
        "function": {"expression": [{"pmid": "", "points": 0.5}, {"pmid": ""}]},
        "rescue": {"human": [{"pmid": "abc", "points": 2}]},  # malformed
        "models": {"cell_culture_model": [{"pmid": "PMID: 123", "points": 1}]},
    }
    assert _warnings({"experimental_evidence": experimental}) == [
        "1 row(s) with points have no PMID and score 0",
        "1 evidence item(s) with invalid or missing PMID",
    ]


def test_legacy_flat_lists() -> None:
    evidence = {
        "genetic_evidence": [
            {"evidence_category": "segregation", "lod_score": 3, "points": 2},
            {"evidence_category": "case_level", "proband_count": 1, "pmid": "1" * 10},
            {"evidence_category": "case_level", "proband_count": 1, "pmid": "PMID:1"},
        ],
        "experimental_evidence": [
            {"evidence_category": "models", "proband_not_counted_points": 1},
            {"evidence_category": None, "pmid": " "},  # blank
        ],
    }
    assert _warnings(evidence) == [
        "1 row(s) with points have no PMID and score 0",
        "1 row(s) with only not-counted points have no PMID",
        "1 evidence item(s) with invalid or missing PMID",
    ]


@pytest.mark.parametrize("value", [True, "n/a", None, "-1", 0])
def test_non_positive_points_do_not_score(value: object) -> None:
    assert _positive(value) is False


SEG_WARNING = "Segregation evidence missing lod_score, points, or segregations_counted"


@pytest.mark.parametrize(
    ("row", "warns"),
    [
        ({"lod_source": "published", "published_lod": 1.5}, False),  # #447 pLOD
        ({"lod_source": "estimated", "lod_formula": "ar_classic"}, False),  # AR
        ({"lod_score": 3}, False),  # old pin with a score
        ({"family_label": "F1"}, True),  # old pin without one
    ],
)
def test_segregation_warning_only_for_rows_without_a_score(
    row: dict, warns: bool
) -> None:
    """W11 A2: rows of the #447 version carry lod_source, not the old columns."""
    evidence = {"genetic_evidence": {"segregation": [{"pmid": "9326933", **row}]}}
    assert (SEG_WARNING in _warnings(evidence)) is warns
