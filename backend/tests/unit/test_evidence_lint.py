"""Reviewer warnings by path (MCP study round 4): PMIDs in free text, a summary total that
differs from the computed one, an experimental row reusing a case row's PMID and variant."""

import pytest

from app.scoring.clingen import ClinGenEngine
from app.scoring.evidence_lint import evidence_warnings

pytestmark = pytest.mark.unit

AD = "genetic_evidence.case_level.autosomal_dominant_or_x_linked.predicted_or_proven_null"
CASE = {
    "pmid": "31558469",
    "variant": "c.100C>T (p.Arg34Ter)",
    "score_status": "score",
    "proband_counted_points": 2,
}


def _evidence(**extra: object) -> dict:
    return {
        "genetic_evidence": {
            "case_level": {
                "autosomal_dominant_or_x_linked": {"predicted_or_proven_null": [CASE]}
            }
        },
        **extra,
    }


def test_pmids_in_free_text_warn_but_ids_and_variants_do_not() -> None:
    evidence = _evidence(
        experimental_evidence={
            "function": {
                "biochemical_function": [
                    {"pmid": "12345678", "explanation": "as in PMID 23456789"},
                    {"pmid": "12345678", "explanation": "see 23456789 and 34567890"},
                    {"pmid": "12345678", "explanation": "chr6:51524409, 2019"},
                ]
            }
        },
        entity_definition={"mondo_id": "MONDO:0009889"},
    )
    at = "experimental_evidence.function.biochemical_function"
    assert [w for w in evidence_warnings(evidence, 2) if "free text" in w] == [
        f"{at}[{i}].explanation: mentions a PMID in free text; record each paper in a "
        "row's pmid field"
        for i in (0, 1)
    ]


@pytest.mark.parametrize(
    ("summary", "claimed"),
    [
        ("Strong: total score 14 points", 14),
        ("Total of 12.5 points, limited", 12.5),
        ("We count 9 points in total.", 9),
        ("Total score = 2", None),  # matches the computed total
        ("Two probands, no total given", None),
    ],
)
def test_summary_total_must_match_the_computed_total(
    summary: str, claimed: float | None
) -> None:
    warnings = [
        w
        for w in evidence_warnings(_evidence(evidence_summary=summary), 2)
        if "claims" in w
    ]
    expected = (
        [
            f"evidence_summary: claims a total of {claimed:g} points; the computed total is 2"
        ]
        if claimed is not None
        else []
    )
    assert warnings == expected


def test_experimental_row_reusing_a_patient_warns() -> None:
    reused = {"pmid": "PMID:31558469", "variant_tested": "c.100C>T (p.Arg34Ter)"}
    other = {"pmid": "31558469", "variant_tested": "c.5G>A"}
    evidence = _evidence(
        experimental_evidence={
            "functional_alteration": {"patient_cells": [other, reused]}
        }
    )
    result = ClinGenEngine().calculate_scores(evidence, {})
    assert [w for w in result.warnings if "reuses" in w] == [
        "experimental_evidence.functional_alteration.patient_cells[1]: reuses PMID "
        f"31558469 and variant c.100C>T (p.Arg34Ter) of {AD}[0]; a patient's variant is "
        "case-level evidence, not experimental"
    ]
