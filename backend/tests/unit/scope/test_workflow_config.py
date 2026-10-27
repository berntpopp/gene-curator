"""Transitions and the reviewer gate come from the item's pinned methodology version (#268)."""

from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.precuration_required import MissingRequiredFieldsError
from app.crud.workflow_engine import WorkflowEngine
from app.models import ActiveCuration, CurationStatus, UserNew, WorkflowStage as S
from app.models.methodology import MethodologyVersion
from app.models.models import CurationNew, CurationSchema, Review, ReviewStatus, Scope
from tests.api.scopes.factories import (
    make_curation,
    make_gene,
    make_member,
    make_precuration,
    make_user,
)

pytestmark = pytest.mark.unit

# 016_seed_precuration_schema.sql: 'approved' is no stage, so the code default applies
SEEDED_PRECURATION_STATES = {
    "entry": {"allowed_transitions": ["precuration"]},
    "precuration": {"allowed_transitions": ["review"]},
    "review": {"allowed_transitions": ["precuration", "approved"]},
    "approved": {"allowed_transitions": ["curation"]},
}


def _pin(db: Session, item: Any, states: Any, rules: Any = None) -> None:
    schema = CurationSchema(
        id=uuid4(),
        name=f"wf-{uuid4().hex[:6]}",
        version="1",
        schema_type="curation",
        field_definitions={},
        workflow_states={},
        ui_configuration={},
        schema_hash=uuid4().hex + uuid4().hex,
    )
    db.add(schema)
    db.flush()
    version = MethodologyVersion(
        schema_id=schema.id,
        version=1,
        snapshot={"workflow_states": states, "validation_rules": rules or {}},
    )
    db.add(version)
    db.flush()
    item.methodology_version_id = version.id
    db.commit()


def _second_reviewer(db: Session, scope: Scope) -> UserNew:
    user = make_user(db, name="Reviewer 2")
    make_member(db, scope, user, "reviewer")
    return user


@pytest.fixture
def two_reviewer_curation(
    db_session: Session, creator: UserNew, scope: Scope
) -> CurationNew:
    curation = make_curation(
        db_session, scope=scope, gene=make_gene(db_session), creator=creator
    )
    _pin(db_session, curation, {"review": {"reviewers_required": 2}})
    return curation


def test_seeded_precuration_snapshot_keeps_the_default_table(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    pre = make_precuration(
        db_session, scope=scope, gene=make_gene(db_session), creator=creator
    )
    _pin(db_session, pre, SEEDED_PRECURATION_STATES)
    assert engine.transitions_for(db_session, pre) == engine.valid_transitions


def test_configured_stage_overrides_only_that_stage(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    curation = make_curation(
        db_session, scope=scope, gene=make_gene(db_session), creator=creator
    )
    _pin(db_session, curation, {"curation": {"allowed_transitions": ["precuration"]}})
    table = engine.transitions_for(db_session, curation)
    assert table[S.CURATION] == [S.PRECURATION]
    assert table[S.REVIEW] == engine.valid_transitions[S.REVIEW]


@pytest.mark.parametrize("states", [None, [], {"review": "x"}, {"x": 1}])
def test_unpinned_or_odd_snapshot_uses_default(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    scope: Scope,
    states: Any,
) -> None:
    curation = make_curation(
        db_session, scope=scope, gene=make_gene(db_session), creator=creator
    )
    if states is not None:
        _pin(db_session, curation, states)
    assert engine.transitions_for(db_session, curation) == engine.valid_transitions


def test_snapshot_forbidding_an_edge_refuses_it_without_state_change(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    curation = make_curation(
        db_session,
        scope=scope,
        gene=make_gene(db_session),
        creator=creator,
        stage=S.CURATION,
        status=CurationStatus.DRAFT,
    )
    _pin(db_session, curation, {"curation": {"allowed_transitions": ["precuration"]}})
    with pytest.raises(ValueError, match="Invalid transition from curation to review"):
        engine.execute_transition(
            db_session, curation.id, "curation", S.REVIEW, creator.id
        )
    db_session.refresh(curation)
    assert (curation.workflow_stage, curation.status) == (
        S.CURATION,
        CurationStatus.DRAFT,
    )
    state = engine.get_workflow_state(db_session, curation.id, "curation", creator.id)
    assert state.available_transitions == [S.PRECURATION]


def test_two_reviewers_required_direct_transitions(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
    two_reviewer_curation: CurationNew,
) -> None:
    curation = two_reviewer_curation
    first = engine.execute_transition(
        db_session, curation.id, "curation", S.ACTIVE, reviewer.id
    )
    assert first.to_stage == S.REVIEW
    db_session.refresh(curation)
    assert (curation.workflow_stage, curation.status) == (
        S.REVIEW,
        CurationStatus.IN_REVIEW,
    )
    assert db_session.scalars(select(ActiveCuration)).all() == []

    # the same reviewer approving again still counts once
    engine.execute_transition(
        db_session, curation.id, "curation", S.ACTIVE, reviewer.id
    )
    db_session.refresh(curation)
    assert curation.workflow_stage == S.REVIEW

    second = _second_reviewer(db_session, scope)
    done = engine.execute_transition(
        db_session, curation.id, "curation", S.ACTIVE, second.id
    )
    assert done.to_stage == S.ACTIVE
    db_session.refresh(curation)
    assert curation.status == CurationStatus.ACTIVE


def test_two_reviewers_required_assigned_reviews(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
    two_reviewer_curation: CurationNew,
) -> None:
    curation = two_reviewer_curation
    first = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", reviewer.id, creator.id
    )
    result = engine.submit_peer_review(
        db_session, first.review_id, reviewer.id, "approve"
    )
    assert result["auto_transitioned"] is False
    db_session.refresh(curation)
    assert curation.workflow_stage == S.REVIEW

    second = _second_reviewer(db_session, scope)
    review = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", second.id, creator.id
    )
    result = engine.submit_peer_review(
        db_session, review.review_id, second.id, "approve"
    )
    assert result["auto_transitioned"] is True
    db_session.refresh(curation)
    assert curation.status == CurationStatus.ACTIVE


def test_author_never_counts_admins_included(
    db_session: Session,
    engine: WorkflowEngine,
    reviewer: UserNew,
    scope: Scope,
) -> None:
    author = make_user(db_session, role="admin", name="Admin author")
    make_member(db_session, scope, author, "admin")
    curation = make_curation(
        db_session, scope=scope, gene=make_gene(db_session), creator=author
    )
    _pin(db_session, curation, {"review": {"reviewers_required": 2}})
    with pytest.raises(ValueError, match="4-eyes"):
        engine.execute_transition(
            db_session, curation.id, "curation", S.ACTIVE, author.id
        )
    # a legacy approval by the author in the open round is not counted either
    db_session.add(
        Review(
            curation_id=curation.id,
            reviewer_id=author.id,
            assigned_by=author.id,
            status=ReviewStatus.APPROVED,
            recommendation="approve",
        )
    )
    db_session.commit()
    engine.execute_transition(
        db_session, curation.id, "curation", S.ACTIVE, reviewer.id
    )
    db_session.refresh(curation)
    assert curation.workflow_stage == S.REVIEW


@pytest.mark.parametrize("value", [0, 6, "2", True, None, 1.5])
def test_invalid_reviewers_required_means_one(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
    value: Any,
) -> None:
    curation = make_curation(
        db_session, scope=scope, gene=make_gene(db_session), creator=creator
    )
    _pin(db_session, curation, {"review": {"reviewers_required": value}})
    engine.execute_transition(
        db_session, curation.id, "curation", S.ACTIVE, reviewer.id
    )
    db_session.refresh(curation)
    assert curation.status == CurationStatus.ACTIVE


def test_reject_returns_a_draft_like_the_dropped_trigger(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
) -> None:
    curation = make_curation(
        db_session, scope=scope, gene=make_gene(db_session), creator=creator
    )
    curation.is_draft = False
    db_session.commit()
    review = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", reviewer.id, creator.id
    )
    engine.submit_peer_review(db_session, review.review_id, reviewer.id, "reject")
    db_session.refresh(curation)
    assert (curation.workflow_stage, curation.status, curation.is_draft) == (
        S.CURATION,
        CurationStatus.REJECTED,
        True,
    )


