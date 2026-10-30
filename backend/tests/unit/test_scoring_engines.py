"""Behaviour tests for the GenCC, qualitative and base scoring engines.

Also covers the ScoringEngineRegistry. Pure unit tests: no database, no network.
"""

from typing import Any

import pytest

from app.scoring.base import ScoringEngine, ScoringResult
from app.scoring.clingen import ClinGenEngine
from app.scoring.gencc import GenCCEngine
from app.scoring.qualitative import QualitativeEngine
from app.scoring.registry import ScoringEngineRegistry, scoring_registry

pytestmark = pytest.mark.unit

VALID_PMID = "12345678"


# =============================================================================
# GenCC engine
# =============================================================================


@pytest.fixture
def gencc() -> GenCCEngine:
    return GenCCEngine()


class TestGenCCClassification:
    @pytest.mark.parametrize(
        ("total", "expected"),
        [
            (12.0, "Definitive"),
            (11.9, "Strong"),
            (7.0, "Strong"),
            (6.9, "Moderate"),
            (4.0, "Moderate"),
            (3.9, "Limited"),
            (1.0, "Limited"),
            (0.9, "No Known Disease Relationship"),
            (0.0, "No Known Disease Relationship"),
        ],
    )
    def test_thresholds(self, gencc: GenCCEngine, total: float, expected: str):
        assert gencc._determine_gencc_classification(total, []) == expected

    def test_contradictory_evidence_overrides_score(self, gencc: GenCCEngine):
        contradictory = [{"pmid": VALID_PMID}]

        assert gencc._determine_gencc_classification(18.0, contradictory) == "Disputed"

    def test_calculate_disputed_when_contradictory_present(self, gencc: GenCCEngine):
        evidence = {
            "genetic_evidence": {
                "case_level_data": [{"points": 12}],
            },
            "contradictory_evidence": [{"pmid": VALID_PMID}],
        }

        result = gencc.calculate_scores(evidence, {})

        assert result.verdict == "Disputed"
        assert "Contradictory evidence" in result.verdict_rationale


class TestGenCCScoring:
    def test_genetic_caps_applied_per_category(self, gencc: GenCCEngine):
        genetic = {
            "case_level_data": [{"points": 15}],  # cap 12
            "segregation_data": [{"points": 5}],  # cap 3
            "case_control_data": [{"points": 7}],  # cap 6
        }

        assert gencc._calculate_genetic_score(genetic) == pytest.approx(12.0)

    def test_genetic_total_capped_at_twelve(self, gencc: GenCCEngine):
        genetic = {
            "case_level_data": [{"points": 10}],
            "segregation_data": [{"points": 3}],
            "case_control_data": [{"points": 6}],
        }

        assert gencc._calculate_genetic_score(genetic) == pytest.approx(12.0)

    def test_experimental_caps_applied_per_category(self, gencc: GenCCEngine):
        experimental = {
            "function": [{"points": 3}],  # cap 2
            "models": [{"points": 5}],  # cap 4
            "rescue": [{"points": 3}],  # cap 2
        }

        assert gencc._calculate_experimental_score(experimental) == pytest.approx(6.0)

    def test_experimental_partial_sum(self, gencc: GenCCEngine):
        experimental = {"function": [{"points": 1}], "rescue": [{"points": 0.5}]}

        assert gencc._calculate_experimental_score(experimental) == pytest.approx(1.5)

    def test_calculate_end_to_end_limited(self, gencc: GenCCEngine):
        evidence = {
            "genetic_evidence": {
                "case_level_data": [{"points": 1, "pmid": VALID_PMID}],
                "segregation_data": [],
            },
            "experimental_evidence": {
                "function": [{"points": 0.5, "pmid": VALID_PMID}]
            },
        }

        result = gencc.calculate_scores(evidence, {})

        assert result.scores["genetic_evidence_score"] == pytest.approx(1.0)
        assert result.scores["experimental_evidence_score"] == pytest.approx(0.5)
        assert result.total_score == pytest.approx(1.5)
        assert result.verdict == "Limited"
        assert result.metadata["guidelines"] == "GenCC_Based"

    def test_uncited_rows_score_nothing(self, gencc: GenCCEngine):
        """Owner decision 2026-10-27: a row with points needs a PMID (GenCC has no variant)."""
        evidence = {
            "genetic_evidence": {
                "case_level_data": [
                    {"points": 2, "pmid": VALID_PMID},
                    {"points": 2},
                    {"points": 0},
                ],
            },
            "experimental_evidence": {"models": [{"points": 1, "pmid": " "}]},
        }
        result = gencc.calculate_scores(evidence, {})
        assert result.total_score == pytest.approx(2.0)
        assert result.evidence_breakdown["excluded"] == [
            {
                "path": "genetic_evidence.case_level_data[1]",
                "field": "pmid",
                "reason": "no_pmid",
            },
            {
                "path": "experimental_evidence.models[0]",
                "field": "pmid",
                "reason": "no_pmid",
            },
        ]
        clean = gencc.calculate_scores({"genetic_evidence": {}}, {})
        assert "excluded" not in clean.evidence_breakdown

    def test_breakdown_counts_items(self, gencc: GenCCEngine):
        evidence = {
            "genetic_evidence": {
                "case_level_data": [{}, {}],
                "segregation_data": [{}],
                "case_control_data": [],
            },
            "experimental_evidence": {"function": [{}], "models": [{}, {}]},
        }

        result = gencc.calculate_scores(evidence, {})
        genetic = result.evidence_breakdown["genetic_evidence"]
        experimental = result.evidence_breakdown["experimental_evidence"]

        assert genetic["case_level_items"] == 2
        assert genetic["segregation_items"] == 1
        assert genetic["case_control_items"] == 0
        assert experimental["function_items"] == 1
        assert experimental["model_items"] == 2
        assert experimental["rescue_items"] == 0

    def test_warnings_for_sparse_evidence(self, gencc: GenCCEngine):
        assert gencc._check_gencc_warnings({}) == [
            "No evidence provided for classification",
            "No case-level data provided",
            "No experimental evidence provided to support mechanism",
        ]

    def test_warning_for_single_case_level_item(self, gencc: GenCCEngine):
        evidence = {
            "genetic_evidence": {"case_level_data": [{"pmid": VALID_PMID}]},
            "experimental_evidence": {"models": [{}]},
        }

        warnings = gencc._check_gencc_warnings(evidence)

        assert warnings == ["Only one case-level evidence item (consider adding more)"]


