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
