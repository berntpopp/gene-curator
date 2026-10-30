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
from tests.unit.test_cited_evidence import uncited_off  # noqa: F401 (fixture)

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


@pytest.mark.usefixtures("uncited_off")
@pytest.mark.parametrize("case", _golden(), ids=lambda c: c["verdict"])
def test_golden_parity_with_pre_interpreter_engine(case: dict) -> None:
    """Captured from the hard-coded ClinGenEngine before it became an interpreter. Cases
    with out-of-range rows score exactly as without those rows (#278), and every category
    without a flagged row keeps its golden score."""
    result = ClinGenEngine().calculate_scores(case["evidence"], {})
    trace = result.evidence_breakdown["trace"]
    if flags := trace.get("out_of_range"):
        trimmed = copy.deepcopy(case["evidence"])
        for flag in flags:
            container, key = _slot(trimmed, flag["path"].rsplit(".", 1)[0])
            container[key] = None  # type: ignore[index]
        again = ClinGenEngine().calculate_scores(trimmed, {})
        assert result.scores == pytest.approx(again.scores)
        assert result.verdict == again.verdict
        # a legacy flat-list flag ("section[i]") names its section, not a category
        tables = {flag["path"].rsplit("[", 1)[0] for flag in flags}
        clean = {
            f"{c['key']}_score": c["score"]
            for s in trace["sections"]
            for c in s["categories"]
            if s["key"] not in tables
            and not tables & {f"{s['key']}.{t['path']}" for t in c["types"]}
        }
        assert clean  # most cases flag one table: parity still covers the rest
        assert clean == pytest.approx({k: case["categories"][k] for k in clean})
        return
    assert result.verdict == case["verdict"]
    assert result.scores == pytest.approx(case["scores"])
    categories = {f"{k}_score": v for k, v in _categories(result).items()}
    assert categories == pytest.approx(case["categories"])


def _slot(evidence: dict, path: str) -> tuple[object, object]:
    """(container, key) of the row at ``a.b[i]``; a legacy {points} summary dict is row 0."""
    head, index = path.rsplit("[", 1)
    *parents, leaf = head.split(".")
    node: object = evidence
    for key in parents:
        node = node[key]  # type: ignore[index]
    if isinstance(node[leaf], dict):  # type: ignore[index]
        return node, leaf
    return node[leaf], int(index.rstrip("]"))  # type: ignore[index]


@pytest.mark.parametrize("case", _golden(), ids=lambda c: c["verdict"])
def test_golden_with_the_citation_policy_on(case: dict) -> None:
    """Real-shaped rows: each excluded row really lacks its citation, and the policy only
    removes those rows' points (the rest scores exactly as with the policy off)."""
    result = ClinGenEngine().calculate_scores(case["evidence"], {})
    excluded = result.evidence_breakdown.get("excluded", [])
    assert result.total_score <= case["scores"]["total_score"] + 1e-9
    trimmed = copy.deepcopy(case["evidence"])
    for entry in excluded:
        container, key = _slot(trimmed, entry["path"])
        value = container[key].get(entry["field"])  # type: ignore[index]
        assert entry["reason"] in ("no_pmid", "no_variant", "placeholder_variant")
        assert entry["reason"] == "placeholder_variant" or not str(value or "").strip()
        container[key] = None  # type: ignore[index]
    again = ClinGenEngine().calculate_scores(trimmed, {})
    assert again.total_score == pytest.approx(result.total_score)
    assert "excluded" not in again.evidence_breakdown


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
            "definitive",
        ),
        (
            18,
            {"contradictory_evidence": [{"pmid": "1", "impact": "disputed"}]},
            "disputed",
        ),
        (12, {"contradictory_evidence": [{"pmid": "1", "impact": "note"}]}, "strong"),
    ],
)
def test_clingen_bands(total: float, flags: dict, expected: str) -> None:
    assert classify(CLINGEN, total, flags, {})["class"] == expected


