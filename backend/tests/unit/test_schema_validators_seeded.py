"""#207: the validator accepts the schema formats the seeds and the renderer use."""

from app.crud.schema_validators import (
    FieldDefinitionsValidator,
    WorkflowStatesValidator,
)


class TestSeededFieldFormats:
    validator = FieldDefinitionsValidator()

    def test_seeded_json_schema_style_fields_accepted(self) -> None:
        """#207: renderer accepts title instead of label and JSON-schema types."""
        schema = {
            "field_definitions": {
                "summary": {"type": "string", "title": "Summary"},
                "count": {"type": "integer", "title": "Count"},
                "kind": {"type": "enum", "title": "Kind", "enum": ["a", "b"]},
            }
        }

        assert self.validator.validate(schema) == []

    def test_sectioned_field_definitions_accepted(self) -> None:
        schema = {"field_definitions": {"sections": [{"id": "a", "fields": []}]}}

        assert self.validator.validate(schema) == []


class TestSeededWorkflowStates:
    validator = WorkflowStatesValidator()

    def test_state_keyed_map_is_accepted(self) -> None:
        """#207: seeded SOP schemas key states by name with custom names."""
        schema = {"workflow_states": {"entry": {"label": "Entry"}, "active": {}}}

        assert self.validator.validate(schema) == []
