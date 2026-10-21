"""Unit tests for WorkflowEngine: transition DAG, authorization, 4-eyes and reviews."""

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.crud.workflow_engine import WorkflowEngine
from app.models.models import (
    ActiveCuration,
    CurationNew,
    CurationStatus,
    Scope,
    UserNew,
    WorkflowStage,
)
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
# Transition DAG
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.ENTRY, S.PRECURATION),
        (S.PRECURATION, S.CURATION),
        (S.PRECURATION, S.ENTRY),  # backwards
        (S.CURATION, S.REVIEW),
        (S.CURATION, S.PRECURATION),  # backwards
        (S.REVIEW, S.ACTIVE),
        (S.REVIEW, S.CURATION),  # backwards: sent back for rework
        (S.ACTIVE, S.REVIEW),  # re-review of an active curation
    ],
)
def test_allowed_transitions(engine: WorkflowEngine, current: S, target: S) -> None:
    assert target in engine.valid_transitions[current]


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.ENTRY, S.ACTIVE),  # cannot skip stages
        (S.CURATION, S.ACTIVE),  # approval requires review
        (S.ACTIVE, S.CURATION),
        (S.REVIEW, S.ENTRY),
    ],
)
def test_forbidden_transitions(engine: WorkflowEngine, current: S, target: S) -> None:
    assert target not in engine.valid_transitions[current]


