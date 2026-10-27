"""MCP study F5: the workflow state knows the caller. Moves the caller may make are
available; the rest are blocked with the reason, and a pending review names its reviewer."""

import pytest
from sqlalchemy.orm import Session

from app.crud.workflow_engine import WorkflowEngine
from app.models.models import Scope, UserNew, WorkflowStage
from tests.api.scopes.factories import make_curation, make_gene

pytestmark = pytest.mark.unit

S = WorkflowStage


def test_author_sees_approval_blocked_and_the_pending_reviewer(
    db_session: Session,
    engine: WorkflowEngine,
    creator: UserNew,
    reviewer: UserNew,
    scope: Scope,
) -> None:
    curation = make_curation(
        db_session, scope=scope, gene=make_gene(db_session), creator=creator
    )
    engine.assign_peer_reviewer(
        db_session, curation.id, "curation", reviewer.id, creator.id
    )

    author = engine.get_workflow_state(db_session, curation.id, "curation", creator.id)
    assert S.ACTIVE not in author.available_transitions
    blocked = {b.stage: b.reason for b in author.blocked}
    assert "Cannot review your own work" in blocked[S.ACTIVE]
    assert "review pending with Reviewer" in blocked[S.ACTIVE]
    assert [r["reviewer_name"] for r in author.pending_reviews] == ["Reviewer"]

    peer = engine.get_workflow_state(db_session, curation.id, "curation", reviewer.id)
    assert S.ACTIVE in peer.available_transitions
    assert S.ACTIVE not in {b.stage for b in peer.blocked}
