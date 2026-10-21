"""Validation rules, business rules, scoring hooks and schema-definition checks
for the schema validation engine (app/core/schema_validator.py)."""

import pytest

from app.core.schema_validator import SchemaValidator
from tests.unit.schema_validator_support import (
    messages as _messages,
    run as _run,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def validator() -> SchemaValidator:
    return SchemaValidator()


# =============================================================================
# Validation rules
# =============================================================================


class TestValidationRules:
    def test_exists_condition_fails_when_missing(self, validator: SchemaValidator):
        result = _run(
            validator,
            {},
            {},
            validation_rules={
                "need_gene": {
                    "type": "condition",
                    "condition": "exists(gene)",
                    "message": "Gene is needed",
                }
            },
        )

        assert result.is_valid is False
        assert result.errors[0]["message"] == "Gene is needed"
        assert result.errors[0]["type"] == "condition"

    def test_compound_condition_is_limited_with_warning(
        self, validator: SchemaValidator
    ):
        result = _run(
            validator,
            {},
            {},
            validation_rules={
                "c": {"type": "condition", "condition": "exists(a) && exists(b)"}
            },
        )

        assert result.is_valid is True
        assert _messages(result, "warnings") == [
            "Complex conditions not fully supported: c"
        ]

    def test_dependency_rule(self, validator: SchemaValidator):
        rules = {
            "dep": {
                "type": "dependency",
                "depends_on": "pmid",
                "field": "rationale",
            }
        }

        bad = _run(validator, {"pmid": "123"}, {}, validation_rules=rules)
        ok = _run(
            validator,
            {"pmid": "123", "rationale": "why"},
            {},
            validation_rules=rules,
        )

        assert bad.errors[0]["field"] == "rationale"
        assert bad.errors[0]["type"] == "dependency"
        assert ok.is_valid is True

    def test_calculation_rule_is_reported_as_limitation(
        self, validator: SchemaValidator
    ):
        result = _run(
            validator,
            {},
            {},
            validation_rules={"sum": {"type": "calculation"}},
        )

        assert _messages(result, "warnings") == [
            "Calculation rules not fully implemented: sum"
        ]

    def test_unknown_rule_type_ignored(self, validator: SchemaValidator):
        result = _run(validator, {}, {}, validation_rules={"x": {"type": "mystery"}})

        assert result.is_valid is True
        assert result.warnings == []

    def test_broken_rule_becomes_system_warning(self, validator: SchemaValidator):
        result = _run(
            validator,
            {},
            {},
            validation_rules={"broken": "not-a-dict"},
        )

        assert result.is_valid is True
        assert result.warnings[0]["type"] == "system"
        assert "Error applying rule broken" in result.warnings[0]["message"]


# =============================================================================
# Business rules
# =============================================================================


class TestBusinessRules:
    def test_genetic_total_over_twelve_violates(self, validator: SchemaValidator):
        result = _run(
            validator,
            {"genetic_evidence": {"total_score": 13}},
            {},
            business_rules=["clingen_genetic_evidence"],
        )

        assert result.is_valid is False
        assert result.business_rule_violations[0]["rule"] == "clingen_genetic_max_score"

    def test_genetic_mixed_case_and_segregation_warns(self, validator):
        result = _run(
            validator,
            {"genetic_evidence": {"case_level_score": 2, "segregation_score": 1}},
            {},
            business_rules=["clingen_genetic_evidence"],
        )

        assert result.is_valid is True
        assert any("double-counting" in w["message"] for w in result.warnings)

    def test_experimental_total_over_six_violates(self, validator):
        result = _run(
            validator,
            {"experimental_evidence": {"total_score": 7}},
            {},
            business_rules=["clingen_experimental_evidence"],
        )

        assert result.business_rule_violations[0]["rule"] == (
            "clingen_experimental_max_score"
        )

    def test_contradictory_evidence_requires_description(self, validator):
        missing = _run(
            validator,
            {"contradictory_evidence": {"has_contradictory": True}},
            {},
            business_rules=["clingen_contradictory_evidence"],
        )
        present = _run(
            validator,
            {
                "contradictory_evidence": {
                    "has_contradictory": True,
                    "description": "Conflicting segregation",
                }
            },
            {},
            business_rules=["clingen_contradictory_evidence"],
        )

        assert missing.business_rule_violations[0]["rule"] == (
            "clingen_contradictory_description"
        )
        assert present.business_rule_violations == []

    @pytest.mark.parametrize(
        ("classification", "violates"),
        [("Definitive", False), ("Possible", True), ("", False)],
    )
    def test_gencc_classification_terms(self, validator, classification, violates):
        result = _run(
            validator,
            {"classification": classification},
            {},
            business_rules=["gencc_classification"],
        )

        assert (len(result.business_rule_violations) == 1) is violates

    def test_unknown_business_rule_ignored(self, validator: SchemaValidator):
        result = _run(validator, {}, {}, business_rules=["does_not_exist"])

        assert result.is_valid is True

    def test_business_rule_exception_becomes_warning(self, validator: SchemaValidator):
        """A list where a dict is expected makes the rule raise; it must not crash."""
        result = _run(
            validator,
            {"genetic_evidence": ["not", "a", "dict"]},
            {},
            business_rules=["clingen_genetic_evidence"],
        )

        assert result.is_valid is True
        assert result.warnings[0]["type"] == "system"
        assert result.warnings[0]["field"] == "business_rules"


# =============================================================================
# Scoring hooks, suggestions
# =============================================================================


class TestScoringHooks:
    def test_clingen_scores_summed(self, validator: SchemaValidator):
        data = {
            "genetic_evidence": {
                "case_level_score": 3,
                "segregation_score": 1,
                "case_control_score": 2,
            },
            "experimental_evidence": {
                "functional_score": 1,
                "model_system_score": 0.5,
                "rescue_score": 0.5,
            },
        }

        result = _run(validator, data, {}, scoring_configuration={"engine": "clingen"})

        assert result.score_calculations == {
            "genetic_evidence_score": 6,
            "experimental_evidence_score": 2,
            "total_score": 8,
        }

    def test_placeholder_engines(self, validator: SchemaValidator):
        gencc = _run(validator, {}, {}, scoring_configuration={"engine": "gencc"})
        qual = _run(validator, {}, {}, scoring_configuration={"engine": "qualitative"})
        unknown = _run(validator, {}, {}, scoring_configuration={"engine": "x"})

        assert gencc.score_calculations == {"gencc_score": 0.0}
        assert qual.score_calculations == {"qualitative_score": 0.0}
        assert unknown.score_calculations == {}

    def test_suggestions(self, validator: SchemaValidator):
        defs = {
            "gene": {"type": "text", "required": True},
            "notes": {"type": "text", "description": "Free-text remarks"},
            "other": {"type": "text"},
        }

        result = _run(validator, {"gene": "ABC"}, defs)

        assert (
            "Consider adding notes: Free-text remarks" in result.suggested_improvements
        )
        assert any("incomplete" in s for s in result.suggested_improvements)

    def test_warning_suggestion(self, validator: SchemaValidator):
        result = _run(validator, {"b": "x"}, {"b": {"type": "boolean"}})

        assert "Address validation warnings to improve data quality." not in (
            result.suggested_improvements
        )
        result = _run(validator, {"s": 1}, {"s": {"type": "select"}})
        assert "Address validation warnings to improve data quality." in (
            result.suggested_improvements
        )


# =============================================================================
# Schema definition validation
# =============================================================================


class TestValidateSchemaDefinition:
    def test_missing_top_level_keys(self, validator: SchemaValidator):
        result = validator.validate_schema_definition({})

        assert result.is_valid is False
        assert _messages(result) == [
            "Missing required field: field_definitions",
            "Missing required field: workflow_states",
        ]

    def test_field_definition_shape(self, validator: SchemaValidator):
        result = validator.validate_schema_definition(
            {
                "field_definitions": {"a": "not-a-dict", "b": {}},
                "workflow_states": ["draft", "submitted"],
            }
        )

        assert "Field 'a' configuration must be an object" in _messages(result)
        assert "Field 'b' missing required 'type' property" in _messages(result)
        assert "Field 'b' missing 'label' property" in _messages(result, "warnings")

    def test_field_definitions_must_be_dict(self, validator: SchemaValidator):
        result = validator.validate_schema_definition(
            {"field_definitions": [], "workflow_states": ["draft", "submitted"]}
        )

        assert _messages(result) == ["field_definitions must be a dictionary"]

    def test_workflow_states_checks(self, validator: SchemaValidator):
        missing = validator.validate_schema_definition(
            {"field_definitions": {}, "workflow_states": ["draft"]}
        )
        wrong_shape = validator.validate_schema_definition(
            {"field_definitions": {}, "workflow_states": {"draft": 1}}
        )

        assert _messages(missing) == ["Missing required workflow state: submitted"]
        assert _messages(wrong_shape) == ["Workflow states must be an array"]

    def test_ui_and_scoring_warnings(self, validator: SchemaValidator):
        result = validator.validate_schema_definition(
            {
                "field_definitions": {"a": {"type": "text", "label": "A"}},
                "workflow_states": ["draft", "submitted"],
                "ui_configuration": {},
                "scoring_configuration": {},
            }
        )

        assert result.is_valid is True
        warnings = _messages(result, "warnings")
        assert "Missing 'sections' - form may not render properly" in warnings
        assert "Missing 'engine' specification" in warnings

    def test_complete_definition_is_valid(self, validator: SchemaValidator):
        result = validator.validate_schema_definition(
            {
                "field_definitions": {"a": {"type": "text", "label": "A"}},
                "workflow_states": ["draft", "submitted"],
                "ui_configuration": {"sections": []},
                "scoring_configuration": {"engine": "clingen"},
            }
        )

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []


# =============================================================================
# JSON Schema generation
# =============================================================================


class TestGenerateJsonSchema:
    def test_sectioned_field_definitions_are_flattened(
        self, validator: SchemaValidator
    ):
        # Shape seeded by migration 016 (ClinGen Precuration)
        schema = validator.generate_json_schema(
            {
                "field_definitions": {
                    "sections": [
                        {
                            "id": "disease_entity",
                            "fields": [
                                {
                                    "id": "disease_name",
                                    "type": "text",
                                    "required": True,
                                },
                                {"id": "note", "type": "textarea", "required": False},
                            ],
                        },
                        {
                            "id": "inheritance",
                            "fields": [
                                {
                                    "id": "mode_of_inheritance",
                                    "type": "select",
                                    "options": [
                                        {"value": "AD", "label": "Autosomal Dominant"}
                                    ],
                                }
                            ],
                        },
                    ]
                }
            }
        )
        assert set(schema["properties"]) == {
            "disease_name",
            "note",
            "mode_of_inheritance",
        }
        assert schema["required"] == ["disease_name"]
        assert schema["properties"]["mode_of_inheritance"]["enumOptions"] == [
            {"value": "AD", "label": "Autosomal Dominant"}
        ]

    def test_select_emits_labelled_enum_options_and_keeps_enum(
        self, validator: SchemaValidator
    ):
        schema = validator.generate_json_schema(
            {
                "field_definitions": {
                    "moi": {
                        "type": "select",
                        "options": [
                            "autosomal_dominant",
                            "AD",
                            {"value": "x_linked", "label": "X-linked (custom)"},
                            {"value": "other_thing"},
                        ],
                    },
                    "tags": {"type": "multiselect", "options": ["a_b"]},
                    "rows": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "kind": {"type": "select", "options": ["case_level"]}
                            },
                        },
                    },
                }
            }
        )
        moi = schema["properties"]["moi"]
        assert moi["enum"] == ["autosomal_dominant", "AD", "x_linked", "other_thing"]
        assert moi["enumOptions"] == [
            {"value": "autosomal_dominant", "label": "Autosomal dominant"},
            {"value": "AD", "label": "AD"},
            {"value": "x_linked", "label": "X-linked (custom)"},
            {"value": "other_thing", "label": "Other thing"},
        ]
        assert schema["properties"]["tags"]["enumOptions"] == [
            {"value": "a_b", "label": "A b"}
        ]
        nested = schema["properties"]["rows"]["items"]["properties"]["kind"]
        assert nested["enumOptions"] == [{"value": "case_level", "label": "Case level"}]

    def test_carries_ui_and_scoring_configuration(self, validator: SchemaValidator):
        schema = validator.generate_json_schema(
            {
                "ui_configuration": {"layout": {"tabs": [{"id": "a"}]}},
                "scoring_configuration": {"engine": "x"},
            }
        )

        assert schema["ui_configuration"]["layout"]["tabs"] == [{"id": "a"}]
        assert schema["scoring_configuration"] == {"engine": "x"}

    def test_string_field_has_no_unknown_type_warning(self, validator: SchemaValidator):
        result = validator.validate_evidence_data(
            {"evidence_summary": "text"},
            {"field_definitions": {"evidence_summary": {"type": "string"}}},
        )

        assert not any("Unknown field type" in w["message"] for w in result.warnings)

    def test_envelope_and_required(self, validator: SchemaValidator):
        schema = validator.generate_json_schema({})

        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert schema["type"] == "object"
        assert schema["properties"] == {}
        assert schema["required"] == []

    def test_scalar_constraints(self, validator: SchemaValidator):
        schema = validator.generate_json_schema(
            {
                "field_definitions": {
                    "name": {
                        "type": "text",
                        "min_length": 1,
                        "max_length": 10,
                        "pattern": "^a",
                        "required": True,
                        "description": "Name",
                    },
                    "count": {"type": "number", "min": 0, "max": 5, "step": 1},
                    "flag": {"type": "boolean"},
                    "when": {"type": "date"},
                    "weird": {"type": "colour"},
                }
            }
        )

        props = schema["properties"]
        assert schema["required"] == ["name"]
        assert props["name"] == {
            "type": "string",
            "minLength": 1,
            "maxLength": 10,
            "pattern": "^a",
            "description": "Name",
        }
        assert props["count"] == {
            "type": "number",
            "minimum": 0,
            "maximum": 5,
            "multipleOf": 1,
        }
        assert props["flag"] == {"type": "boolean"}
        assert props["when"] == {"type": "string"}
        assert props["weird"] == {"type": "string"}

    def test_enum_and_multiselect(self, validator: SchemaValidator):
        schema = validator.generate_json_schema(
            {
                "field_definitions": {
                    "kind": {"type": "select", "options": ["a", {"value": "b"}]},
                    "tags": {"type": "multiselect", "options": ["x", "y"]},
                }
            }
        )

        props = schema["properties"]
        assert props["kind"]["enum"] == ["a", "b"]
        assert [o["value"] for o in props["kind"]["enumOptions"]] == ["a", "b"]
        assert props["tags"]["items"] == {"enum": ["x", "y"]}
        assert [o["label"] for o in props["tags"]["enumOptions"]] == ["X", "Y"]

    def test_array_items_and_item_schema(self, validator: SchemaValidator):
        schema = validator.generate_json_schema(
            {
                "field_definitions": {
                    "refs": {
                        "type": "array",
                        "min_items": 1,
                        "items": {"type": "pmid"},
                    },
                    "rows": {
                        "type": "array",
                        "item_schema": {
                            "a": {"type": "text", "required": True},
                            "b": {"type": "number"},
                        },
                    },
                }
            }
        )

        props = schema["properties"]
        assert props["refs"] == {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string"},
        }
        assert props["rows"]["items"] == {
            "type": "object",
            "properties": {"a": {"type": "string"}, "b": {"type": "number"}},
            "required": ["a"],
        }

    def test_nested_object_properties(self, validator: SchemaValidator):
        schema = validator.generate_json_schema(
            {
                "field_definitions": {
                    "claim": {
                        "type": "object",
                        "properties": {"x": {"type": "number"}},
                        "required": ["x"],
                    }
                }
            }
        )

        assert schema["properties"]["claim"] == {
            "type": "object",
            "properties": {"x": {"type": "number"}},
            "required": ["x"],
        }


