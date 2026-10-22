"""#433: the validator applies the shared condition semantics (crud/precuration_required.py)."""

from typing import Any

import pytest

from app.core.schema_validator import SchemaValidator

pytestmark = pytest.mark.unit


def required_errors(
    data: dict[str, Any], fields: dict[str, Any], rules: dict[str, Any] | None = None
) -> list[str]:
    schema = {"field_definitions": fields, "validation_rules": rules or {}}
    result = SchemaValidator().validate_evidence_data(data, schema)
    return [e["field"] for e in result.errors if e["type"] == "required"]


TEXT = {"type": "text"}
DETAIL = {"kind": TEXT, "detail": {**TEXT, "required_when": {"kind": "other"}}}
MOI = {
    "moi": {
        "type": "object",
        "properties": {
            "code": TEXT,
            "note": {**TEXT, "required": True, "visible_when": {"moi.code": "Other"}},
        },
    }
}


@pytest.mark.parametrize(
    ("data", "missing"),
    [({"kind": "other"}, ["detail"]), ({"kind": "AD"}, []), ({}, [])],
)
def test_required_when_is_enforced(data: dict[str, Any], missing: list[str]) -> None:
    assert required_errors(data, DETAIL) == missing


@pytest.mark.parametrize(("code", "missing"), [("Other", ["moi.note"]), ("AD", [])])
def test_nested_child_conditions_start_at_the_root(
    code: str, missing: list[str]
) -> None:
    assert required_errors({"moi": {"code": code}}, MOI) == missing


def test_a_hidden_parent_hides_its_required_children() -> None:
    fields = {
        "on": {"type": "boolean"},
        "extra": {
            "type": "object",
            "visible_when": {"on": True},
            "properties": {"why": {**TEXT, "required": True}},
        },
    }
    assert required_errors({"on": False, "extra": {}}, fields) == []
    assert required_errors({"on": True, "extra": {}}, fields) == ["extra.why"]


def test_required_when_on_array_rows() -> None:
    fields = {
        "mode": TEXT,
        "rows": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"pmid": {**TEXT, "required_when": {"mode": "pmid"}}},
            },
        },
    }
    assert required_errors({"mode": "pmid", "rows": [{}]}, fields) == ["rows[0].pmid"]
    assert required_errors({"mode": "free", "rows": [{}]}, fields) == []


def test_listed_and_conditional_rules_skip_hidden_fields() -> None:
    fields = {"why": {**TEXT, "show_when": {"on": True}}}
    rules = {
        "required_fields": ["why"],
        "conditional_required": {"why": {"when": {"kind": "x"}}},
    }
    assert required_errors({"on": False, "kind": "x"}, fields, rules) == []
    assert required_errors({"on": True}, fields, rules) == ["why"]


def test_a_malformed_conditional_rule_requires() -> None:
    rules = {"conditional_required": {"why": {"when": "oops"}}}
    assert required_errors({}, {"why": TEXT}, rules) == ["why"]


def test_json_schema_carries_required_when_for_the_form() -> None:
    schema = SchemaValidator().generate_json_schema(
        {"field_definitions": {**DETAIL, **MOI}}
    )
    detail = schema["properties"]["detail"]
    assert detail["required_when"] == {"kind": "other"}
    note = schema["properties"]["moi"]["properties"]["note"]
    assert note["visible_when"] == {"moi.code": "Other"}


@pytest.mark.parametrize(
    ("data", "missing"), [({}, ["answer"]), ({"answer": False}, [])]
)
def test_required_boolean_needs_an_answer(
    data: dict[str, Any], missing: list[str]
) -> None:
    assert (
        required_errors(data, {"answer": {"type": "boolean", "required": True}})
        == missing
    )


def test_dotted_required_rules_respect_values_and_parent_visibility() -> None:
    fields = {
        "parent": {
            "type": "object",
            "show_when": {"on": True},
            "properties": {"child": TEXT},
        },
    }
    rules = {"required_fields": ["parent.child"]}
    assert (
        required_errors({"on": True, "parent": {"child": "answered"}}, fields, rules)
        == []
    )
    assert required_errors({"on": False}, fields, rules) == []
    assert required_errors({"on": True, "parent": {}}, fields, rules) == [
        "parent.child"
    ]
