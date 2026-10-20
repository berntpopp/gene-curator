"""Behaviour tests for the ClinGen SOP v11 scoring engine.

Covers point caps per category, classification thresholds (including boundary
values), the nested SOP v11 and legacy flat-list input formats, warnings and
validation. Pure unit tests: no database, no network.
"""

import math

import pytest

from app.scoring.clingen import ClinGenEngine

pytestmark = pytest.mark.unit

VALID_PMID = "12345678"


@pytest.fixture
def engine() -> ClinGenEngine:
    return ClinGenEngine()


def _nested_case_level(null_items=(), other_items=()):
    return {
        "case_level": {
            "autosomal_dominant_or_x_linked": {
                "predicted_or_proven_null": list(null_items),
                "other_variant_type": list(other_items),
            },
            "autosomal_recessive": {
                "predicted_or_proven_null": [],
                "other_variant_type": [],
            },
        }
    }


def _null_item(points: float = 1.5, pmid: str = VALID_PMID) -> dict:
    return {"pmid": pmid, "proband_counted_points": points}


# =============================================================================
# Classification thresholds
# =============================================================================


class TestClassification:
    @pytest.mark.parametrize(
        ("total", "expected"),
        [
            (18.0, "definitive"),
            (12.0, "definitive"),
            (11.99, "strong"),
            (7.0, "strong"),
            (6.99, "moderate"),
            (2.0, "moderate"),
            (1.99, "limited"),
            (0.1, "limited"),
            (0.09, "no_known"),
            (0.0, "no_known"),
            (-0.5, "disputed"),
            (-1.0, "disputed"),
            (-1.01, "refuted"),
            (-2.0, "refuted"),
        ],
    )
    def test_classify_boundaries(
        self, engine: ClinGenEngine, total: float, expected: str
    ):
        assert engine._classify(total) == expected

    def test_empty_evidence_is_no_known(self, engine: ClinGenEngine):
        result = engine.calculate_scores({}, {})

        assert result.total_score == 0.0
        assert result.verdict == "no_known"
        assert "No genetic evidence provided" in " ".join(result.warnings)

    def test_rationale_names_classification(self, engine: ClinGenEngine):
        rationale = engine._generate_rationale(12.0, 6.0, 18.0, "definitive")

        assert "total score = 18.0 points" in rationale
        assert "DEFINITIVE" in rationale

    def test_metadata_reports_sop_version(self, engine: ClinGenEngine):
        result = engine.calculate_scores({}, {}, {"scope": "x"})

        assert result.metadata["sop_version"] == "v11"
        assert result.metadata["engine_version"] == "11.0.0"
        assert result.metadata["scope_context"] == {"scope": "x"}


# =============================================================================
# Nested SOP v11 format - genetic evidence
# =============================================================================


