"""Behaviour tests for the dynamic schema validation engine (app/core/schema_validator.py).

Covers per-field-type validation and required-field handling. Rule, scoring and
schema-definition tests live in test_schema_validator_rules.py. Pure unit tests.
"""

from datetime import datetime

import pytest

from app.core.schema_validator import SchemaValidator
from tests.unit.schema_validator_support import messages as _messages, run as _run

pytestmark = pytest.mark.unit


@pytest.fixture
def validator() -> SchemaValidator:
    return SchemaValidator()


# =============================================================================
# Required fields and dispatch
# =============================================================================


class TestFieldDispatch:
    def test_required_missing_is_recorded(self, validator: SchemaValidator):
        result = _run(
            validator,
            {"gene": ""},
            {"gene": {"type": "text", "required": True}},
        )

        assert result.is_valid is False
        assert result.required_fields_missing == ["gene"]
        assert result.errors[0]["type"] == "required"

    def test_optional_absent_field_is_skipped(self, validator: SchemaValidator):
        result = _run(validator, {}, {"note": {"type": "number"}})

        assert result.is_valid is True
        assert result.errors == []

    def test_unknown_field_type_warns(self, validator: SchemaValidator):
        result = _run(validator, {"x": 1}, {"x": {"type": "colour"}})

        assert result.is_valid is True
        assert _messages(result, "warnings") == ["Unknown field type: colour"]

    def test_completeness_counts_only_filled_fields(self, validator: SchemaValidator):
        defs = {f: {"type": "text"} for f in ["a", "b", "c", "d"]}
        data = {"a": "value here", "b": "", "c": "   ", "d": 0}

        result = _run(validator, data, defs)

        # a and d (0 is a real value) count; "" and whitespace-only do not
        assert result.completeness_score == pytest.approx(50.0)

    def test_completeness_zero_without_definitions(self, validator: SchemaValidator):
        result = _run(validator, {"a": 1}, {})

        assert result.completeness_score == 0


# =============================================================================
# Individual field types
# =============================================================================


class TestTextField:
    @pytest.mark.parametrize(
        ("config", "value", "message"),
        [
            ({"min_length": 5}, "abc", "Text must be at least 5 characters"),
            ({"max_length": 3}, "abcdef", "Text must not exceed 3 characters"),
            ({"pattern": "^[A-Z]+$"}, "abc", "Text does not match required pattern"),
            ({}, 42, "Value must be a string"),
        ],
    )
    def test_errors(self, validator, config, value, message):
        result = _run(validator, {"f": value}, {"f": {"type": "text", **config}})

        assert result.is_valid is False
        assert message in _messages(result)

    def test_invalid_regex_pattern_is_a_configuration_error(
        self, validator: SchemaValidator
    ):
        result = _run(validator, {"f": "abc"}, {"f": {"type": "text", "pattern": "("}})

        assert result.is_valid is False
        assert "Schema has an invalid regex pattern" in _messages(result)

    def test_whitespace_and_brevity_warnings(self, validator: SchemaValidator):
        result = _run(validator, {"f": " two words "}, {"f": {"type": "text"}})

        assert result.is_valid is True
        warnings = _messages(result, "warnings")
        assert "Text has leading/trailing whitespace" in warnings
        assert "Consider providing more detailed description" in warnings

    def test_quality_checks_can_be_disabled(self, validator: SchemaValidator):
        result = _run(
            validator,
            {"f": " hi "},
            {"f": {"type": "text", "quality_checks": False}},
        )

        assert result.warnings == []


class TestNumberField:
    def test_non_numeric_rejected(self, validator: SchemaValidator):
        result = _run(validator, {"n": "abc"}, {"n": {"type": "number"}})

        assert _messages(result) == ["Value must be a number"]

    def test_numeric_string_accepted(self, validator: SchemaValidator):
        result = _run(validator, {"n": "3.5"}, {"n": {"type": "number"}})

        assert result.is_valid is True

    def test_range_bounds(self, validator: SchemaValidator):
        defs = {"n": {"type": "number", "min_value": 0, "max_value": 12}}

        low = _run(validator, {"n": -0.1}, defs)
        high = _run(validator, {"n": 12.5}, defs)
        edge = _run(validator, {"n": 12}, defs)

        assert "Value must be at least 0" in _messages(low)
        assert "Value must not exceed 12" in _messages(high)
        assert edge.is_valid is True

    def test_decimal_places(self, validator: SchemaValidator):
        defs = {"n": {"type": "number", "decimal_places": 2}}

        ok = _run(validator, {"n": 1.25}, defs)
        bad = _run(validator, {"n": 1.234}, defs)

        assert ok.is_valid is True
        assert bad.errors[0]["type"] == "precision"


