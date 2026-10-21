"""Definitive (replication over time), contradictory evidence and rationale ranges."""

import pytest

from app.scoring.clingen import ClinGenEngine

pytestmark = pytest.mark.unit


@pytest.fixture
def engine() -> ClinGenEngine:
    return ClinGenEngine()


class TestDefinitiveAndContradictory:
    def test_definitive_needs_strong_points_and_replication(
        self, engine: ClinGenEngine
    ):
        assert engine._classify(12.0, replicated_over_time=True) == "definitive"
        assert engine._classify(12.0) == "strong"
        assert engine._classify(11.99, replicated_over_time=True) == "moderate"

    def test_contradictory_evidence_is_disputed(self, engine: ClinGenEngine):
        assert engine._classify(18.0, has_contradictory=True) == "disputed"
        assert (
            engine._classify(18.0, has_contradictory=True, replicated_over_time=True)
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
        dis = {**rep, "contradictory_evidence": [{"pmid": "1"}]}
        assert engine.calculate_scores(dis, {}).verdict == "disputed"

    def test_empty_contradictory_row_does_not_dispute(self, engine: ClinGenEngine):
        null = {"pmid": "12345678", "proband_counted_points": 3.0}
        case = {
            "autosomal_dominant_or_x_linked": {"predicted_or_proven_null": [null] * 4}
        }
        base = {"genetic_evidence": {"case_level": case}, "experimental_evidence": {}}
        blank = {"pmid": "", "description": "  ", "tags": [], "note": None}
        for rows in ([blank], [{}], [blank, {}]):
            ev = {**base, "contradictory_evidence": rows}
            assert engine.calculate_scores(ev, {}).verdict == "strong"
        ev = {**base, "contradictory_evidence": [blank, {"pmid": "1"}]}
        assert engine.calculate_scores(ev, {}).verdict == "disputed"

    def test_rationale_uses_sop_v11_ranges(self, engine: ClinGenEngine):
        text = engine._generate_rationale(1, 0, 1, "limited")
        assert "1-6 points" in text