class TestNestedGeneticEvidence:
    def test_exact_scores_for_representative_set(self, engine: ClinGenEngine):
        evidence = {
            "genetic_evidence": {
                "case_level": {
                    "autosomal_dominant_or_x_linked": {
                        "predicted_or_proven_null": [_null_item(1.5), _null_item(1.5)],
                        "other_variant_type": [_null_item(0.1)],
                    },
                },
            },
            "experimental_evidence": {},
        }

        result = engine.calculate_scores(evidence, {})

        assert result.scores["genetic_evidence_total"] == pytest.approx(3.1)
        assert result.scores["experimental_evidence_total"] == 0.0
        assert result.verdict == "moderate"

    def test_case_level_null_default_points(self, engine: ClinGenEngine):
        score, _ = engine._calculate_genetic_evidence(
            _nested_case_level(null_items=[{"pmid": VALID_PMID}])
        )

        assert score == pytest.approx(1.5)

    def test_case_level_capped_at_twelve(self, engine: ClinGenEngine):
        items = [_null_item(1.5) for _ in range(10)]  # 15 raw points

        score, details = engine._calculate_genetic_evidence(
            _nested_case_level(null_items=items)
        )

        assert score == pytest.approx(12.0)
        assert details["case_level_details"]["total"] == pytest.approx(12.0)

    def test_segregation_points_capped_at_three(self, engine: ClinGenEngine):
        evidence = {
            "segregation": [{"points": 2}, {"points": 2}],
        }

        score, details = engine._calculate_genetic_evidence(evidence)

        assert score == pytest.approx(3.0)
        assert details["segregation_score"] == pytest.approx(3.0)

    @pytest.mark.parametrize(
        ("lod", "points"),
        [
            (0.59, 0.0),
            (0.6, 1.0),
            (1.19, 1.0),
            (1.2, 2.0),
            (2.39, 2.0),
            (2.4, 3.0),
            (5.0, 3.0),
        ],
    )
    def test_sop11_lod_to_points_boundaries(
        self, engine: ClinGenEngine, lod: float, points: float
    ):
        assert engine._lod_to_points_sop11(lod) == points

    def test_segregation_lod_score_converted(self, engine: ClinGenEngine):
        assert engine._score_segregation_nested({"lod_score": 1.5}) == 2.0

    def test_segregation_counted_fallback(self, engine: ClinGenEngine):
        # 3 segregations -> LOD = 3 * log10(2) ~= 0.903 -> 1 point
        assert engine._score_segregation_nested({"segregations_counted": 3}) == 1.0
        assert engine._score_segregation_nested({"segregations_counted": 0}) == 0.0
        assert engine._score_segregation_nested({}) == 0.0

    def test_case_control_takes_max_of_single_and_aggregate(
        self, engine: ClinGenEngine
    ):
        evidence = {
            "case_control": {
                "single_variant_analysis": [{"points": 2.0}, {"points": 2.0}],
                "aggregate_variant_analysis": [{"points": 3.0}],
            }
        }

        score, details = engine._calculate_genetic_evidence(evidence)

        assert score == pytest.approx(4.0)  # max(4, 3), not the sum
        assert details["case_control_details"]["total"] == pytest.approx(4.0)

    def test_case_control_capped_at_six(self, engine: ClinGenEngine):
        evidence = {"case_control": {"single_variant_analysis": [{"points": 7.0}]}}

        score, _ = engine._calculate_genetic_evidence(evidence)

        assert score == pytest.approx(6.0)

    def test_genetic_total_capped_at_twelve(self, engine: ClinGenEngine):
        evidence = {
            "case_level": {
                "autosomal_dominant_or_x_linked": {
                    "predicted_or_proven_null": [_null_item(1.5) for _ in range(10)],
                },
            },
            "segregation": [{"points": 3}],
            "case_control": {"single_variant_analysis": [{"points": 6}]},
        }

        score, _ = engine._calculate_genetic_evidence(evidence)

        assert score == pytest.approx(12.0)  # 12 + 3 + 6 = 21, capped


# =============================================================================
# Nested SOP v11 format - experimental evidence
# =============================================================================


class TestNestedExperimentalEvidence:
    def test_category_caps_and_total_cap(self, engine: ClinGenEngine):
        evidence = {
            "function": {
                "biochemical_function": [{"points": 1.5}],
                "protein_interaction": [{"points": 1.0}],
                "expression": [{"points": 0.5}],
            },  # 3.0 -> cap 2
            "functional_alteration": {
                "patient_cells": [{}, {}],  # default 1.0 each
                "non_patient_cells": [{"points": 0.5}],
            },  # 2.5 -> cap 2
            "models": {
                "non_human_model_organism": [{}],  # default 2.0
                "cell_culture_model": [{"points": 3.0}],
            },  # 5.0 -> cap 4
            "rescue": {
                "human": [{}],  # 2.0
                "non_human_model_organism": [{}],  # 2.0
                "cell_culture": [{}],  # 1.0
                "patient_cells": [{}],  # 1.0
            },  # 6.0 -> cap 4
        }

        total, details = engine._calculate_experimental_evidence(evidence)

        assert details["function_score"] == pytest.approx(2.0)
        assert details["functional_alteration_score"] == pytest.approx(2.0)
        assert details["models_score"] == pytest.approx(4.0)
        assert details["rescue_score"] == pytest.approx(4.0)
        assert total == pytest.approx(6.0)  # 12 raw, capped at 6

    def test_experimental_total_below_cap_is_summed(self, engine: ClinGenEngine):
        evidence = {"function": {"biochemical_function": [{"points": 1.0}]}}

        total, _ = engine._calculate_experimental_evidence(evidence)

        assert total == pytest.approx(1.0)


# =============================================================================
# Nested format end-to-end
# =============================================================================


