"""Unit tests for WorkflowEngine peer review, eligible reviewers and statistics."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.crud.review_round import reassign_earlier_reviewers
from app.crud.workflow_engine import WorkflowEngine
from app.models.models import (
    CurationNew,
    CurationStatus,
    NotificationNew,
    Review,
    ReviewStatus,
    Scope,
    ScopeMembership,
    UserNew,
    WorkflowStage,
)
from app.services.scope_permissions import ScopePermissionService
from tests.api.scopes.factories import (
    auth_headers,
    make_curation,
    make_gene,
    make_member,
    make_precuration,
    make_user,
)

pytestmark = pytest.mark.unit

S = WorkflowStage


# -----------------------------------------------------------------------------
# Peer review
# -----------------------------------------------------------------------------


def _review_setup(
    db_session: Session,
    creator: UserNew,
    scope: Scope,
    stage: S = S.REVIEW,
) -> CurationNew:
    gene = make_gene(db_session)
    return make_curation(
        db_session, scope=scope, gene=gene, creator=creator, stage=stage
    )


def test_assign_reviewer_requires_review_stage(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
) -> None:
    curation = _review_setup(db_session, creator, scope, stage=S.CURATION)

    with pytest.raises(ValueError, match="submit it for review"):
        engine.assign_peer_reviewer(
            db_session, curation.id, "curation", reviewer.id, creator.id
        )


def test_assign_reviewer_rejects_original_creator(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    curation = _review_setup(db_session, creator, scope)

    with pytest.raises(ValueError, match="4-eyes principle violation"):
        engine.assign_peer_reviewer(
            db_session, curation.id, "curation", creator.id, creator.id
        )


def test_assign_reviewer_creates_pending_review_and_notifies(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
) -> None:
    curation = _review_setup(db_session, creator, scope)

    request = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", reviewer.id, creator.id
    )

    assert request.reviewer_id == reviewer.id
    assert request.status == ReviewStatus.PENDING
    state = engine.get_workflow_state(db_session, curation.id, "curation")
    assert [r["reviewer_id"] for r in state.pending_reviews] == [reviewer.id]


def test_assign_reviewer_rejects_precurations(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
) -> None:
    """The engine assigns curations only; precurations route via services/review_assignment."""
    gene = make_gene(db_session)
    precuration = make_precuration(
        db_session, scope=scope, gene=gene, creator=creator, stage=S.REVIEW
    )

    with pytest.raises(ValueError, match="Cannot assign a reviewer to"):
        engine.assign_peer_reviewer(
            db_session, precuration.id, "precuration", reviewer.id, creator.id
        )


def test_submit_review_rejects_wrong_reviewer_and_bad_decision(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
) -> None:
    curation = _review_setup(db_session, creator, scope)
    request = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", reviewer.id, creator.id
    )

    with pytest.raises(ValueError, match="Only assigned reviewer"):
        engine.submit_peer_review(db_session, request.review_id, creator.id, "approve")
    with pytest.raises(ValueError, match="Invalid decision"):
        engine.submit_peer_review(db_session, request.review_id, reviewer.id, "maybe")
    with pytest.raises(ValueError, match="Review not found"):
        engine.submit_peer_review(db_session, uuid4(), reviewer.id, "approve")


def test_submit_review_only_once(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
) -> None:
    curation = _review_setup(db_session, creator, scope)
    request = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", reviewer.id, creator.id
    )
    engine.submit_peer_review(db_session, request.review_id, reviewer.id, "reject")

    with pytest.raises(ValueError, match="already been completed"):
        engine.submit_peer_review(db_session, request.review_id, reviewer.id, "approve")


def test_single_approval_auto_activates_curation(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
) -> None:
    curation = _review_setup(db_session, creator, scope)
    request = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", reviewer.id, creator.id
    )

    result = engine.submit_peer_review(
        db_session, request.review_id, reviewer.id, "approve", comments="fine"
    )

    assert result["auto_transitioned"] is True
    db_session.refresh(curation)
    assert curation.workflow_stage == S.ACTIVE
    review = db_session.get(Review, request.review_id)
    assert review.status == ReviewStatus.APPROVED
    assert review.comments == "fine"


def test_rejection_is_recorded_as_rejected_and_blocks_activation(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
) -> None:
    """Regression: a reject decision must not be stored as APPROVED."""
    curation = _review_setup(db_session, creator, scope)
    other = make_user(db_session)
    make_member(db_session, scope, other, "reviewer")
    first = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", reviewer.id, creator.id
    )
    second = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", other.id, creator.id
    )

    rejected = engine.submit_peer_review(
        db_session, first.review_id, reviewer.id, "reject"
    )
    # the round is closed: the second reviewer can no longer approve it
    with pytest.raises(ValueError, match="not in review"):
        engine.submit_peer_review(db_session, second.review_id, other.id, "approve")

    assert rejected["auto_transitioned"] is False
    assert db_session.get(Review, first.review_id).status == ReviewStatus.REJECTED
    db_session.refresh(curation)
    assert curation.workflow_stage == S.CURATION
    assert curation.status == CurationStatus.REJECTED


@pytest.mark.parametrize(
    ("decision", "status"),
    [
        ("request_changes", CurationStatus.DRAFT),
        ("reject", CurationStatus.REJECTED),
    ],
)
def test_non_approve_decision_returns_curation_to_curator(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
    decision: str,
    status: CurationStatus,
) -> None:
    """#354: the curation must not stay IN_REVIEW; the curator can edit and resubmit."""
    curation = _review_setup(db_session, creator, scope)
    request = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", reviewer.id, creator.id
    )
    engine.submit_peer_review(db_session, request.review_id, reviewer.id, decision)

    db_session.refresh(curation)
    assert (curation.workflow_stage, curation.status) == (S.CURATION, status)
    assert ScopePermissionService.can_edit_curation(db_session, creator, curation)

    engine.execute_transition(db_session, curation.id, "curation", S.REVIEW, creator.id)
    db_session.refresh(curation)
    assert (curation.workflow_stage, curation.status) == (
        S.REVIEW,
        CurationStatus.IN_REVIEW,
    )


