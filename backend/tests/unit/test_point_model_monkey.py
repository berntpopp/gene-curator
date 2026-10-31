"""Wave 10 UI monkey round 1: blank points score the type default (B2), list cells in
``in``/``present`` rules (B9), flat (UI-built) forms score and are path-checked (B3)."""

from typing import Any

import pytest

from app.scoring.point_model import point_model, score
from app.scoring.registry import engine_for
from tests.unit.test_schema_validators_seeded import errors

pytestmark = pytest.mark.unit

PMID = "12345678"


def _model(*types: dict[str, Any], key: str = "genetic") -> dict[str, Any]:
    return {
        "sections": [{"key": key, "categories": [{"key": "c", "types": list(types)}]}],
        "bands": [{"class": "any"}],
    }


def _total(model: dict[str, Any], evidence: dict[str, Any]) -> float:
    return float(score(model, evidence)["total"])


@pytest.mark.parametrize("blank", [None, "", "  "])
def test_blank_points_score_the_type_default(blank: Any) -> None:
    rows = [{"pmid": PMID, "points": blank}, {"pmid": PMID, "points": 0}]
    cfg = {"engine": "point_model", "point_model": _model({"path": "p", "default": 1})}
    result = engine_for(cfg).calculate_scores({"genetic": {"p": rows}}, cfg)
    assert result.scores["total_score"] == 1


def test_clingen_engine_keeps_an_explicit_null_at_zero() -> None:
    cfg = {
        "engine": "clingen_sop_v11",
        "point_model": _model({"path": "p", "default": 1}),
    }
    model = point_model(cfg)
    assert model is not None
    assert _total(model, {"genetic": {"p": [{"pmid": PMID, "points": None}]}}) == 0


def test_in_matches_a_list_cell_and_an_empty_list_is_blank() -> None:
    rules = [
        {"field": "variant_class", "in": ["lof"], "points": 2},
        {"field": "pmids", "present": True, "points": 1.5},
    ]
    model = _model({"path": "probands", "default": 0, "points_when": rules})
    rows = [
        {"pmid": PMID, "variant_class": ["missense", "lof"]},
        {"pmid": PMID, "variant_class": [], "pmids": []},
        {"pmid": PMID, "variant_class": "lof"},
    ]
    assert _total(model, {"genetic": {"probands": rows}}) == 4


def test_flat_form_evidence_scores_under_a_section_key() -> None:
    model = _model({"path": "probands", "default": 1})
    result = score(model, {"probands": [{"pmid": PMID}, {"pmid": PMID, "points": 2}]})
    assert result["total"] == 3


TABLE = {"type": "evidence_table", "columns": {"pmid": {"type": "text"}}}
SECTIONED = {"sections": [{"id": "s1", "fields": [{"id": "probands", **TABLE}]}]}


def _path_errors(model: dict[str, Any], fields: dict[str, Any]) -> list[str]:
    cfg = {"engine": "point_model", "point_model": model}
    found = errors(field_definitions=fields, scoring_configuration=cfg)
    return [p for p, _ in found if p.startswith("scoring_configuration")]


def test_flat_paths_are_checked_against_the_form_fields() -> None:
    types = "scoring_configuration.point_model.sections[0].categories[0].types"
    assert _path_errors(_model({"path": "probands"}), SECTIONED) == []
    assert _path_errors(_model({"path": "proband"}), SECTIONED) == [f"{types}[0].path"]
    rule = {"field": "pmd", "present": True, "points": 1}
    model = _model({"path": "probands", "points_when": [rule]})
    assert _path_errors(model, SECTIONED) == [f"{types}[0].points_when[0].field"]


def test_a_mixed_model_checks_each_section_where_the_scorer_reads_it() -> None:
    """One section nested under a field, one read from the top level (review of B3)."""
    fields = {
        "genetic": {"type": "object", "properties": {"probands": TABLE}},
        "models": TABLE,
    }
    model = {
        "sections": [
            {
                "key": key,
                "categories": [{"key": "c", "types": [{"path": p, "default": 1}]}],
            }
            for key, p in (("genetic", "probands"), ("experimental", "models"))
        ],
        "bands": [{"class": "any"}],
    }
    assert _path_errors(model, fields) == []
    flat = {"genetic": {"probands": [{"pmid": PMID}]}, "models": [{"pmid": PMID}]}
    assert score(model, flat)["total"] == 2