class TestNestedEndToEnd:
    def test_nested_evidence_scores_without_error(self, engine: ClinGenEngine):
        """Regression: nested SOP v11 genetic evidence used to raise AttributeError."""
        evidence = {
            "genetic_evidence": _nested_case_level(
                null_items=[_null_item(1.5), _null_item(1.5)]
            ),
            "experimental_evidence": {
                "function": {"biochemical_function": [{"points": 1.0, "pmid": "x"}]},
            },
        }

        result = engine.calculate_scores(evidence, {})

        assert result.total_score == pytest.approx(4.0)
        assert result.verdict == "moderate"
        assert result.scores["genetic_evidence_total"] == pytest.approx(3.0)
        assert result.scores["experimental_evidence_total"] == pytest.approx(1.0)

    def test_nested_warnings_count_invalid_pmids(self, engine: ClinGenEngine):
        evidence = {
            "genetic_evidence": _nested_case_level(
                null_items=[_null_item(pmid="123"), _null_item(pmid=VALID_PMID)]
            ),
            "experimental_evidence": {},
        }

        result = engine.calculate_scores(evidence, {})

        assert "1 evidence item(s) with invalid or missing PMID" in result.warnings
        assert any("No experimental evidence" in w for w in result.warnings)

    def test_nested_case_level_warning_when_fewer_than_two(self, engine: ClinGenEngine):
        evidence = {
            "genetic_evidence": _nested_case_level(null_items=[_null_item()]),
            "experimental_evidence": {},
        }

        result = engine.calculate_scores(evidence, {})

        assert (
            "Only 1 case-level evidence item(s) - consider adding more for stronger support"
            in result.warnings
        )

    def test_nested_segregation_missing_score_warning(self, engine: ClinGenEngine):
        evidence = {
            "genetic_evidence": {"segregation": [{"pmid": VALID_PMID}]},
            "experimental_evidence": {},
        }

        result = engine.calculate_scores(evidence, {})

        assert any("Segregation evidence missing" in w for w in result.warnings)


# =============================================================================
# Legacy flat-list format
# =============================================================================


