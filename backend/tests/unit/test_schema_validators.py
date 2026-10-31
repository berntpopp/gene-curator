"""Schema structure checks: one vocabulary (`core.schema_rules`), JSON-path diagnostics (#269)."""

from typing import Any

import pytest

from app.core.schema_rules import VALID_FIELD_TYPES, check_schema_definition
from app.crud.schema_validators import validate_schema_structure

pytestmark = pytest.mark.unit

VALID: dict[str, Any] = {
    "field_definitions": {"gene": {"type": "text", "label": "Gene", "llm_share": True}},
    "workflow_states": ["draft", "submitted"],
    "ui_configuration": {"sections": []},
}


def found(schema: dict[str, Any], severity: str = "error") -> list[tuple[str, str]]:
    return [(p, m) for s, p, m in check_schema_definition(schema) if s == severity]


def paths(schema: dict[str, Any], severity: str = "error") -> list[str]:
    return [p for p, _ in found(schema, severity)]


def test_valid_schema_has_no_diagnostics() -> None:
    assert check_schema_definition(VALID) == []
    assert validate_schema_structure(VALID) == ([], [])


@pytest.mark.parametrize(
    "key", ["field_definitions", "workflow_states", "ui_configuration"]
)
@pytest.mark.parametrize("value", [None, {}])
def test_missing_or_empty_top_level_key(key: str, value: Any) -> None:
    schema = {**VALID, key: value}
    if value is None:
        del schema[key]
    assert (key, f"Missing required field: {key}") in found(schema)


def test_empty_schema_reports_every_required_key() -> None:
    assert paths({}) == ["field_definitions", "workflow_states", "ui_configuration"]


class TestFieldDefinitions:
    def test_not_a_dict(self) -> None:
        assert paths({**VALID, "field_definitions": ["x"]}) == ["field_definitions"]

    def test_field_config_not_a_dict(self) -> None:
        assert paths({**VALID, "field_definitions": {"a": "text"}}) == [
            "field_definitions.a"
        ]

    def test_missing_and_invalid_type(self) -> None:
        schema = {
            **VALID,
            "field_definitions": {"a": {"label": "A"}, "b": {"type": "x"}},
        }
        assert found(schema) == [
            ("field_definitions.a.type", "Field 'a' missing required property: type"),
            ("field_definitions.b.type", "Field 'b' has invalid type: x"),
        ]

    def test_label_is_optional_and_all_types_accepted(self) -> None:
        defs = {t: {"type": t} for t in VALID_FIELD_TYPES if t != "evidence_table"}
        assert found({**VALID, "field_definitions": defs}) == []

    def test_section_fields_are_checked_by_index(self) -> None:
        sections = [{"id": "s", "fields": [{"id": "ok", "type": "text"}, {"id": "x"}]}]
        schema = {**VALID, "field_definitions": {"sections": sections}}
        assert paths(schema) == ["field_definitions.sections[0].fields[1].type"]

    def test_malformed_sections_are_skipped(self) -> None:
        schema = {
            **VALID,
            "field_definitions": {"sections": ["junk", {"fields": None}]},
        }
        assert found(schema) == []


class TestWorkflowStates:
    @pytest.mark.parametrize(
        "states",
        [
            ["draft", "submitted", "approved"],
            {"states": [{"name": "draft"}, {"name": "submitted"}], "transitions": {}},
            {
                "entry": {"label": "Entry"},
                "precuration": {},
                "review": {},
                "active": {},
            },
        ],
    )
    def test_accepted_shapes(self, states: Any) -> None:
        assert found({**VALID, "workflow_states": states}) == []

    def test_list_requires_draft_and_submitted(self) -> None:
        messages = [m for _, m in found({**VALID, "workflow_states": ["approved"]})]
        assert messages == [
            "Missing required workflow state: draft",
            "Missing required workflow state: submitted",
        ]

    @pytest.mark.parametrize(
        ("states", "message"),
        [
            ("draft", "workflow_states must be a list"),
            (
                {"draft": 5},
                "workflow_states must list states or map state names to objects",
            ),
            (
                {"transitions": {"a": ["b"]}},
                "workflow_states must list states or map state names to objects",
            ),
        ],
    )
    def test_bad_shapes(self, states: Any, message: str) -> None:
        assert found({**VALID, "workflow_states": states}) == [
            ("workflow_states", message)
        ]

    def test_legacy_transition_targets_must_be_states(self) -> None:
        states = {
            "states": [{"name": "draft"}, {"name": "submitted"}],
            "transitions": {"draft": ["submitted", "nowhere"]},
        }
        assert found({**VALID, "workflow_states": states}) == [
            (
                "workflow_states.transitions.draft[1]",
                "Unknown transition target: nowhere",
            )
        ]


class TestOptionalSections:
    def test_ui_configuration(self) -> None:
        assert paths({**VALID, "ui_configuration": ["x"]}) == ["ui_configuration"]
        assert paths({**VALID, "ui_configuration": {"layout": "x"}}, "warning") == [
            "ui_configuration.sections"
        ]

    def test_scoring_configuration(self) -> None:
        assert found({**VALID, "scoring_configuration": None}) == []
        assert paths({**VALID, "scoring_configuration": "x"}) == [
            "scoring_configuration"
        ]
        assert paths({**VALID, "scoring_configuration": {}}, "warning") == [
            "scoring_configuration.engine"
        ]
        assert found({**VALID, "scoring_configuration": {"engine": "nope"}}) == [
            ("scoring_configuration.engine", "Unknown scoring engine: nope")
        ]
        ok = {**VALID, "scoring_configuration": {"engine": "clingen_sop_v11"}}
        assert check_schema_definition(ok) == []

    def test_validation_rules(self) -> None:
        assert paths({**VALID, "validation_rules": ["x"]}) == ["validation_rules"]
        assert found({**VALID, "validation_rules": {"x": {"type": "regex"}}}) == []


def test_crud_wrapper_prefixes_messages_with_their_path() -> None:
    errors, warnings = validate_schema_structure(
        {**VALID, "ui_configuration": {"a": 1}, "workflow_states": ["x"]}
    )
    assert errors == [
        "workflow_states: Missing required workflow state: draft",
        "workflow_states: Missing required workflow state: submitted",
    ]
    assert warnings == [
        "ui_configuration.sections: UI configuration missing 'sections' - form may not render properly"
    ]


def test_a_tab_layout_is_not_missing_sections() -> None:
    """MUI-23: KGDB-style `layout.tabs` renders as well as `sections` (normalizeDefinition.ts)."""
    tabs = {"layout": {"type": "tabs", "tabs": [{"id": "a", "sections": []}]}}
    assert check_schema_definition({**VALID, "ui_configuration": tabs}) == []
    # tabs that are not a list lay nothing out: the warning stays
    for bad in ({"tabs": {"a": 1}}, {"tabs": "x"}, {"tabs": []}):
        ui = {"layout": bad}
        assert check_schema_definition({**VALID, "ui_configuration": ui}) != []
