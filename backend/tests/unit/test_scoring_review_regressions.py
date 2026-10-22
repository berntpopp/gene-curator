"""Regression cases for #434's review: invalid legacy numbers and complete model paths."""

import copy
import json

import pytest
from sqlalchemy.orm import Session

from app.models import CurationNew
from app.scoring.clingen import ClinGenEngine
from app.scoring.point_model import template
from app.services import recompute_scores
from tests.unit.test_point_model import _custom_model

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "1e309", -3])
@pytest.mark.parametrize(
    ("section", "category", "key"),
    [
        ("experimental_evidence", "models", "points"),
        ("experimental_evidence", "rescue", "points"),
        ("genetic_evidence", "case_control", "computed_score"),
    ],
)
def test_legacy_invalid_points_are_flagged_and_json_safe(
    value: object, section: str, category: str, key: str
) -> None:
    evidence = {section: [{"evidence_category": category, key: value, "pmid": "1"}]}
    result = ClinGenEngine().calculate_scores(evidence, {})
    assert result.total_score == (-3 if value == -3 else 0)
    (flag,) = result.evidence_breakdown["trace"]["out_of_range"]
    assert flag["path"] == f"{section}[0].{key}"
    assert flag["value"] == (-3 if value == -3 else str(float(str(value))))
    assert len(result.warnings) == 1
    json.dumps(result.model_dump(), allow_nan=False)


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "1e309"])
@pytest.mark.parametrize("legacy", [False, True])
def test_nonfinite_lod_never_becomes_a_maximum_score(value: str, legacy: bool) -> None:
    row = {"lod_score": value, "pmid": "1", "evidence_category": "segregation"}
    data = [row] if legacy else {"segregation": [row]}
    result = ClinGenEngine().calculate_scores({"genetic_evidence": data}, {})
    assert result.total_score == 0
    (flag,) = result.evidence_breakdown["trace"]["out_of_range"]
    assert flag["path"].endswith("[0].lod_score")
    json.dumps(result.model_dump(), allow_nan=False)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_count_fallback_is_flagged(value: float) -> None:
    result = ClinGenEngine().calculate_scores(
        {"genetic_evidence": {"segregation": [{"segregations_counted": value}]}}, {}
    )
    assert result.total_score == 0
    (flag,) = result.evidence_breakdown["trace"]["out_of_range"]
    assert flag["path"].endswith("[0].segregations_counted")
    json.dumps(result.model_dump(), allow_nan=False)


def test_empty_form_keys_do_not_skip_a_custom_model() -> None:
    model = _custom_model()
    model["bands"] = [{"class": "limited"}]
    model["overrides"] = []
    evidence = {
        "contradictory_evidence": [],
        "replicated_over_time": False,
        "experimental_evidence": {"rescue": {"human": []}},
        "unknown": {"nested": "   "},
    }
    assert recompute_scores._unscored_keys(evidence, model) == []


def test_unmapped_nested_type_is_reported_without_rejecting_row_fields() -> None:
    model = copy.deepcopy(template("clingen_sop_v11"))
    category = model["sections"][1]["categories"][-1]
    category["types"] = [t for t in category["types"] if t["path"] != "rescue.human"]
    evidence = {
        "experimental_evidence": {
            "rescue": {
                "human": [{"points": 2}],
                "patient_cells": [{"points": 1, "extra_description": "curator text"}],
            }
        }
    }
    assert recompute_scores._unscored_keys(evidence, model) == [
        "experimental_evidence.rescue.human"
    ]


def test_recompute_reports_flagged_ids_and_paths_even_when_unchanged(
    db_session: Session,
    test_curation: CurationNew,
    test_user_admin: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summaries: list[dict] = []
    monkeypatch.setattr(
        recompute_scores.logger, "info", lambda msg, **kw: summaries.append(kw)
    )
    test_curation.evidence_data = {
        "experimental_evidence": {"rescue": {"human": [{"points": 99}]}}
    }
    db_session.commit()
    for _ in range(2):
        recompute_scores.recompute_all_scores(db_session)
        assert summaries[-1]["out_of_range"] == {
            str(test_curation.id): ["experimental_evidence.rescue.human[0].points"]
        }