class TestLegacyFormat:
    def test_case_level_bonuses_exact(self, engine: ClinGenEngine):
        # predicted_null 2 probands: 3.0 base + 1.0 de novo + 0.8 functional
        item = {
            "evidence_category": "case_level",
            "variant_type": "predicted_null",
            "proband_count": 2,
            "de_novo": True,
            "functional_alteration": True,
        }

        assert engine._score_case_level(item) == pytest.approx(4.8)

    @pytest.mark.parametrize(
        ("variant_type", "de_novo", "expected"),
        [
            ("missense", False, 0.3),
            ("missense", True, 0.3 + 0.4 * 3),
            ("other", True, 1.5),  # de novo bonus only for null/missense
            ("PREDICTED_NULL", False, 4.5),  # case-insensitive
        ],
    )
    def test_case_level_variant_types(
        self, engine: ClinGenEngine, variant_type, de_novo, expected
    ):
        item = {
            "variant_type": variant_type,
            "proband_count": 3,
            "de_novo": de_novo,
        }

        assert engine._score_case_level(item) == pytest.approx(expected)

    def test_case_level_negative_proband_count_clamped(self, engine: ClinGenEngine):
        assert (
            engine._score_case_level(
                {"variant_type": "predicted_null", "proband_count": -4}
            )
            == 0.0
        )

    def test_legacy_case_level_capped_at_twelve(self, engine: ClinGenEngine):
        evidence = [
            {
                "evidence_category": "case_level",
                "variant_type": "predicted_null",
                "proband_count": 1,
            }
            for _ in range(10)
        ]

        score, details = engine._calculate_genetic_evidence(evidence)

        assert score == pytest.approx(12.0)
        assert details["case_level_score"] == pytest.approx(12.0)

    @pytest.mark.parametrize(
        ("lod", "points"),
        [
            (2.9, 0.0),
            (3.0, 1.0),
            (4.99, 1.0),
            (5.0, 2.0),
            (6.99, 2.0),
            (7.0, 2.0),  # continuous with the 5-7 band
            (9.0, 3.0),
            (17.0, 7.0),  # 2 + (17 - 7) * 0.5
            (100.0, 7.0),  # capped
        ],
    )
    def test_legacy_lod_to_points(self, engine: ClinGenEngine, lod, points):
        assert engine._lod_to_points(lod, "autosomal_dominant") == pytest.approx(points)

    def test_dominant_lod_from_family_count(self, engine: ClinGenEngine):
        assert engine._calculate_dominant_lod(0) == 0.0
        assert engine._calculate_dominant_lod(1) == pytest.approx(3 * math.log10(2))

    def test_recessive_lod_from_family_count(self, engine: ClinGenEngine):
        assert engine._calculate_recessive_lod(0) == 0.0
        assert engine._calculate_recessive_lod(5) == pytest.approx(10 * math.log10(2))

    def test_segregation_from_family_count(self, engine: ClinGenEngine):
        # 1 dominant family -> LOD 0.90 -> 0 points
        assert (
            engine._score_segregation(
                {"family_count": 1, "inheritance_pattern": "autosomal_dominant"}
            )
            == 0.0
        )
        # 5 recessive families -> LOD 3.01 -> 1 point
        assert (
            engine._score_segregation(
                {"family_count": 5, "inheritance_pattern": "autosomal_recessive"}
            )
            == 1.0
        )

    def test_segregation_unknown_inheritance_scores_zero(self, engine: ClinGenEngine):
        assert (
            engine._score_segregation(
                {"family_count": 50, "inheritance_pattern": "mitochondrial"}
            )
            == 0.0
        )

    def test_segregation_explicit_lod_used_directly(self, engine: ClinGenEngine):
        assert engine._score_segregation({"lod_score": 5.5}) == 2.0

    def test_legacy_segregation_capped_at_three(self, engine: ClinGenEngine):
        evidence = [
            {"evidence_category": "segregation", "lod_score": 9.0},
            {"evidence_category": "segregation", "lod_score": 9.0},
        ]

        score, _ = engine._calculate_genetic_evidence(evidence)

        assert score == pytest.approx(3.0)

    def test_legacy_experimental_caps(self, engine: ClinGenEngine):
        items = [
            {"evidence_category": "expression", "model_system": "cell", "points": 1.5},
            {"evidence_category": "expression", "model_system": "cell", "points": 1.5},
            {"evidence_category": "models", "model_system": "patient_cells"},  # 4.0
            {
                "evidence_category": "rescue",
                "model_system": "human",
                "rescue_observed": True,
            },  # 2.0
        ]

        total, details = engine._calculate_experimental_evidence(items)

        assert details["function_score"] == pytest.approx(2.0)  # 3.0 capped
        assert details["models_score"] == pytest.approx(4.0)
        assert details["rescue_score"] == pytest.approx(2.0)
        assert total == pytest.approx(6.0)  # 8.0 capped

    def test_legacy_rescue_default_zero_without_observation(
        self, engine: ClinGenEngine
    ):
        items = [{"evidence_category": "rescue", "model_system": "human"}]

        total, _ = engine._calculate_experimental_evidence(items)

        assert total == 0.0

    def test_legacy_end_to_end_verdict(self, engine: ClinGenEngine):
        evidence = {
            "genetic_evidence": [
                {
                    "evidence_category": "case_level",
                    "variant_type": "predicted_null",
                    "proband_count": 4,
                    "de_novo": True,
                    "pmid": VALID_PMID,
                },
                {
                    "evidence_category": "case_level",
                    "variant_type": "predicted_null",
                    "proband_count": 2,
                    "pmid": VALID_PMID,
                },
                {
                    "evidence_category": "segregation",
                    "lod_score": 6.0,
                    "pmid": VALID_PMID,
                },
            ],
            "experimental_evidence": [],
        }

        result = engine.calculate_scores(evidence, {})

        # case-level: 4*2.0 + 2*1.5 = 11.0; segregation LOD 6.0 -> 2.0 points;
        # raw 13.0 is capped at 12
        assert result.scores["genetic_evidence_total"] == pytest.approx(12.0)
        assert result.verdict == "definitive"
        assert result.total_score == pytest.approx(12.0)


# =============================================================================
# Validation
# =============================================================================


