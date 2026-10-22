"""Generated schemas retain declared defaults, including false and null, without inferring them."""

import pytest

from app.core.schema_validator import schema_validator

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("default", [False, 0, "", None, "assigned"])
def test_generated_schema_preserves_declared_scalar_default(default):
    definition = {
        "field_definitions": {
            "answer": {"type": "boolean", "default": default},
            "missing": {"type": "boolean"},
        }
    }
    properties = schema_validator.generate_json_schema(definition)["properties"]
    assert "default" in properties["answer"]
    assert properties["answer"]["default"] == default
    assert "default" not in properties["missing"]
