"""The generic transition endpoint applies the approve rules to review decisions: reviewer or
scope admin only, and nobody decides on their own work (D1, admins included)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CurationStatus, Scope, UserNew, WorkflowStage as S
from tests.api.scopes.factories import (
    auth_headers,
    make_curation,
    make_gene,
    make_precuration,
)

pytestmark = pytest.mark.unit

BASE = "/api/v1/workflow"


def _transition(
    client: TestClient, user: UserNew, item: str, item_id: object, **body: object
):
    return client.post(
        f"{BASE}/{item}/{item_id}/transition", json=body, headers=auth_headers(user)
    )


def test_scope_admin_cannot_send_back_own_curation(
    client: TestClient, db_session: Session, owner: UserNew, scope_with_admin: Scope
) -> None:
    own = make_curation(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=owner
    )
    sent = _transition(client, owner, "curation", own.id, target_stage="curation")
    assert sent.status_code == 400
    assert "4-eyes" in sent.json()["detail"]


@pytest.mark.parametrize("stage", [S.REVIEW, S.PRECURATION])
@pytest.mark.parametrize("who", ["owner", "curator"])
def test_owner_cannot_approve_own_precuration_by_transition(
    client: TestClient,
    db_session: Session,
    scope_with_admin: Scope,
    request: pytest.FixtureRequest,
    stage: S,
    who: str,
) -> None:
    author: UserNew = request.getfixturevalue(who)
    pre = make_precuration(
        db_session,
        scope=scope_with_admin,
        gene=make_gene(db_session),
        creator=author,
        stage=stage,
    )
    pre.status = CurationStatus.SUBMITTED
    db_session.commit()

    sent = _transition(client, author, "precuration", pre.id, target_stage="curation")
    assert sent.status_code == 400, sent.text
    db_session.refresh(pre)
    assert (pre.workflow_stage, pre.status) == (stage, CurationStatus.SUBMITTED)


def test_reviewer_approves_precuration_by_transition(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
) -> None:
    pre = make_precuration(
        db_session,
        scope=scope_with_admin,
        gene=make_gene(db_session),
        creator=curator,
        stage=S.REVIEW,
    )
    pre.status = CurationStatus.SUBMITTED
    db_session.commit()

    sent = _transition(client, reviewer, "precuration", pre.id, target_stage="curation")
    assert sent.status_code == 200, sent.text
    db_session.refresh(pre)
    assert (pre.workflow_stage, pre.status) == (S.CURATION, CurationStatus.APPROVED)