class TestValidateEvidence:
    def test_missing_genetic_evidence_is_error(self, engine: ClinGenEngine):
        errors = engine.validate_evidence({"genetic_evidence": []}, {})

        assert "At least one genetic evidence item is required" in errors

    def test_legacy_item_missing_category(self, engine: ClinGenEngine):
        errors = engine.validate_evidence(
            {"genetic_evidence": [{"pmid": VALID_PMID}]}, {}
        )

        assert errors == ["Genetic evidence item 1: Missing evidence_category"]

    def test_case_level_required_fields_and_variant_type(self, engine: ClinGenEngine):
        errors = engine.validate_evidence(
            {"genetic_evidence": [{"evidence_category": "case_level"}]}, {}
        )

        assert "Case-level evidence 1: Missing proband_count" in errors
        assert "Case-level evidence 1: Missing variant_type" in errors

    def test_case_level_invalid_variant_type(self, engine: ClinGenEngine):
        errors = engine.validate_evidence(
            {
                "genetic_evidence": [
                    {
                        "evidence_category": "case_level",
                        "proband_count": 1,
                        "variant_type": "frameshift",
                    }
                ]
            },
            {},
        )

        assert any("Invalid variant_type" in e for e in errors)

    def test_segregation_requires_lod_or_family_count(self, engine: ClinGenEngine):
        errors = engine.validate_evidence(
            {
                "genetic_evidence": [
                    {"evidence_category": "segregation", "inheritance_pattern": "x"}
                ]
            },
            {},
        )

        assert any("Must provide either lod_score or family_count" in e for e in errors)

    def test_segregation_requires_inheritance_pattern(self, engine: ClinGenEngine):
        errors = engine.validate_evidence(
            {
                "genetic_evidence": [
                    {"evidence_category": "segregation", "lod_score": 3.0}
                ]
            },
            {},
        )

        assert "Segregation evidence 1: Missing inheritance_pattern" in errors

    def test_case_control_requires_computed_score(self, engine: ClinGenEngine):
        errors = engine.validate_evidence(
            {"genetic_evidence": [{"evidence_category": "case_control"}]}, {}
        )

        assert "Case-control evidence 1: Missing computed_score" in errors

    def test_legacy_experimental_validation(self, engine: ClinGenEngine):
        errors = engine.validate_evidence(
            {
                "genetic_evidence": [
                    {
                        "evidence_category": "case_level",
                        "proband_count": 1,
                        "variant_type": "missense",
                    }
                ],
                "experimental_evidence": [
                    {"evidence_category": "bogus"},
                    {"evidence_category": "models"},
                    {"evidence_category": "rescue", "model_system": "cell"},
                    {"model_system": "cell"},
                ],
            },
            {},
        )

        assert any("Invalid category" in e for e in errors)
        assert "Experimental evidence 2: Missing model_system" in errors
        assert "Rescue evidence 3: Missing rescue_observed field" in errors
        assert "Experimental evidence item 4: Missing evidence_category" in errors

    def test_nested_experimental_requires_pmid_points_rationale(
        self, engine: ClinGenEngine
    ):
        errors = engine.validate_evidence(
            {
                "genetic_evidence": [
                    {
                        "evidence_category": "case_level",
                        "proband_count": 1,
                        "variant_type": "missense",
                    }
                ],
                "experimental_evidence": {
                    "function": {"biochemical_function": [{}]},
                },
            },
            {},
        )

        assert "function.biochemical_function[0]: Missing PMID" in errors
        assert "function.biochemical_function[0]: Missing points value" in errors
        assert "function.biochemical_function[0]: Missing rationale" in errors

    def test_valid_nested_experimental_has_no_errors(self, engine: ClinGenEngine):
        errors = engine.validate_evidence(
            {
                "genetic_evidence": [
                    {
                        "evidence_category": "case_level",
                        "proband_count": 1,
                        "variant_type": "missense",
                    }
                ],
                "experimental_evidence": {
                    "models": {
                        "cell_culture_model": [
                            {"pmid": VALID_PMID, "points": 1.0, "rationale": "ok"}
                        ]
                    }
                },
            },
            {},
        )

        assert errors == []


def test_supports_schema_only_sop_v11(engine: ClinGenEngine):
    assert engine.supports_schema("ClinGen_SOP_11.0", "11.0") is True
    assert engine.supports_schema("ClinGen_SOP_10", "10.0") is False
    assert engine.supports_schema("GenCC", "1.0") is False
