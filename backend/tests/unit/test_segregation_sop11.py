"""#447: ``rule: segregation_sop11``, family/method-aware segregation scoring (SOP v11
pp.28-35, Figure 6). S1-S9 are the SOP's examples, T1-T5 the boundary cases of
.planning/waves/wave11/SEGREGATION-SPEC.md; section 8 there holds the binding decisions."""

import json
import math
from pathlib import Path
from typing import Any

import pytest

from app.scoring.clingen import ClinGenEngine
from app.scoring.point_model import score, template
from tests.unit.test_clingen_successor import successor_model

pytestmark = pytest.mark.unit

PMID = "12345678"
SEG = {
    "path": "segregation",
    "rule": "segregation_sop11",
    "assessment": "segregation_assessment",
}
MODEL = {
    "sections": [
        {
            "key": "genetic_evidence",
            "categories": [{"key": "segregation", "cap": 3, "types": [SEG]}],
        }
    ],
    "bands": [{"class": "any"}],
}
ASSERTED = {"disorder_rare_highly_penetrant": True, "phenocopies_rare": True}
EXOME, CANDIDATE = "comprehensive", "candidate_gene"


def ad(n: int, method: str = EXOME, **kw: Any) -> dict[str, Any]:
    return {
        "family_label": "Fam",
        "pmid": PMID,
        "inheritance": "AD",
        "lod_source": "estimated",
        "lod_formula": "ad_xl",
        "segregations_counted": n,
        "sequencing_method": method,
    } | kw


def ar(a: int, u: int, method: str = EXOME, **kw: Any) -> dict[str, Any]:
    return {
        "family_label": "Fam",
        "pmid": PMID,
        "inheritance": "AR",
        "lod_source": "estimated",
        "lod_formula": "ar_classic",
        "affected_count": a,
        "unaffected_count": u,
        "genotypes_complete": True,
        "sequencing_method": method,
    } | kw


def plod(lod: float, method: str = EXOME, **kw: Any) -> dict[str, Any]:
    return {
        "family_label": "Fam",
        "pmid": PMID,
        "inheritance": "AD",
        "lod_source": "published",
        "published_lod": lod,
        "sequencing_method": method,
    } | kw


def adjusted(lod: float, method: str = EXOME, **kw: Any) -> dict[str, Any]:
    return (
        ad(0, method, lod_formula="adjusted", adjusted_lod=lod, explanation="exact")
        | kw
    )


def run(
    *families: dict[str, Any], assessment: Any = ASSERTED
) -> tuple[dict[str, Any], dict[str, Any]]:
    evidence = {
        "genetic_evidence": {
            "segregation": list(families),
            "segregation_assessment": assessment,
        }
    }
    result = score(MODEL, evidence)
    applied = result["trace"].get("rules_applied", [])
    entry = next(r for r in applied if r["rule"] == "segregation_sop11")
    return result, entry


def lods(entry: dict[str, Any]) -> list[float | None]:
    return [f["lod"] for f in entry["families"]]


def statuses(entry: dict[str, Any]) -> list[str]:
    return [f["status"] for f in entry["families"]]


class TestSopExamples:
    def test_s1_pedigree_a_four_segregations(self) -> None:
        _, entry = run(ad(4))
        assert lods(entry) == [pytest.approx(4 * math.log10(2))]
        assert statuses(entry) == ["included"]
        assert entry["families"][0]["rationale"] == (
            f"Fam (PMID {PMID}): AD, eLOD 1.20 from 4 segregations, comprehensive; "
            "included"
        )

    def test_s2_x_linked_obligate_carriers_are_counted_by_the_curator(self) -> None:
        _, entry = run(ad(4, inheritance="XL"))
        assert statuses(entry) == ["included"]

    @pytest.mark.parametrize(("segregations", "lod"), [(2, 0.602), (1, 0.301)])
    def test_s3_twins_dizygotic_twice_monozygotic_once(
        self, segregations: int, lod: float
    ) -> None:
        _, entry = run(ad(segregations))
        assert lods(entry) == [pytest.approx(lod, abs=1e-3)]
        assert statuses(entry) == ["excluded"]

    def test_s4_lods_are_summed(self) -> None:
        result, entry = run(ad(4), ad(6))
        assert entry["total"] == pytest.approx(3.01, abs=1e-3)
        assert entry["band"] == "3-4.99"
        assert result["total"] == 2

    def test_s5_ar_pedigrees_b_to_e(self) -> None:
        result, entry = run(ar(3, 2), ar(3, 1), ar(3, 2), ar(1, 0))
        assert [round(x, 3) for x in lods(entry)] == [1.454, 1.329, 1.454, 0]
        assert statuses(entry) == ["included"] * 3 + ["excluded"]
        assert "needs >= 3 affected" in entry["families"][3]["rationale"]
        assert entry["total"] == pytest.approx(4.237, abs=1e-3)
        assert result["total"] == 2

    def test_s6_example_1_comprehensive_lod_3(self) -> None:
        result, entry = run(ad(10))
        assert (entry["C"], entry["D"]) == (1, 2)
        assert result["total"] == 2

    @pytest.mark.parametrize(
        "families",
        [
            [plod(1.5), plod(1.3), plod(1.5, CANDIDATE)],
            [ar(3, 2), ar(3, 1), ar(3, 2, CANDIDATE)],
        ],
    )
    def test_s7_example_2_mixed_methods(self, families: list[Any]) -> None:
        result, entry = run(*families)
        assert entry["formula_points"] == 1.7
        assert entry["comprehensive_only_points"] == 1
        assert result["total"] == 1.7
        assert statuses(entry) == ["included"] * 3

    def test_s8_lower_quality_candidate_evidence_is_omitted(self) -> None:
        result, entry = run(adjusted(3.1), ad(4, CANDIDATE))
        assert entry["formula_points"] == 1.7
        assert entry["comprehensive_only_points"] == 2
        assert result["total"] == 2
        assert statuses(entry) == ["included", "omitted_lower"]
        assert entry["families"][1]["rationale"].endswith(
            "omitted: lower-quality candidate evidence (SOP v11 p.35)"
        )
        assert entry["families"][0]["rationale"] == (
            f"Fam (PMID {PMID}): AD, eLOD 3.10 adjusted, comprehensive; included"
        )

    @pytest.mark.parametrize(("a", "u", "lod"), [(3, 1, 3), (4, 2, 5)])
    def test_s9_ar_one_parent_affected(self, a: int, u: int, lod: int) -> None:
        _, entry = run(ar(a, u, lod_formula="ar_one_parent_affected"))
        assert lods(entry) == [pytest.approx(lod * math.log10(2))]
        assert "one parent affected" in entry["families"][0]["rationale"]


