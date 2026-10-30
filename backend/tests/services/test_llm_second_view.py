"""LLM second view (#464, #465): blind input, cited findings, engine-scored proposals,
the three-way diff, and advisory-only output (nothing in the curation changes)."""

import json
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.llm.output import InvalidLLMOutputError
from app.models import CurationNew, Review
from app.models.llm import LLMFinding, LLMRun
from app.services import llm_worker
from app.services.llm_runs import curation_values, enqueue_run, load_golden
from app.services.llm_second_view import (
    cited_findings,
    diff_rows,
    proposal,
    second_view,
)
from tests.api.llm_api_support import llm_env  # noqa: F401
from tests.services.llm_run_support import (
    World,
    canned,
    factory,
    world_fixture,  # noqa: F401
)

pytestmark = [pytest.mark.unit, pytest.mark.usefixtures("llm_env")]

EXPERT = load_golden()[0]["expert_evidence"]  # ClinGen SOP v11: limited


def _output(**extra: Any) -> str:
    return json.dumps(
        {
            "verdict": "supported",  # the world's prompt schema requires it
            "findings": [
                {
                    "category": "case_level",
                    "message": "P1 is counted twice",
                    "citations": ["31000001", "not a citation"],
                },
                {"category": "function", "message": "uncited", "citations": []},
            ],
            "proposed_evidence": json.dumps(EXPERT),
            **extra,
        }
    )


def test_cited_findings_keep_only_cited_and_normalize_pmids() -> None:
    data = {
        "findings": [
            {"category": "a", "message": "m", "citations": ["pmid: 123", "ClinVar:9"]},
            {"category": "b", "message": "m", "citations": ["see paper"]},
            {"category": "c", "message": " ", "citations": ["PMID:1"]},
            {"message": "m", "citations": ["HP:0001250", "HP:0001250"]},
            "not a finding",
            {"category": "d", "message": "m", "citations": "PMID:1"},
        ]
    }
    assert cited_findings(data) == [
        {"category": "a", "message": "m", "citations": ["PMID:123", "ClinVar:9"]},
        {"category": "general", "message": "m", "citations": ["HP:0001250"]},
    ]
    assert cited_findings({"findings": {"x": 1}}) == []


def test_proposal_scores_with_the_engine() -> None:
    scores, verdict = proposal({"proposed_evidence": json.dumps(EXPERT)}, {})
    assert verdict == "limited" and scores and scores["total_score"] > 0
    assert proposal({"proposed_evidence": EXPERT}, {})[1] == "limited"
    assert proposal({}, {}) == (None, None)
    for bad in ("not json", "[]", 3):
        with pytest.raises(InvalidLLMOutputError):
            proposal({"proposed_evidence": bad}, {})


def test_the_model_never_sees_the_curators_conclusion(
    db_session: Session, world: World
) -> None:
    world.curation.computed_scores = {"total_score": 17.5}
    world.curation.computed_verdict = "definitive"
    world.curation.evidence_data = {
        **(world.curation.evidence_data or {}),
        "initial_assessment": {"preliminary_verdict": "definitive"},
    }
    db_session.commit()
    sent = json.dumps(curation_values(db_session, world.curation))
    for conclusion in ("definitive", "17.5", "Strong evidence", "total_score"):
        assert conclusion not in sent
    assert "segregates" in sent  # the evidence itself is still sent


def test_no_curator_judgement_reaches_the_provider(
    db_session: Session, world: World
) -> None:
    world.curation.evidence_data = {
        "genetic_evidence": {
            "case_level": {
                "autosomal_dominant_or_x_linked": {
                    "predicted_or_proven_null": [
                        {
                            "proband_label": "P1",
                            "variant": "c.100C>T",
                            "pmid": "31000001",
                            "proband_counted_points": 2.75,
                            "score_status": "score",
                            "explanation": "upgraded for de novo",
                        }
                    ]
                }
            }
        },
        "evidence_summary": "Classified as DEFINITIVE by the curator",
        "contradictory_evidence": [{"pmid": "34000001", "impact": "disputed"}],
        "replicated_over_time": True,
    }
    db_session.commit()
    sent = curation_values(db_session, world.curation)["curation_data"]
    for judgement in (
        "proband_counted_points",
        "2.75",
        "score_status",
        "upgraded",
        "DEFINITIVE",
        "impact",
        "replicated_over_time",
    ):
        assert judgement not in sent
    for fact in ("P1", "c.100C>T", "31000001", "34000001"):
        assert fact in sent


