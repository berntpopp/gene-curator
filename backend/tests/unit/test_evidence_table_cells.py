"""Monkey L2: submit enforces evidence-table column types and required cells as the UI
does, each error naming the row and column."""

import pytest

from app.services.evidence_ids import evidence_errors

pytestmark = pytest.mark.unit

DEFINITION = {
    "field_definitions": {
        "probands": {
            "type": "evidence_table",
            "columns": {
                "zygosity": {"type": "select", "required": True},
                "points": {"type": "number", "max": 3},
                "count": {"type": "integer"},
                "note": {"type": "text"},
                "carrier": {"type": "boolean", "required": True},
            },
        }
    }
}


def _paths(rows: list[dict]) -> list[tuple[str, str]]:
    return [
        (e.path, e.message) for e in evidence_errors({"probands": rows}, DEFINITION)
    ]


def test_bad_numbers_and_blank_required_cells_are_named() -> None:
    rows = [
        {"zygosity": "het", "points": 1, "count": "2", "carrier": False},
        {"zygosity": "", "points": "abc", "count": "x", "carrier": True},
        {"points": 4},
    ]
    assert _paths(rows) == [
        ("probands[1].zygosity", "Required field is missing"),
        ("probands[1].points", "Value must be a number"),
        ("probands[1].count", "Value must be a number"),
        ("probands[2].zygosity", "Required field is missing"),
        ("probands[2].points", "Value must not exceed 3"),
        ("probands[2].carrier", "Required field is missing"),
    ]


def test_a_complete_table_passes() -> None:
    assert _paths([{"zygosity": "het", "points": "1.5", "carrier": False}]) == []
