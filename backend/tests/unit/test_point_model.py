"""Point-model interpreter: golden parity with the old ClinGen engine, bands, caps, custom
categories, and saves scoring with the row's pinned methodology version."""

import copy
import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud.curation import curation_crud
from app.models.methodology import MethodologyVersion
from app.models.models import CurationNew, CurationSchema
from app.schemas.curation import CurationDraftSave
from app.scoring.clingen import ClinGenEngine
from app.scoring.point_limits import (
    enforce_clingen_point_ranges,
    point_range_errors,
    point_ranges,
)
from app.scoring.point_model import classify, point_model, score, template

pytestmark = pytest.mark.unit

GOLDEN = Path(__file__).with_name("point_model_golden.jsonl")
CLINGEN = template("clingen_sop_v11")
assert CLINGEN is not None
PMID = "12345678"


def _categories(result) -> dict[str, float]:
    return {
        c["key"]: c["score"]
        for s in result.evidence_breakdown["trace"]["sections"]
        for c in s["categories"]
    }


def _golden() -> list[dict]:
    return [json.loads(line) for line in GOLDEN.read_text().splitlines()]


@pytest.mark.parametrize("case", _golden(), ids=lambda c: c["verdict"])
def test_golden_parity_with_pre_interpreter_engine(case: dict) -> None:
    """Captured from the hard-coded ClinGenEngine before it became an interpreter."""
    result = ClinGenEngine().calculate_scores(case["evidence"], {})
    assert result.verdict == case["verdict"]
    assert result.scores == pytest.approx(case["scores"])
    categories = {f"{k}_score": v for k, v in _categories(result).items()}
    assert categories == pytest.approx(case["categories"])


@pytest.mark.parametrize(
    ("total", "flags", "expected"),
    [
        (-2, {}, "refuted"),
        (-1.01, {}, "refuted"),
        (-1, {}, "disputed"),
        (-0.5, {}, "disputed"),
        (0, {}, "no_known"),
        (0.09, {}, "no_known"),
        (0.1, {}, "limited"),
        (1, {}, "limited"),
        (6, {}, "limited"),
        (6.99, {}, "limited"),
        (7, {}, "moderate"),
        (11, {}, "moderate"),
        (11.99, {"replicated_over_time": True}, "moderate"),
        (12, {}, "strong"),
        (18, {}, "strong"),
        (12, {"replicated_over_time": True}, "definitive"),
        (
            18,
            {"replicated_over_time": True, "contradictory_evidence": [{"pmid": "1"}]},
            "disputed",
        ),
    ],
)
def test_clingen_bands(total: float, flags: dict, expected: str) -> None:
    assert classify(CLINGEN, total, flags)["class"] == expected


def _row(type_def: dict, points: float) -> dict:
    return {type_def.get("points_key", "points"): points, "pmid": PMID}


def _put(evidence: dict, path: str, rows: list) -> None:
    *parents, leaf = path.split(".")
    for key in parents:
        evidence = evidence.setdefault(key, {})
    evidence[leaf] = rows


CATEGORIES = [
    (section["key"], category)
    for section in CLINGEN["sections"]
    for category in section["categories"]
]


@pytest.mark.parametrize(
    ("section", "category"), CATEGORIES, ids=[c["key"] for _, c in CATEGORIES]
)
def test_each_category_cap_boundary(section: str, category: dict) -> None:
    type_def = category["types"][0]
    cap = category["cap"]
    for rows, expected in (
        ([_row(type_def, cap - 0.5)], cap - 0.5),
        ([_row(type_def, cap - 0.5), _row(type_def, 0.5)], cap),
        ([_row(type_def, cap - 0.5), _row(type_def, 1.0)], cap),
    ):
        evidence: dict = {}
        _put(evidence, type_def["path"], rows)
        result = ClinGenEngine().calculate_scores({section: evidence}, {})
        assert _categories(result)[category["key"]] == pytest.approx(expected)


def test_section_and_total_caps() -> None:
    experimental = {
        "function": {"expression": [{"points": 2}]},
        "functional_alteration": {"patient_cells": [{"points": 2}]},
        "models": {"cell_culture_model": [{"points": 2}]},
        "rescue": {"cell_culture": [{"points": 1}]},
    }  # 7 raw
    genetic = {
        "case_level": {
            "autosomal_recessive": {
                "predicted_or_proven_null": [{"proband_counted_points": 3}] * 4
            }
        },
        "segregation": [{"points": 1}],
    }  # 13 raw
    result = ClinGenEngine().calculate_scores(
        {"genetic_evidence": genetic, "experimental_evidence": experimental}, {}
    )
    trace = result.evidence_breakdown["trace"]
    assert [(s["raw"], s["score"]) for s in trace["sections"]] == [(13, 12), (7, 6)]
    assert (trace["raw_total"], trace["total"], result.total_score) == (18, 18, 18)
    model = {**CLINGEN, "total_cap": 17}
    capped = ClinGenEngine().calculate_scores(
        {"genetic_evidence": genetic, "experimental_evidence": experimental},
        {"point_model": model},
    )
    assert capped.total_score == 17


