"""Migration 033 repairs approval-created curations only."""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.models import (
    CurationNew,
    CurationSchema,
    Gene,
    PrecurationNew,
    Scope,
    UserNew,
    WorkflowPair,
)

pytestmark = pytest.mark.postgres

MIGRATION = (
    Path(__file__).parents[3]
    / "database/sql/033_precuration_authorship_and_draft_uniqueness.sql"
)


def test_repairs_approval_created_but_not_completed(owner_session: Session) -> None:
    users = owner_session.scalars(select(UserNew)).all()
    scope = owner_session.scalars(select(Scope)).first()
    pair = owner_session.scalars(select(WorkflowPair)).first()
    schema = owner_session.scalars(select(CurationSchema)).first()
    assert len(users) >= 2 and scope and pair and schema
    author, other = users[0], users[1]

    def build(symbol: str, computed: dict) -> tuple[PrecurationNew, CurationNew]:
        gene = Gene(
            id=uuid4(),
            hgnc_id=f"HGNC:{uuid4().int % 10**8}",
            approved_symbol=symbol,
            record_hash=uuid4().hex * 2,
        )
        owner_session.add(gene)
        owner_session.flush()
        pre = PrecurationNew(
            id=uuid4(),
            gene_id=gene.id,
            scope_id=scope.id,
            precuration_schema_id=schema.id,
            status="approved",
            workflow_stage="curation",
            evidence_data={},
            computed_fields=computed,
            created_by=author.id,
            updated_by=other.id,
        )
        owner_session.add(pre)
        owner_session.flush()
        cur = CurationNew(
            id=uuid4(),
            gene_id=gene.id,
            scope_id=scope.id,
            workflow_pair_id=pair.id,
            precuration_id=pre.id,
            workflow_stage="curation",
            evidence_data={},
            created_by=other.id,
        )
        owner_session.add(cur)
        owner_session.flush()
        return pre, cur

    _, approved = build("AUTH033A", {})
    _, completed = build("AUTH033B", {"completed_by": str(other.id)})
    for _ in range(2):
        owner_session.execute(text(MIGRATION.read_text()))
    owner_session.refresh(approved)
    owner_session.refresh(completed)
    assert approved.created_by == author.id
    assert completed.created_by == other.id
