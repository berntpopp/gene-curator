"""Definitive (replication over time), contradictory evidence and rationale ranges."""

import pytest

from app.scoring.clingen import ClinGenEngine
from app.scoring.point_model import classify, template

pytestmark = pytest.mark.unit


@pytest.fixture
def engine() -> ClinGenEngine:
    return ClinGenEngine()


def _classify(total: float, **evidence: object) -> str:
    return str(classify(template("clingen_sop_v11"), total, evidence)["class"])


class TestDefinitiveAndContradictory:
    def test_definitive_needs_strong_points_and_replication(self):
        assert _classify(12.0, replicated_over_time=True) == "definitive"
        assert _classify(18.0, replicated_over_time=True) == "definitive"
        assert _classify(12.0, replicated_over_time="true") == "strong"
        assert _classify(12.0) == "strong"
        assert _classify(11.99, replicated_over_time=True) == "moderate"

    def test_contradictory_evidence_is_disputed(self):
        contradictory = [{"pmid": "1", "impact": "disputed"}]
        assert _classify(18.0, contradictory_evidence=contradictory) == "disputed"
        assert (
            _classify(
                18.0, contradictory_evidence=contradictory, replicated_over_time=True
            )
            == "disputed"
        )

    def test_calculate_scores_reads_flags(self, engine: ClinGenEngine):
        null = {"pmid": "12345678", "proband_counted_points": 3.0}
        case = {
            "autosomal_dominant_or_x_linked": {"predicted_or_proven_null": [null] * 4}
        }
        base = {"genetic_evidence": {"case_level": case}, "experimental_evidence": {}}
        assert engine.calculate_scores(base, {}).verdict == "strong"
        rep = {**base, "replicated_over_time": True}
        assert engine.calculate_scores(rep, {}).verdict == "definitive"
        dis = {**rep, "contradictory_evidence": [{"pmid": "1", "impact": "disputed"}]}
        assert engine.calculate_scores(dis, {}).verdict == "disputed"

    def test_empty_contradictory_row_does_not_dispute(self, engine: ClinGenEngine):
        null = {"pmid": "12345678", "proband_counted_points": 3.0}
        case = {
            "autosomal_dominant_or_x_linked": {"predicted_or_proven_null": [null] * 4}
        }
        base = {"genetic_evidence": {"case_level": case}, "experimental_evidence": {}}
        blank = {"pmid": "", "description": "  ", "tags": [], "note": None}
        fresh = {
            "label": "",
            "pmid": "",
            "evidence_type": "population",
            "description": "",
            "impact": "note",
            "explanation": "",
        }
        for rows in ([blank], [{}], [blank, {}], [fresh]):
            ev = {**base, "contradictory_evidence": rows}
            assert engine.calculate_scores(ev, {}).verdict == "strong"
        ev = {**base, "contradictory_evidence": [blank, {"impact": "disputed"}]}
        assert engine.calculate_scores(ev, {}).verdict == "disputed"

    def test_rationale_uses_sop_v11_ranges(self, engine: ClinGenEngine):
        evidence = {"genetic_evidence": {"segregation": [{"points": 1}]}}
        text = engine.calculate_scores(evidence, {}).verdict_rationale
        assert "1-6 points" in text


def _case_score(autosomal_recessive: dict) -> float:
    evidence = {"case_level": {"autosomal_recessive": autosomal_recessive}}
    result = ClinGenEngine().calculate_scores({"genetic_evidence": evidence}, {})
    return result.scores["genetic_evidence_total"]


def test_fresh_empty_case_level_row_scores_nothing():
    fresh = {
        "variant_type": "nonsense",
        "variant": "",
        "pmid": "",
        "score_status": "score",
        "proband_counted_points": 1.5,
    }
    assert _case_score({"predicted_or_proven_null": [fresh]}) == 0
    filled = {**fresh, "pmid": "12345678"}
    assert _case_score({"predicted_or_proven_null": [filled]}) == 1.5


def test_changed_points_score_on_otherwise_blank_row_and_missing_points_are_zero():
    nulls = {"predicted_or_proven_null": [{"proband_counted_points": 1.75}]}
    assert _case_score(nulls) == 1.75
    other = {"other_variant_type": [{"proband_counted_points": 0.9}]}
    assert _case_score(other) == 0.9
    default = {"other_variant_type": [{"proband_counted_points": 0.1}]}
    assert _case_score(default) == 0
    no_points = {"predicted_or_proven_null": [{"pmid": "1"}]}  # frontend: 0
    assert _case_score(no_points) == 0
