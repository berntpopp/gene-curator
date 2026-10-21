"""046: the corrected ClinGen v1 evidence definitions accept what the forms write and enforce
the SOP v11 point ranges through validate-evidence's validator."""

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.core.schema_validator import schema_validator
from app.scoring.point_model import template

pytestmark = pytest.mark.unit

SQL = Path(__file__).parents[3] / "database/sql/046_clingen_v1_correction.sql"
NULL_AD = (
    "genetic_evidence",
    "case_level",
    "autosomal_dominant_or_x_linked",
    "predicted_or_proven_null",
)


def literal(tag: str) -> Any:
    """A JSON literal embedded in 046 as $tag$...$tag$."""
    found = re.search(rf"\${tag}\$(.*?)\${tag}\$", SQL.read_text(), re.S)
    assert found
    return json.loads(found.group(1))


FIELDS = literal("fields")


def _tables(node: dict, path: tuple = ()) -> list[tuple[tuple, dict]]:
    if node.get("type") == "array":
        return [(path, node)]
    return [
        table
        for key, child in node.get("properties", {}).items()
        for table in _tables(child, (*path, key))
    ]


TABLES = [t for key, node in FIELDS.items() for t in _tables(node, (key,))]


def _new_row(table: dict) -> dict:
    """A freshly added form row: defaults, every other column empty."""
    return {
        key: column.get("default", "")
        for key, column in table["items"]["properties"].items()
    }


def _put(evidence: dict, path: tuple, rows: list) -> None:
    node = evidence
    for key in path[:-1]:
        node = node.setdefault(key, {})
    node[path[-1]] = rows


def _evidence() -> dict:
    evidence: dict = {
        "evidence_summary": "Strong evidence",
        "replicated_over_time": True,
    }
    for path, table in TABLES:
        _put(evidence, path, [_new_row(table)])
    _at(evidence, NULL_AD)[0].update(
        proband_label="P1",
        variant="NM_000000.1:c.100C>T",
        pmid="PMID: 12345678",
        explanation="Nonsense variant, de novo",
    )
    return evidence


def _at(evidence: dict, path: tuple) -> Any:
    for key in path:
        evidence = evidence[key]
    return evidence


def _errors(evidence: dict) -> list[str]:
    result = schema_validator.validate_evidence_data(
        evidence, {"field_definitions": FIELDS}
    )
    assert result.is_valid is not bool(result.errors)
    return [e["field"] for e in result.errors]


def test_corrects_all_eighteen_tables_of_the_forms() -> None:
    assert len(TABLES) == 19  # 18 evidence tables + contradictory evidence
    for _, table in TABLES:
        columns = table["items"]["properties"]
        orders = sorted(c["order"] for c in columns.values())
        assert orders == list(range(1, len(columns) + 1))  # jsonb loses key order
        for key, column in columns.items():
            if column["type"] == "select":  # every new row starts valid
                values = [o["value"] for o in column["options"]]
                assert column["default"] in values, key


def test_definitive_flag_is_a_field() -> None:
    model = template("clingen_sop_v11")
    assert model
    (definitive,) = [b for b in model["bands"] if b["class"] == "definitive"]
    assert FIELDS[definitive["requires"]]["type"] == "boolean"


def test_real_form_data_is_valid() -> None:
    assert _errors(_evidence()) == []


@pytest.mark.parametrize("bad", [99, "abc", -0.1, 3.1])
def test_out_of_range_points_are_rejected(bad: object) -> None:
    evidence = _evidence()
    _at(evidence, NULL_AD)[0]["proband_counted_points"] = bad
    assert _errors(evidence) == [
        "genetic_evidence.case_level.autosomal_dominant_or_x_linked"
        ".predicted_or_proven_null[0].proband_counted_points"
    ]


def test_bad_pmid_select_and_shape_are_rejected() -> None:
    evidence = _evidence()
    row = _at(evidence, NULL_AD)[0]
    row.update(pmid="abc", variant_type="bogus")
    assert len(_errors(evidence)) == 2
    legacy = copy.deepcopy(_evidence())
    legacy["genetic_evidence"] = []  # the array the legacy seed declared
    assert _errors(legacy) == ["genetic_evidence"]


def test_point_columns_match_the_point_model_ranges() -> None:
    model = template("clingen_sop_v11")
    assert model
    tables = {".".join(path): table for path, table in TABLES}
    for section in model["sections"]:
        for category in section["categories"]:
            for type_def in category["types"]:
                table = tables[f"{section['key']}.{type_def['path']}"]
                column = table["items"]["properties"][
                    type_def.get("points_key", "points")
                ]
                low, high = type_def["range"]
                assert (column["min_value"], column["max_value"]) == (low, high)
                assert (column["min"], column["max"]) == (low, high)


def test_embedded_point_model_is_the_template() -> None:
    """046 pins the corrected model into the v1 snapshots; it must equal the template file."""
    assert literal("model") == template("clingen_sop_v11")