@pytest.mark.parametrize(
    ("decision", "expected_status"),
    [
        ("request_changes", ReviewStatus.NEEDS_REVISION),
        ("reject", ReviewStatus.REJECTED),
    ],
)
def test_non_approve_decisions_store_their_status(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
    decision: str,
    expected_status: ReviewStatus,
) -> None:
    curation = _review_setup(db_session, creator, scope)
    request = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", reviewer.id, creator.id
    )

    engine.submit_peer_review(db_session, request.review_id, reviewer.id, decision)

    review = db_session.get(Review, request.review_id)
    assert review.status == expected_status
    assert review.recommendation == decision


def test_two_approvals_needed_before_auto_activation(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
) -> None:
    curation = _review_setup(db_session, creator, scope)
    other = make_user(db_session)
    make_member(db_session, scope, other, "reviewer")
    first = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", reviewer.id, creator.id
    )
    second = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", other.id, creator.id
    )

    early = engine.submit_peer_review(
        db_session, first.review_id, reviewer.id, "approve"
    )
    late = engine.submit_peer_review(db_session, second.review_id, other.id, "approve")

    assert early["auto_transitioned"] is False
    assert late["auto_transitioned"] is True


def test_rejection_notifies_creator(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
) -> None:
    from app.models.models import NotificationNew

    curation = _review_setup(db_session, creator, scope)
    request = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", reviewer.id, creator.id
    )
    engine.submit_peer_review(db_session, request.review_id, reviewer.id, "reject")

    notes = db_session.query(NotificationNew).filter_by(user_id=creator.id).all()
    assert any("rejected" in n.message.lower() for n in notes)


# -----------------------------------------------------------------------------
# Eligible reviewers and statistics
# -----------------------------------------------------------------------------


