"""Writes persist engine scores; score previews are read-only."""

import pytest
from sqlalchemy.orm import Session

from app.crud.curation import curation_crud
from app.models.models import CurationNew, CurationStatus, PrecurationNew

pytestmark = pytest.mark.unit

_NULL = {"pmid": "12345678", "variant": "c.1A>T", "proband_counted_points": 1.5}


def test_calculate_score_reports_without_persisting_genetic_score(
    db_session: Session, test_curation: CurationNew
) -> None:
    test_curation.evidence_data = {
        "genetic_evidence": {
            "case_level": {
                "autosomal_dominant_or_x_linked": {
                    "predicted_or_proven_null": [_NULL, _NULL]
                }
            }
        },
        "experimental_evidence": {},
    }

    db_session.commit()
    before = dict(test_curation.computed_scores)
    result = curation_crud.calculate_score(db_session, test_curation)

    assert result.genetic_score == pytest.approx(3.0)
    assert result.total_score == pytest.approx(3.0)
    assert not db_session.is_modified(test_curation)
    db_session.expire(test_curation)
    assert test_curation.computed_scores == before
    assert test_curation.computed_verdict is None


def test_scope_list_reads_persisted_engine_scores(
    db_session: Session, test_curation: CurationNew
) -> None:
    test_curation.computed_scores = {
        "total_score": 7,
        "genetic_evidence_total": 5,
        "experimental_evidence_total": 2,
    }
    test_curation.computed_verdict = "moderate"
    db_session.commit()
    summaries, _ = curation_crud.get_multi_filtered(db_session)
    summary = next(row for row in summaries if row.id == test_curation.id)
    assert summary.computed_verdict == "Moderate"
    assert summary.computed_scores == {
        "total_score": 7,
        "genetic_score": 5,
        "experimental_score": 2,
    }


@pytest.mark.parametrize("operation", ["create", "update", "draft", "submit"])
def test_evidence_writes_persist_engine_result(
    db_session: Session,
    test_curation: CurationNew,
    approved_precuration: PrecurationNew,
    operation: str,
) -> None:
    from app.schemas.curation import (
        CurationCreate,
        CurationDraftSave,
        CurationSubmit,
        CurationUpdate,
    )
    from app.scoring.clingen import ClinGenEngine

    evidence = {
        "genetic_evidence": {
            "case_control": {
                "single_variant_analysis": [{"points": 2, "pmid": "12345678"}]
            }
        }
    }
    user_id = test_curation.created_by
    if operation == "create":
        # An open curation blocks a new one
        test_curation.status = CurationStatus.ARCHIVED
        db_session.commit()
        result = curation_crud.create_curation(
            db_session,
            obj_in=CurationCreate(
                gene_id=test_curation.gene_id,
                scope_id=test_curation.scope_id,
                workflow_pair_id=test_curation.workflow_pair_id,
                evidence_data=evidence,
            ),
            user_id=user_id,
        )
    elif operation == "update":
        test_curation.is_draft = False
        result = curation_crud.update_with_lock(
            db_session,
            db_obj=test_curation,
            obj_in=CurationUpdate(
                lock_version=test_curation.lock_version, evidence_data=evidence
            ),
            user_id=user_id,
        )
    elif operation == "draft":
        saved = curation_crud.save_draft(
            db_session,
            db_obj=test_curation,
            draft_data=CurationDraftSave(
                evidence_data=evidence, lock_version=test_curation.lock_version
            ),
            user_id=user_id,
        )
        result = saved[0] if saved else None
    else:
        test_curation.evidence_data = evidence
        db_session.commit()
        result = curation_crud.submit_for_review(
            db_session,
            db_obj=test_curation,
            submit_data=CurationSubmit(lock_version=test_curation.lock_version),
            user_id=user_id,
        )
    assert result is not None
    db_session.expire(result)
    expected = ClinGenEngine().calculate_scores(evidence, {})
    assert result.computed_scores["total_score"] == expected.total_score
    assert result.computed_scores["genetic_evidence_total"] == 2
    assert result.computed_verdict == expected.verdict
    assert result.computed_summary == expected.verdict_rationale


def test_draft_can_save_unscored_rows(
    db_session: Session, test_curation: CurationNew
) -> None:
    from app.schemas.curation import CurationDraftSave

    evidence = {
        "genetic_evidence": {
            "case_level": {
                "autosomal_dominant_or_x_linked": {
                    "predicted_or_proven_null": [{"proband_counted_points": None}],
                    "other_variant_type": [{"proband_counted_points": None}],
                }
            },
            "segregation": [{"points": None}],
            "case_control": {
                "single_variant_analysis": [{"points": None}],
                "aggregate_variant_analysis": [{"points": None}],
            },
        },
        "experimental_evidence": {"function": {"expression": [{"points": None}]}},
    }
    saved = curation_crud.save_draft(
        db_session,
        db_obj=test_curation,
        draft_data=CurationDraftSave(
            evidence_data=evidence, lock_version=test_curation.lock_version
        ),
        user_id=test_curation.created_by,
    )
    assert saved is not None
    result = saved[0]
    assert result.evidence_data == evidence
    assert result.computed_scores["total_score"] == 0


def test_recompute_all_scores_is_idempotent(
    db_session: Session, test_curation: CurationNew, test_user_admin: object
) -> None:
    from app.services.recompute_scores import recompute_all_scores

    test_curation.evidence_data = {
        "genetic_evidence": {
            "case_level": {
                "autosomal_dominant_or_x_linked": {
                    "predicted_or_proven_null": [_NULL, _NULL]
                }
            }
        },
        "experimental_evidence": {},
    }
    test_curation.computed_verdict = None
    test_curation.computed_scores = {"raw_scores": {}}
    db_session.commit()
    updated_at = test_curation.updated_at

    assert recompute_all_scores(db_session) >= 1
    db_session.refresh(test_curation)
    first = (
        test_curation.computed_verdict,
        test_curation.computed_scores["total_score"],
    )
    assert first == ("limited", 3.0)
    recompute_all_scores(db_session)
    db_session.refresh(test_curation)
    assert first == (
        test_curation.computed_verdict,
        test_curation.computed_scores["total_score"],
    )
    assert test_curation.updated_at == updated_at


