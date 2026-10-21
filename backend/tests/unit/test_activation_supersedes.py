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


def test_second_active_curation_for_same_gene_scope_is_rejected(
    db_session: Session,
    test_scope: Scope,
    test_gene: Gene,
    test_workflow_pair: WorkflowPair,
    test_user_curator: UserNew,
) -> None:
    from sqlalchemy.exc import IntegrityError

    first = _curation(
        db_session, test_scope, test_gene, test_workflow_pair, test_user_curator
    )
    second = _curation(
        db_session, test_scope, test_gene, test_workflow_pair, test_user_curator
    )
    first.status = CurationStatus.ACTIVE
    db_session.commit()
    second.status = CurationStatus.ACTIVE
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_reapproval_restamps_approver_and_time(
    db_session: Session,
    test_scope: Scope,
    test_gene: Gene,
    test_workflow_pair: WorkflowPair,
    test_user_curator: UserNew,
    test_user_admin: UserNew,
) -> None:
    c = _curation(
        db_session, test_scope, test_gene, test_workflow_pair, test_user_curator
    )
    workflow_engine._transition_to_active(
        db_session, c, test_user_curator.id, None, None
    )
    db_session.commit()
    first_at = c.approved_at
    c.status = CurationStatus.APPROVED  # reopened, edited, approved again
    db_session.commit()
    workflow_engine._transition_to_active(db_session, c, test_user_admin.id, None, None)
    db_session.commit()
    assert c.approved_by == test_user_admin.id
    assert c.approved_at > first_at