def test_precuration_submit_reads_pinned_validation_rules(
    db_session: Session, creator: UserNew, scope: Scope
) -> None:
    from app.crud.precuration import precuration_crud
    from app.schemas.precuration import PrecurationSubmit

    pre = make_precuration(
        db_session, scope=scope, gene=make_gene(db_session), creator=creator
    )
    _pin(db_session, pre, {}, rules={"required_fields": ["mondo_id"]})
    with pytest.raises(MissingRequiredFieldsError, match="mondo_id"):
        precuration_crud.submit_for_review(
            db_session,
            db_obj=pre,
            submit_data=PrecurationSubmit(lock_version=pre.lock_version),
            user_id=creator.id,
        )


@pytest.mark.parametrize(
    ("states", "approved"),
    [
        (SEEDED_PRECURATION_STATES, True),
        ({"review": {"allowed_transitions": ["precuration"]}}, False),
    ],
)
def test_precuration_approve_follows_the_pinned_snapshot(
    db_session: Session,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
    states: Any,
    approved: bool,
) -> None:
    from app.crud.precuration import precuration_crud

    pre = make_precuration(
        db_session,
        scope=scope,
        gene=make_gene(db_session),
        creator=creator,
        stage=S.REVIEW,
    )
    pre.status = CurationStatus.SUBMITTED
    _pin(db_session, pre, states)
    if approved:
        precuration_crud.approve_and_create_curation(
            db_session, db_obj=pre, approver_id=reviewer.id, create_curation=False
        )
    else:
        with pytest.raises(ValueError, match="from review to curation"):
            precuration_crud.approve_and_create_curation(
                db_session, db_obj=pre, approver_id=reviewer.id
            )
    db_session.refresh(pre)
    assert pre.status == (
        CurationStatus.APPROVED if approved else CurationStatus.SUBMITTED
    )


def test_two_rounds_count_only_approvals_of_the_current_round(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
    two_reviewer_curation: CurationNew,
) -> None:
    curation = two_reviewer_curation
    bob, carol = reviewer, _second_reviewer(db_session, scope)
    dave = _second_reviewer(db_session, scope)
    engine.execute_transition(db_session, curation.id, "curation", S.ACTIVE, bob.id)
    engine.execute_transition(
        db_session, curation.id, "curation", S.CURATION, carol.id, notes="fix"
    )
    engine.execute_transition(db_session, curation.id, "curation", S.REVIEW, creator.id)
    # bob's approval belongs to the first round
    engine.execute_transition(db_session, curation.id, "curation", S.ACTIVE, carol.id)
    db_session.refresh(curation)
    assert (curation.workflow_stage, curation.status) == (
        S.REVIEW,
        CurationStatus.IN_REVIEW,
    )
    engine.execute_transition(db_session, curation.id, "curation", S.ACTIVE, dave.id)
    db_session.refresh(curation)
    assert curation.status == CurationStatus.ACTIVE