class TestGenCCValidation:
    def test_valid_case_has_no_errors(self, gencc: GenCCEngine):
        evidence = {
            "genetic_evidence": {
                "case_level_data": [{"pmid": VALID_PMID, "points": 1.5}]
            }
        }

        assert gencc.validate_evidence(evidence, {}) == []

    def test_pmid_as_json_number_is_accepted(self, gencc: GenCCEngine):
        """Regression: an integer PMID used to raise AttributeError."""
        evidence = {
            "genetic_evidence": {"case_level_data": [{"pmid": 12345678, "points": 1}]}
        }

        assert gencc.validate_evidence(evidence, {}) == []

    @pytest.mark.parametrize("pmid", ["123", "abcdefgh", "", None])
    def test_invalid_pmid_rejected(self, gencc: GenCCEngine, pmid):
        evidence = {"genetic_evidence": {"case_level_data": [{"pmid": pmid}]}}

        errors = gencc.validate_evidence(evidence, {})

        assert errors == ["Case-level item 1: Invalid PMID format"]

    @pytest.mark.parametrize("points", [-1, 2.5, "1"])
    def test_points_out_of_range_or_wrong_type(self, gencc: GenCCEngine, points):
        evidence = {
            "genetic_evidence": {
                "case_level_data": [{"pmid": VALID_PMID, "points": points}]
            }
        }

        errors = gencc.validate_evidence(evidence, {})

        assert errors == ["Case-level item 1: Points must be 0-2"]

    def test_requires_some_evidence_category(self, gencc: GenCCEngine):
        errors = gencc.validate_evidence({}, {})

        assert errors == [
            "At least one evidence category required for GenCC classification"
        ]

    def test_supports_schema(self, gencc: GenCCEngine):
        assert gencc.supports_schema("GenCC_Gene_Disease", "1.2") is True
        assert gencc.supports_schema("ClinGen_SOP", "11.0") is False
        assert gencc.supports_schema("GenCC_Gene_Disease", "2.0") is False


# =============================================================================
# Qualitative engine
# =============================================================================


@pytest.fixture
def qualitative() -> QualitativeEngine:
    return QualitativeEngine()


