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


def _result(total: float, genetic: float = 0) -> dict:
    return {"total": total, "sections": {"genetic_evidence": genetic}}


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
                    {"pmid": "12345678", "explanation": "as in PMID: 23456789"},
                    {"pmid": "12345678", "explanation": "also PMID12345678"},
                    {"pmid": "12345678", "explanation": "pubmed 1234567"},
                    {
                        "pmid": "1",
                        "explanation": "https://pubmed.ncbi.nlm.nih.gov/2345/",
                    },
                    {"pmid": "12345678", "explanation": "see 23456789 and 34567890"},
                    {"pmid": "12345678", "explanation": "chr6:51524409, 2019"},
                    {"pmid": "12345678", "explanation": "seen 20190101"},
                    {"pmid": "12345678", "explanation": "no PMID available"},
                    {"pmid": "12345678", "explanation": "position 51524409 on chr6"},
                ]
            }
        },
        entity_definition={"mondo_id": "MONDO:0009889"},
        evidence_summary="Strong (PMID: 23456789, PMID: 34567890)",
    )
    at = "experimental_evidence.function.biochemical_function"
    assert [w for w in evidence_warnings(evidence, _result(2)) if "free text" in w] == [
        f"{at}[{i}].explanation: mentions a PMID in free text; record each paper in a "
        "row's pmid field"
        for i in (0, 1, 2, 3)
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
        for w in evidence_warnings(_evidence(evidence_summary=summary), _result(2))
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


@pytest.mark.parametrize(
    ("genetic", "replicated", "hint"),
    [(12, None, True), (12, False, True), (12, True, False), (11.9, None, False)],
)
def test_definitive_hint_once_genetic_evidence_reaches_twelve(
    genetic: float, replicated: bool | None, hint: bool
) -> None:
    evidence = _evidence() | (
        {} if replicated is None else {"replicated_over_time": replicated}
    )
    warnings = evidence_warnings(evidence, _result(genetic, genetic))
    assert (
        any(
            w.startswith("replicated_over_time: genetic evidence reaches 12")
            for w in warnings
        )
        is hint
    )


def test_engine_shows_the_definitive_hint() -> None:
    rows = [
        {**CASE, "proband_counted_points": 3, "pmid": str(10**7 + i)} for i in range(4)
    ]
    evidence = {
        "genetic_evidence": {
            "case_level": {
                "autosomal_dominant_or_x_linked": {"predicted_or_proven_null": rows}
            }
        }
    }
    result = ClinGenEngine().calculate_scores(evidence, {})
    assert result.verdict == "strong"
    assert any(w.startswith("replicated_over_time:") for w in result.warnings)


def test_model_row_describing_a_patient_warns() -> None:
    evidence = _evidence(
        experimental_evidence={
            "models": {
                "cell_culture_model": [
                    {"pmid": "2", "description": "iPSC line from the Proband II-1"},
                    {"pmid": "2", "description": "HEK293 knockout"},
                ]
            },
            "functional_alteration": {
                "patient_cells": [{"pmid": "2", "cell_type": "patient fibroblasts"}]
            },
            "rescue": {"cell_culture": [{"pmid": "2", "explanation": "two families"}]},
        }
    )
    assert [
        w for w in evidence_warnings(evidence, _result(2)) if "mentions '" in w
    ] == [
        "experimental_evidence.models.cell_culture_model[0]: mentions 'proband'; a "
        "described patient is case-level evidence (or patient_cells), not a model or "
        "experimental row",
        "experimental_evidence.rescue.cell_culture[0]: mentions 'families'; a described "
        "patient is case-level evidence (or patient_cells), not a model or experimental row",
    ]
