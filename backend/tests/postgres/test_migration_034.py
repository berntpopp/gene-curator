"""Migration 034 + activation keep exactly one active curation per gene+scope."""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.crud.workflow_engine import workflow_engine
from app.models.models import (
    CurationNew,
    CurationStatus,
    Gene,
    Scope,
    UserNew,
    WorkflowPair,
)

pytestmark = pytest.mark.postgres

MIGRATION = Path(__file__).parents[3] / "database/sql/034_single_active_curation.sql"


def test_activation_and_repair(owner_session: Session) -> None:
    scope = owner_session.scalars(select(Scope)).first()
    user = owner_session.scalars(select(UserNew)).first()
    pair = owner_session.scalars(select(WorkflowPair)).first()
    assert scope and user and pair
    gene = Gene(
        id=uuid4(),
        hgnc_id="HGNC:999034",
        approved_symbol="ACT034",
        record_hash="0" * 64,
    )
    owner_session.add(gene)
    owner_session.flush()

    def new() -> CurationNew:
        c = CurationNew(
            id=uuid4(),
            gene_id=gene.id,
            scope_id=scope.id,
            workflow_pair_id=pair.id,
            workflow_stage="review",
            status=CurationStatus.APPROVED,
            evidence_data={"n": uuid4().hex},
            created_by=user.id,
        )
        owner_session.add(c)
        owner_session.flush()
        return c

    first, second = new(), new()
    workflow_engine._transition_to_active(owner_session, first, user.id, None, None)
    workflow_engine._transition_to_active(owner_session, second, user.id, None, None)
    owner_session.refresh(first)
    assert first.status == CurationStatus.ARCHIVED
    assert second.status == CurationStatus.ACTIVE and second.approved_at is not None

    # Legacy damage: an older curation left at 'active' next to the live one.
    owner_session.execute(text("DROP INDEX IF EXISTS uq_curations_one_active"))
    first.status = CurationStatus.ACTIVE
    owner_session.flush()
    for _ in range(2):
        owner_session.execute(text(MIGRATION.read_text()))
    owner_session.refresh(first)
    owner_session.refresh(second)
    assert first.status == CurationStatus.ARCHIVED
    assert second.status == CurationStatus.ACTIVE
    assert owner_session.scalar(
        text(
            "SELECT count(*) FROM pg_indexes WHERE indexname='uq_curations_one_active'"
        )
    )
