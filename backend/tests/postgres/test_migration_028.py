"""Application scores survive non-draft writes after migration 028."""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.crud.curation import curation_crud
from app.models.models import CurationNew, Gene, Scope, UserNew, WorkflowPair
from app.schemas.curation import CurationUpdate
from app.scoring.clingen import ClinGenEngine

pytestmark = pytest.mark.postgres


def test_non_draft_update_preserves_engine_scores(owner_session: Session) -> None:
    scope = owner_session.scalars(select(Scope)).first()
    user = owner_session.scalars(select(UserNew)).first()
    pair = owner_session.scalars(select(WorkflowPair)).first()
    assert scope is not None and user is not None and pair is not None
    gene = Gene(
        id=uuid4(),
        hgnc_id="HGNC:999028",
        approved_symbol="SCORE028",
        record_hash="0" * 64,
    )
    owner_session.add(gene)
    owner_session.flush()
    curation = CurationNew(
        id=uuid4(),
        gene_id=gene.id,
        scope_id=scope.id,
        workflow_pair_id=pair.id,
        workflow_stage="curation",
        is_draft=False,
        evidence_data={},
        created_by=user.id,
    )
    owner_session.add(curation)
    owner_session.flush()
    evidence = {
        "genetic_evidence": {
            "case_control": {"single_variant_analysis": [{"points": 2}]}
        }
    }
    result = curation_crud.update_with_lock(
        owner_session,
        db_obj=curation,
        obj_in=CurationUpdate(
            lock_version=curation.lock_version, evidence_data=evidence
        ),
        user_id=user.id,
    )
    assert result is not None
    owner_session.expire(result)
    expected = ClinGenEngine().calculate_scores(evidence, {})
    assert result.is_draft is False
    assert result.computed_verdict == expected.verdict
    assert result.computed_scores["total_score"] == expected.total_score
    assert result.computed_summary == expected.verdict_rationale


def test_migration_is_idempotent(owner_session: Session) -> None:
    migration = (
        Path(__file__).parents[3]
        / "database/sql/028_drop_placeholder_scoring_trigger.sql"
    )
    for _ in range(2):
        owner_session.execute(text(migration.read_text()))
    assert (
        owner_session.scalar(
            text(
                "SELECT count(*) FROM pg_trigger WHERE tgname = 'trigger_calculate_schema_scores'"
            )
        )
        == 0
    )
    assert (
        owner_session.scalar(
            text(
                "SELECT count(*) FROM pg_proc WHERE proname = 'calculate_schema_scores'"
            )
        )
        == 0
    )


def test_recompute_backfill_under_rls_keeps_updated_at(owner_session: Session) -> None:
    from app.services.recompute_scores import recompute_all_scores

    curation = owner_session.scalars(select(CurationNew)).first()
    if curation is None:
        scope = owner_session.scalars(select(Scope)).first()
        user = owner_session.scalars(select(UserNew)).first()
        pair = owner_session.scalars(select(WorkflowPair)).first()
        assert scope is not None and user is not None and pair is not None
        gene = Gene(
            id=uuid4(),
            hgnc_id="HGNC:999029",
            approved_symbol="BACKFILL",
            record_hash="0" * 64,
        )
        owner_session.add(gene)
        owner_session.flush()
        curation = CurationNew(
            id=uuid4(),
            gene_id=gene.id,
            scope_id=scope.id,
            workflow_pair_id=pair.id,
            workflow_stage="curation",
            is_draft=False,
            evidence_data={},
            created_by=user.id,
        )
        owner_session.add(curation)
        owner_session.flush()
    updated_at = curation.updated_at
    owner_session.execute(
        text("UPDATE curations SET computed_verdict = NULL WHERE id = :i"),
        {"i": curation.id},
    )
    assert recompute_all_scores(owner_session) >= 1
    owner_session.refresh(curation)
    assert curation.computed_verdict == "no_known"
    assert curation.updated_at == updated_at