def test_row_field_override_passes_the_static_check() -> None:
    from app.core.schema_rules import check_schema_definition

    def errors(model: dict) -> list[str]:
        schema = {
            "field_definitions": {"gene": {"type": "text"}},
            "workflow_states": ["draft", "submitted"],
            "ui_configuration": {"sections": []},
            "scoring_configuration": {
                "engine": "clingen_sop_v11",
                "point_model": model,
            },
        }
        return [p for s, p, _ in check_schema_definition(schema) if s == "error"]

    assert errors(CLINGEN) == []
    bad = copy.deepcopy(CLINGEN)
    bad["overrides"][0]["in"] = "disputed"  # a string would match substrings
    assert errors(bad) == ["scoring_configuration.point_model.overrides[0].in"]
    del bad["overrides"][0]["field"]
    bad["overrides"][0]["in"] = [
        "disputed"
    ]  # without a field it would dispute on any row
    assert errors(bad) == ["scoring_configuration.point_model.overrides[0].field"]


def _row(type_def: dict, points: float) -> dict:
    return {
        "score_status": "score",
        type_def.get("points_key", "points"): points,
        "pmid": PMID,
        "variant": "c.1A>T",
    }


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
    high = type_def["range"][1]  # rows above their range count nothing (#278)
    below = [_row(type_def, high)] * int((cap - 0.5) // high)
    below.append(_row(type_def, cap - 0.5 - high * len(below)))
    for rows, expected in (
        (below, cap - 0.5),
        ([*below, _row(type_def, 0.5)], cap),
        ([*below, _row(type_def, 1.0)], cap),
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
        "models": {"non_human_model_organism": [{"points": models, "pmid": PMID}]},
        "rescue": {"human": [{"points": rescue, "pmid": PMID}]},
    }
    result = ClinGenEngine().calculate_scores(
        {"experimental_evidence": experimental}, {}
    )
    assert _categories(result)["models_and_rescue"] == expected
    assert result.total_score == expected
    legacy = [
        {"evidence_category": "models", "points": models, "pmid": PMID},
        {"evidence_category": "rescue", "points": rescue, "pmid": PMID},
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
        "function": {"expression": [{"points": 2, "pmid": PMID}]},
        "functional_alteration": {"patient_cells": [{"points": 2, "pmid": PMID}]},
        "models": {"cell_culture_model": [{"points": 2, "pmid": PMID}]},
        "rescue": {"cell_culture": [{"points": 1, "pmid": PMID}]},
    }  # 7 raw
    genetic = {
        "case_level": {
            "autosomal_recessive": {
                "predicted_or_proven_null": [
                    {
                        "proband_counted_points": 3,
                        "pmid": PMID,
                        "variant_1": "c.1A>T",
                        "score_status": "score",
                    }
                ]
                * 4
            }
        },
        "segregation": [{"points": 1, "pmid": PMID}],
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
    "genetic_evidence": {
        "patient_registry_cohort": {
            "cohorts": [{"pmid": PMID}, {"points": 0.5, "pmid": PMID}]
        }
    },
    "experimental_evidence": {"rescue": {"human": [{"points": 2, "pmid": PMID}]}},
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
    result = score(model, {"s": {"t": [{"pmid": PMID}, {"pmid": PMID}]}})
    assert (result["total"], result["class"]) == (4, "high")
    assert score(model, {"s": {"t": [{"pmid": PMID}]}})["class"] == "low"
    uncited = score(model, {"s": {"t": [{}]}})  # default points need a citation too
    assert (uncited["total"], uncited["excluded"]) == (
        0,
        [{"path": "s.t[0]", "field": "pmid", "reason": "no_pmid"}],
    )
    assert score({**model, "bands": []}, {})["class"] == "no_known"


def test_point_model_selection() -> None:
    assert point_model({"point_model": {"x": 1}}) == {"x": 1}
    assert point_model({"engine": "clingen_sop_v11"}) is CLINGEN
    assert point_model({"engine": "gencc_based"}) is None
    assert point_model({"engine": "../../etc/passwd"}) is None
    assert point_model(None) is None


def test_custom_ranges_come_from_the_model() -> None:
    ranges = point_ranges(_custom_model())
    assert ranges["patient_registry_cohort.cohorts"] == (0, 2)
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
    return result[0]


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
        "genetic_evidence": {
            "patient_registry_cohort": {"cohorts": [{"points": 1.5, "pmid": PMID}]}
        }
    }
    ok_v2_only = {"genetic_evidence": {"segregation": [{"points": 4, "pmid": PMID}]}}

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
    test_curation.computed_scores = {"total_score": 2.0}
    test_curation.computed_verdict = "limited"
    db_session.commit()
    recompute_all_scores(db_session)
    db_session.refresh(test_curation)
    # The pinned custom model cannot score this nested type: preserve the stored result.
    assert test_curation.computed_scores == {"total_score": 2.0}
    assert test_curation.computed_verdict == "limited"


def test_recompute_logs_class_changes_and_uses_other_engines(
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
            "segregation": [{"points": 3, "pmid": PMID}],
            "case_control": {"single_variant_analysis": [{"points": 4, "pmid": PMID}]},
        },  # 7
        "experimental_evidence": {
            "models": {"non_human_model_organism": [{"points": 4, "pmid": PMID}]},
            "rescue": {"human": [{"points": 4, "pmid": PMID}]},
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
    # scored by the GenCC engine, never with ClinGen points (#496)
    assert test_curation.computed_verdict == "No Known Disease Relationship"

    test_curation.methodology_version_id = v1.id
    test_curation.computed_scores = {"total_score": 12.0}  # same class, other total
    test_curation.computed_verdict = "moderate"
    db_session.commit()
    recompute_scores.recompute_all_scores(db_session)
    assert calls[-1]["total"] == "12.0 -> 11.0"
    assert calls[-1]["verdict"] == "moderate -> moderate"


def test_ar_other_variant_proband_may_score_three_but_ad_not() -> None:
    """SOP v11: each AR variant 0-1.5, summed per proband (max 3); AD/XL other max 1.5."""

    def rows(inheritance: str, points: float) -> dict:
        case = {
            inheritance: {"other_variant_type": [{"proband_counted_points": points}]}
        }
        return {"genetic_evidence": {"case_level": case}}

    assert point_range_errors(rows("autosomal_recessive", 3)) == []
    assert point_range_errors(rows("autosomal_recessive", 3.1))
    assert point_range_errors(rows("autosomal_dominant_or_x_linked", 2))
    assert point_range_errors(rows("unknown_shape", 2))  # strictest range applies


def test_case_control_analyses_are_summed_up_to_twelve() -> None:
    """SOP v11: single variant (0-6) + aggregate (0-6) analyses summed, category max 12."""
    for single, aggregate, expected in ((4, 3, 7), (6, 6, 12), (6, 0, 6)):
        evidence = {
            "case_control": {
                "single_variant_analysis": [{"points": single, "pmid": PMID}],
                "aggregate_variant_analysis": [{"points": aggregate, "pmid": PMID}],
            }
        }
        result = ClinGenEngine().calculate_scores({"genetic_evidence": evidence}, {})
        assert _categories(result)["case_control"] == expected


def test_validate_evidence_scores_with_the_pinned_point_model(
    client, admin_token, db_session: Session, test_curation: CurationNew
) -> None:
    """Live score for the forms: verdict and trace from the pinned version, nothing saved."""
    config = {"engine": "clingen_sop_v11", "point_model": _custom_model()}
    pinned = _version(db_session, test_curation, 1, config)
    _version(db_session, test_curation, 2, {"engine": "clingen_sop_v11"})
    before = test_curation.computed_scores
    r = client.post(
        "/api/v1/validation/validate-evidence",
        json={
            "evidence_data": CUSTOM_EVIDENCE,
            "methodology_version_id": str(pinned.id),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    scores = r.json()["score_calculations"]
    saved = ClinGenEngine().calculate_scores(
        CUSTOM_EVIDENCE, config
    )  # what a save stores
    assert (scores["total_score"], scores["verdict"]) == (1.5, "limited")
    assert scores["trace"] == saved.evidence_breakdown["trace"]
    db_session.refresh(test_curation)
    assert test_curation.computed_scores == before


@pytest.mark.parametrize(
    "evidence",
    [
        {},
        {"replicated_over_time": True},
        {"contradictory_evidence": [{"impact": "disputed"}]},
    ],
)
def test_trace_records_exact_selected_classification_rule(evidence: dict) -> None:
    model = copy.deepcopy(CLINGEN)
    model["bands"] = [
        {"class": "replicated", "min": 0, "requires": "replicated_over_time"},
        {"class": "custom", "min": 0, "description": "Custom classification"},
    ]
    result = score(model, evidence)
    assert result["trace"]["classification_rule"] == classify(model, 0, evidence, {})
    assert result["total"] == 0
