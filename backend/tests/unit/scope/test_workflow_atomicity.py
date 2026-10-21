"""Workflow changes and their notifications must persist together."""

from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.workflow_engine import WorkflowEngine
from app.models import ActiveCuration, CurationStatus, UserNew, WorkflowStage as S
from app.models.models import NotificationNew, Review, ReviewStatus, Scope
from tests.api.scopes.factories import make_curation, make_gene, make_precuration

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (S.CURATION, S.REVIEW),
        (S.REVIEW, S.CURATION),
        (S.REVIEW, S.ACTIVE),
        (S.CURATION, S.PRECURATION),
        (S.PRECURATION, S.ENTRY),
    ],
)
def test_notification_failure_rolls_back_transition(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
    source: S,
    target: S,
):
    curation = make_curation(
        db_session,
        scope=scope,
        gene=make_gene(db_session),
        creator=creator,
        stage=source,
    )
    old_status = curation.status
    emit = engine._emit_transition_notification

    def fail_after_notification(*args):
        emit(*args)
        raise RuntimeError("Notification storage failed")

    with (
        patch.object(
            engine, "_emit_transition_notification", side_effect=fail_after_notification
        ),
        pytest.raises(RuntimeError, match="Notification storage failed"),
    ):
        engine.execute_transition(
            db_session,
            curation.id,
            "curation",
            target,
            reviewer.id if source == S.REVIEW else creator.id,
        )

    db_session.refresh(curation)
    assert curation.workflow_stage == source
    assert curation.status == old_status
    assert db_session.scalars(select(ActiveCuration)).all() == []
    assert db_session.scalars(select(NotificationNew)).all() == []


def test_approval_persists_notification_with_scoped_link(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
):
    curation = make_curation(
        db_session, scope=scope, gene=make_gene(db_session), creator=creator
    )
    engine.execute_transition(
        db_session, curation.id, "curation", S.ACTIVE, reviewer.id
    )
    db_session.expire_all()
    notification = db_session.scalars(select(NotificationNew)).one()
    assert notification.user_id == creator.id
    assert notification.link == f"/scopes/{scope.id}/curations/{curation.id}"
    assert curation.status == CurationStatus.ACTIVE


def test_precuration_submission_metadata_rolls_back_on_failure(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    scope: Scope,
):
    from app.crud.precuration import precuration_crud
    from app.schemas.precuration import PrecurationSubmit

    precuration = make_precuration(
        db_session, scope=scope, gene=make_gene(db_session), creator=creator
    )
    with (
        patch.object(
            engine,
            "_emit_transition_notification",
            side_effect=RuntimeError("Notifications failed"),
        ),
        patch("app.crud.precuration.workflow_engine", engine),
        pytest.raises(RuntimeError, match="Notifications failed"),
    ):
        precuration_crud.submit_for_review(
            db_session,
            db_obj=precuration,
            submit_data=PrecurationSubmit(lock_version=precuration.lock_version),
            user_id=creator.id,
        )
    db_session.refresh(precuration)
    assert precuration.workflow_stage == S.PRECURATION
    assert precuration.status == CurationStatus.DRAFT
    assert precuration.is_draft is True


def test_review_decision_rolls_back_when_auto_activation_fails(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
):
    curation = make_curation(
        db_session, scope=scope, gene=make_gene(db_session), creator=creator
    )
    assignment = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", reviewer.id, creator.id
    )
    with (
        patch.object(
            engine,
            "_emit_transition_notification",
            side_effect=RuntimeError("Notifications failed"),
        ),
        pytest.raises(RuntimeError, match="Notifications failed"),
    ):
        engine.submit_peer_review(
            db_session, assignment.review_id, reviewer.id, "approve"
        )
    db_session.expire_all()
    review = db_session.get(Review, assignment.review_id)
    assert review.status == ReviewStatus.PENDING
    assert curation.workflow_stage == S.REVIEW


