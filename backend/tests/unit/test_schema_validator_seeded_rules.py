"""#408: list-shaped validation_rules from the seeded precuration schema are applied."""

from typing import Any

import pytest

from app.core.schema_validator import SchemaValidator
from tests.unit.schema_validator_support import messages

pytestmark = pytest.mark.unit

# validation_rules exactly as database/sql/016_seed_precuration_schema.sql seeds them
SEEDED_RULES: dict[str, Any] = {
    "required_fields": ["mondo_id", "disease_name", "mode_of_inheritance"],
    "conditional_required": {
        "lumping_splitting_rationale": {"when": {"lumping_splitting_applicable": True}}
    },
    "custom_validators": [
        {
            "type": "mondo_id_format",
            "field": "mondo_id",
            "pattern": r"^MONDO:\d{6,9}$",
            "comment": "Mondo IDs have 6-9 digits",
        }
    ],
}
FIELDS = {
    "sections": [{"id": "disease", "fields": [{"id": "mondo_id", "type": "string"}]}]
}


def validate(data: dict[str, Any]) -> Any:
    schema = {"field_definitions": FIELDS, "validation_rules": SEEDED_RULES}
    return SchemaValidator().validate_evidence_data(data, schema)


def test_seeded_list_rules_do_not_warn_and_pass_valid_data() -> None:
    result = validate(
        {
            "mondo_id": "MONDO:0000001",
            "disease_name": "x",
            "mode_of_inheritance": "AD",
        }
    )
    assert not [w for w in messages(result, "warnings") if "Error applying" in w]
    assert result.is_valid


def test_required_fields_rule_reports_missing_fields() -> None:
    result = validate({"mondo_id": "MONDO:0000001", "disease_name": ""})
    assert {e["field"] for e in result.errors} == {
        "disease_name",
        "mode_of_inheritance",
    }
    assert set(result.required_fields_missing) == {
        "disease_name",
        "mode_of_inheritance",
    }


def test_custom_validator_pattern_is_applied() -> None:
    result = validate(
        {"mondo_id": "MONDO:12", "disease_name": "x", "mode_of_inheritance": "AD"}
    )
    assert [e["field"] for e in result.errors] == ["mondo_id"]


def test_conditional_required_applies_only_when_condition_holds() -> None:
    base = {
        "mondo_id": "MONDO:0000001",
        "disease_name": "x",
        "mode_of_inheritance": "AD",
    }
    assert validate({**base, "lumping_splitting_applicable": False}).is_valid
    result = validate({**base, "lumping_splitting_applicable": True})
    assert [e["field"] for e in result.errors] == ["lumping_splitting_rationale"]


@pytest.mark.parametrize(
    "rules",
    [
        {"required_fields": "mondo_id", "conditional_required": ["x"]},
        {"conditional_required": {"a": "x", "b": {"when": ["x"]}}},
        {
            "custom_validators": [
                "junk",
                {"field": 1},
                {"field": "mondo_id", "pattern": 5},
            ]
        },
        {"custom_validators": {"field": "mondo_id"}},
    ],
)
def test_malformed_list_rules_are_skipped(rules: dict[str, Any]) -> None:
    schema = {"field_definitions": FIELDS, "validation_rules": rules}
    result = SchemaValidator().validate_evidence_data({"mondo_id": "x"}, schema)
    assert result.is_valid


# The lumping/splitting section as 016_seed_precuration_schema.sql seeds it
LUMPING = {
    "sections": [
        {
            "id": "lumping_splitting",
            "fields": [
                {
                    "id": "lumping_splitting_applicable",
                    "type": "boolean",
                    "required": True,
                },
                {
                    "id": "lumping_splitting_decision",
                    "type": "select",
                    "required": True,
                    "show_when": {"lumping_splitting_applicable": True},
                    "options": [{"value": "LUMP"}, {"value": "SPLIT"}],
                },
                {
                    "id": "lumping_splitting_rationale",
                    "type": "textarea",
                    "required": True,
                    "visible_when": {"lumping_splitting_applicable": [True]},
                },
            ],
        }
    ]
}


def test_hidden_required_fields_are_not_missing() -> None:
    result = SchemaValidator().validate_evidence_data(
        {"lumping_splitting_applicable": False}, {"field_definitions": LUMPING}
    )
    assert result.required_fields_missing == []
    assert result.is_valid


def test_visible_required_fields_are_missing() -> None:
    result = SchemaValidator().validate_evidence_data(
        {"lumping_splitting_applicable": True}, {"field_definitions": LUMPING}
    )
    assert result.required_fields_missing == [
        "lumping_splitting_decision",
        "lumping_splitting_rationale",
    ]


def test_hidden_field_values_are_still_validated() -> None:
    data = {"lumping_splitting_applicable": False, "lumping_splitting_decision": "X"}
    result = SchemaValidator().validate_evidence_data(
        data, {"field_definitions": LUMPING}
    )
    assert [e["field"] for e in result.errors] == ["lumping_splitting_decision"]
