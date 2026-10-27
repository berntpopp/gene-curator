"""Approval creates the curation with the scope's workflow pair, never an arbitrary first match (#448)."""

import pytest
from sqlalchemy.orm import Session

from app.crud.precuration import precuration_crud
from app.models import (
    CurationNew,
    CurationStatus,
    PrecurationNew,
    WorkflowPair,
    WorkflowStage,
)
from tests.api.scopes.factories import (
    make_gene,
    make_member,
    make_precuration,
    make_scope,
    make_user,
)

pytestmark = pytest.mark.unit


def _setup(db: Session, pairs: int, default: int | None, *, mismatch: bool = False):
    author, reviewer = make_user(db), make_user(db)
    scope = make_scope(db)
    make_member(db, scope, author, "curator")
    make_member(db, scope, reviewer, "reviewer")
    pre = make_precuration(
        db, scope=scope, gene=make_gene(db), creator=author, stage=WorkflowStage.REVIEW
    )
    pre.status = CurationStatus.SUBMITTED
    made = [
        WorkflowPair(
            name=f"wf-{i}-{pre.id}",
            version="1.0",
            precuration_schema_id=pre.precuration_schema_id,
            is_active=True,
        )
        for i in range(pairs)
    ]
    other = WorkflowPair(name=f"other-{pre.id}", version="1.0", is_active=True)
    db.add_all([*made, other])
    db.flush()
    if mismatch:
        scope.default_workflow_pair_id = other.id
    elif default is not None:
        scope.default_workflow_pair_id = made[default].id
    db.commit()
    return pre, reviewer, made


def _approve(db: Session, pre: PrecurationNew, reviewer):
    return precuration_crud.approve_and_create_curation(
        db, db_obj=pre, approver_id=reviewer.id
    )


@pytest.mark.parametrize("default", [0, 1])
def test_uses_scope_default_when_pairs_share_the_precuration_schema(
    db_session: Session, default: int
):
    pre, reviewer, pairs = _setup(db_session, 2, default)
    result = _approve(db_session, pre, reviewer)
    curation = db_session.get(CurationNew, result.curation_id)
    assert curation.workflow_pair_id == pairs[default].id


def test_single_matching_pair_is_used_when_default_does_not_apply(
    db_session: Session,
):
    pre, reviewer, pairs = _setup(db_session, 1, None, mismatch=True)
    result = _approve(db_session, pre, reviewer)
    curation = db_session.get(CurationNew, result.curation_id)
    assert curation.workflow_pair_id == pairs[0].id


@pytest.mark.parametrize("mismatch", [False, True])
def test_ambiguous_pairs_without_applicable_default_refuse_and_change_nothing(
    db_session: Session, mismatch: bool
):
    pre, reviewer, _ = _setup(db_session, 2, None, mismatch=mismatch)
    with pytest.raises(ValueError, match="default workflow pair"):
        _approve(db_session, pre, reviewer)
    db_session.rollback()
    db_session.refresh(pre)
    assert pre.status == CurationStatus.SUBMITTED
    assert pre.workflow_stage == WorkflowStage.REVIEW
    assert db_session.query(CurationNew).count() == 0
