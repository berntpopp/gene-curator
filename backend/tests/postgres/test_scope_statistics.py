"""Scope statistics use PostgreSQL-only SQL (EXTRACT), so they are tested here, not on SQLite."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.scope import scope_crud
from app.models.models import CurationNew, Gene, Scope, UserNew, WorkflowPair
from tests.api.scopes.factories import (
    make_member,
    make_user,
)
from tests.postgres.test_scope_crud import (  # noqa: F401 (fixtures)
    admin_user,
    test_scope,
)

pytestmark = pytest.mark.postgres


def test_detailed_statistics_counts_only_accepted_members(
    db: Session,
    admin_user: UserNew,  # noqa: F811
    test_scope: Scope,  # noqa: F811
) -> None:
    make_member(db, test_scope, make_user(db), "viewer")
    make_member(
        db, test_scope, make_user(db), "curator", accepted=False
    )  # pending invite

    stats = scope_crud.get_detailed_statistics(db, scope_id=test_scope.id)

    assert stats["member_count"] == 1
    assert stats["completed_genes"] <= stats["total_genes_assigned"]


def test_performance_metrics_empty_scope(
    db: Session,
    admin_user: UserNew,  # noqa: F811
    test_scope: Scope,  # noqa: F811
) -> None:
    metrics = scope_crud.get_performance_metrics(db, scope_id=test_scope.id)

    assert metrics["approval_rate"] is None


def test_detailed_statistics_count_curations_by_status(owner_session: Session) -> None:
    """#403: the status breakdown keyed the enum's repr, so curations in review counted 0."""
    db = owner_session
    scope = db.scalars(select(Scope)).first()
    user = db.scalars(select(UserNew)).first()
    pair = db.scalars(select(WorkflowPair)).first()
    assert scope and user and pair
    before = scope_crud.get_detailed_statistics(db, scope_id=scope.id)
    for n in (1, 2):
        gene = Gene(
            hgnc_id=f"HGNC:99840{n}",
            approved_symbol=f"STAT40{n}",
            record_hash=str(n) * 64,
        )
        db.add(gene)
        db.flush()
        db.add(
            CurationNew(
                gene_id=gene.id,
                scope_id=scope.id,
                workflow_pair_id=pair.id,
                status="in_review",
                workflow_stage="review",
                created_by=user.id,
            )
        )
    db.flush()

    after = scope_crud.get_detailed_statistics(db, scope_id=scope.id)

    assert after["curations_in_review"] - before["curations_in_review"] == 2
