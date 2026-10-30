"""Evidence-table list cells (#577): a multiselect or array column publishes, and its lists
pass validation unchanged."""

from app.core.schema_validator import SchemaValidator
from tests.unit.test_schema_validators_seeded import errors

FIELDS = {
    "diagnostics": {
        "type": "evidence_table",
        "columns": {
            "tools": {"type": "array"},
            "audiences": {
                "type": "multiselect",
                "options": [{"value": "clinician"}, {"value": "lab"}],
            },
        },
    }
}


def test_list_columns_publish_and_validate_as_lists() -> None:
    assert errors(field_definitions=FIELDS, validation_rules={}) == []
    data = {
        "diagnostics": [{"tools": ["WES", "CNV"], "audiences": ["clinician", "lab"]}]
    }
    result = SchemaValidator().validate_evidence_data(
        data, {"field_definitions": FIELDS}
    )
    assert result.is_valid and not result.errors
    assert data["diagnostics"][0]["tools"] == ["WES", "CNV"]
