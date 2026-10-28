"""Schema validation uses the engines configured by seeded schemas."""

import json
from pathlib import Path

import pytest

from app.core.schema_validator import SchemaValidator

pytestmark = pytest.mark.unit


@pytest.fixture
def seeded_clingen_schema():
    seed = (
        Path(__file__).resolve().parents[3]
        / "database/sql/020_complete_sop11_schema.sql"
    ).read_text()
    decoder = json.JSONDecoder()
    return {
        key: decoder.raw_decode(seed.split(f"{key} = '", 1)[1])[0]
        for key in ["field_definitions", "scoring_configuration"]
    }


def test_seeded_clingen_schema_returns_scores(seeded_clingen_schema):
    result = SchemaValidator().validate_evidence_data(
        {"genetic_evidence": {"segregation": [{"pmid": "12345678", "lod_score": 1.5}]}},
        seeded_clingen_schema,
    )
    assert result.is_valid is True
    trace = result.score_calculations.pop("trace")
    assert result.score_calculations == {
        "genetic_evidence_total": 2.0,
        "experimental_evidence_total": 0.0,
        "total_score": 2.0,
        "verdict": "limited",
        "excluded": [],
    }
    assert (trace["total"], trace["class"]) == (2.0, "limited")


@pytest.mark.parametrize("field_type", ["number", "score"])
def test_empty_number_is_absent_and_min_max_apply(field_type):
    fields = {"points": {"type": field_type, "min": 0, "max": 3}}
    for value, errors in (("", 0), (None, 0), (3, 0), (4, 1), ("abc", 1)):
        result = SchemaValidator().validate_evidence_data(
            {"points": value}, {"field_definitions": fields}
        )
        assert len(result.errors) == errors, value


def test_unknown_engine_is_a_clear_configuration_error():
    result = SchemaValidator().validate_evidence_data(
        {}, {"scoring_configuration": {"engine": "missing_engine"}}
    )
    assert result.is_valid is False
    assert result.errors == [
        {
            "field": "scoring_configuration.engine",
            "message": "Unknown scoring engine: missing_engine",
            "type": "configuration",
            "severity": "error",
        }
    ]
    assert result.score_calculations == {}


@pytest.mark.parametrize("name", ["gencc_based", "qualitative_assessment"])
def test_other_registered_engines_return_scores(name):
    result = SchemaValidator().validate_evidence_data(
        {}, {"scoring_configuration": {"engine": name}}
    )
    assert result.score_calculations["total_score"] == 0.0
    assert len(result.score_calculations) >= 3


def test_preview_lists_the_rows_that_score_zero(seeded_clingen_schema):
    """The live preview carries breakdown.excluded so the workspace can name the rows."""
    row = {"score_status": "score", "pmid": "1", "proband_counted_points": 2}
    ad = {"predicted_or_proven_null": [row]}
    evidence = {
        "genetic_evidence": {"case_level": {"autosomal_dominant_or_x_linked": ad}}
    }
    result = SchemaValidator().validate_evidence_data(evidence, seeded_clingen_schema)
    assert result.score_calculations["excluded"] == [
        {
            "path": "genetic_evidence.case_level.autosomal_dominant_or_x_linked"
            ".predicted_or_proven_null[0]",
            "field": "variant",
            "reason": "no_variant",
        }
    ]
