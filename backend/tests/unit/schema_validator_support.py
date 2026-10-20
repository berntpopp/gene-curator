"""Shared helpers for schema validator unit tests."""

from typing import Any

from app.core.schema_validation_result import SchemaValidationResult
from app.core.schema_validator import SchemaValidator


def run(
    validator: SchemaValidator,
    data: dict[str, Any],
    field_definitions: dict[str, Any],
    **extra: Any,
) -> SchemaValidationResult:
    schema: dict[str, Any] = {"field_definitions": field_definitions, **extra}
    return validator.validate_evidence_data(data, schema)


def messages(result: SchemaValidationResult, kind: str = "errors") -> list[str]:
    return [item["message"] for item in getattr(result, kind)]
