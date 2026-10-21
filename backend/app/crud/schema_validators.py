"""Schema structure validation for the schema repository; one vocabulary in `core` (#269)."""

from typing import Any

from app.core.schema_validator import schema_validator


def validate_schema_structure(
    schema_data: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """(errors, warnings) of `SchemaValidator.validate_schema_definition`, as strings."""
    result = schema_validator.validate_schema_definition(schema_data)
    return (
        [f"{e['field']}: {e['message']}" for e in result.errors],
        [f"{w['field']}: {w['message']}" for w in result.warnings],
    )