def test_validate_transition_reports_invalid_stage_jump(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    gene = make_gene(db_session)
    curation = make_curation(
        db_session, scope=scope, gene=gene, creator=creator, stage=S.CURATION
    )

    result = engine.validate_transition(
        db_session, S.CURATION, S.ACTIVE, creator.id, curation.id, "curation"
    )

    assert result.is_valid is False
    assert "Invalid transition from curation to active" in result.errors


def test_validate_transition_unknown_user(
    db_session: Session, engine: WorkflowEngine, scope: Scope, creator: UserNew
) -> None:
    gene = make_gene(db_session)
    curation = make_curation(db_session, scope=scope, gene=gene, creator=creator)

    result = engine.validate_transition(
        db_session, S.CURATION, S.REVIEW, uuid4(), curation.id, "curation"
    )

    assert result.is_valid is False
    assert result.errors == ["User not found"]


def test_role_requirements_cover_backwards_transitions(engine: WorkflowEngine) -> None:
    permissive = ["curator", "admin", "scope_admin"]
    assert engine._get_role_requirements(S.REVIEW, S.CURATION) == [
        *permissive,
        "reviewer",
    ]
    assert engine._get_role_requirements(S.CURATION, S.PRECURATION) == permissive
    assert engine._get_role_requirements(S.ACTIVE, S.REVIEW) == ["admin", "scope_admin"]
    # Unmapped pairs fall back to admin-only
    assert engine._get_role_requirements(S.ENTRY, S.ACTIVE) == ["admin"]


def test_content_requirements_per_target(engine: WorkflowEngine) -> None:
    assert engine._get_content_requirements(S.CURATION, S.REVIEW)
    assert engine._get_content_requirements(S.REVIEW, S.ACTIVE)
    assert engine._get_content_requirements(S.ENTRY, S.PRECURATION) == []


# -----------------------------------------------------------------------------
# Authorization
# -----------------------------------------------------------------------------


def test_admin_is_always_authorized(
    db_session: Session, engine: WorkflowEngine, scope: Scope
) -> None:
    admin = make_user(db_session, role="admin")

    assert engine._check_role_authorization(db_session, admin, ["curator"], scope.id)
    assert engine._has_review_permissions(db_session, admin, _Item(scope.id))


def test_scope_curator_is_authorized_for_curation_transition(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    assert engine._check_role_authorization(
        db_session, creator, ["curator", "admin"], scope.id
    )


def test_scope_viewer_is_not_authorized(
    db_session: Session, engine: WorkflowEngine, scope: Scope
) -> None:
    viewer = make_user(db_session)
    make_member(db_session, scope, viewer, "viewer")

    assert not engine._check_role_authorization(
        db_session, viewer, ["curator", "admin"], scope.id
    )


def test_non_member_without_global_role_is_not_authorized(
    db_session: Session, engine: WorkflowEngine, scope: Scope
) -> None:
    stranger = make_user(db_session)

    assert not engine._check_role_authorization(
        db_session, stranger, ["curator", "admin"], scope.id
    )
    assert not engine._check_role_authorization(
        db_session, stranger, ["curator", "admin"], None
    )


def test_pending_invitation_grants_no_workflow_authority(
    db_session: Session, engine: WorkflowEngine, scope: Scope
) -> None:
    """Regression: an unaccepted invitation (accepted_at NULL) is not membership."""
    invitee = make_user(db_session)
    make_member(db_session, scope, invitee, "curator", accepted=False)

    assert not engine._check_role_authorization(
        db_session, invitee, ["curator", "admin"], scope.id
    )


def test_pending_invitation_is_not_a_reviewer(
    db_session: Session, engine: WorkflowEngine, scope: Scope
) -> None:
    invitee = make_user(db_session)
    make_member(db_session, scope, invitee, "reviewer", accepted=False)

    assert not engine._has_review_permissions(db_session, invitee, _Item(scope.id))


def test_inactive_membership_grants_nothing(
    db_session: Session, engine: WorkflowEngine, scope: Scope
) -> None:
    former = make_user(db_session)
    make_member(db_session, scope, former, "curator", is_active=False)

    assert not engine._check_role_authorization(
        db_session, former, ["curator"], scope.id
    )


def test_review_permission_requires_eligible_scope_role(
    db_session: Session, engine: WorkflowEngine, scope: Scope, reviewer: UserNew
) -> None:
    viewer = make_user(db_session)
    make_member(db_session, scope, viewer, "viewer")

    assert engine._has_review_permissions(db_session, reviewer, _Item(scope.id))
    assert not engine._has_review_permissions(db_session, viewer, _Item(scope.id))


def test_item_without_scope_skips_membership_check(
    db_session: Session, engine: WorkflowEngine
) -> None:
    anyone = make_user(db_session)

    assert engine._has_review_permissions(db_session, anyone, _Item(None))


def test_four_eyes_blocks_creator_approving_own_work(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    gene = make_gene(db_session)
    curation = make_curation(db_session, scope=scope, gene=gene, creator=creator)

    result = engine.validate_transition(
        db_session, S.REVIEW, S.ACTIVE, creator.id, curation.id, "curation"
    )

    assert result.is_valid is False
    assert any("4-eyes" in e for e in result.errors)


def test_submission_to_review_does_not_require_second_person(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    gene = make_gene(db_session)
    curation = make_curation(
        db_session, scope=scope, gene=gene, creator=creator, stage=S.CURATION
    )

    result = engine.validate_transition(
        db_session, S.CURATION, S.REVIEW, creator.id, curation.id, "curation"
    )

    assert result.is_valid is True
    assert result.requirements  # content requirements are reported


def test_review_requires_evidence_and_warns_without_scores(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    gene = make_gene(db_session)
    empty = make_curation(
        db_session,
        scope=scope,
        gene=gene,
        creator=creator,
        stage=S.CURATION,
        evidence_data={},
    )
    filled = make_curation(
        db_session, scope=scope, gene=gene, creator=creator, stage=S.CURATION
    )

    blocked = engine.validate_transition(
        db_session, S.CURATION, S.REVIEW, creator.id, empty.id, "curation"
    )
    warned = engine.validate_transition(
        db_session, S.CURATION, S.REVIEW, creator.id, filled.id, "curation"
    )

    assert blocked.is_valid is False
    assert "Evidence data is required before review" in blocked.errors
    assert warned.is_valid is True
    assert "Final score not calculated" in warned.warnings
    assert not any("summary" in w for w in warned.warnings)


# -----------------------------------------------------------------------------
# execute_transition
# -----------------------------------------------------------------------------


def test_full_cycle_curation_review_back_and_forth_to_active(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
) -> None:
    gene = make_gene(db_session)
    curation = make_curation(
        db_session,
        scope=scope,
        gene=gene,
        creator=creator,
        stage=S.CURATION,
        status=CurationStatus.DRAFT,
    )

    to_review = engine.execute_transition(
        db_session, curation.id, "curation", S.REVIEW, creator.id, notes="ready"
    )
    assert to_review.from_stage == S.CURATION
    assert to_review.to_stage == S.REVIEW
    assert to_review.success is True
    db_session.refresh(curation)
    assert curation.status == CurationStatus.IN_REVIEW

    sent_back = engine.execute_transition(
        db_session, curation.id, "curation", S.CURATION, reviewer.id
    )
    assert sent_back.to_stage == S.CURATION
    db_session.refresh(curation)
    assert curation.workflow_stage == S.CURATION
    assert curation.status == CurationStatus.DRAFT

    engine.execute_transition(db_session, curation.id, "curation", S.REVIEW, creator.id)
    activated = engine.execute_transition(
        db_session, curation.id, "curation", S.ACTIVE, reviewer.id
    )
    assert activated.to_stage == S.ACTIVE
    db_session.refresh(curation)
    assert curation.status == CurationStatus.ACTIVE
    active = db_session.query(ActiveCuration).filter_by(curation_id=curation.id).one()
    assert active.archived_at is None
    assert active.activated_by == reviewer.id


def test_execute_transition_missing_item_raises(
    db_session: Session, engine: WorkflowEngine, creator: UserNew
) -> None:
    with pytest.raises(ValueError, match="curation not found"):
        engine.execute_transition(db_session, uuid4(), "curation", S.REVIEW, creator.id)


def test_execute_transition_invalid_target_raises(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    scope: Scope,
) -> None:
    gene = make_gene(db_session)
    curation = make_curation(
        db_session, scope=scope, gene=gene, creator=creator, stage=S.CURATION
    )

    with pytest.raises(ValueError, match="Invalid transition"):
        engine.execute_transition(
            db_session, curation.id, "curation", S.ACTIVE, creator.id
        )


def test_execute_transition_unauthorized_user_raises(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    gene = make_gene(db_session)
    curation = make_curation(
        db_session, scope=scope, gene=gene, creator=creator, stage=S.CURATION
    )
    outsider = make_user(db_session)

    with pytest.raises(ValueError, match="not authorized"):
        engine.execute_transition(
            db_session, curation.id, "curation", S.REVIEW, outsider.id
        )


def test_execute_precuration_transition_sets_stage(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    gene = make_gene(db_session)
    precuration = make_precuration(
        db_session, scope=scope, gene=gene, creator=creator, stage=S.PRECURATION
    )

    engine.execute_transition(
        db_session, precuration.id, "precuration", S.ENTRY, creator.id
    )

    db_session.refresh(precuration)
    assert precuration.workflow_stage == S.ENTRY


def test_precuration_stage_lookup_and_fallback(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    gene = make_gene(db_session)
    precuration = make_precuration(db_session, scope=scope, gene=gene, creator=creator)
    curation = make_curation(
        db_session, scope=scope, gene=gene, creator=creator, stage=S.CURATION
    )

    stage, item = engine._get_current_stage_and_item(
        db_session, precuration.id, "precuration"
    )
    assert stage == S.PRECURATION
    assert item.id == precuration.id
    assert engine._get_current_stage_and_item(db_session, uuid4(), "precuration") == (
        None,
        None,
    )
    assert engine._get_current_stage_and_item(db_session, curation.id, "unknown") == (
        None,
        None,
    )


def test_stage_is_derived_from_legacy_status(
    engine: WorkflowEngine, db_session: Session
) -> None:
    item = CurationNew(status=CurationStatus.IN_REVIEW, workflow_stage=None)
    assert engine._get_stage_from_curation_status(item) == S.REVIEW

    item.status = CurationStatus.ACTIVE
    assert engine._get_stage_from_curation_status(item) == S.ACTIVE

    item.status = CurationStatus.SUBMITTED
    assert engine._get_stage_from_curation_status(item) == S.CURATION


# -----------------------------------------------------------------------------
# Workflow state
# -----------------------------------------------------------------------------


def test_workflow_state_lists_transitions_and_progress(
    db_session: Session, engine: WorkflowEngine, creator: UserNew, scope: Scope
) -> None:
    gene = make_gene(db_session)
    curation = make_curation(
        db_session, scope=scope, gene=gene, creator=creator, stage=S.CURATION
    )

    state = engine.get_workflow_state(db_session, curation.id, "curation")

    assert state.current_stage == S.CURATION
    assert S.REVIEW in state.available_transitions
    assert state.progress_metrics["current_stage_index"] == 2
    assert state.progress_metrics["total_stages"] == 5
    assert state.pending_reviews == []


def test_workflow_state_unknown_item_raises(
    db_session: Session, engine: WorkflowEngine
) -> None:
    with pytest.raises(ValueError, match="not found"):
        engine.get_workflow_state(db_session, uuid4(), "curation")


def test_progress_metrics_fall_back_for_unknown_stage(engine: WorkflowEngine) -> None:
    metrics = engine._calculate_progress_metrics(S.ACTIVE, [])

    assert metrics["current_stage_index"] == 4
    assert metrics["progress_percentage"] == 100.0
    assert engine._calculate_progress_metrics(S.REVIEW, [])["stages_remaining"] == 1


class _Item:
    """Minimal stand-in exposing scope_id for permission helpers."""

    def __init__(self, scope_id: object) -> None:
        self.scope_id = scope_id
