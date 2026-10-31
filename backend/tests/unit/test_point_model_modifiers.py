"""#615 (KGDB iteration 8): ``points_when`` rules with ``factor`` or ``max`` scale or cap a
row's points, entered or not, and ``group_by`` takes a list of fields. Models without them
score exactly as before."""

from typing import Any

import pytest

from app.scoring.point_model import score
from tests.unit.test_point_model_group_cap import _type_errors
from tests.unit.test_point_model_rules import TYPE, _model, _probands, _scoring_errors

pytestmark = pytest.mark.unit

HALF = {"field": "phase", "in": ["unknown"], "factor": 0.5}
AT_MOST_2 = {
    "field": "consanguinity",
    "in": ["yes"],
    "and": [{"field": "zygosity", "in": ["homozygous"]}],
    "max": 2,
}
TYPE_DEF = {
    "path": "probands",
    "default": 1,
    "range": [0, 3],
    "points_when": [
        {"field": "duplicate_of", "present": True, "points": 0},
        {"field": "de_novo", "in": ["confirmed"], "points": 1.5},
        HALF,
        AT_MOST_2,
    ],
}


@pytest.mark.parametrize(
    ("row", "points"),
    [
        ({"phase": "unknown"}, 0.5),  # the default, halved
        ({"phase": "unknown", "points": 3}, 1.5),  # entered points are halved too
        ({"phase": "unknown", "de_novo": "confirmed"}, 0.75),  # fill, then factor
        ({"phase": "unknown", "duplicate_of": "P1", "points": 3}, 0),
        ({"consanguinity": "yes", "zygosity": "homozygous", "points": 3}, 2),
        ({"consanguinity": "yes", "zygosity": "homozygous", "points": 1.5}, 1.5),
        ({"consanguinity": "yes", "zygosity": "compound_heterozygous", "points": 3}, 3),
        ({"consanguinity": "no", "zygosity": "homozygous", "points": 3}, 3),
    ],
)
def test_factor_and_max_rules(row: dict[str, Any], points: float) -> None:
    assert score(_model(TYPE_DEF), _probands(row))["total"] == points


def test_modifiers_are_traced() -> None:
    result = score(_model(TYPE_DEF), _probands({"phase": "unknown", "points": 3}))
    assert result["trace"]["rules_applied"] == [
        {
            "path": "g.probands[0]",
            "rule": "points_when",
            "index": 2,
            "entered": 3.0,
            "points": 1.5,
            "applied": True,
        }
    ]


def test_group_by_fields_caps_per_variant_and_population() -> None:
    model = _model({**TYPE_DEF, "group_by": ["variant", "population"], "group_cap": 3})
    rows = [
        *[{"variant": "c.1A>G", "population": "Japan", "points": 1.5}] * 3,
        *[{"variant": " C.1a>g", "population": "japan "}],  # same group, normalised
        *[{"variant": "c.1A>G", "population": "Finland", "points": 1.5}] * 2,
        *[{"variant": "c.1A>G", "points": 1.5}] * 3,  # no population: one group
        {"population": "Japan", "points": 1},  # no variant: never grouped
    ]
    result = score(model, _probands(*rows))
    assert result["total"] == 3 + 3 + 3 + 1
    groups = {g["value"] for g in result["trace"]["capped_groups"]}
    assert groups == {"c.1A>G | Japan", "c.1A>G | "}


def test_a_string_group_by_and_points_only_rules_score_as_before() -> None:
    """Old pins: a single field and fill/exclusion rules, unchanged."""
    model = _model(
        {
            "path": "probands",
            "default": 1,
            "group_by": "variant",
            "group_cap": 2,
            "points_when": [{"field": "de_novo", "in": ["confirmed"], "points": 1.5}],
        }
    )
    rows = [{"variant": "v", "population": p, "de_novo": "confirmed"} for p in "abc"]
    result = score(model, _probands(*rows, {"variant": "w", "points": 0.5}))
    assert result["total"] == 2.5
    assert [g["value"] for g in result["trace"]["capped_groups"]] == ["v"]


def test_valid_shapes() -> None:
    assert _scoring_errors(_model(TYPE_DEF)) == []
    assert _type_errors(group_by=["variant", "population"], group_cap=3) == []


@pytest.mark.parametrize(
    "rule",
    [
        {"field": "x", "in": [1], "factor": "0.5"},
        {"field": "x", "in": [1], "max": None},
        {"field": "x", "in": [1], "points": 1, "max": 2},
        {"field": "x", "in": [1]},
    ],
)
def test_a_rule_needs_exactly_one_of_points_factor_max(rule: dict[str, Any]) -> None:
    found = _scoring_errors(_model({"path": "p", "points_when": [rule]}))
    assert found == [f"{TYPE}.points_when[0].points"]


@pytest.mark.parametrize("by", [[], ["variant", 1], {"variant": 1}])
def test_bad_group_by_lists(by: Any) -> None:
    assert _type_errors(group_by=by, group_cap=3) == [".group_by"]


def test_group_values_cap_named_groups_and_leave_the_rest() -> None:
    """Review of #619: ``group_values`` maps a field's values to named groups; unmapped
    values are never grouped, and grouped rows do not feed the hotspot flag."""
    model = _model(
        {
            "path": "probands",
            "default": 0.5,
            "group_by": "subtype",
            "group_cap": 2,
            "group_values": {"expression": "function", "interaction": "function"},
        }
    )
    rows = [{"subtype": "expression"}] * 5 + [{"subtype": "Interaction "}]
    result = score(model, _probands(*rows, {"subtype": "rescue", "points": 2}))
    assert result["total"] == 2 + 2
    assert [g["value"] for g in result["trace"]["capped_groups"]] == ["function"]
    assert result["variant_points"] == {}


def test_group_values_must_be_a_mapping() -> None:
    assert _type_errors(group_by="s", group_cap=2, group_values={"a": "g"}) == []
    assert _type_errors(group_by="s", group_cap=2, group_values=["a"]) == [
        ".group_values"
    ]


def test_range_is_checked_on_the_entered_value_before_factor_and_max() -> None:
    """Review of #619: 5 entered on a [0, 3] row is out of range even if halved to 2.5."""
    result = score(_model(TYPE_DEF), _probands({"phase": "unknown", "points": 5}))
    assert result["total"] == 0
    assert [f["value"] for f in result["trace"]["out_of_range"]] == [5.0]
