"""
Schema Structure Validators.

Following SOLID principles to break down complex schema validation:
- Single Responsibility: Each validator checks ONE aspect
- Open/Closed: Easy to add new validators without modification
- Liskov Substitution: All validators follow same interface
- Interface Segregation: Focused, single-purpose validator interface
- Dependency Inversion: Depend on SchemaValidator abstraction

Extracts the complex validate_schema_structure logic (C901 ~18)
into maintainable, testable, focused validator classes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass
class ValidationMessage:
    """
    Represents a validation error or warning.

    Provides structure for validation feedback with severity levels.
    """

    severity: str  # "error" or "warning"
    message: str
    field_path: str  # JSON path to the problematic field
    context: dict[str, Any] = field(default_factory=dict)


class SchemaValidator(ABC):
    """
    Abstract base validator following Interface Segregation Principle.

    Each validator focuses on ONE aspect of schema validation.
    """

    @abstractmethod
    def validate(self, schema_data: dict[str, Any]) -> list[ValidationMessage]:
        """
        Validate a specific aspect of the schema.

        Args:
            schema_data: The schema dictionary to validate

        Returns:
            List of ValidationMessage objects (errors or warnings)
        """
        pass

    @property
    @abstractmethod
    def validator_name(self) -> str:
        """Name of this validator for logging."""
        pass


class RequiredFieldsValidator(SchemaValidator):
    """Validates that required top-level fields are present."""

    @property
    def validator_name(self) -> str:
        return "RequiredFields"

    def validate(self, schema_data: dict[str, Any]) -> list[ValidationMessage]:
        """
        Validate required top-level schema fields.

        Complexity: 3 (simple iteration + check)

        Args:
            schema_data: The schema to validate

        Returns:
            List of validation messages
        """
        messages = []

        # Data-driven approach - easy to add/remove required fields
        required_fields = ["field_definitions", "workflow_states", "ui_configuration"]

        for field_name in required_fields:
            if field_name not in schema_data or not schema_data[field_name]:
                messages.append(
                    ValidationMessage(
                        severity="error",
                        message=f"Missing required field: {field_name}",
                        field_path=field_name,
                    )
                )

        return messages


class FieldDefinitionsValidator(SchemaValidator):
    """Validates field_definitions structure and content."""

    # Valid field types (data-driven)
    VALID_FIELD_TYPES: ClassVar[list[str]] = [
        "text",
        "number",
        "boolean",
        "array",
        "object",
        "date",
        "select",
        "multiselect",
    ]

    @property
    def validator_name(self) -> str:
        return "FieldDefinitions"

    def validate(self, schema_data: dict[str, Any]) -> list[ValidationMessage]:
        """
        Validate field definitions.

        Complexity: 4 (guard + iteration + two validations)

        Args:
            schema_data: The schema to validate

        Returns:
            List of validation messages
        """
        messages = []

        if "field_definitions" not in schema_data:
            return messages  # Already caught by RequiredFieldsValidator

        field_defs = schema_data["field_definitions"]

        # Validate structure type
        if not isinstance(field_defs, dict):
            messages.append(
                ValidationMessage(
                    severity="error",
                    message="field_definitions must be a dictionary",
                    field_path="field_definitions",
                )
            )
            return messages  # Can't continue if not a dict

        # Validate each field definition
        for field_name, field_config in field_defs.items():
            messages.extend(self._validate_single_field(field_name, field_config))

        return messages

    def _validate_single_field(
        self, field_name: str, field_config: Any
    ) -> list[ValidationMessage]:
        """
        Validate a single field definition.

        Complexity: 3 (three independent checks)

        Args:
            field_name: Name of the field
            field_config: Configuration dictionary for the field

        Returns:
            List of validation messages for this field
        """
        messages = []
        field_path = f"field_definitions.{field_name}"

        # Check if field_config is a dict
        if not isinstance(field_config, dict):
            messages.append(
                ValidationMessage(
                    severity="error",
                    message=f"Field configuration for '{field_name}' must be a dictionary",
                    field_path=field_path,
                )
            )
            return messages  # Can't continue if not a dict

        # Check required properties
        required_props = {"type": "type", "label": "label"}
        for prop_name, prop_label in required_props.items():
            if prop_name not in field_config:
                messages.append(
                    ValidationMessage(
                        severity="error",
                        message=f"Field '{field_name}' missing required property: {prop_label}",
                        field_path=f"{field_path}.{prop_name}",
                    )
                )

        # Validate field type
        if "type" in field_config:
            field_type = field_config["type"]
            if field_type not in self.VALID_FIELD_TYPES:
                messages.append(
                    ValidationMessage(
                        severity="error",
                        message=f"Field '{field_name}' has invalid type: {field_type}",
                        field_path=f"{field_path}.type",
                        context={"valid_types": self.VALID_FIELD_TYPES},
                    )
                )

        return messages


class WorkflowStatesValidator(SchemaValidator):
    """Validates workflow_states configuration."""

    @property
    def validator_name(self) -> str:
        return "WorkflowStates"

    def validate(self, schema_data: dict[str, Any]) -> list[ValidationMessage]:
        """
        Validate workflow states.

        Complexity: 3 (guard + type check + required states)

        Args:
            schema_data: The schema to validate

        Returns:
            List of validation messages
        """
        messages = []

        if "workflow_states" not in schema_data:
            return messages  # Already caught by RequiredFieldsValidator

        workflow_states = schema_data["workflow_states"]

        # Validate structure type
        if not isinstance(workflow_states, list):
            messages.append(
                ValidationMessage(
                    severity="error",
                    message="workflow_states must be a list",
                    field_path="workflow_states",
                )
            )
            return messages

        # Check for required states
        required_states = ["draft", "submitted"]
        for state in required_states:
            if state not in workflow_states:
                messages.append(
                    ValidationMessage(
                        severity="error",
                        message=f"Missing required workflow state: {state}",
                        field_path="workflow_states",
                        context={"missing_state": state},
                    )
                )

        return messages


class UIConfigurationValidator(SchemaValidator):
    """Validates ui_configuration structure."""

    @property
    def validator_name(self) -> str:
        return "UIConfiguration"

    def validate(self, schema_data: dict[str, Any]) -> list[ValidationMessage]:
        """
        Validate UI configuration.

        Complexity: 3 (guard + type check + sections check)

        Args:
            schema_data: The schema to validate

        Returns:
            List of validation messages
        """
        messages = []

        if "ui_configuration" not in schema_data:
            return messages  # Already caught by RequiredFieldsValidator

        ui_config = schema_data["ui_configuration"]

        # Validate structure type
        if not isinstance(ui_config, dict):
            messages.append(
                ValidationMessage(
                    severity="error",
                    message="ui_configuration must be a dictionary",
                    field_path="ui_configuration",
                )
            )
            return messages

        # Check for sections (warning, not error)
        if "sections" not in ui_config:
            messages.append(
                ValidationMessage(
                    severity="warning",
                    message="UI configuration missing 'sections' - form may not render properly",
                    field_path="ui_configuration.sections",
                )
            )

        return messages


class ScoringConfigurationValidator(SchemaValidator):
    """Validates optional scoring_configuration."""

    @property
    def validator_name(self) -> str:
        return "ScoringConfiguration"

    def validate(self, schema_data: dict[str, Any]) -> list[ValidationMessage]:
        """
        Validate scoring configuration if present.

        Complexity: 3 (guard + type check + engine check)

        Args:
            schema_data: The schema to validate

        Returns:
            List of validation messages
        """
        messages = []

        if "scoring_configuration" not in schema_data:
            return messages  # Optional field

        scoring_config = schema_data["scoring_configuration"]

        # Validate structure type
        if not isinstance(scoring_config, dict):
            messages.append(
                ValidationMessage(
                    severity="error",
                    message="scoring_configuration must be a dictionary",
                    field_path="scoring_configuration",
                )
            )
            return messages

        # Check for engine specification (warning)
        if "engine" not in scoring_config:
            messages.append(
                ValidationMessage(
                    severity="warning",
                    message="Scoring configuration missing 'engine' specification",
                    field_path="scoring_configuration.engine",
                )
            )

        return messages


class ValidationRulesValidator(SchemaValidator):
    """Validates optional validation_rules."""

    @property
    def validator_name(self) -> str:
        return "ValidationRules"

    def validate(self, schema_data: dict[str, Any]) -> list[ValidationMessage]:
        """
        Validate validation rules if present.

        Complexity: 2 (guard + type check)

        Args:
            schema_data: The schema to validate

        Returns:
            List of validation messages
        """
        messages = []

        if "validation_rules" not in schema_data:
            return messages  # Optional field

        validation_rules = schema_data["validation_rules"]

        # Validate structure type
        if not isinstance(validation_rules, dict):
            messages.append(
                ValidationMessage(
                    severity="error",
                    message="validation_rules must be a dictionary",
                    field_path="validation_rules",
                )
            )

        return messages


class SchemaValidatorChain:
    """
    Chain of validators following Chain of Responsibility pattern.

    Follows:
    - Open/Closed Principle: Add validators without modifying this class
    - Dependency Inversion: Depends on SchemaValidator abstraction
    """

    def __init__(self, validators: list[SchemaValidator] | None = None):
        """
        Initialize validator chain.

        Args:
            validators: Optional list of custom validators (defaults to standard set)
        """
        self.validators = validators or self._default_validators()

    @staticmethod
    def _default_validators() -> list[SchemaValidator]:
        """Get default set of validators in logical order."""
        return [
            RequiredFieldsValidator(),
            FieldDefinitionsValidator(),
            WorkflowStatesValidator(),
            UIConfigurationValidator(),
            ScoringConfigurationValidator(),
            ValidationRulesValidator(),
        ]

    def validate(self, schema_data: dict[str, Any]) -> list[ValidationMessage]:
        """
        Run all validators in chain.

        Complexity: 2 (simple iteration)

        Args:
            schema_data: The schema to validate

        Returns:
            List of all validation messages from all validators
        """
        all_messages = []

        for validator in self.validators:
            messages = validator.validate(schema_data)
            all_messages.extend(messages)

        return all_messages


def validate_schema_structure(
    schema_data: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """
    Convenience function for backward compatibility.

    Validates schema structure and returns errors and warnings.

    Complexity: 2 (delegation + list comprehensions)

    Args:
        schema_data: The schema dictionary to validate

    Returns:
        Tuple of (errors, warnings) as lists of strings
    """
    chain = SchemaValidatorChain()
    messages = chain.validate(schema_data)

    errors = [msg.message for msg in messages if msg.severity == "error"]
    warnings = [msg.message for msg in messages if msg.severity == "warning"]

    return errors, warnings
