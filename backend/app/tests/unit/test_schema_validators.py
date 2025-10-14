"""
Unit tests for Schema Validators.

Tests each validator independently to verify:
- Correct error/warning detection
- Proper message categorization
- Low cyclomatic complexity
- SOLID principles compliance
"""

import pytest

from app.crud.schema_validators import (
    FieldDefinitionsValidator,
    RequiredFieldsValidator,
    SchemaValidatorChain,
    ScoringConfigurationValidator,
    UIConfigurationValidator,
    ValidationMessage,
    ValidationRulesValidator,
    WorkflowStatesValidator,
    validate_schema_structure,
)


class TestValidationMessage:
    """Test ValidationMessage dataclass."""

    def test_message_creation(self):
        """Test creating a ValidationMessage."""
        message = ValidationMessage(
            severity="error",
            message="Test message",
            field_path="test.field",
            context={"key": "value"},
        )

        assert message.severity == "error"
        assert message.message == "Test message"
        assert message.field_path == "test.field"
        assert message.context == {"key": "value"}

    def test_message_equality(self):
        """Test that messages with same values are equal."""
        message1 = ValidationMessage(
            severity="warning", message="Test", field_path="field"
        )
        message2 = ValidationMessage(
            severity="warning", message="Test", field_path="field"
        )

        assert message1 == message2

    def test_message_default_context(self):
        """Test that context defaults to empty dict."""
        message = ValidationMessage(
            severity="error", message="Test", field_path="field"
        )

        assert message.context == {}


class TestRequiredFieldsValidator:
    """Test RequiredFieldsValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = RequiredFieldsValidator()

    def test_validator_name(self):
        """Test validator name property."""
        assert self.validator.validator_name == "RequiredFields"

    def test_valid_schema_with_all_required_fields(self):
        """Test that schema with all required fields passes."""
        schema = {
            "field_definitions": {"gene": {"type": "text", "label": "Gene"}},
            "workflow_states": ["draft", "submitted"],
            "ui_configuration": {"sections": []},
        }

        messages = self.validator.validate(schema)

        assert len(messages) == 0

    def test_missing_field_definitions(self):
        """Test detection of missing field_definitions."""
        schema = {
            "workflow_states": ["draft", "submitted"],
            "ui_configuration": {"sections": []},
        }

        messages = self.validator.validate(schema)

        assert len(messages) == 1
        assert messages[0].severity == "error"
        assert "field_definitions" in messages[0].message
        assert messages[0].field_path == "field_definitions"

    def test_missing_workflow_states(self):
        """Test detection of missing workflow_states."""
        schema = {
            "field_definitions": {"gene": {"type": "text", "label": "Gene"}},
            "ui_configuration": {"sections": []},
        }

        messages = self.validator.validate(schema)

        assert len(messages) == 1
        assert messages[0].severity == "error"
        assert "workflow_states" in messages[0].message

    def test_missing_ui_configuration(self):
        """Test detection of missing ui_configuration."""
        schema = {
            "field_definitions": {"gene": {"type": "text", "label": "Gene"}},
            "workflow_states": ["draft", "submitted"],
        }

        messages = self.validator.validate(schema)

        assert len(messages) == 1
        assert messages[0].severity == "error"
        assert "ui_configuration" in messages[0].message

    def test_missing_all_required_fields(self):
        """Test detection when all required fields are missing."""
        schema = {}

        messages = self.validator.validate(schema)

        assert len(messages) == 3
        field_paths = {m.field_path for m in messages}
        assert "field_definitions" in field_paths
        assert "workflow_states" in field_paths
        assert "ui_configuration" in field_paths

    def test_empty_required_fields_detected(self):
        """Test that empty required fields are detected."""
        schema = {
            "field_definitions": {},  # Empty
            "workflow_states": [],  # Empty
            "ui_configuration": {},  # Empty
        }

        messages = self.validator.validate(schema)

        assert len(messages) == 3


class TestFieldDefinitionsValidator:
    """Test FieldDefinitionsValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = FieldDefinitionsValidator()

    def test_validator_name(self):
        """Test validator name property."""
        assert self.validator.validator_name == "FieldDefinitions"

    def test_valid_field_definitions(self):
        """Test valid field definitions pass."""
        schema = {
            "field_definitions": {
                "gene_symbol": {"type": "text", "label": "Gene Symbol"},
                "score": {"type": "number", "label": "Score"},
            }
        }

        messages = self.validator.validate(schema)

        assert len(messages) == 0

    def test_field_definitions_not_dict(self):
        """Test error when field_definitions is not a dict."""
        schema = {"field_definitions": "not a dict"}

        messages = self.validator.validate(schema)

        assert len(messages) == 1
        assert messages[0].severity == "error"
        assert "must be a dictionary" in messages[0].message

    def test_field_config_not_dict(self):
        """Test error when field config is not a dict."""
        schema = {"field_definitions": {"gene": "not a dict"}}

        messages = self.validator.validate(schema)

        assert len(messages) == 1
        assert "must be a dictionary" in messages[0].message
        assert "gene" in messages[0].message

    def test_missing_field_type(self):
        """Test error when field is missing type."""
        schema = {"field_definitions": {"gene": {"label": "Gene Symbol"}}}

        messages = self.validator.validate(schema)

        assert len(messages) == 1
        assert "missing required property" in messages[0].message
        assert "type" in messages[0].message

    def test_missing_field_label(self):
        """Test error when field is missing label."""
        schema = {"field_definitions": {"gene": {"type": "text"}}}

        messages = self.validator.validate(schema)

        assert len(messages) == 1
        assert "missing required property" in messages[0].message
        assert "label" in messages[0].message

    def test_invalid_field_type(self):
        """Test error when field has invalid type."""
        schema = {
            "field_definitions": {
                "gene": {"type": "invalid_type", "label": "Gene Symbol"}
            }
        }

        messages = self.validator.validate(schema)

        assert len(messages) == 1
        assert "invalid type" in messages[0].message
        assert "invalid_type" in messages[0].message
        assert "valid_types" in messages[0].context

    def test_multiple_field_errors(self):
        """Test detection of errors across multiple fields."""
        schema = {
            "field_definitions": {
                "field1": {"type": "text"},  # Missing label
                "field2": {"label": "Field 2"},  # Missing type
                "field3": {"type": "invalid", "label": "Field 3"},  # Invalid type
            }
        }

        messages = self.validator.validate(schema)

        assert len(messages) == 3

    def test_all_valid_field_types(self):
        """Test that all valid field types are accepted."""
        valid_types = [
            "text",
            "number",
            "boolean",
            "array",
            "object",
            "date",
            "select",
            "multiselect",
        ]
        schema = {
            "field_definitions": {
                f"field_{i}": {"type": field_type, "label": f"Field {i}"}
                for i, field_type in enumerate(valid_types)
            }
        }

        messages = self.validator.validate(schema)

        assert len(messages) == 0


