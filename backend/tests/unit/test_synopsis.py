"""Synopsis per curated entity: the schema names one text field (ui_configuration)."""

import pytest

from app.core.schema_rules import check_schema_definition
from app.core.synopsis import synopsis_diagnostics, synopsis_of

pytestmark = pytest.mark.unit

FIELDS = {
    "evidence_summary": {"type": "textarea"},
    "notes": {"type": "object", "properties": {"short": {"type": "text"}}},
    "points": {"type": "number"},
    "sections": [{"fields": [{"id": "clinical", "type": "text"}]}],
}


def _errors(path: object) -> list[str]:
    schema = {"field_definitions": FIELDS, "ui_configuration": {"synopsis_field": path}}
    return [p for _, p, _ in synopsis_diagnostics(schema)]


def test_synopsis_field_must_name_a_text_field() -> None:
    for good in ("evidence_summary", "notes.short", "clinical"):
        assert _errors(good) == [], good
    for bad in ("points", "missing", "notes", "notes.x", 3):
        assert _errors(bad) == ["ui_configuration.synopsis_field"], bad
    assert synopsis_diagnostics({"field_definitions": FIELDS}) == []  # unset: none
    schema = {
        "field_definitions": FIELDS,
        "workflow_states": {"draft": {}},
        "ui_configuration": {"sections": [], "synopsis_field": "points"},
    }
    assert any(
        p == "ui_configuration.synopsis_field"
        for _, p, _ in check_schema_definition(schema)
    )


def test_synopsis_of_reads_the_named_text() -> None:
    ui = {"synopsis_field": "notes.short"}
    assert synopsis_of({"notes": {"short": "  CKD  "}}, ui) == "CKD"
    assert synopsis_of({"notes": {"short": " "}}, ui) is None
    assert synopsis_of({"notes": "x"}, ui) is None
    assert synopsis_of({"evidence_summary": "x"}, {}) is None
    assert synopsis_of(None, None) is None
