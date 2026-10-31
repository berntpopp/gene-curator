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
        ("probands[1].count", "Value must be a whole number"),
        ("probands[2].zygosity", "Required field is missing"),
        ("probands[2].points", "Value must not exceed 3"),
        ("probands[2].carrier", "Required field is missing"),
    ]


def test_a_complete_table_passes() -> None:
    assert _paths([{"zygosity": "het", "points": "1.5", "carrier": False}]) == []


def test_an_integer_column_rejects_a_fraction() -> None:
    rows = [{"zygosity": "het", "count": 2.5, "carrier": True}]
    rows.append({"zygosity": "het", "count": "3", "carrier": True})
    assert _paths(rows) == [("probands[0].count", "Value must be a whole number")]


def test_a_fully_blank_row_is_dropped_not_validated() -> None:
    rows = [{"zygosity": "het", "carrier": True}, {}, {"zygosity": "", "note": " "}]
    assert _paths(rows) == []


# #611: every column kind with a validator; the KGDB diagnostics shapes
RESOURCES = {
    "field_definitions": {
        "resources": {
            "type": "evidence_table",
            "columns": {
                "type": {"type": "select", "options": [{"value": "registry"}]},
                "name": {"type": "text", "max_length": 5},
                "audiences": {"type": "multiselect", "options": ["patients"]},
                "verified_date": {"type": "date"},
                "sources": {"type": "source"},
            },
        },
        "evidence_summary": {"type": "textarea", "max_length": 10},
    }
}


def test_select_date_length_and_source_cells_are_checked() -> None:
    evidence = {
        "resources": [
            {
                "type": "patient_organization",
                "name": "too long",
                "audiences": ["doctors"],
                "verified_date": "2026-10-30T12:00:00Z",
                "sources": "PMID:1",
            },
            {"type": "registry", "name": "ok", "verified_date": "2026-10-30"},
        ],
        "evidence_summary": "x" * 11,
    }
    assert [e.path for e in evidence_errors(evidence, RESOURCES)] == [
        "resources[0].type",
        "resources[0].name",
        "resources[0].audiences",
        "resources[0].verified_date",
        "resources[0].sources",
        "evidence_summary",
    ]


def test_valid_kgdb_diagnostics_still_pass() -> None:
    """KGDB reads evidence.diagnostics: the bundle's valid rows are never refused."""
    from tests.unit.test_kgdb_methodology import SCHEMAS

    definition = SCHEMAS["KGDB Mendelian Curation"]
    diagnostics = {
        "recommended_transcript": {"refseq": "NM_006580.4", "mane_status": "select"},
        "detectability": [
            {
                "challenge": next(
                    o["value"]
                    for o in definition["field_definitions"]["diagnostics"][
                        "properties"
                    ]["detectability"]["columns"]["challenge"]["options"]
                ),
                "methods": ["long_read_sequencing"],
                "tools": ["VNtyper | https://github.com/x | PMID:1"],
                "sources": ["PMID:31558469"],
                "negative_report_does_not_exclude": True,
            }
        ],
        "resources": [
            {
                "type": "other",
                "name": "ERKNet",
                "url": "https://www.erknet.org",
                "audiences": ["patients", "clinicians"],
                "verified_method": "fetched",
                "verified_date": "2026-10-30",
            }
        ],
    }
    evidence = {
        "diagnostics": diagnostics,
        "diagnostics_notes": {"detectability_note": "short-read testing adequate"},
    }
    assert evidence_errors(evidence, definition) == []