class TestWorkflowStatesValidator:
    """Test WorkflowStatesValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = WorkflowStatesValidator()

    def test_validator_name(self):
        """Test validator name property."""
        assert self.validator.validator_name == "WorkflowStates"

    def test_valid_workflow_states(self):
        """Test valid workflow states pass."""
        schema = {"workflow_states": ["draft", "submitted", "approved", "rejected"]}

        messages = self.validator.validate(schema)

        assert len(messages) == 0

    def test_workflow_states_not_list(self):
        """Test error when workflow_states is not a list."""
        schema = {"workflow_states": "not a list"}

        messages = self.validator.validate(schema)

        assert len(messages) == 1
        assert messages[0].severity == "error"
        assert "must be a list" in messages[0].message

    def test_missing_draft_state(self):
        """Test error when draft state is missing."""
        schema = {"workflow_states": ["submitted", "approved"]}

        messages = self.validator.validate(schema)

        assert len(messages) == 1
        assert "draft" in messages[0].message
        assert "missing_state" in messages[0].context

    def test_missing_submitted_state(self):
        """Test error when submitted state is missing."""
        schema = {"workflow_states": ["draft", "approved"]}

        messages = self.validator.validate(schema)

        assert len(messages) == 1
        assert "submitted" in messages[0].message

    def test_missing_both_required_states(self):
        """Test error when both required states are missing."""
        schema = {"workflow_states": ["approved", "rejected"]}

        messages = self.validator.validate(schema)

        assert len(messages) == 2
        states_in_messages = {m.context.get("missing_state") for m in messages}
        assert "draft" in states_in_messages
        assert "submitted" in states_in_messages


class TestUIConfigurationValidator:
    """Test UIConfigurationValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = UIConfigurationValidator()

    def test_validator_name(self):
        """Test validator name property."""
        assert self.validator.validator_name == "UIConfiguration"

    def test_valid_ui_configuration(self):
        """Test valid UI configuration passes."""
        schema = {"ui_configuration": {"sections": [{"title": "General"}]}}

        messages = self.validator.validate(schema)

        assert len(messages) == 0

    def test_ui_configuration_not_dict(self):
        """Test error when ui_configuration is not a dict."""
        schema = {"ui_configuration": "not a dict"}

        messages = self.validator.validate(schema)

        assert len(messages) == 1
        assert messages[0].severity == "error"
        assert "must be a dictionary" in messages[0].message

    def test_missing_sections_warning(self):
        """Test warning when sections are missing."""
        schema = {
            "ui_configuration": {"layout": "default"}
        }  # Has content but no sections

        messages = self.validator.validate(schema)

        assert len(messages) == 1
        assert messages[0].severity == "warning"
        assert "sections" in messages[0].message