def _snapshot(curation: CurationNew) -> tuple[Any, ...]:
    return (
        json.dumps(curation.evidence_data, sort_keys=True),
        json.dumps(curation.computed_scores, sort_keys=True),
        curation.computed_verdict,
        curation.status,
        curation.workflow_stage,
        curation.lock_version,
    )


@pytest.mark.asyncio
async def test_worker_stores_cited_findings_and_proposal_only(
    db_session: Session, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = _snapshot(world.curation)
    reviews = db_session.scalar(select(func.count()).select_from(Review))
    canned(monkeypatch, _output())
    run = enqueue_run(db_session, world.scope_admin, world.curation.id, "skeptic")

    assert await llm_worker.process_next(factory(db_session.get_bind())) is True  # type: ignore[arg-type]

    db_session.expire_all()
    done = db_session.get(LLMRun, run.id)
    assert done is not None and done.status == "succeeded"
    assert done.proposed_verdict == "limited" and done.proposed_scores
    findings = db_session.scalars(select(LLMFinding)).all()
    assert [(f.category, f.citations) for f in findings] == [
        ("case_level", ["PMID:31000001"])
    ]
    # advisory only: no evidence, score, class, state or review changes
    curation = db_session.get(CurationNew, world.curation.id)
    assert curation is not None and _snapshot(curation) == before
    assert db_session.scalar(select(func.count()).select_from(Review)) == reviews

    view = second_view(db_session, curation)
    assert view["runs"][0]["model_id"] == "mock-model" and not view["pending"]
    assert view["findings"][0]["strategy"] == "skeptic"
    by_category = {r["category"]: r for r in view["diff"]}
    assert by_category["classification"]["skeptic"] == "limited"
    assert by_category["total_score"]["skeptic"] == done.proposed_scores["total_score"]


@pytest.mark.asyncio
async def test_unscorable_proposal_fails_the_run_and_keeps_nothing(
    db_session: Session, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    canned(monkeypatch, _output(proposed_evidence="{broken"))
    run = enqueue_run(db_session, world.scope_admin, world.curation.id, "skeptic")
    await llm_worker.process_next(factory(db_session.get_bind()))  # type: ignore[arg-type]
    db_session.expire_all()
    done = db_session.get(LLMRun, run.id)
    assert done is not None
    assert (done.status, done.error_code) == ("failed", "invalid_output")
    assert done.proposed_verdict is None
    assert db_session.scalars(select(LLMFinding)).all() == []


@pytest.mark.asyncio
async def test_a_run_no_longer_running_keeps_no_findings(
    db_session: Session, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    canned(monkeypatch, _output())
    run = enqueue_run(db_session, world.scope_admin, world.curation.id, "skeptic")
    original = llm_worker._call

    async def failed_meanwhile(prepared: Any, outcome: Any) -> None:
        await original(prepared, outcome)
        with factory(db_session.get_bind())() as other:  # type: ignore[arg-type]
            other.execute(
                LLMRun.__table__.update()
                .where(LLMRun.id == run.id)
                .values(status="failed", error_code="interrupted")
            )
            other.commit()

    monkeypatch.setattr(llm_worker, "_call", failed_meanwhile)
    await llm_worker.process_next(factory(db_session.get_bind()))  # type: ignore[arg-type]
    assert db_session.scalars(select(LLMFinding)).all() == []


def test_diff_puts_disagreements_first(db_session: Session, world: World) -> None:
    world.curation.computed_scores = {"genetic_evidence_total": 6, "total_score": 6.5}
    world.curation.computed_verdict = "limited"
    advocate = LLMRun(
        proposed_scores={"genetic_evidence_total": 6.0, "total_score": 9.0},
        proposed_verdict="moderate",
    )
    skeptic = LLMRun(
        proposed_scores={"genetic_evidence_total": 6.0, "total_score": 6.5},
        proposed_verdict="limited",
    )
    rows = diff_rows(world.curation, {"advocate": advocate, "skeptic": skeptic})
    assert [(r["category"], r["disagree"]) for r in rows] == [
        ("total_score", True),
        ("classification", True),
        ("genetic_evidence_total", False),
    ]
    only_human = diff_rows(world.curation, {})
    assert only_human == [
        {
            "category": "classification",
            "human": "limited",
            "advocate": None,
            "skeptic": None,
            "disagree": False,
        }
    ]