def _custom_model() -> dict:
    """ClinGen minus rescue-in-human, plus a patient registry cohort category."""
    model = copy.deepcopy(CLINGEN)
    genetic, experimental = model["sections"]
    genetic["categories"].append(
        {
            "key": "patient_registry_cohort",
            "cap": 2,
            "types": [
                {
                    "path": "patient_registry_cohort.cohorts",
                    "default": 1,
                    "range": [0, 2],
                }
            ],
        }
    )
    rescue = next(c for c in experimental["categories"] if c["key"] == "rescue")
    rescue["types"] = [t for t in rescue["types"] if t["path"] != "rescue.human"]
    return model


CUSTOM_EVIDENCE = {
    "genetic_evidence": {"patient_registry_cohort": {"cohorts": [{}, {"points": 0.5}]}},
    "experimental_evidence": {"rescue": {"human": [{"points": 2}]}},
}


def test_custom_category_scores_without_code_changes() -> None:
    result = ClinGenEngine().calculate_scores(
        CUSTOM_EVIDENCE, {"point_model": _custom_model()}
    )
    assert _categories(result)["patient_registry_cohort"] == 1.5
    assert _categories(result)["rescue"] == 0  # removed type no longer counts
    assert result.total_score == 1.5
    assert result.verdict == "limited"
    default = ClinGenEngine().calculate_scores(CUSTOM_EVIDENCE, {})
    assert default.total_score == 2  # the template ignores the custom key


def test_plain_model_needs_no_clingen_rules() -> None:
    model = {
        "sections": [
            {
                "key": "s",
                "categories": [{"key": "c", "types": [{"path": "t", "default": 2}]}],
            }
        ],
        "bands": [{"class": "high", "min": 3}, {"class": "low"}],
    }
    result = score(model, {"s": {"t": [{}, {}]}})
    assert (result["total"], result["class"]) == (4, "high")
    assert score(model, {"s": {"t": [{}]}})["class"] == "low"
    assert score({**model, "bands": []}, {})["class"] == "no_known"


def test_point_model_selection() -> None:
    assert point_model({"point_model": {"x": 1}}) == {"x": 1}
    assert point_model({"engine": "clingen_sop_v11"}) is CLINGEN
    assert point_model({"engine": "gencc_based"}) is None
    assert point_model({"engine": "../../etc/passwd"}) is None
    assert point_model(None) is None


def test_custom_ranges_come_from_the_model() -> None:
    ranges = point_ranges(_custom_model())
    assert ranges["cohorts"] == (0, 2)
    bad = {
        "genetic_evidence": {"patient_registry_cohort": {"cohorts": [{"points": 3}]}}
    }
    (error,) = point_range_errors(bad, ranges=ranges)
    assert "cohorts[0].points must be a number between 0 and 2" in error
    assert point_range_errors(bad) == []  # not a ClinGen type


def _version(
    db: Session, curation: CurationNew, number: int, config: dict
) -> MethodologyVersion:
    pair = curation.workflow_pair
    if pair.curation_schema_id is None:
        schema = CurationSchema(
            id=uuid4(),
            name="Point model schema",
            version="1.0",
            schema_type="curation",
            field_definitions={},
            workflow_states={},
            ui_configuration={},
            scoring_configuration={"engine": "gencc_based"},
            schema_hash=uuid4().hex,
        )
        db.add(schema)
        db.flush()
        pair.curation_schema_id = schema.id
    version = MethodologyVersion(
        id=uuid4(),
        schema_id=pair.curation_schema_id,
        version=number,
        snapshot={"scoring_configuration": config},
    )
    db.add(version)
    db.commit()
    return version


def _save(db: Session, curation: CurationNew, evidence: dict) -> CurationNew:
    result = curation_crud.save_draft(
        db,
        db_obj=curation,
        draft_data=CurationDraftSave(
            evidence_data=evidence, lock_version=curation.lock_version
        ),
        user_id=curation.created_by,
    )
    assert result is not None
    return result


def test_save_scores_with_pinned_version_and_stores_trace(
    db_session: Session, test_curation: CurationNew
) -> None:
    pinned = _version(db_session, test_curation, 1, {"point_model": _custom_model()})
    _version(db_session, test_curation, 2, {"engine": "clingen_sop_v11"})

    latest = _save(db_session, test_curation, CUSTOM_EVIDENCE)  # unpinned: latest wins
    assert latest.computed_scores["total_score"] == 2

    test_curation.methodology_version_id = pinned.id
    db_session.commit()
    saved = _save(db_session, test_curation, CUSTOM_EVIDENCE)
    assert saved.computed_scores["total_score"] == 1.5
    assert saved.computed_scores["trace"]["total"] == 1.5
    assert saved.computed_verdict == "limited"
    preview = curation_crud.calculate_score(db_session, saved)
    assert preview.total_score == 1.5


def test_point_ranges_use_pinned_version(
    db_session: Session, test_curation: CurationNew
) -> None:
    pinned = _version(db_session, test_curation, 1, {"point_model": _custom_model()})
    _version(db_session, test_curation, 2, {"engine": "clingen_sop_v11"})
    bad = {
        "genetic_evidence": {"patient_registry_cohort": {"cohorts": [{"points": 3}]}}
    }
    pair_id = test_curation.workflow_pair_id
    enforce_clingen_point_ranges(db_session, pair_id, bad)  # latest: no such type
    with pytest.raises(HTTPException) as exc:
        enforce_clingen_point_ranges(db_session, pair_id, bad, pinned.id)
    assert exc.value.status_code == 422