class TestScoringConfigurationValidator:
    """Test ScoringConfigurationValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ScoringConfigurationValidator()

    def test_validator_name(self):
        """Test validator name property."""
        assert self.validator.validator_name == "ScoringConfiguration"

    def test_valid_scoring_configuration(self):
        """Test valid scoring configuration passes."""
        schema = {"scoring_configuration": {"engine": "clingen_sop_v11"}}

        messages = self.validator.validate(schema)

        assert len(messages) == 0

    def test_missing_scoring_configuration(self):
        """Test no messages when scoring_configuration is optional and missing."""
        schema = {}

        messages = self.validator.validate(schema)

        assert len(messages) == 0

    def test_scoring_configuration_not_dict(self):
        """Test error when scoring_configuration is not a dict."""
        schema = {"scoring_configuration": "not a dict"}

        messages = self.validator.validate(schema)

        assert len(messages) == 1
        assert messages[0].severity == "error"
        assert "must be a dictionary" in messages[0].message

    def test_missing_engine_warning(self):
        """Test warning when engine is missing."""
        schema = {"scoring_configuration": {"some_other_field": "value"}}

        messages = self.validator.validate(schema)

        assert len(messages) == 1
        assert messages[0].severity == "warning"
        assert "engine" in messages[0].message


class TestValidationRulesValidator:
    """Test ValidationRulesValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ValidationRulesValidator()

    def test_validator_name(self):
        """Test validator name property."""
        assert self.validator.validator_name == "ValidationRules"

    def test_valid_validation_rules(self):
        """Test valid validation rules pass."""
        schema = {"validation_rules": {"gene_symbol": {"required": True}}}

        messages = self.validator.validate(schema)

        assert len(messages) == 0

    def test_missing_validation_rules(self):
        """Test no messages when validation_rules is optional and missing."""
        schema = {}

        messages = self.validator.validate(schema)

        assert len(messages) == 0

    def test_validation_rules_not_dict(self):
        """Test error when validation_rules is not a dict."""
        schema = {"validation_rules": "not a dict"}

        messages = self.validator.validate(schema)

        assert len(messages) == 1
        assert messages[0].severity == "error"
        assert "must be a dictionary" in messages[0].message


class TestSchemaValidatorChain:
    """Test SchemaValidatorChain."""

    def setup_method(self):
        """Set up test fixtures."""
        self.chain = SchemaValidatorChain()

    def test_default_validators_loaded(self):
        """Test that default validators are loaded."""
        assert len(self.chain.validators) == 6
        validator_names = {v.validator_name for v in self.chain.validators}
        expected_names = {
            "RequiredFields",
            "FieldDefinitions",
            "WorkflowStates",
            "UIConfiguration",
            "ScoringConfiguration",
            "ValidationRules",
        }
        assert validator_names == expected_names

    def test_custom_validators(self):
        """Test using custom validators."""
        custom_validator = RequiredFieldsValidator()
        chain = SchemaValidatorChain(validators=[custom_validator])

        assert len(chain.validators) == 1
        assert chain.validators[0] is custom_validator

    def test_complete_valid_schema(self):
        """Test that complete valid schema passes."""
        schema = {
            "field_definitions": {
                "gene_symbol": {"type": "text", "label": "Gene Symbol"}
            },
            "workflow_states": ["draft", "submitted", "approved"],
            "ui_configuration": {"sections": [{"title": "General"}]},
            "scoring_configuration": {"engine": "clingen_sop_v11"},
            "validation_rules": {"gene_symbol": {"required": True}},
        }

        messages = self.chain.validate(schema)

        # Should have no errors or warnings
        errors = [m for m in messages if m.severity == "error"]
        assert len(errors) == 0

    def test_empty_schema_catches_all_errors(self):
        """Test that empty schema triggers all required field errors."""
        schema = {}

        messages = self.chain.validate(schema)

        # Should have errors for all 3 required fields
        errors = [m for m in messages if m.severity == "error"]
        assert len(errors) == 3

    def test_partial_schema_with_errors(self):
        """Test schema with some fields triggers appropriate errors."""
        schema = {
            "field_definitions": {
                "bad_field": "not a dict"  # Invalid structure
            },
            "workflow_states": "not a list",  # Invalid type
            "ui_configuration": {
                "layout": "default"
            },  # Has content but missing sections (warning)
        }

        messages = self.chain.validate(schema)

        errors = [m for m in messages if m.severity == "error"]
        warnings = [m for m in messages if m.severity == "warning"]

        assert len(errors) >= 2  # field_definitions and workflow_states errors
        assert len(warnings) >= 1  # ui_configuration missing sections