def test_recompute_requires_an_admin(db_session: Session) -> None:
    from app.services.recompute_scores import recompute_all_scores

    with pytest.raises(RuntimeError, match="admin"):
        recompute_all_scores(db_session)


def test_recompute_continues_past_a_failing_curation(
    db_session: Session,
    test_curation: CurationNew,
    test_user_admin: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.scoring.clingen import ClinGenEngine
    from app.services.recompute_scores import recompute_all_scores

    def boom(self: object, *args: object, **kwargs: object) -> None:
        raise ValueError("bad shape")

    monkeypatch.setattr(ClinGenEngine, "calculate_scores", boom)
    test_curation.evidence_data = {"genetic_evidence": []}
    db_session.commit()
    with pytest.raises(RuntimeError, match="1 of"):
        recompute_all_scores(db_session)


def test_recompute_skips_unscored_keys_and_counts_unchanged(
    db_session: Session, test_curation: CurationNew, test_user_admin: object
) -> None:
    from app.scoring.point_model import template
    from app.services.recompute_scores import _unscored_keys, recompute_all_scores

    model = template("clingen_sop_v11")
    assert _unscored_keys({"genetic_evidence_score": 3}, model)
    assert _unscored_keys(
        {"genetic_evidence": {"case_level_ad_xl": {"points": 1}}}, model
    )
    assert _unscored_keys("x", model)
    assert not _unscored_keys({"genetic_evidence": [], "evidence_summary": {}}, model)
    assert not _unscored_keys(None, model)

    test_curation.evidence_data = {"genetic_evidence_score": 3}
    test_curation.computed_verdict = "keep"
    db_session.commit()
    recompute_all_scores(db_session)
    db_session.refresh(test_curation)
    assert test_curation.computed_verdict == "keep"
    recompute_all_scores(db_session)  # second run: unchanged branch


def test_recompute_scores_custom_categories_of_the_pinned_model(
    db_session: Session,
    test_curation: CurationNew,
    test_user_admin: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Known keys come from the pinned point model: its custom categories are scored and
    reported; keys it does not score still skip the row and are reported (#434)."""
    from app.services import recompute_scores
    from tests.unit.test_point_model import CUSTOM_EVIDENCE, _custom_model, _version

    summaries: list[dict] = []
    monkeypatch.setattr(
        recompute_scores.logger, "info", lambda msg, **kw: summaries.append(kw)
    )
    v1 = _version(db_session, test_curation, 1, {"point_model": _custom_model()})
    v2 = _version(db_session, test_curation, 2, {"engine": "clingen_sop_v11"})
    test_curation.methodology_version_id = v1.id
    custom_evidence = {"genetic_evidence": CUSTOM_EVIDENCE["genetic_evidence"]}
    test_curation.evidence_data = {**custom_evidence, "evidence_summary": "cohort"}
    test_curation.computed_scores = {"total_score": 0.0}
    test_curation.computed_verdict = "no_known"
    db_session.commit()
    recompute_scores.recompute_all_scores(db_session)
    db_session.refresh(test_curation)
    assert test_curation.computed_scores["total_score"] == 1.5
    assert test_curation.computed_verdict == "limited"
    assert summaries[-1]["custom_categories"] == [
        "genetic_evidence.patient_registry_cohort"
    ]
    assert summaries[-1]["unscored"] == {}

    unknown = {"genetic_evidence": {"made_up": [{"points": 9}]}, "extra": 1}
    for version, evidence, keys in (
        (v1, unknown, ["extra", "genetic_evidence.made_up"]),
        (v2, custom_evidence, ["genetic_evidence.patient_registry_cohort"]),
    ):  # v2 is the template: the custom key is unknown there
        test_curation.methodology_version_id = version.id
        test_curation.evidence_data = evidence
        test_curation.computed_verdict = "keep"
        db_session.commit()
        recompute_scores.recompute_all_scores(db_session)
        db_session.refresh(test_curation)
        assert test_curation.computed_verdict == "keep"
        assert summaries[-1]["unscored"] == {str(test_curation.id): keys}
        assert summaries[-1]["custom_categories"] == []


def test_recompute_counts_a_refused_update_as_skipped(
    db_session: Session,
    test_curation: CurationNew,
    test_user_admin: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 0-row update (on Postgres: a curation of an inactive scope, 054) is skipped, not updated.
    SQLite has no RLS, so the row disappears between the read and the update instead."""
    from sqlalchemy import delete

    from app.services import recompute_scores

    summaries: list[dict] = []
    monkeypatch.setattr(
        recompute_scores.logger, "info", lambda msg, **kw: summaries.append(kw)
    )
    real = recompute_scores.scoring_configuration

    def vanish(db: Session, *args: object) -> object:
        db.execute(delete(CurationNew).where(CurationNew.id == test_curation.id))
        return real(db, *args)

    monkeypatch.setattr(recompute_scores, "scoring_configuration", vanish)
    test_curation.evidence_data = {"genetic_evidence": [], "experimental_evidence": {}}
    test_curation.computed_scores = {"raw_scores": {}}
    test_curation.computed_verdict = None
    db_session.commit()
    assert recompute_scores.recompute_all_scores(db_session) == 0
    assert summaries[-1]["updated"] == 0
    assert str(test_curation.id) in summaries[-1]["skipped_ids"]
