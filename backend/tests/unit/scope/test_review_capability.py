"""Only roles holding the REVIEW capability (scope reviewer, scope admin) may review.

Scope curators and platform admins without a membership get no review bypass; D1 holds.
"""

import pytest
from sqlalchemy.orm import Session

from app.api.v1.endpoints.curations import _can_user_review_curation
from app.crud.workflow_engine import WorkflowEngine
from app.models.models import Review, ReviewStatus, Scope, UserNew, WorkflowStage
from tests.api.scopes.factories import make_curation, make_gene, make_member, make_user

pytestmark = pytest.mark.unit


@pytest.fixture
def curation(db_session: Session, scope: Scope, creator: UserNew):
    return make_curation(
        db_session, scope=scope, gene=make_gene(db_session), creator=creator
    )


def _other(
    db: Session, scope: Scope, role: str | None, app_role: str = "user"
) -> UserNew:
    user = make_user(db, role=app_role)
    if role:
        make_member(db, scope, user, role)
    return user


@pytest.mark.parametrize(
    ("role", "app_role", "allowed"),
    [
        ("reviewer", "user", True),
        ("admin", "user", True),  # scope admin
        ("curator", "user", False),
        ("viewer", "user", False),
        (None, "admin", False),  # platform admin without membership
    ],
)
def test_review_capability_matrix(
    db_session: Session,
    engine: WorkflowEngine,
    scope: Scope,
    creator: UserNew,
    curation,
    role,
    app_role,
    allowed,
) -> None:
    user = _other(db_session, scope, role, app_role)
    assert _can_user_review_curation(db_session, user, curation) is allowed
    if allowed:
        engine.assign_peer_reviewer(
            db_session, curation.id, "curation", user.id, creator.id
        )
    else:
        with pytest.raises(ValueError, match="not allowed to review"):
            engine.assign_peer_reviewer(
                db_session, curation.id, "curation", user.id, creator.id
            )
    target = WorkflowStage.ACTIVE
    ok = engine.validate_transition(
        db_session, WorkflowStage.REVIEW, target, user.id, curation.id, "curation"
    ).is_valid
    assert ok is allowed


def test_curator_cannot_submit_a_review(
    db_session: Session, engine: WorkflowEngine, scope: Scope, curation
) -> None:
    other_curator = _other(db_session, scope, "curator")
    review = Review(
        curation_id=curation.id,
        reviewer_id=other_curator.id,
        status=ReviewStatus.PENDING,
    )
    db_session.add(review)
    db_session.commit()
    with pytest.raises(ValueError, match="not allowed to review"):
        engine.submit_peer_review(db_session, review.id, other_curator.id, "approve")


def test_eligible_reviewers_are_reviewers_and_admins_only(
    db_session: Session, engine: WorkflowEngine, scope: Scope
) -> None:
    ids = {
        r: _other(db_session, scope, r).id
        for r in ("reviewer", "admin", "curator", "viewer")
    }
    listed = {
        r["id"]
        for r in engine.get_eligible_peer_reviewers(db_session, scope_id=scope.id)
    }
    assert {ids["reviewer"], ids["admin"]} <= listed
    assert not {ids["curator"], ids["viewer"]} & listed