@pytest.mark.parametrize("operation", ["assign", "approve", "reject"])
def test_notification_insert_failure_rolls_back_review_operation(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
    operation: str,
):
    from sqlalchemy import event

    curation = make_curation(
        db_session, scope=scope, gene=make_gene(db_session), creator=creator
    )
    assignment = None
    if operation != "assign":
        assignment = engine.assign_peer_reviewer(
            db_session, curation.id, "curation", reviewer.id, creator.id
        )

    def fail_insert(*args):
        raise RuntimeError("Notification insert failed")

    event.listen(NotificationNew, "before_insert", fail_insert)
    try:
        with pytest.raises(RuntimeError, match="Notification insert failed"):
            if operation == "assign":
                engine.assign_peer_reviewer(
                    db_session, curation.id, "curation", reviewer.id, creator.id
                )
            else:
                engine.submit_peer_review(
                    db_session, assignment.review_id, reviewer.id, operation
                )
    finally:
        event.remove(NotificationNew, "before_insert", fail_insert)
    db_session.expire_all()
    assert curation.workflow_stage == S.REVIEW
    assert curation.status == CurationStatus.IN_REVIEW
    assert db_session.scalars(select(ActiveCuration)).all() == []
    reviews = db_session.scalars(select(Review)).all()
    if operation == "assign":
        assert reviews == []
        assert db_session.scalars(select(NotificationNew)).all() == []
    else:
        assert len(reviews) == 1
        assert reviews[0].status == ReviewStatus.PENDING
        notifications = db_session.scalars(select(NotificationNew)).all()
        assert len(notifications) == 1
        assert notifications[0].user_id == reviewer.id


def test_resubmission_notifies_pending_reviewer_with_scoped_link(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
):
    curation = make_curation(
        db_session, scope=scope, gene=make_gene(db_session), creator=creator
    )
    engine.assign_peer_reviewer(
        db_session, curation.id, "curation", reviewer.id, creator.id
    )
    engine.execute_transition(
        db_session, curation.id, "curation", S.CURATION, reviewer.id
    )
    engine.execute_transition(db_session, curation.id, "curation", S.REVIEW, creator.id)
    db_session.expire_all()
    notes = db_session.scalars(
        select(NotificationNew).where(NotificationNew.user_id == reviewer.id)
    ).all()
    assert len(notes) == 2
    assert all(
        note.link == f"/scopes/{scope.id}/curations/{curation.id}" for note in notes
    )


def test_failed_notification_on_the_gating_approval_rolls_back(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
):
    """reviewers_required: 2 (#268): the second approval activates; a failed notification
    undoes the activation and that approval, the first one stays."""
    from tests.api.scopes.factories import make_member, make_user
    from tests.unit.scope.test_workflow_config import _pin

    curation = make_curation(
        db_session, scope=scope, gene=make_gene(db_session), creator=creator
    )
    _pin(db_session, curation, {"review": {"reviewers_required": 2}})
    engine.execute_transition(
        db_session, curation.id, "curation", S.ACTIVE, reviewer.id
    )
    second = make_user(db_session)
    make_member(db_session, scope, second, "reviewer")
    with (
        patch.object(
            engine,
            "_emit_transition_notification",
            side_effect=RuntimeError("Notifications failed"),
        ),
        pytest.raises(RuntimeError, match="Notifications failed"),
    ):
        engine.execute_transition(
            db_session, curation.id, "curation", S.ACTIVE, second.id
        )
    db_session.expire_all()
    assert (curation.workflow_stage, curation.status) == (
        S.REVIEW,
        CurationStatus.IN_REVIEW,
    )
    assert db_session.scalars(select(ActiveCuration)).all() == []
    approvals = db_session.scalars(
        select(Review.reviewer_id).where(Review.status == ReviewStatus.APPROVED)
    ).all()
    assert approvals == [reviewer.id]