class TestQualitativeScoring:
    @pytest.mark.parametrize(
        ("total", "verdict"),
        [
            (10.0, "Strong Association"),
            (8.0, "Strong Association"),
            (7.0, "Moderate Association"),
            (5.0, "Moderate Association"),
            (4.0, "Weak Association"),
            (2.0, "Weak Association"),
            (1.0, "Insufficient Evidence"),
            (0.0, "Insufficient Evidence"),
        ],
    )
    def test_combined_verdict_thresholds(
        self, qualitative: QualitativeEngine, total: float, verdict: str
    ):
        clinical = min(total, 5.0)
        literature = total - clinical

        result = qualitative._combine_assessments(clinical, literature)

        assert result["score"] == pytest.approx(total)
        assert result["verdict"] == verdict

    def test_clinical_scores_case_insensitive(self, qualitative: QualitativeEngine):
        score = qualitative._assess_clinical_evidence(
            {
                "phenotype_match": "GOOD",
                "inheritance_consistency": "Partially_Consistent",
            }
        )

        assert score == pytest.approx(3.0)

    def test_literature_scores(self, qualitative: QualitativeEngine):
        score = qualitative._assess_literature_evidence(
            {"evidence_quality": "low", "study_design_strength": "adequate"}
        )

        assert score == pytest.approx(2.0)

    def test_full_marks_end_to_end(self, qualitative: QualitativeEngine):
        evidence: dict[str, Any] = {
            "clinical_assessment": {
                "phenotype_match": "excellent",
                "inheritance_consistency": "consistent",
            },
            "literature_review": {
                "evidence_quality": "high",
                "study_design_strength": "strong",
            },
        }

        result = qualitative.calculate_scores(evidence, {})

        assert result.total_score == pytest.approx(10.0)
        assert result.verdict == "Strong Association"
        assert result.scores["overall_score"] == pytest.approx(10.0)
        assert result.evidence_breakdown["total_assessment"]["score_percentage"] == (
            pytest.approx(100.0)
        )
        assert "Clinical assessment score: 5.0/5" in result.verdict_rationale

    def test_breakdown_reports_not_assessed_defaults(
        self, qualitative: QualitativeEngine
    ):
        breakdown = qualitative._create_assessment_breakdown({}, {}, 0.0, 0.0)

        assert breakdown["clinical_assessment"]["phenotype_match"] == "Not assessed"
        assert breakdown["literature_review"]["evidence_quality"] == "Not assessed"
        assert breakdown["total_assessment"]["max_possible_score"] == 10.0

    def test_unknown_values_score_zero(self, qualitative: QualitativeEngine):
        assert qualitative._get_phenotype_score("weird") == 0.0
        assert qualitative._get_inheritance_score("weird") == 0.0
        assert qualitative._get_evidence_quality_score("weird") == 0.0
        assert qualitative._get_study_design_score("weird") == 0.0

    def test_result_is_scoring_result(self, qualitative: QualitativeEngine):
        result = qualitative.calculate_scores({}, {})

        assert isinstance(result, ScoringResult)
        assert result.verdict == "Insufficient Evidence"
        assert result.metadata["assessment_type"] == "qualitative"


class TestQualitativeValidation:
    def test_valid_values_produce_no_errors(self, qualitative: QualitativeEngine):
        evidence = {
            "clinical_assessment": {
                "phenotype_match": "fair",
                "inheritance_consistency": "inconsistent",
            },
            "literature_review": {
                "evidence_quality": "moderate",
                "study_design_strength": "weak",
            },
        }

        assert qualitative.validate_evidence(evidence, {}) == []

    def test_invalid_values_reported(self, qualitative: QualitativeEngine):
        evidence = {
            "clinical_assessment": {
                "phenotype_match": "great",
                "inheritance_consistency": "maybe",
            },
            "literature_review": {
                "evidence_quality": "superb",
                "study_design_strength": "robust",
            },
        }

        errors = qualitative.validate_evidence(evidence, {})

        assert errors == [
            "Invalid phenotype match value: great",
            "Invalid inheritance consistency value: maybe",
            "Invalid evidence quality value: superb",
            "Invalid study design strength value: robust",
        ]

    def test_requires_at_least_one_assessment(self, qualitative: QualitativeEngine):
        assert qualitative.validate_evidence({}, {}) == [
            "At least one assessment category (clinical or literature) is required"
        ]

    def test_supports_schema(self, qualitative: QualitativeEngine):
        assert qualitative.supports_schema("Qualitative_Institutional", "1.0")
        assert not qualitative.supports_schema("ClinGen_SOP", "11.0")


# =============================================================================
# Base class defaults and registry
# =============================================================================


