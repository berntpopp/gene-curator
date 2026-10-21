"""Result container for schema validation runs."""

import re
from typing import Any


class SchemaValidationResult:
    """Result of schema validation."""

    def __init__(self) -> None:
        self.is_valid: bool = True
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.field_validations: dict[str, dict[str, Any]] = {}
        self.business_rule_violations: list[dict[str, Any]] = []
        self.score_calculations: dict[str, Any] = {}
        self.completeness_score: float = 0.0
        self.required_fields_missing: list[str] = []
        self.suggested_improvements: list[str] = []

    def add_error(
        self, field: str, message: str, error_type: str = "validation"
    ) -> None:
        """Add a validation error."""
        self.is_valid = False
        error = {
            "field": field,
            "message": message,
            "type": error_type,
            "severity": "error",
        }
        self.errors.append(error)

        if field not in self.field_validations:
            self.field_validations[field] = {"errors": [], "warnings": []}
        self.field_validations[field]["errors"].append(error)

    def check_pattern(
        self, field: str, pattern: str, value: str, config: dict[str, Any] | None = None
    ) -> bool:
        """Error if value does not match pattern; a bad pattern is a schema error."""
        try:
            matched = re.match(pattern, value)
        except re.error:
            self.add_error(
                field, "Schema has an invalid regex pattern", "configuration"
            )
            return False
        if not matched:
            self.add_error(
                field,
                (config or {}).get("pattern_message")
                or "Text does not match required pattern",
                "pattern",
            )
        return bool(matched)

    def add_warning(
        self, field: str, message: str, warning_type: str = "quality"
    ) -> None:
        """Add a validation warning."""
        warning = {
            "field": field,
            "message": message,
            "type": warning_type,
            "severity": "warning",
        }
        self.warnings.append(warning)

        if field not in self.field_validations:
            self.field_validations[field] = {"errors": [], "warnings": []}
        self.field_validations[field]["warnings"].append(warning)

    def add_business_rule_violation(
        self, rule: str, message: str, severity: str = "error"
    ) -> None:
        """Add a business rule violation."""
        violation = {"rule": rule, "message": message, "severity": severity}
        self.business_rule_violations.append(violation)

        if severity == "error":
            self.is_valid = False