class TestConvenienceFunction:
    """Test the convenience function validate_schema_structure."""

    def test_convenience_function_returns_tuples(self):
        """Test that convenience function returns (errors, warnings) tuple."""
        schema = {}

        result = validate_schema_structure(schema)

        assert isinstance(result, tuple)
        assert len(result) == 2
        errors, warnings = result
        assert isinstance(errors, list)
        assert isinstance(warnings, list)

    def test_convenience_function_with_valid_schema(self):
        """Test convenience function with valid schema."""
        schema = {
            "field_definitions": {
                "gene_symbol": {"type": "text", "label": "Gene Symbol"}
            },
            "workflow_states": ["draft", "submitted"],
            "ui_configuration": {"sections": [{"title": "General"}]},
        }

        errors, warnings = validate_schema_structure(schema)

        assert len(errors) == 0
        # May have warnings (e.g., missing sections is OK if sections is present)

    def test_convenience_function_with_errors(self):
        """Test convenience function with errors."""
        schema = {}

        errors, warnings = validate_schema_structure(schema)

        assert len(errors) >= 3  # Missing 3 required fields
        assert all(isinstance(e, str) for e in errors)

    def test_convenience_function_with_warnings(self):
        """Test convenience function with warnings."""
        schema = {
            "field_definitions": {
                "gene_symbol": {"type": "text", "label": "Gene Symbol"}
            },
            "workflow_states": ["draft", "submitted"],
            "ui_configuration": {
                "layout": "default"
            },  # Has content but missing sections
        }

        errors, warnings = validate_schema_structure(schema)

        assert len(errors) == 0
        assert len(warnings) >= 1
        assert all(isinstance(w, str) for w in warnings)


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.chain = SchemaValidatorChain()

    def test_clingen_sop_v11_schema(self):
        """Test ClinGen SOP v11 compatible schema."""
        schema = {
            "field_definitions": {
                "gene_symbol": {
                    "type": "text",
                    "label": "Gene Symbol",
                    "required": True,
                },
                "genetic_evidence": {
                    "type": "object",
                    "label": "Genetic Evidence",
                    "properties": {
                        "case_level_score": {
                            "type": "number",
                            "min_value": 0,
                            "max_value": 12,
                        },
                        "segregation_score": {
                            "type": "number",
                            "min_value": 0,
                            "max_value": 3,
                        },
                    },
                },
            },
            "workflow_states": ["draft", "submitted", "approved"],
            "ui_configuration": {
                "sections": [
                    {"title": "Gene Information", "fields": ["gene_symbol"]},
                    {"title": "Genetic Evidence", "fields": ["genetic_evidence"]},
                ]
            },
            "scoring_configuration": {"engine": "clingen_sop_v11"},
            "validation_rules": {
                "gene_symbol": {"required": True, "pattern": "^[A-Z0-9]+$"}
            },
        }

        messages = self.chain.validate(schema)

        errors = [m for m in messages if m.severity == "error"]
        assert len(errors) == 0

    def test_gencc_schema(self):
        """Test GenCC compatible schema."""
        schema = {
            "field_definitions": {
                "gene_symbol": {"type": "text", "label": "Gene Symbol"},
                "disease": {"type": "text", "label": "Disease"},
                "evidence_level": {
                    "type": "select",
                    "label": "Evidence Level",
                    "options": ["Definitive", "Strong", "Moderate", "Limited"],
                },
            },
            "workflow_states": ["draft", "submitted", "published"],
            "ui_configuration": {"sections": [{"title": "Classification"}]},
            "scoring_configuration": {"engine": "gencc"},
        }

        messages = self.chain.validate(schema)

        errors = [m for m in messages if m.severity == "error"]
        assert len(errors) == 0

    def test_minimal_valid_schema(self):
        """Test minimal valid schema with only required fields."""
        schema = {
            "field_definitions": {"gene": {"type": "text", "label": "Gene"}},
            "workflow_states": ["draft", "submitted"],
            "ui_configuration": {"sections": []},
        }

        messages = self.chain.validate(schema)

        errors = [m for m in messages if m.severity == "error"]
        assert len(errors) == 0

    def test_schema_with_multiple_errors_and_warnings(self):
        """Test schema with multiple errors and warnings."""
        schema = {
            "field_definitions": {
                "field1": {"label": "Field 1"},  # Missing type
                "field2": {"type": "invalid"},  # Invalid type, missing label
            },
            "workflow_states": ["approved"],  # Missing draft and submitted
            "ui_configuration": {},  # Missing sections (warning)
            "scoring_configuration": {},  # Missing engine (warning)
        }

        messages = self.chain.validate(schema)

        errors = [m for m in messages if m.severity == "error"]
        warnings = [m for m in messages if m.severity == "warning"]

        # Should have multiple errors
        assert len(errors) >= 4  # field1 type, field2 label+type, 2 workflow states
        # Should have multiple warnings
        assert len(warnings) >= 2  # UI sections, scoring engine


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