class _StubEngine(ScoringEngine):
    """Minimal engine that only implements the abstract members."""

    def __init__(self, engine_name: str = "stub_engine") -> None:
        self._name = engine_name

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return "0.1.0"

    def calculate_scores(self, evidence_data, schema_config, scope_context=None):
        return ScoringResult(
            scores={"x": 1.0},
            total_score=1.0,
            verdict="stub",
            verdict_rationale="stub",
            evidence_breakdown={},
        )

    def validate_evidence(self, evidence_data, schema_config):
        return [] if evidence_data else ["empty"]


class TestBaseDefaults:
    def test_defaults_are_permissive(self):
        engine = _StubEngine()

        assert engine.supports_schema("anything", "0") is True
        assert engine.get_supported_verdicts() == []
        assert engine.get_scoring_categories() == []


class TestRegistry:
    def test_default_engines_registered(self):
        names = scoring_registry.get_engine_names()

        assert {"clingen_sop_v11", "gencc_based", "qualitative_assessment"} <= set(
            names
        )

    def test_register_replaces_same_name(self):
        registry = ScoringEngineRegistry()
        replacement = _StubEngine("clingen_sop_v11")

        registry.register(replacement)

        assert registry.get_engine("clingen_sop_v11") is replacement

    def test_list_engines_metadata(self):
        listing = {e["name"]: e for e in scoring_registry.list_engines()}

        clingen = listing["clingen_sop_v11"]
        assert clingen["version"] == "11.0.0"
        assert "definitive" in clingen["supported_verdicts"]
        assert clingen["scoring_categories"] == [
            "genetic_evidence",
            "experimental_evidence",
        ]

    def test_clingen_verdicts_come_from_the_schema_point_model(self):
        engine = ClinGenEngine()
        model = {
            "overrides": [{"when": "x", "class": "refuted"}],
            "bands": [
                {"class": "established_risk", "min": 7},
                {"class": "uncertain_risk", "min": 0},
                {"class": "refuted"},
            ],
        }

        assert engine.get_supported_verdicts({"point_model": model}) == [
            "established_risk",
            "uncertain_risk",
            "refuted",
        ]
        assert engine.get_supported_verdicts() == engine.get_supported_verdicts({})
        assert "definitive" in engine.get_supported_verdicts()
        config = {"point_model": model}
        info = scoring_registry.get_engine_info("gencc_based", config)
        assert info is not None
        assert info["supported_verdicts"] == GenCCEngine().get_supported_verdicts()

    def test_engine_info_includes_docstring(self):
        info = scoring_registry.get_engine_info("clingen_sop_v11")

        assert info is not None
        assert info["name"] == "clingen_sop_v11"
        assert info["description"].startswith("ClinGenEngine - ")

    def test_engine_info_description_prefixes_class_name(self):
        registry = ScoringEngineRegistry()
        registry.register(_StubEngine("stub"))

        info = registry.get_engine_info("stub")

        assert info is not None
        assert info["description"].startswith("_StubEngine - ")

    def test_unknown_engine_behaviour(self):
        registry = ScoringEngineRegistry()

        assert registry.get_engine("nope") is None
        assert registry.get_engine_info("nope") is None
        assert registry.calculate_scores("nope", {}, {}) is None
        assert registry.validate_evidence("nope", {}, {}) == [
            "Unknown scoring engine: nope"
        ]
        assert registry.get_supported_verdicts("nope") == []
        assert registry.get_scoring_categories("nope") == []
        assert registry.supports_schema("nope", "ClinGen_SOP", "11.0") is False

    def test_calculate_and_validate_delegate(self):
        evidence = {
            "clinical_assessment": {"phenotype_match": "good"},
        }

        result = scoring_registry.calculate_scores(
            "qualitative_assessment", evidence, {}
        )
        errors = scoring_registry.validate_evidence(
            "qualitative_assessment", evidence, {}
        )

        assert result is not None
        assert result.total_score == pytest.approx(2.0)
        assert errors == []

    def test_find_engines_for_schema(self):
        assert scoring_registry.find_engines_for_schema("ClinGen_SOP_11.0", "11.0") == [
            "clingen_sop_v11"
        ]
        assert scoring_registry.find_engines_for_schema(
            "Qualitative_Institutional", "1.0"
        ) == ["qualitative_assessment"]
        assert scoring_registry.find_engines_for_schema("Unknown", "1") == []

    def test_supports_schema_for_known_engine(self):
        assert scoring_registry.supports_schema(
            "gencc_based", "GenCC_Gene_Disease", "1.0"
        )
        assert not scoring_registry.supports_schema(
            "gencc_based", "ClinGen_SOP_11.0", "11.0"
        )