class TestBoundaries:
    def test_t1_three_segregations_are_too_few(self) -> None:
        result, entry = run(ad(3, family_label="Fam 2", pmid="123"))
        assert result["total"] == 0
        assert entry["families"][0]["rationale"] == (
            "Fam 2 (PMID 123): AD, eLOD 0.90 from 3 segregations, comprehensive; "
            "excluded: AD/XL eLOD needs >= 4 segregations (SOP v11 p.28)"
        )

    @pytest.mark.parametrize(("method", "points"), [(CANDIDATE, 1), (EXOME, 2)])
    def test_t2_mixed_inheritance_sums(self, method: str, points: float) -> None:
        result, entry = run(ad(6, method), ar(3, 0, method))
        assert entry["total"] == pytest.approx(3.01, abs=1e-3)
        assert result["total"] == points

    def test_t3_rounds_half_up(self) -> None:
        result, entry = run(ad(4, CANDIDATE), ad(4))
        assert (entry["C"], entry["D"]) == (0.5, 1)
        assert entry["formula_points"] == 0.8
        assert result["total"] == 0.8

    def test_t4_maximum_is_three(self) -> None:
        result, entry = run(ad(10), plod(2.0))
        assert entry["band"] == ">=5"
        assert result["total"] == 3
        result, entry = run(ad(10), plod(2.0), ad(8))
        assert (result["total"], entry["points"], entry["max"]) == (3, 3, 3)

    def test_t5_unphased_compound_het_and_disputed_plod(self) -> None:
        result, entry = run(
            ar(4, 0, compound_het=True, in_trans_shown=False),
            plod(3.5, published_lod_disputed=True),
        )
        assert result["total"] == 0
        assert statuses(entry) == ["excluded", "excluded"]
        assert "not shown to be in trans" in entry["families"][0]["rationale"]
        assert "disputed" in entry["families"][1]["rationale"]


class TestExclusions:
    def test_unasserted_preconditions_exclude_every_elod_but_not_a_plod(self) -> None:
        for assessment in ({}, {"disorder_rare_highly_penetrant": True}, None):
            result, entry = run(ad(10), plod(3.0), assessment=assessment)
            assert statuses(entry) == ["excluded", "included"]
            assert "preconditions" in entry["families"][0]["rationale"]
            assert result["total"] == 2

    @pytest.mark.parametrize(
        ("row", "reason"),
        [
            (ad(10, unexplained_non_segregation=True), "unexplained non-segregation"),
            (plod(3, unexplained_non_segregation=True), "unexplained non-segregation"),
            (ad(10, scored=False), "Score? unchecked"),
            (ad(10, sequencing_method=None), "sequencing method"),
            (ad(10, inheritance="AR"), "needs AD or XL"),
            (ar(4, 0, inheritance="AD"), "needs AR"),
            (ar(4, 0, genotypes_complete=False), "genotypes"),
            (ar(0, 0), "affected_count"),
            (ad(10, segregations_counted=2.5), "whole number"),
            (ad(10, lod_formula="guess"), "LOD formula"),
            (ad(10, lod_source=None), "LOD source"),
            (plod(-1), "published LOD"),
            (plod("x"), "published LOD"),  # type: ignore[arg-type]
            (adjusted(3, explanation=" "), "notes"),
            (adjusted(-2), "adjusted LOD"),
        ],
    )
    def test_excluded_family_scores_nothing_and_says_why(
        self, row: dict[str, Any], reason: str
    ) -> None:
        result, entry = run(row)
        assert result["total"] == 0
        assert statuses(entry) == ["excluded"]
        assert reason in entry["families"][0]["rationale"]

    def test_uncited_family_is_excluded_and_listed(self) -> None:
        result, entry = run(ad(10, pmid=""))
        assert result["total"] == 0
        assert result["excluded"] == [
            {
                "path": "genetic_evidence.segregation[0]",
                "field": "pmid",
                "reason": "no_pmid",
            }
        ]
        assert entry["families"][0]["rationale"].startswith("Fam (no PMID): AD")

    def test_other_inheritance_takes_an_adjusted_lod_only(self) -> None:
        _, entry = run(adjusted(3.0, inheritance="other"))
        assert statuses(entry) == ["included"]
        _, entry = run(ad(10, inheritance="other"))
        assert statuses(entry) == ["excluded"]

    def test_blank_rows_are_skipped_and_no_rows_score_nothing(self) -> None:
        result, entry = run({"id": "new", "scored": True}, ad(10))
        assert [f["index"] for f in entry["families"]] == [1]
        result = score(MODEL, {"genetic_evidence": {"segregation": []}})
        assert result["total"] == 0
        assert "rules_applied" not in result["trace"]


