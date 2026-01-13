"""
Schema validation engine for dynamic form validation and data integrity.
Validates evidence data against schema definitions and enforces business rules.
"""

import re
from datetime import datetime
from typing import Any


class SchemaValidationResult:
    """Result of schema validation."""

    def __init__(self) -> None:
        self.is_valid: bool = True
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.field_validations: dict[str, dict[str, Any]] = {}
        self.business_rule_violations: list[dict[str, Any]] = []
        self.score_calculations: dict[str, float] = {}
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


class SchemaValidator:
    """
    Core schema validation engine for the schema-agnostic curation system.
    Validates evidence data against schema definitions and enforces business rules.
    """

    def __init__(self) -> None:
        self.field_validators = {
            "text": self._validate_text_field,
            "number": self._validate_number_field,
            "boolean": self._validate_boolean_field,
            "array": self._validate_array_field,
            "object": self._validate_object_field,
            "date": self._validate_date_field,
            "select": self._validate_select_field,
            "multiselect": self._validate_multiselect_field,
            "email": self._validate_email_field,
            "url": self._validate_url_field,
            "pmid": self._validate_pmid_field,
            "hgnc_id": self._validate_hgnc_id_field,
            "score": self._validate_score_field,
        }

        self.business_rules = {
            "clingen_genetic_evidence": self._validate_clingen_genetic_evidence,
            "clingen_experimental_evidence": self._validate_clingen_experimental_evidence,
            "clingen_contradictory_evidence": self._validate_clingen_contradictory_evidence,
            "gencc_classification": self._validate_gencc_classification,
            "institutional_review": self._validate_institutional_review,
        }

    def validate_evidence_data(
        self,
        evidence_data: dict[str, Any],
        schema_definition: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> SchemaValidationResult:
        """
        Validate evidence data against a schema definition.

        Args:
            evidence_data: The evidence data to validate
            schema_definition: The schema definition containing field definitions and rules
            context: Additional context (gene info, scope info, etc.)

        Returns:
            SchemaValidationResult with validation results
        """
        result = SchemaValidationResult()

        # Extract schema components
        field_definitions = schema_definition.get("field_definitions", {})
        validation_rules = schema_definition.get("validation_rules", {})
        scoring_config = schema_definition.get("scoring_configuration", {})
        business_rules = schema_definition.get("business_rules", [])

        # 1. Validate individual fields
        self._validate_fields(evidence_data, field_definitions, result)

        # 2. Apply validation rules
        self._apply_validation_rules(evidence_data, validation_rules, result)

        # 3. Apply business rules
        self._apply_business_rules(evidence_data, business_rules, result, context)

        # 4. Calculate scores if scoring is configured
        if scoring_config:
            self._calculate_scores(evidence_data, scoring_config, result)

        # 5. Calculate completeness
        self._calculate_completeness(evidence_data, field_definitions, result)

        # 6. Generate improvement suggestions
        self._generate_suggestions(evidence_data, schema_definition, result)

        return result

    def validate_schema_definition(
        self, schema_definition: dict[str, Any]
    ) -> SchemaValidationResult:
        """
        Validate a schema definition itself for correctness and completeness.

        Args:
            schema_definition: The schema definition to validate

        Returns:
            SchemaValidationResult with validation results
        """
        result = SchemaValidationResult()

        # Required top-level fields
        required_fields = ["field_definitions", "workflow_states"]
        for field in required_fields:
            if field not in schema_definition:
                result.add_error(
                    "schema", f"Missing required field: {field}", "structure"
                )

        # Validate field definitions
        if "field_definitions" in schema_definition:
            self._validate_field_definitions(
                schema_definition["field_definitions"], result
            )

        # Validate workflow states
        if "workflow_states" in schema_definition:
            self._validate_workflow_states(schema_definition["workflow_states"], result)

        # Validate UI configuration
        if "ui_configuration" in schema_definition:
            self._validate_ui_configuration(
                schema_definition["ui_configuration"], result
            )

        # Validate scoring configuration
        if "scoring_configuration" in schema_definition:
            self._validate_scoring_configuration(
                schema_definition["scoring_configuration"], result
            )

        return result

    def generate_json_schema(self, schema_definition: dict[str, Any]) -> dict[str, Any]:
        """
        Generate a JSON Schema from a curation schema definition.

        Args:
            schema_definition: The curation schema definition

        Returns:
            JSON Schema for validation
        """
        field_definitions = schema_definition.get("field_definitions", {})

        json_schema: dict[str, Any] = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {},
            "required": [],
        }

        for field_name, field_config in field_definitions.items():
            json_schema["properties"][field_name] = self._convert_field_to_json_schema(
                field_config
            )

            if field_config.get("required", False):
                json_schema["required"].append(field_name)

        return json_schema

    # Private validation methods

    def _validate_fields(
        self,
        evidence_data: dict[str, Any],
        field_definitions: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Validate individual fields against their definitions."""
        for field_name, field_config in field_definitions.items():
            field_value = evidence_data.get(field_name)

            # Check if required field is missing
            if field_config.get("required", False) and (
                field_value is None or field_value == ""
            ):
                result.add_error(field_name, "Required field is missing", "required")
                result.required_fields_missing.append(field_name)
                continue

            # Skip validation if field is not provided and not required
            if field_value is None:
                continue

            # Validate field type
            field_type = field_config.get("type", "text")
            if field_type in self.field_validators:
                self.field_validators[field_type](
                    field_name, field_value, field_config, result
                )
            else:
                result.add_warning(
                    field_name, f"Unknown field type: {field_type}", "configuration"
                )

    def _validate_text_field(
        self,
        field_name: str,
        value: Any,
        config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Validate text field."""
        if not isinstance(value, str):
            result.add_error(field_name, "Value must be a string", "type")
            return

        # Length validation
        min_length = config.get("min_length", 0)
        max_length = config.get("max_length")

        if len(value) < min_length:
            result.add_error(
                field_name, f"Text must be at least {min_length} characters", "length"
            )

        if max_length and len(value) > max_length:
            result.add_error(
                field_name, f"Text must not exceed {max_length} characters", "length"
            )

        # Pattern validation
        pattern = config.get("pattern")
        if pattern and not re.match(pattern, value):
            result.add_error(
                field_name, "Text does not match required pattern", "pattern"
            )

        # Content quality checks
        if config.get("quality_checks", True):
            if len(value.strip()) != len(value):
                result.add_warning(
                    field_name, "Text has leading/trailing whitespace", "quality"
                )

            if len(value) > 0 and len(value.split()) < 3:
                result.add_warning(
                    field_name,
                    "Consider providing more detailed description",
                    "completeness",
                )

    def _validate_number_field(
        self,
        field_name: str,
        value: Any,
        config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Validate number field."""
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            result.add_error(field_name, "Value must be a number", "type")
            return

        # Range validation
        min_value = config.get("min_value")
        max_value = config.get("max_value")

        if min_value is not None and num_value < min_value:
            result.add_error(field_name, f"Value must be at least {min_value}", "range")

        if max_value is not None and num_value > max_value:
            result.add_error(field_name, f"Value must not exceed {max_value}", "range")

        # Decimal places validation
        decimal_places = config.get("decimal_places")
        if (
            decimal_places is not None
            and "." in str(value)
            and len(str(value).split(".")[1]) > decimal_places
        ):
            result.add_error(
                field_name,
                f"Value cannot have more than {decimal_places} decimal places",
                "precision",
            )

    def _validate_boolean_field(
        self,
        field_name: str,
        value: Any,
        config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Validate boolean field."""
        if not isinstance(value, bool):
            result.add_error(field_name, "Value must be true or false", "type")

    def _validate_array_field(
        self,
        field_name: str,
        value: Any,
        config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Validate array field."""
        if not isinstance(value, list):
            result.add_error(field_name, "Value must be an array", "type")
            return

        # Length validation
        min_items = config.get("min_items", 0)
        max_items = config.get("max_items")

        if len(value) < min_items:
            result.add_error(
                field_name, f"Array must have at least {min_items} items", "length"
            )

        if max_items and len(value) > max_items:
            result.add_error(
                field_name, f"Array must not have more than {max_items} items", "length"
            )

        # Item validation
        item_schema = config.get("items")
        if item_schema:
            for i, item in enumerate(value):
                item_field_name = f"{field_name}[{i}]"
                item_type = item_schema.get("type", "text")
                if item_type in self.field_validators:
                    self.field_validators[item_type](
                        item_field_name, item, item_schema, result
                    )

    def _validate_object_field(
        self,
        field_name: str,
        value: Any,
        config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Validate object field."""
        if not isinstance(value, dict):
            result.add_error(field_name, "Value must be an object", "type")
            return

        # Validate object properties
        properties = config.get("properties", {})
        for prop_name, prop_config in properties.items():
            prop_value = value.get(prop_name)
            full_field_name = f"{field_name}.{prop_name}"

            if prop_config.get("required", False) and prop_value is None:
                result.add_error(
                    full_field_name, "Required property is missing", "required"
                )
                continue

            if prop_value is not None:
                prop_type = prop_config.get("type", "text")
                if prop_type in self.field_validators:
                    self.field_validators[prop_type](
                        full_field_name, prop_value, prop_config, result
                    )

    def _validate_date_field(
        self,
        field_name: str,
        value: Any,
        config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Validate date field."""
        if isinstance(value, datetime):
            return  # Already a datetime object

        if not isinstance(value, str):
            result.add_error(field_name, "Date must be a string in ISO format", "type")
            return

        try:
            parsed_date = datetime.fromisoformat(value.replace("Z", "+00:00"))

            # Date range validation
            min_date = config.get("min_date")
            max_date = config.get("max_date")

            if min_date and parsed_date < datetime.fromisoformat(min_date):
                result.add_error(field_name, f"Date must be after {min_date}", "range")

            if max_date and parsed_date > datetime.fromisoformat(max_date):
                result.add_error(field_name, f"Date must be before {max_date}", "range")

        except ValueError:
            result.add_error(
                field_name, "Invalid date format. Use ISO format (YYYY-MM-DD)", "format"
            )

    def _validate_select_field(
        self,
        field_name: str,
        value: Any,
        config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Validate select field."""
        options = config.get("options", [])
        if not options:
            result.add_warning(
                field_name, "No options defined for select field", "configuration"
            )
            return

        valid_values = [
            opt["value"] if isinstance(opt, dict) else opt for opt in options
        ]

        if value not in valid_values:
            result.add_error(
                field_name,
                f"Value must be one of: {', '.join(map(str, valid_values))}",
                "options",
            )

    def _validate_multiselect_field(
        self,
        field_name: str,
        value: Any,
        config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Validate multiselect field."""
        if not isinstance(value, list):
            result.add_error(field_name, "Value must be an array", "type")
            return

        options = config.get("options", [])
        if not options:
            result.add_warning(
                field_name, "No options defined for multiselect field", "configuration"
            )
            return

        valid_values = [
            opt["value"] if isinstance(opt, dict) else opt for opt in options
        ]

        for item in value:
            if item not in valid_values:
                result.add_error(
                    field_name,
                    f"Invalid option: {item}. Must be one of: {', '.join(map(str, valid_values))}",
                    "options",
                )

    def _validate_email_field(
        self,
        field_name: str,
        value: Any,
        config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Validate email field."""
        if not isinstance(value, str):
            result.add_error(field_name, "Email must be a string", "type")
            return

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, value):
            result.add_error(field_name, "Invalid email format", "format")

    def _validate_url_field(
        self,
        field_name: str,
        value: Any,
        config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Validate URL field."""
        if not isinstance(value, str):
            result.add_error(field_name, "URL must be a string", "type")
            return

        url_pattern = r"^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w)*)?)?$"
        if not re.match(url_pattern, value):
            result.add_error(field_name, "Invalid URL format", "format")

    def _validate_pmid_field(
        self,
        field_name: str,
        value: Any,
        config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Validate PubMed ID field."""
        if isinstance(value, int):
            value = str(value)

        if not isinstance(value, str):
            result.add_error(field_name, "PMID must be a string or number", "type")
            return

        if not value.isdigit():
            result.add_error(field_name, "PMID must contain only digits", "format")
            return

        # PMID validation - must be reasonable length
        if len(value) < 1 or len(value) > 10:
            result.add_error(field_name, "PMID must be 1-10 digits long", "format")

    def _validate_hgnc_id_field(
        self,
        field_name: str,
        value: Any,
        config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Validate HGNC ID field."""
        if not isinstance(value, str):
            result.add_error(field_name, "HGNC ID must be a string", "type")
            return

        if not value.startswith("HGNC:") or not value[5:].isdigit():
            result.add_error(
                field_name,
                "HGNC ID must be in format HGNC:#### where #### is a number",
                "format",
            )

    def _validate_score_field(
        self,
        field_name: str,
        value: Any,
        config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Validate score field with special scoring rules."""
        # First do basic number validation
        self._validate_number_field(field_name, value, config, result)

        # Additional score-specific validation
        if (
            field_name in result.field_validations
            and result.field_validations[field_name]["errors"]
        ):
            return  # Skip if basic validation failed

        score_value = float(value)

        # Score must be non-negative for most scoring systems
        if score_value < 0:
            result.add_warning(
                field_name, "Negative scores are unusual - please verify", "quality"
            )

        # Check for reasonable score ranges based on field name
        if "genetic_evidence" in field_name.lower() and score_value > 12:
            result.add_warning(
                field_name,
                "ClinGen genetic evidence scores typically don't exceed 12 points",
                "range",
            )

        if "experimental_evidence" in field_name.lower() and score_value > 6:
            result.add_warning(
                field_name,
                "ClinGen experimental evidence scores typically don't exceed 6 points",
                "range",
            )

    def _apply_validation_rules(
        self,
        evidence_data: dict[str, Any],
        validation_rules: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Apply custom validation rules."""
        for rule_name, rule_config in validation_rules.items():
            try:
                rule_type = rule_config.get("type", "condition")

                if rule_type == "condition":
                    self._apply_condition_rule(
                        evidence_data, rule_name, rule_config, result
                    )
                elif rule_type == "dependency":
                    self._apply_dependency_rule(
                        evidence_data, rule_name, rule_config, result
                    )
                elif rule_type == "calculation":
                    self._apply_calculation_rule(
                        evidence_data, rule_name, rule_config, result
                    )

            except Exception as e:
                result.add_warning(
                    "validation_rules",
                    f"Error applying rule {rule_name}: {e!s}",
                    "system",
                )

    def _apply_condition_rule(
        self,
        evidence_data: dict[str, Any],
        rule_name: str,
        rule_config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Apply conditional validation rule."""
        condition = rule_config.get("condition", "")
        message = rule_config.get("message", f"Condition rule {rule_name} failed")

        # Simple condition evaluation (would need more sophisticated parser for complex rules)
        if "&&" in condition or "||" in condition:
            result.add_warning(
                "validation_rules",
                f"Complex conditions not fully supported: {rule_name}",
                "limitation",
            )
            return

        # Basic field existence checks
        if condition.startswith("exists(") and condition.endswith(")"):
            field_name = condition[7:-1]
            if field_name not in evidence_data or evidence_data[field_name] is None:
                result.add_error(field_name, message, "condition")

    def _apply_dependency_rule(
        self,
        evidence_data: dict[str, Any],
        rule_name: str,
        rule_config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Apply field dependency rule."""
        depends_on = rule_config.get("depends_on", "")
        required_field = rule_config.get("field", "")
        message = rule_config.get(
            "message",
            f"Field {required_field} is required when {depends_on} is provided",
        )

        if (
            depends_on in evidence_data
            and evidence_data[depends_on] is not None
            and (
                required_field not in evidence_data
                or evidence_data[required_field] is None
            )
        ):
            result.add_error(required_field, message, "dependency")

    def _apply_calculation_rule(
        self,
        evidence_data: dict[str, Any],
        rule_name: str,
        rule_config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Apply calculation validation rule."""
        # This would implement calculation validation (e.g., totals, sums)
        result.add_warning(
            "validation_rules",
            f"Calculation rules not fully implemented: {rule_name}",
            "limitation",
        )

    def _apply_business_rules(
        self,
        evidence_data: dict[str, Any],
        business_rules: list[str],
        result: SchemaValidationResult,
        context: dict[str, Any] | None,
    ) -> None:
        """Apply business-specific validation rules."""
        for rule_name in business_rules:
            if rule_name in self.business_rules:
                try:
                    self.business_rules[rule_name](evidence_data, result, context)
                except Exception as e:
                    result.add_warning(
                        "business_rules",
                        f"Error applying business rule {rule_name}: {e!s}",
                        "system",
                    )

    def _validate_clingen_genetic_evidence(
        self,
        evidence_data: dict[str, Any],
        result: SchemaValidationResult,
        context: dict[str, Any] | None,
    ) -> None:
        """Validate ClinGen genetic evidence business rules."""
        genetic_evidence = evidence_data.get("genetic_evidence", {})

        # Check if case-level data and segregation data are mutually exclusive for some categories
        case_level_score = genetic_evidence.get("case_level_score", 0)
        segregation_score = genetic_evidence.get("segregation_score", 0)

        if case_level_score > 0 and segregation_score > 0:
            result.add_warning(
                "genetic_evidence",
                "Consider whether case-level and segregation data should be counted separately to avoid double-counting",
                "quality",
            )

        # Validate total genetic evidence score doesn't exceed maximum
        total_genetic = genetic_evidence.get(
            "total_score", case_level_score + segregation_score
        )
        if total_genetic > 12:
            result.add_business_rule_violation(
                "clingen_genetic_max_score",
                "ClinGen genetic evidence score cannot exceed 12 points",
                "error",
            )

    def _validate_clingen_experimental_evidence(
        self,
        evidence_data: dict[str, Any],
        result: SchemaValidationResult,
        context: dict[str, Any] | None,
    ) -> None:
        """Validate ClinGen experimental evidence business rules."""
        experimental_evidence = evidence_data.get("experimental_evidence", {})

        # Validate total experimental evidence score
        total_experimental = experimental_evidence.get("total_score", 0)
        if total_experimental > 6:
            result.add_business_rule_violation(
                "clingen_experimental_max_score",
                "ClinGen experimental evidence score cannot exceed 6 points",
                "error",
            )

    def _validate_clingen_contradictory_evidence(
        self,
        evidence_data: dict[str, Any],
        result: SchemaValidationResult,
        context: dict[str, Any] | None,
    ) -> None:
        """Validate ClinGen contradictory evidence business rules."""
        contradictory = evidence_data.get("contradictory_evidence", {})

        if contradictory.get("has_contradictory", False) and not contradictory.get(
            "description"
        ):
            result.add_business_rule_violation(
                "clingen_contradictory_description",
                "Contradictory evidence must include a detailed description",
                "error",
            )

    def _validate_gencc_classification(
        self,
        evidence_data: dict[str, Any],
        result: SchemaValidationResult,
        context: dict[str, Any] | None,
    ) -> None:
        """Validate GenCC classification business rules."""
        classification = evidence_data.get("classification", "")
        evidence_data.get("confidence_level", "")

        # GenCC-specific validation rules would go here
        valid_classifications = [
            "Definitive",
            "Strong",
            "Moderate",
            "Limited",
            "Disputed",
            "Refuted",
        ]
        if classification and classification not in valid_classifications:
            result.add_business_rule_violation(
                "gencc_valid_classification",
                f"Classification must be one of: {', '.join(valid_classifications)}",
                "error",
            )

    def _validate_institutional_review(
        self,
        evidence_data: dict[str, Any],
        result: SchemaValidationResult,
        context: dict[str, Any] | None,
    ) -> None:
        """Validate institutional review business rules."""
        # Institutional-specific validation rules would go here
        pass

    def _calculate_scores(
        self,
        evidence_data: dict[str, Any],
        scoring_config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Calculate scores based on scoring configuration."""
        engine_type = scoring_config.get("engine", "")

        if engine_type == "clingen":
            self._calculate_clingen_scores(evidence_data, scoring_config, result)
        elif engine_type == "gencc":
            self._calculate_gencc_scores(evidence_data, scoring_config, result)
        elif engine_type == "qualitative":
            self._calculate_qualitative_scores(evidence_data, scoring_config, result)

    def _calculate_clingen_scores(
        self,
        evidence_data: dict[str, Any],
        scoring_config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Calculate ClinGen SOP v11 scores."""
        genetic_evidence = evidence_data.get("genetic_evidence", {})
        experimental_evidence = evidence_data.get("experimental_evidence", {})

        # Calculate genetic evidence score
        genetic_score = (
            genetic_evidence.get("case_level_score", 0)
            + genetic_evidence.get("segregation_score", 0)
            + genetic_evidence.get("case_control_score", 0)
        )

        # Calculate experimental evidence score
        experimental_score = (
            experimental_evidence.get("functional_score", 0)
            + experimental_evidence.get("model_system_score", 0)
            + experimental_evidence.get("rescue_score", 0)
        )

        # Total score
        total_score = genetic_score + experimental_score

        result.score_calculations = {
            "genetic_evidence_score": genetic_score,
            "experimental_evidence_score": experimental_score,
            "total_score": total_score,
        }

    def _calculate_gencc_scores(
        self,
        evidence_data: dict[str, Any],
        scoring_config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Calculate GenCC-based scores."""
        # GenCC scoring logic would go here
        result.score_calculations = {"gencc_score": 0.0}

    def _calculate_qualitative_scores(
        self,
        evidence_data: dict[str, Any],
        scoring_config: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Calculate qualitative assessment scores."""
        # Qualitative scoring logic would go here
        result.score_calculations = {"qualitative_score": 0.0}

    def _calculate_completeness(
        self,
        evidence_data: dict[str, Any],
        field_definitions: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Calculate data completeness score."""
        total_fields = len(field_definitions)
        completed_fields = 0

        for field_name, _field_config in field_definitions.items():
            field_value = evidence_data.get(field_name)

            if (
                field_value is not None
                and field_value != ""
                and (
                    (isinstance(field_value, str) and field_value.strip())
                    or not isinstance(field_value, str)
                )
            ):
                completed_fields += 1

        result.completeness_score = (
            (completed_fields / total_fields) * 100 if total_fields > 0 else 0
        )

    def _generate_suggestions(
        self,
        evidence_data: dict[str, Any],
        schema_definition: dict[str, Any],
        result: SchemaValidationResult,
    ) -> None:
        """Generate improvement suggestions."""
        field_definitions = schema_definition.get("field_definitions", {})

        # Suggest completing missing optional fields
        for field_name, field_config in field_definitions.items():
            if (
                not field_config.get("required", False)
                and field_name not in evidence_data
            ):
                description = field_config.get("description", "")
                if description:
                    result.suggested_improvements.append(
                        f"Consider adding {field_name}: {description}"
                    )

        # Suggest improvements based on completeness
        if result.completeness_score < 50:
            result.suggested_improvements.append(
                "Evidence data appears incomplete. Consider providing more detailed information."
            )

        # Suggest improvements based on warnings
        if len(result.warnings) > 0:
            result.suggested_improvements.append(
                "Address validation warnings to improve data quality."
            )

    def _validate_field_definitions(
        self, field_definitions: dict[str, Any], result: SchemaValidationResult
    ) -> None:
        """Validate field definitions in schema."""
        if not isinstance(field_definitions, dict):
            result.add_error(  # type: ignore[unreachable]
                "field_definitions",
                "field_definitions must be a dictionary",
                "structure",
            )
            return

        for field_name, field_config in field_definitions.items():
            if not isinstance(field_config, dict):
                result.add_error(
                    "field_definitions",
                    f"Field '{field_name}' configuration must be an object",
                    "structure",
                )
                continue

            # Required properties
            if "type" not in field_config:
                result.add_error(
                    "field_definitions",
                    f"Field '{field_name}' missing required 'type' property",
                    "structure",
                )

            if "label" not in field_config:
                result.add_warning(
                    "field_definitions",
                    f"Field '{field_name}' missing 'label' property",
                    "usability",
                )

    def _validate_workflow_states(
        self, workflow_states: list[str], result: SchemaValidationResult
    ) -> None:
        """Validate workflow states."""
        if not isinstance(workflow_states, list):
            result.add_error(  # type: ignore[unreachable]
                "workflow_states", "Workflow states must be an array", "structure"
            )
            return

        required_states = ["draft", "submitted"]
        for state in required_states:
            if state not in workflow_states:
                result.add_error(
                    "workflow_states",
                    f"Missing required workflow state: {state}",
                    "structure",
                )

    def _validate_ui_configuration(
        self, ui_configuration: dict[str, Any], result: SchemaValidationResult
    ) -> None:
        """Validate UI configuration."""
        if "sections" not in ui_configuration:
            result.add_warning(
                "ui_configuration",
                "Missing 'sections' - form may not render properly",
                "usability",
            )

    def _validate_scoring_configuration(
        self, scoring_configuration: dict[str, Any], result: SchemaValidationResult
    ) -> None:
        """Validate scoring configuration."""
        if "engine" not in scoring_configuration:
            result.add_warning(
                "scoring_configuration",
                "Missing 'engine' specification",
                "configuration",
            )

    def _convert_field_to_json_schema(  # noqa: C901
        self, field_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Convert field configuration to JSON Schema property."""
        field_type = field_config.get("type", "text")

        json_schema_prop: dict[str, Any] = {}

        # Map field types to JSON Schema types
        type_mapping = {
            "text": "string",
            "string": "string",
            "number": "number",
            "boolean": "boolean",
            "array": "array",
            "object": "object",
            "date": "string",
            "select": "string",
            "multiselect": "array",
            "email": "string",
            "url": "string",
            "pmid": "string",
            "hgnc_id": "string",
            "score": "number",
            "enum": "string",
        }

        json_schema_prop["type"] = type_mapping.get(field_type, "string")

        # Add additional constraints
        if field_type == "text":
            if "min_length" in field_config:
                json_schema_prop["minLength"] = field_config["min_length"]
            if "max_length" in field_config:
                json_schema_prop["maxLength"] = field_config["max_length"]
            if "pattern" in field_config:
                json_schema_prop["pattern"] = field_config["pattern"]

        elif field_type == "number" or field_type == "score":
            # Handle both min/max and min_value/max_value formats
            if "min_value" in field_config:
                json_schema_prop["minimum"] = field_config["min_value"]
            elif "min" in field_config:
                json_schema_prop["minimum"] = field_config["min"]
            if "max_value" in field_config:
                json_schema_prop["maximum"] = field_config["max_value"]
            elif "max" in field_config:
                json_schema_prop["maximum"] = field_config["max"]
            if "step" in field_config:
                json_schema_prop["multipleOf"] = field_config["step"]

        elif field_type in ["select", "multiselect", "enum"]:
            options = field_config.get("options", [])
            if options:
                enum_values = [
                    opt["value"] if isinstance(opt, dict) else opt for opt in options
                ]
                if field_type in ["select", "enum"]:
                    json_schema_prop["enum"] = enum_values
                else:  # multiselect
                    json_schema_prop["items"] = {"enum": enum_values}

        elif field_type == "array":
            if "min_items" in field_config:
                json_schema_prop["minItems"] = field_config["min_items"]
            if "max_items" in field_config:
                json_schema_prop["maxItems"] = field_config["max_items"]
            # Handle both "items" and "item_schema" (used in ClinGen schema)
            if "items" in field_config:
                json_schema_prop["items"] = self._convert_field_to_json_schema(
                    field_config["items"]
                )
            elif "item_schema" in field_config:
                # item_schema is a flat dict of field definitions, convert to object
                item_props = {}
                item_required = []
                for item_name, item_config in field_config["item_schema"].items():
                    item_props[item_name] = self._convert_field_to_json_schema(
                        item_config
                    )
                    if item_config.get("required"):
                        item_required.append(item_name)
                json_schema_prop["items"] = {
                    "type": "object",
                    "properties": item_props,
                }
                if item_required:
                    json_schema_prop["items"]["required"] = item_required

        elif field_type == "object":
            # Recursively convert nested object properties
            if "properties" in field_config:
                json_schema_prop["properties"] = {}
                for prop_name, prop_config in field_config["properties"].items():
                    json_schema_prop["properties"][
                        prop_name
                    ] = self._convert_field_to_json_schema(prop_config)
            # Handle required properties within object
            if "required" in field_config and isinstance(
                field_config["required"], list
            ):
                json_schema_prop["required"] = field_config["required"]

        # Add description
        if "description" in field_config:
            json_schema_prop["description"] = field_config["description"]

        return json_schema_prop


# Create singleton instance
schema_validator = SchemaValidator()
