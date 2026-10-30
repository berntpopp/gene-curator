"""Type ``group_by``/``group_cap`` (#557): a recurrent variant scores at most ``group_cap``
however many rows carry it; the trace lists each capped group."""

from typing import Any

import pytest

from app.scoring.point_model import score
from tests.unit.test_schema_validators_seeded import errors

pytestmark = pytest.mark.unit

PMID = "12345678"


def _model(**type_keys: Any) -> dict[str, Any]:
    types = [{"path": "probands", **type_keys}]
    return {
        "sections": [{"key": "g", "categories": [{"key": "c", "types": types}]}],
        "bands": [{"class": "any"}],
    }


def _rows(*variants: Any, points: float = 1) -> dict[str, Any]:
    rows = [{"variant": v, "points": points, "pmid": PMID} for v in variants]
    return {"g": {"probands": rows}}


def test_one_recurrent_variant_scores_at_most_the_group_cap() -> None:
    model = _model(group_by="variant", group_cap=2)
    result = score(model, _rows(*["c.100A>G"] * 6))
    assert result["total"] == 2
    assert result["trace"]["capped_groups"] == [
        {"path": "g.probands", "value": "c.100a>g", "raw": 6, "capped": 2}
    ]
    assert score(_model(), _rows(*["c.100A>G"] * 6))["total"] == 6  # unchanged without


def test_distinct_and_blank_variants_are_not_capped() -> None:
    model = _model(group_by="variant", group_cap=2)
    result = score(model, _rows("c.1A>G", "c.2A>G", "c.3A>G", "", None, "  "))
    assert result["total"] == 6
    assert "capped_groups" not in result["trace"]


def test_group_values_are_normalised() -> None:
    model = _model(group_by="variant", group_cap=2)
    result = score(model, _rows(" c.1A>G", "C.1a>g ", "c.2A>G", points=1.5))
    assert result["total"] == 3.5
    (group,) = result["trace"]["capped_groups"]
    assert (group["raw"], group["capped"]) == (3, 2)


def _type_errors(**type_keys: Any) -> list[str]:
    cfg = {"engine": "clingen_sop_v11", "point_model": _model(**type_keys)}
    prefix = "scoring_configuration.point_model.sections[0].categories[0].types[0]"
    return [p.removeprefix(prefix) for p, _ in errors(scoring_configuration=cfg)]


def test_valid_group_keys() -> None:
    assert _type_errors(group_by="variant", group_cap=2) == []
    assert _type_errors(group_by="variant", group_cap=1.5) == []


@pytest.mark.parametrize(
    ("keys", "paths"),
    [
        ({"group_by": 1, "group_cap": 2}, [".group_by"]),
        ({"group_by": "variant", "group_cap": "2"}, [".group_cap"]),
        ({"group_by": "variant", "group_cap": True}, [".group_cap"]),
        ({"group_by": "variant"}, [".group_cap"]),
        ({"group_cap": 2}, [".group_by"]),
    ],
)
def test_invalid_group_keys(keys: dict[str, Any], paths: list[str]) -> None:
    assert _type_errors(**keys) == paths