class TestOverride:
    def test_override_with_rationale_replaces_the_computed_points(self) -> None:
        assessment = ASSERTED | {"override_points": 1, "override_rationale": "weak"}
        result, entry = run(ad(10), assessment=assessment)
        assert result["total"] == 1
        assert entry["computed_points"] == 2
        assert entry["override"] == {"points": 1, "applied": True, "rationale": "weak"}

    @pytest.mark.parametrize(
        ("assessment", "reason"),
        [
            ({"override_points": 1}, "override_rationale"),
            ({"override_points": 4, "override_rationale": "x"}, "0-3"),
        ],
    )
    def test_invalid_override_is_ignored(self, assessment: Any, reason: str) -> None:
        result, entry = run(ad(10), assessment=ASSERTED | assessment)
        assert result["total"] == 2
        assert entry["override"]["applied"] is False
        assert reason in entry["override"]["reason"]

    def test_override_raises_a_reviewer_flag(self) -> None:
        config = {"point_model": MODEL}
        evidence = {
            "genetic_evidence": {
                "segregation": [ad(10)],
                "segregation_assessment": ASSERTED
                | {"override_points": 0.5, "override_rationale": "single small study"},
            }
        }
        warnings = ClinGenEngine().calculate_scores(evidence, config).warnings
        flags = [w for w in warnings if "segregation_override" in w]
        assert flags == [
            "review_flags.segregation_override: genetic_evidence.segregation: the "
            "curator set 0.5 points instead of the computed 2 (single small study); "
            "check the override"
        ]
        evidence["genetic_evidence"]["segregation_assessment"] = ASSERTED | {
            "override_points": 1
        }
        warnings = ClinGenEngine().calculate_scores(evidence, config).warnings
        assert any("override ignored" in w for w in warnings)


BUNDLE = Path(__file__).parents[3] / "docs/schemas/clingen/clingen-methodology.json"


def bundle_model() -> dict[str, Any]:
    schemas = json.loads(BUNDLE.read_text())["schemas"]
    curation = next(s for s in schemas if s["schema_type"] == "curation")
    model: dict[str, Any] = curation["scoring_configuration"]["point_model"]
    return model


def test_bundle_scores_segregation_with_the_rule() -> None:
    evidence = {
        "genetic_evidence": {
            "segregation": [adjusted(3.1), ad(4, CANDIDATE)],
            "segregation_assessment": ASSERTED,
        }
    }
    result = ClinGenEngine().calculate_scores(
        evidence, {"engine": "clingen_sop_v11", "point_model": bundle_model()}
    )
    assert result.scores["genetic_evidence_total"] == 2


def test_old_pins_score_as_before() -> None:
    """v1 keeps its LOD fallback, the Wave 5 successor its explicit points (#447)."""
    rows = [{"pmid": PMID, "lod_score": 1.2, "points": 1.5}]
    evidence = {"genetic_evidence": {"segregation": rows}}
    v1 = ClinGenEngine().calculate_scores(
        evidence, {"point_model": template("clingen_sop_v11")}
    )
    successor = ClinGenEngine().calculate_scores(
        evidence, {"point_model": successor_model()}
    )
    assert (v1.total_score, successor.total_score) == (1.5, 1.5)
    rows[0].pop("points")
    v1 = ClinGenEngine().calculate_scores(
        evidence, {"point_model": template("clingen_sop_v11")}
    )
    assert v1.total_score == 2


def test_legacy_flat_rows_keep_explicit_points_under_the_rule() -> None:
    """A legacy flat list carries no family table: explicit points, never LOD fallbacks."""
    evidence = {
        "genetic_evidence": [
            {"evidence_category": "segregation", "pmid": PMID, "lod_score": 9}
        ]
    }
    result = ClinGenEngine().calculate_scores(evidence, {"point_model": bundle_model()})
    assert result.total_score == 0