class TestScoreField:
    def test_negative_score_warns(self, validator: SchemaValidator):
        result = _run(validator, {"s": -1}, {"s": {"type": "score"}})

        assert result.is_valid is True
        assert _messages(result, "warnings") == [
            "Negative scores are unusual - please verify"
        ]

    def test_genetic_evidence_field_over_twelve_warns(self, validator):
        result = _run(
            validator,
            {"genetic_evidence_total": 13},
            {"genetic_evidence_total": {"type": "score"}},
        )

        assert any(
            "typically don't exceed 12" in w for w in _messages(result, "warnings")
        )

    def test_experimental_field_over_six_warns(self, validator):
        result = _run(
            validator,
            {"experimental_evidence_score": 7},
            {"experimental_evidence_score": {"type": "score"}},
        )

        assert any(
            "typically don't exceed 6" in w for w in _messages(result, "warnings")
        )

    def test_non_numeric_score_is_error_not_crash(self, validator):
        result = _run(validator, {"s": "x"}, {"s": {"type": "score"}})

        assert _messages(result) == ["Value must be a number"]


class TestBooleanAndArrayFields:
    def test_boolean_must_be_bool(self, validator: SchemaValidator):
        result = _run(validator, {"b": "yes"}, {"b": {"type": "boolean"}})

        assert _messages(result) == ["Value must be true or false"]

    def test_array_must_be_list(self, validator: SchemaValidator):
        result = _run(validator, {"a": "x"}, {"a": {"type": "array"}})

        assert _messages(result) == ["Value must be an array"]

    def test_array_item_count_bounds(self, validator: SchemaValidator):
        defs = {"a": {"type": "array", "min_items": 2, "max_items": 3}}

        few = _run(validator, {"a": [1]}, defs)
        many = _run(validator, {"a": [1, 2, 3, 4]}, defs)

        assert "Array must have at least 2 items" in _messages(few)
        assert "Array must not have more than 3 items" in _messages(many)

    def test_array_items_validated_with_indexed_field_names(
        self, validator: SchemaValidator
    ):
        defs = {"refs": {"type": "array", "items": {"type": "pmid"}}}

        result = _run(validator, {"refs": ["123", "abc"]}, defs)

        assert result.is_valid is False
        assert result.errors[0]["field"] == "refs[1]"
        assert result.errors[0]["message"] == "PMID must contain only digits"


class TestObjectField:
    def test_object_properties_validated(self, validator: SchemaValidator):
        defs = {
            "claim": {
                "type": "object",
                "properties": {
                    "count": {"type": "number", "min_value": 0},
                    "desc": {"type": "text", "required": True},
                },
            }
        }

        result = _run(validator, {"claim": {"count": -1}}, defs)

        fields = {e["field"] for e in result.errors}
        assert fields == {"claim.count", "claim.desc"}

    def test_object_must_be_dict(self, validator: SchemaValidator):
        defs = {"claim": {"type": "object"}}

        result = _run(validator, {"claim": ["x"]}, defs)

        assert _messages(result) == ["Value must be an object"]


