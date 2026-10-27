"""Successor-only clinical cases; historical v1 golden expectations stay unchanged.

SOP v11 pp.17/20/21: two null=3; mixed=1.5 (GCI-rounded example); two other=0.2.
Segregation containment preserves curator assignments, not unsupported per-row LOD estimates.
"""

import copy

import pytest

from app.scoring.clingen import ClinGenEngine
from app.scoring.point_model import template
from tests.unit.test_cited_evidence import uncited_off  # noqa: F401 (fixture)

# Points arithmetic written before the citation policy (tests/unit/test_cited_evidence.py)
pytestmark = [pytest.mark.unit, pytest.mark.usefixtures("uncited_off")]


def successor_model() -> dict:
    model = copy.deepcopy(template("clingen_sop_v11"))
    assert model
    types = model["sections"][0]["categories"][0]["types"]
    for t in types:
        if "autosomal_recessive" in t["path"]:
            t["blank_at"] = None
    seg = model["sections"][0]["categories"][1]["types"][0]
    seg.update(rule="explicit_points", default=0)
    return model


def result(evidence: dict, successor: bool = True):
    config = {"point_model": successor_model()} if successor else {}
    return ClinGenEngine().calculate_scores(evidence, config)


@pytest.mark.parametrize(
    ("table", "selector", "points"),
    [
        ("predicted_or_proven_null", "two_null", 3),
        ("predicted_or_proven_null", "null_and_null", 3),
        ("other_variant_type", "null_and_other", 1.5),
        ("other_variant_type", "two_other", 0.2),
        ("other_variant_type", "homozygous_other", 0.2),
    ],
)
def test_successor_case_defaults_need_entered_evidence(table, selector, points) -> None:
    row = {
        "id": "new-row",
        "variant_type": selector,
        "score_status": "score",
        "proband_counted_points": points,
    }
    evidence = {
        "genetic_evidence": {"case_level": {"autosomal_recessive": {table: [row]}}}
    }
    assert result(evidence).total_score == 0  # untouched/selector-only/default-only row
    row["pmid"] = "12345678"
    assert result(evidence).total_score == points
    row["proband_counted_points"] = 0
    assert result(evidence).total_score == 0  # curator may intentionally downscore
    row["proband_counted_points"] = 1.6
    assert (
        result(evidence).total_score == 1.6
    )  # retain deliberate unrounded mixed score


@pytest.mark.parametrize("shape", ["nested", "legacy"])
@pytest.mark.parametrize("points", ["absent", None, "", 0, 1, 2])
def test_successor_segregation_uses_only_explicit_points(shape, points) -> None:
    row = {"lod_score": 9, "family_count": 5, "pmid": "12345678"}
    if points != "absent":
        row["points"] = points
    data = (
        {"segregation": [row]}
        if shape == "nested"
        else [{**row, "evidence_category": "segregation"}]
    )
    scored = result({"genetic_evidence": data})
    missing = points in ("absent", None, "")
    assert scored.total_score == (0 if missing else points)
    assert any("Enter segregation points" in w for w in scored.warnings) is missing


def test_successor_segregation_count_cannot_supply_points_and_category_cap_stays_three() -> (
    None
):
    assert (
        result(
            {"genetic_evidence": {"segregation": [{"segregations_counted": 3}]}}
        ).total_score
        == 0
    )
    scored = result(
        {"genetic_evidence": {"segregation": [{"points": 2}, {"points": 2}]}}
    )
    assert scored.total_score == 3


def test_v1_keeps_finite_lod_count_and_legacy_behavior() -> None:
    assert (
        result(
            {"genetic_evidence": {"segregation": [{"lod_score": 1.2}]}}, False
        ).total_score
        == 2
    )
    assert (
        result(
            {"genetic_evidence": {"segregation": [{"segregations_counted": 3}]}}, False
        ).total_score
        == 1
    )
    assert (
        result(
            {
                "genetic_evidence": [
                    {"evidence_category": "segregation", "lod_score": 9, "points": 0}
                ]
            },
            False,
        ).total_score
        == 3
    )