def test_eligible_reviewers_filter_scope_status_and_pending_invites(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
) -> None:
    pending = make_user(db_session, name="Zz Pending")
    make_member(db_session, scope, pending, "reviewer", accepted=False)
    inactive = make_user(db_session, name="Zz Inactive", is_active=False)
    make_member(db_session, scope, inactive, "reviewer")
    viewer = make_user(db_session, name="Zz Viewer")
    make_member(db_session, scope, viewer, "viewer")

    result = engine.get_eligible_peer_reviewers(
        db_session, scope_id=scope.id, exclude_user_id=creator.id
    )

    ids = [r["id"] for r in result]
    assert reviewer.id in ids
    assert creator.id not in ids
    assert pending.id not in ids
    assert inactive.id not in ids
    assert viewer.id not in ids


def test_eligible_reviewers_without_scope_lists_active_users(
    db_session: Session, engine: WorkflowEngine, reviewer: UserNew
) -> None:
    result = engine.get_eligible_peer_reviewers(db_session)

    entry = next(r for r in result if r["id"] == reviewer.id)
    assert entry["pending_review_count"] == 0
    assert "reviewer" in entry["scope_roles"]


def test_workflow_statistics_counts_reviews_and_approval_rate(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
) -> None:
    approved_item = _review_setup(db_session, creator, scope)
    rejected_item = _review_setup(db_session, creator, scope)
    a = engine.assign_peer_reviewer(
        db_session, approved_item.id, "curation", reviewer.id, creator.id
    )
    r = engine.assign_peer_reviewer(
        db_session, rejected_item.id, "curation", reviewer.id, creator.id
    )
    engine.submit_peer_review(db_session, a.review_id, reviewer.id, "approve")
    engine.submit_peer_review(db_session, r.review_id, reviewer.id, "reject")

    stats = engine.get_workflow_statistics(db_session, scope.id, days=30)

    assert stats.total_reviews == 2
    assert stats.completed_reviews == 2
    assert stats.pending_reviews == 0
    assert stats.approval_rate == 0.5
    assert stats.time_period_days == 30


def test_workflow_statistics_empty_scope(
    db_session: Session, engine: WorkflowEngine
) -> None:
    stats = engine.get_workflow_statistics(db_session, uuid4())

    assert stats.total_reviews == 0
    assert stats.approval_rate == 0.0


def _two_reviewer_round(db_session, engine, creator, scope):
    a, b = make_user(db_session), make_user(db_session)
    make_member(db_session, scope, a, "reviewer")
    make_member(db_session, scope, b, "reviewer")
    curation = _review_setup(db_session, creator, scope)
    ra = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", a.id, creator.id
    )
    rb = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", b.id, creator.id
    )
    return curation, a, b, ra, rb