class TestDateField:
    def test_valid_iso_date(self, validator: SchemaValidator):
        result = _run(validator, {"d": "2024-05-01"}, {"d": {"type": "date"}})

        assert result.is_valid is True

    def test_datetime_object_accepted(self, validator: SchemaValidator):
        result = _run(
            validator,
            {"d": datetime(2024, 5, 1)},
            {"d": {"type": "date"}},
        )

        assert result.is_valid is True

    def test_invalid_format_and_type(self, validator: SchemaValidator):
        bad = _run(validator, {"d": "2024-13-45"}, {"d": {"type": "date"}})
        wrong_type = _run(validator, {"d": 20240501}, {"d": {"type": "date"}})

        assert _messages(bad) == ["Invalid date format. Use ISO format (YYYY-MM-DD)"]
        assert _messages(wrong_type) == ["Date must be a string in ISO format"]

    def test_min_and_max_bounds(self, validator: SchemaValidator):
        defs = {
            "d": {"type": "date", "min_date": "2025-01-01", "max_date": "2026-01-01"}
        }

        early = _run(validator, {"d": "2024-05-01"}, defs)
        late = _run(validator, {"d": "2027-05-01"}, defs)

        assert _messages(early) == ["Date must be after 2025-01-01"]
        assert _messages(late) == ["Date must be before 2026-01-01"]

    def test_timezone_aware_value_against_naive_bound(self, validator: SchemaValidator):
        """Regression: aware vs naive comparison used to raise TypeError."""
        defs = {"d": {"type": "date", "min_date": "2020-01-01"}}

        result = _run(validator, {"d": "2024-05-01T10:00:00Z"}, defs)

        assert result.is_valid is True

    def test_timezone_aware_bound_against_naive_value(self, validator: SchemaValidator):
        defs = {"d": {"type": "date", "max_date": "2030-01-01T00:00:00Z"}}

        result = _run(validator, {"d": "2024-05-01"}, defs)

        assert result.is_valid is True


class TestSelectFields:
    def test_select_membership(self, validator: SchemaValidator):
        defs = {"s": {"type": "select", "options": ["a", {"value": "b"}]}}

        ok = _run(validator, {"s": "b"}, defs)
        bad = _run(validator, {"s": "c"}, defs)

        assert ok.is_valid is True
        assert _messages(bad) == ["Value must be one of: a, b"]

    def test_select_without_options_warns(self, validator: SchemaValidator):
        result = _run(validator, {"s": "x"}, {"s": {"type": "select"}})

        assert result.is_valid is True
        assert _messages(result, "warnings") == ["No options defined for select field"]

    def test_multiselect_items_checked(self, validator: SchemaValidator):
        defs = {"m": {"type": "multiselect", "options": ["x", "y"]}}

        result = _run(validator, {"m": ["x", "z"]}, defs)

        assert _messages(result) == ["Invalid option: z. Must be one of: x, y"]

    def test_multiselect_must_be_list(self, validator: SchemaValidator):
        result = _run(
            validator,
            {"m": "x"},
            {"m": {"type": "multiselect", "options": ["x"]}},
        )

        assert _messages(result) == ["Value must be an array"]

    def test_multiselect_without_options_warns(self, validator: SchemaValidator):
        result = _run(validator, {"m": ["x"]}, {"m": {"type": "multiselect"}})

        assert _messages(result, "warnings") == [
            "No options defined for multiselect field"
        ]


class TestFormatFields:
    @pytest.mark.parametrize(
        ("field_type", "good", "bad"),
        [
            ("email", "a.b@example.org", "a@b"),
            ("url", "https://example.org/path?q=1", "ftp://example.org"),
            ("hgnc_id", "HGNC:5", "HGNC5"),
            ("hgnc_id", "HGNC:12345", "HGNC:ABC"),
            ("pmid", 12345678, "12a"),
            ("pmid", "1234567890", "12345678901"),
        ],
    )
    def test_format_validators(self, validator, field_type, good, bad):
        defs = {"f": {"type": field_type}}

        assert _run(validator, {"f": good}, defs).is_valid is True
        assert _run(validator, {"f": bad}, defs).is_valid is False

    def test_pmid_type_error(self, validator: SchemaValidator):
        result = _run(validator, {"f": ["1"]}, {"f": {"type": "pmid"}})

        assert _messages(result) == ["PMID must be a string or number"]

    def test_hgnc_non_string_error(self, validator: SchemaValidator):
        result = _run(validator, {"f": 5}, {"f": {"type": "hgnc_id"}})

        assert _messages(result) == ["HGNC ID must be a string"]