_MONDO_DEFS = {
    "entity_definition": {
        "type": "object",
        "properties": {"mondo_id": {"type": "string", "validation": "mondo_id_format"}},
    }
}
_MONDO_RULES = {
    "mondo_id_format": {
        "type": "regex",
        "pattern": "^MONDO:[0-9]{7}$",
        "message": "MONDO ID must look like MONDO:0000000",
    }
}


class TestNamedRegexRules:
    def _validate(self, validator, mondo_id):
        return validator.validate_evidence_data(
            {"entity_definition": {"mondo_id": mondo_id}},
            {"field_definitions": _MONDO_DEFS, "validation_rules": _MONDO_RULES},
        )

    def test_bad_mondo_id_gets_the_format_message_not_the_detail_hint(self, validator):
        result = self._validate(validator, "MONDO:12")

        assert [e["message"] for e in result.errors] == [
            "MONDO ID must look like MONDO:0000000"
        ]
        assert not any("detailed description" in w["message"] for w in result.warnings)

    def test_valid_mondo_id_passes(self, validator):
        assert self._validate(validator, "MONDO:0000123").is_valid


def test_disease_fields_read_nested_and_flat_shapes():
    from app.schemas.curation import disease_fields

    nested = {"entity_definition": {"disease_name": "D", "mondo_id": "M"}}
    flat = {"disease_name": "F", "mode_of_inheritance": "AD"}

    assert disease_fields({}, nested) == {
        "disease_name": "D",
        "mondo_id": "M",
        "mode_of_inheritance": None,
    }
    assert disease_fields(flat, nested) == {
        "disease_name": "F",
        "mondo_id": "M",
        "mode_of_inheritance": "AD",
    }
    assert disease_fields(None, None)["disease_name"] is None
