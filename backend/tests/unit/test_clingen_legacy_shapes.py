"""Legacy stored evidence shapes must not crash the ClinGen engine."""

from app.scoring.clingen import ClinGenEngine


def test_legacy_summary_dicts_and_stray_strings_do_not_crash():
    # Shapes found in stored data: {count, points} dicts where lists belong, bare strings.
    evidence = {
        "genetic_evidence": {
            "segregation": {"points": 2.0, "lod_score": 3.31},
            "case_level": {
                "autosomal_dominant_or_x_linked": {
                    "predicted_or_proven_null": ["junk"],
                    "other_variant_type": {"points": 0.5},
                }
            },
            "case_control": {"single_variant_analysis": ["junk"]},
        },
        "experimental_evidence": {
            "function": {
                "protein_interaction": {"count": 1, "points": 0.5},
                "biochemical_function": ["junk", {"points": 0.5}],
            },
            "models": {"non_human_model_organism": {"count": 1, "points": 0.5}},
        },
    }
    result = ClinGenEngine().calculate_scores(evidence, {})
    assert result.scores["experimental_evidence_total"] == 1.5
