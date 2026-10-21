"""Unit tests for WorkflowEngine peer review, eligible reviewers and statistics."""

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.crud.workflow_engine import WorkflowEngine
from app.models.models import (
    CurationNew,
    CurationStatus,
    Review,
    ReviewStatus,
    Scope,
    UserNew,
    WorkflowStage,
)
from app.services.scope_permissions import ScopePermissionService
from tests.api.scopes.factories import (
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

    with pytest.raises(ValueError, match="review stage"):
        engine.assign_peer_reviewer(
            db_session, curation.id, "curation", reviewer.id, creator.id
        )


def test_assign_reviewer_rejects_original_creator(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    curation = _review_setup(db_session, creator, scope)

    with pytest.raises(ValueError, match="Cannot assign original creator"):
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
    """Reviews reference curations only; a precuration must be refused, not 500."""
    gene = make_gene(db_session)
    precuration = make_precuration(
        db_session, scope=scope, gene=gene, creator=creator, stage=S.REVIEW
    )

    with pytest.raises(ValueError, match="only supported for curations"):
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
    new = engine.assign_peer_reviewer(
        db_session, curation.id, "curation", a.id, creator.id
    )
    result = engine.submit_peer_review(db_session, new.review_id, a.id, "approve")
    assert result["auto_transitioned"] is True
    db_session.refresh(curation)
    assert curation.workflow_stage == S.ACTIVE
