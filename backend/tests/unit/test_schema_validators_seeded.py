"""#207: the validator accepts the schema formats the seeds and the renderer use."""

from app.crud.schema_validators import (
    FieldDefinitionsValidator,
    ScoringConfigurationValidator,
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


class TestStricterSeededFormats:
    def test_section_fields_are_validated(self) -> None:
        bad = {
            "field_definitions": {"sections": [{"fields": [{"id": "x", "label": "X"}]}]}
        }
        good = {
            "field_definitions": {
                "sections": [
                    {
                        "fields": [
                            {"id": "x", "type": "external_reference", "label": "X"}
                        ]
                    }
                ]
            }
        }

        assert len(FieldDefinitionsValidator().validate(bad)) == 1
        assert FieldDefinitionsValidator().validate(good) == []

    def test_state_keyed_map_values_must_be_dicts(self) -> None:
        validator = WorkflowStatesValidator()

        assert validator.validate({"workflow_states": {"draft": 5}})
        assert validator.validate({"workflow_states": {"transitions": {"a": ["b"]}}})

    def test_unknown_scoring_engine_is_reported(self) -> None:
        validator = ScoringConfigurationValidator()

        found = validator.validate({"scoring_configuration": {"engine": "nope"}})
        assert [m.severity for m in found] == ["warning"]
        assert (
            validator.validate({"scoring_configuration": {"engine": "clingen_sop_v11"}})
            == []
        )