def test_other_reviewer_cannot_submit_after_changes_requested(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    curation, a, b, ra, rb = _two_reviewer_round(db_session, engine, creator, scope)
    engine.submit_peer_review(db_session, ra.review_id, a.id, "request_changes")
    with pytest.raises(ValueError, match="not in review"):
        engine.submit_peer_review(db_session, rb.review_id, b.id, "reject")
    db_session.refresh(curation)
    assert curation.status == CurationStatus.DRAFT  # still the curator's to edit
    # reviewer load and the dashboard count ignore the closed round
    load = {
        r["id"]: r["pending_review_count"]
        for r in engine.get_eligible_peer_reviewers(db_session, scope_id=scope.id)
    }
    assert load[b.id] == 0


def test_resubmit_then_approve_activates(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    curation, a, b, ra, rb = _two_reviewer_round(db_session, engine, creator, scope)
    engine.submit_peer_review(db_session, ra.review_id, a.id, "request_changes")
    engine.execute_transition(db_session, curation.id, "curation", S.REVIEW, creator.id)
    # old round's pending review of B cannot be used in the new round
    with pytest.raises(ValueError, match="previous review round"):
        engine.submit_peer_review(db_session, rb.review_id, b.id, "approve")
    # both earlier reviewers were re-assigned in the new round; both must approve
    new = {
        r.reviewer_id: r.id
        for r in db_session.query(Review).filter(
            Review.curation_id == curation.id, Review.status == ReviewStatus.PENDING
        )
        if r.id != rb.review_id
    }
    first = engine.submit_peer_review(db_session, new[a.id], a.id, "approve")
    assert first["auto_transitioned"] is False
    result = engine.submit_peer_review(db_session, new[b.id], b.id, "approve")
    assert result["auto_transitioned"] is True
    db_session.refresh(curation)
    assert curation.workflow_stage == S.ACTIVE


def test_resubmit_reassigns_earlier_reviewers_and_notifies(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    curation, a, b, ra, _rb = _two_reviewer_round(db_session, engine, creator, scope)
    engine.submit_peer_review(db_session, ra.review_id, a.id, "request_changes")
    engine.execute_transition(db_session, curation.id, "curation", S.REVIEW, creator.id)
    db_session.expire_all()
    state = engine.get_workflow_state(db_session, curation.id, "curation")
    assert {r["reviewer_id"] for r in state.pending_reviews} == {a.id, b.id}
    for u in (a, b):
        notes = db_session.scalars(
            select(NotificationNew).where(
                NotificationNew.user_id == u.id,
                NotificationNew.title == "New review assigned",
            )
        ).all()
        assert len(notes) == 2  # first assignment and the new round
    # the curator never gets a review of their own work, even as an earlier "reviewer"
    assert creator.id not in {r["reviewer_id"] for r in state.pending_reviews}


def test_pending_status_filter_ignores_stale_reviews(
    client, db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    _curation, a, b, ra, _rb = _two_reviewer_round(db_session, engine, creator, scope)
    engine.submit_peer_review(db_session, ra.review_id, a.id, "request_changes")
    r = client.get(
        "/api/v1/workflow/reviews/my-assignments?status=pending",
        headers=auth_headers(b),
    )
    assert r.json() == []  # B's review belongs to the closed round


def test_reassign_without_a_submission_is_a_noop(
    db_session: Session, creator: UserNew, scope: Scope
) -> None:
    curation = _review_setup(db_session, creator, scope)
    assert reassign_earlier_reviewers(db_session, curation, creator.id) == []


def test_demoted_reviewer_is_not_reassigned_and_approval_still_works(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    curation, a, b, ra, _rb = _two_reviewer_round(db_session, engine, creator, scope)
    engine.submit_peer_review(db_session, ra.review_id, a.id, "request_changes")
    db_session.query(ScopeMembership).filter(ScopeMembership.user_id == b.id).update(
        {"role": "curator"}
    )
    db_session.commit()
    engine.execute_transition(db_session, curation.id, "curation", S.REVIEW, creator.id)
    pending = {
        r["reviewer_id"]
        for r in engine.get_workflow_state(
            db_session, curation.id, "curation"
        ).pending_reviews
    }
    assert pending == {a.id}  # B lost the REVIEW capability
    review = (
        db_session.query(Review)
        .filter(Review.reviewer_id == a.id, Review.status == ReviewStatus.PENDING)
        .one()
    )
    assert engine.submit_peer_review(db_session, review.id, a.id, "approve")[
        "auto_transitioned"
    ]


def test_manual_assign_after_auto_reassign_does_not_duplicate(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    curation, a, _b, ra, _rb = _two_reviewer_round(db_session, engine, creator, scope)
    engine.submit_peer_review(db_session, ra.review_id, a.id, "request_changes")
    engine.execute_transition(db_session, curation.id, "curation", S.REVIEW, creator.id)
    with pytest.raises(ValueError, match="already has a pending review"):
        engine.assign_peer_reviewer(
            db_session, curation.id, "curation", a.id, creator.id
        )
    pending = db_session.query(Review).filter(
        Review.curation_id == curation.id,
        Review.reviewer_id == a.id,
        Review.status == ReviewStatus.PENDING,
    )
    assert pending.count() == 1
    notes = db_session.query(NotificationNew).filter(
        NotificationNew.user_id == a.id, NotificationNew.title == "New review assigned"
    )
    assert notes.count() == 2  # first round + the automatic one, no third


def test_denied_review_submission_is_403_not_500(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
) -> None:
    curation = _review_setup(db_session, creator, scope)
    request = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", reviewer.id, creator.id
    )
    with (
        patch.object(db_session, "commit", side_effect=StaleDataError("0 rows")),
        pytest.raises(HTTPException) as raised,
    ):
        engine.submit_peer_review(
            db_session, request.review_id, reviewer.id, "request_changes"
        )
    assert raised.value.status_code == 403
