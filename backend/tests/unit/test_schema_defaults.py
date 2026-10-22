"""Publication rejects unusable selector-driven defaults and preserves them for forms."""

import copy

import pytest

from app.core.schema_rules import check_schema_definition
from app.core.schema_validator import schema_validator
from tests.unit.test_clingen_v1_correction import FIELDS

pytestmark = pytest.mark.unit


def definition():
    fields = copy.deepcopy(FIELDS)
    columns = fields["genetic_evidence"]["properties"]["case_level"]["properties"][
        "autosomal_recessive"
    ]["properties"]["other_variant_type"]["items"]["properties"]
    columns["proband_counted_points"]["default_by"] = {
        "field": "variant_type",
        "values": {"null_and_other": 1.5, "two_other": 0.2, "homozygous_other": 0.2},
    }
    return {
        "field_definitions": fields,
        "workflow_states": ["draft", "submitted"],
        "ui_configuration": {"sections": []},
    }, columns


def mapping_errors(schema):
    return [d for d in check_schema_definition(schema) if d[0] == "error"]


@pytest.mark.parametrize(
    "mapping",
    [
        None,
        [],
        {},
        {"field": 4, "values": {}},
        {"field": "missing", "values": {"two_other": 0.2}},
        {"field": "variant_type", "values": []},
        {"field": "variant_type", "values": {"unknown": 1}},
        {"field": "variant_type", "values": {"two_other": float("inf")}},
        {"field": "variant_type", "values": {"two_other": float("nan")}},
        {"field": "variant_type", "values": {"two_other": True}},
        {"field": "variant_type", "values": {"two_other": "0.2"}},
        {"field": "variant_type", "values": {"two_other": -1}},
        {"field": "variant_type", "values": {"two_other": 4}},
    ],
)
def test_rejects_bad_default_mapping(mapping):
    schema, columns = definition()
    columns["proband_counted_points"]["default_by"] = mapping
    errors = mapping_errors(schema)
    assert errors and any("default_by" in d[1] for d in errors)


def test_accepts_and_preserves_valid_mapping_and_scalar_defaults():
    schema, columns = definition()
    assert mapping_errors(schema) == []
    generated = schema_validator.generate_json_schema(schema)
    prop = generated["properties"]["genetic_evidence"]["properties"]["case_level"][
        "properties"
    ]["autosomal_recessive"]["properties"]["other_variant_type"]["items"]["properties"][
        "proband_counted_points"
    ]
    assert prop["default_by"] == columns["proband_counted_points"]["default_by"]
    assert prop["default"] == columns["proband_counted_points"]["default"]


@pytest.mark.parametrize("blank_at", ["bad", False, [], float("inf")])
def test_rejects_invalid_blank_sentinels(blank_at):
    from tests.unit.test_clingen_successor import successor_model

    schema, _ = definition()
    model = successor_model()
    model["sections"][0]["categories"][0]["types"][2]["blank_at"] = blank_at
    schema["scoring_configuration"] = {
        "engine": "clingen_sop_v11",
        "point_model": model,
    }
    assert any("blank_at" in d[1] for d in mapping_errors(schema))


@pytest.mark.parametrize("column_type", ["text", "boolean"])
def test_rejects_mapping_on_nonnumeric_column(column_type):
    schema, columns = definition()
    columns["proband_counted_points"]["type"] = column_type
    assert any("numeric columns" in d[2] for d in mapping_errors(schema))


@pytest.mark.parametrize("options", [[], None, "invalid"])
def test_rejects_selector_without_options(options):
    schema, columns = definition()
    columns["variant_type"]["options"] = options
    assert any("selector options" in d[2] for d in mapping_errors(schema))


def test_validates_list_columns_and_legacy_item_schema():
    from app.core.schema_defaults import check_default_mappings

    selector = {"key": "variant", "type": "select", "options": ["null", "other"]}
    score = {
        "key": "score",
        "type": "number",
        "default_by": {"field": "variant", "values": {"bad": 1}},
    }
    for container in ("columns", "item_schema"):
        fields = {"rows": {"type": "array", container: [selector, score, None]}}
        errors = check_default_mappings(fields)
        assert len(errors) == 1
        assert errors[0][1] == f"field_definitions.rows.{container}.score.default_by"
