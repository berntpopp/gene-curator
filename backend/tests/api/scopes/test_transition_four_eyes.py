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
    make_member,
    make_precuration,
    make_user,
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


def _refused_decider(who: str, db: Session, scope: Scope, author: UserNew) -> UserNew:
    if who == "admin-author":
        author.role = "admin"
        db.commit()
        return author
    user = make_user(db, role="admin" if who == "admin-outsider" else "user")
    if who == "viewer":
        make_member(db, scope, user, "viewer")
    elif who == "invited-reviewer":
        make_member(db, scope, user, "reviewer", accepted=False)
    return user


@pytest.mark.parametrize(
    "who", ["admin-outsider", "viewer", "invited-reviewer", "admin-author"]
)
@pytest.mark.parametrize("target", ["active", "curation"])
def test_review_decision_refused_without_review_capability(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    scope_with_admin: Scope,
    who: str,
    target: str,
) -> None:
    curation = make_curation(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator
    )
    user = _refused_decider(who, db_session, scope_with_admin, curator)
    sent = _transition(client, user, "curation", curation.id, target_stage=target)
    assert sent.status_code == 400, sent.text
    db_session.refresh(curation)
    assert (curation.workflow_stage, curation.status) == (
        S.REVIEW,
        CurationStatus.IN_REVIEW,
    )


@pytest.mark.parametrize(
    "who", ["admin-outsider", "viewer", "invited-reviewer", "admin-author"]
)
def test_precuration_approval_refused_without_review_capability(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    scope_with_admin: Scope,
    who: str,
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
    user = _refused_decider(who, db_session, scope_with_admin, curator)
    sent = _transition(client, user, "precuration", pre.id, target_stage="curation")
    assert sent.status_code == 400, sent.text
    db_session.refresh(pre)
    assert pre.status == CurationStatus.SUBMITTED


@pytest.mark.parametrize("status", [CurationStatus.DRAFT, CurationStatus.REJECTED])
def test_reviewer_cannot_approve_an_unsubmitted_precuration(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
    status: CurationStatus,
) -> None:
    pre = make_precuration(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator
    )
    pre.status = status
    db_session.commit()
    sent = _transition(client, reviewer, "precuration", pre.id, target_stage="curation")
    assert sent.status_code == 400
    assert "submitted" in sent.json()["detail"]
    db_session.refresh(pre)
    assert (pre.workflow_stage, pre.status) == (S.PRECURATION, status)


def test_precuration_send_back_points_to_reject(
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
    sent = _transition(
        client, reviewer, "precuration", pre.id, target_stage="precuration"
    )
    assert sent.status_code == 400
    assert "/reject" in sent.json()["detail"]
    db_session.refresh(pre)
    assert (pre.workflow_stage, pre.status) == (S.REVIEW, CurationStatus.SUBMITTED)
