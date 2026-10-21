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


@pytest.mark.parametrize(
    ("models", "rescue", "expected"),
    [(2, 1.5, 3.5), (2, 2, 4), (4, 4, 4), (1, 0, 1), (0, 4, 4)],
)
def test_models_and_rescue_share_one_cap_of_four(
    models: float, rescue: float, expected: float
) -> None:
    """SOP v11 experimental matrix: Models & Rescue is one category, max 4 points."""
    experimental = {
        "models": {"non_human_model_organism": [{"points": models}]},
        "rescue": {"human": [{"points": rescue}]},
    }
    result = ClinGenEngine().calculate_scores(
        {"experimental_evidence": experimental}, {}
    )
    assert _categories(result)["models_and_rescue"] == expected
    assert result.total_score == expected
    legacy = [
        {"evidence_category": "models", "points": models},
        {"evidence_category": "rescue", "points": rescue},
    ]
    flat = ClinGenEngine().calculate_scores({"experimental_evidence": legacy}, {})
    assert _categories(flat)["models_and_rescue"] == expected


def test_experimental_categories_follow_sop_v11() -> None:
    """Function 2, Functional Alteration 2, Models & Rescue 4; experimental total 6."""
    _, experimental = CLINGEN["sections"]
    caps = {c["key"]: c["cap"] for c in experimental["categories"]}
    assert caps == {"function": 2, "functional_alteration": 2, "models_and_rescue": 4}
    assert experimental["cap"] == 6


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
    rescue = next(
        c for c in experimental["categories"] if c["key"] == "models_and_rescue"
    )
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
    assert (
        _categories(result)["models_and_rescue"] == 0
    )  # removed type no longer counts
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


def _narrowed_model() -> dict:
    """v2: cohorts narrowed to 0-1, segregation widened to 0-5."""
    model = _custom_model()
    for category in model["sections"][0]["categories"]:
        for type_def in category["types"]:
            if type_def["path"] == "patient_registry_cohort.cohorts":
                type_def["range"] = [0, 1]
            if type_def["path"] == "segregation":
                type_def["range"] = [0, 5]
    return model


def test_update_and_submit_check_ranges_of_the_pinned_version(
    client, admin_token, db_session: Session, test_curation: CurationNew
) -> None:
    v1 = _version(db_session, test_curation, 1, {"point_model": _custom_model()})
    _version(db_session, test_curation, 2, {"point_model": _narrowed_model()})
    test_curation.methodology_version_id = v1.id
    db_session.commit()
    headers = {"Authorization": f"Bearer {admin_token}"}
    url = f"/api/v1/curations/{test_curation.id}"
    ok_v1 = {
        "genetic_evidence": {"patient_registry_cohort": {"cohorts": [{"points": 1.5}]}}
    }
    ok_v2_only = {"genetic_evidence": {"segregation": [{"points": 4}]}}

    r = client.put(
        url, json={"evidence_data": ok_v1, "lock_version": 0}, headers=headers
    )
    assert r.status_code == 200, r.text
    lock = r.json()["lock_version"]
    r = client.put(
        url, json={"evidence_data": ok_v2_only, "lock_version": lock}, headers=headers
    )
    assert r.status_code == 422 and "between 0 and 3" in r.text

    test_curation.evidence_data = ok_v2_only  # e.g. saved through /draft
    db_session.commit()
    r = client.post(f"{url}/submit", json={"lock_version": lock}, headers=headers)
    assert r.status_code == 422 and "between 0 and 3" in r.text


def test_recompute_scores_with_the_pinned_version(
    db_session: Session, test_curation: CurationNew, test_user_admin: object
) -> None:
    from app.services.recompute_scores import recompute_all_scores

    v1 = _version(db_session, test_curation, 1, {"point_model": _custom_model()})
    _version(db_session, test_curation, 2, {"engine": "clingen_sop_v11"})
    test_curation.evidence_data = {
        "experimental_evidence": {"rescue": {"human": [{"points": 2}]}}
    }
    test_curation.methodology_version_id = v1.id
    db_session.commit()
    recompute_all_scores(db_session)
    db_session.refresh(test_curation)
    assert (
        test_curation.computed_scores["total_score"] == 0
    )  # v1 has no rescue in human


def test_recompute_logs_class_changes_and_skips_other_engines(
    db_session: Session,
    test_curation: CurationNew,
    test_user_admin: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import recompute_scores

    calls: list[dict] = []
    monkeypatch.setattr(
        recompute_scores.logger, "warning", lambda msg, **kw: calls.append(kw)
    )
    v1 = _version(db_session, test_curation, 1, {"engine": "clingen_sop_v11"})
    test_curation.methodology_version_id = v1.id
    test_curation.evidence_data = {
        "genetic_evidence": {
            "segregation": [{"points": 3}],
            "case_control": {"single_variant_analysis": [{"points": 4}]},
        },  # 7
        "experimental_evidence": {
            "models": {"non_human_model_organism": [{"points": 4}]},
            "rescue": {"human": [{"points": 4}]},
        },
    }  # two caps of 4 gave 7 + 6 = 13 Strong; SOP v11 one cap of 4: 7 + 4 = 11 Moderate
    test_curation.computed_scores = {"total_score": 13.0}
    test_curation.computed_verdict = "strong"
    db_session.commit()
    recompute_scores.recompute_all_scores(db_session)
    db_session.refresh(test_curation)
    assert test_curation.computed_scores["total_score"] == 11
    assert test_curation.computed_verdict == "moderate"
    (change,) = calls
    assert change["curation_id"] == str(test_curation.id)
    assert change["gene"] == test_curation.gene.approved_symbol
    assert (change["total"], change["verdict"]) == (
        "13.0 -> 11.0",
        "strong -> moderate",
    )

    v2 = _version(db_session, test_curation, 2, {"engine": "gencc_based"})
    test_curation.methodology_version_id = v2.id
    test_curation.computed_verdict = "keep"
    db_session.commit()
    recompute_scores.recompute_all_scores(db_session)
    db_session.refresh(test_curation)
    assert test_curation.computed_verdict == "keep"  # never scored with ClinGen points
