"""Activating a curation supersedes the previous active one for the gene+scope."""

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.crud.workflow_engine import workflow_engine
from app.models.models import (
    ActiveCuration,
    CurationNew,
    CurationStatus,
    Gene,
    Scope,
    UserNew,
    WorkflowPair,
)

pytestmark = pytest.mark.unit


def _curation(db, scope, gene, pair, user) -> CurationNew:
    c = CurationNew(
        id=uuid4(),
        scope_id=scope.id,
        gene_id=gene.id,
        workflow_pair_id=pair.id,
        workflow_stage="review",
        status=CurationStatus.APPROVED,
        evidence_data={},
        created_by=user.id,
    )
    db.add(c)
    db.commit()
    return c


def test_activation_archives_previous_and_stamps_approval(
    db_session: Session,
    test_scope: Scope,
    test_gene: Gene,
    test_workflow_pair: WorkflowPair,
    test_user_curator: UserNew,
    test_user_admin: UserNew,
) -> None:
    first = _curation(
        db_session, test_scope, test_gene, test_workflow_pair, test_user_curator
    )
    second = _curation(
        db_session, test_scope, test_gene, test_workflow_pair, test_user_curator
    )

    for c in (first, second):
        workflow_engine._transition_to_active(
            db_session, c, test_user_admin.id, None, None
        )
        db_session.commit()
        db_session.refresh(c)
    db_session.refresh(first)

    assert first.status == CurationStatus.ARCHIVED
    assert second.status == CurationStatus.ACTIVE
    assert second.approved_at is not None
    assert second.approved_by == test_user_admin.id
    pointers = (
        db_session.query(ActiveCuration)
        .filter(ActiveCuration.archived_at.is_(None))
        .all()
    )
    assert [p.curation_id for p in pointers] == [second.id]
