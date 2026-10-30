"""Regression tests for precuration submission and scope permissions."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.models import CurationStatus, PrecurationNew, UserNew, WorkflowStage
from app.schemas.precuration import PrecurationReject
from tests.api.scopes.factories import auth_headers, make_member, make_user

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def no_rls_on_sqlite():
    with patch("app.api.v1.endpoints.precurations.set_rls_context"):
        yield


@pytest.mark.parametrize("as_admin", [False, True])
def test_creator_can_submit_precuration(
    client: TestClient,
    db_session: Session,
    test_precuration: PrecurationNew,
    test_user_curator: UserNew,
    as_admin: bool,
):
    if as_admin:
        test_user_curator.role = "admin"
        db_session.commit()
    response = client.post(
        f"/api/v1/precurations/{test_precuration.id}/submit",
        json={"lock_version": test_precuration.lock_version},
        headers=auth_headers(test_user_curator),
    )
    assert response.status_code == 200, response.text
    assert response.json()["workflow_stage"] == "review"
    db_session.refresh(test_precuration)
    assert test_precuration.status == CurationStatus.SUBMITTED
    assert test_precuration.is_draft is False


@pytest.mark.parametrize("action", ["approve", "reject", "complete"])
def test_viewer_cannot_review_or_complete_precuration(
    client: TestClient,
    db_session: Session,
    test_precuration: PrecurationNew,
    test_user_viewer: UserNew,
    action: str,
):
    test_precuration.status = (
        CurationStatus.SUBMITTED if action != "complete" else CurationStatus.DRAFT
    )
    db_session.commit()
    response = client.post(
        f"/api/v1/precurations/{test_precuration.id}/{action}",
        json={"reason": "Needs changes"} if action == "reject" else None,
        headers=auth_headers(test_user_viewer),
    )
    assert response.status_code == 403, response.text


def test_reviewer_returns_precuration_via_reject_not_transition(
    client: TestClient,
    db_session: Session,
    test_precuration: PrecurationNew,
    test_user_curator: UserNew,
):
    reviewer = make_user(db_session, name="Bob Jones")
    from app.models import Scope

    scope = db_session.get(Scope, test_precuration.scope_id)
    make_member(db_session, scope, reviewer, "reviewer")
    test_precuration.workflow_stage = WorkflowStage.REVIEW
    test_precuration.status = CurationStatus.SUBMITTED
    db_session.commit()
    response = client.post(
        f"/api/v1/workflow/precuration/{test_precuration.id}/transition",
        json={"target_stage": "precuration"},
        headers=auth_headers(reviewer),
    )
    assert response.status_code == 400, response.text
    response = client.post(
        f"/api/v1/precurations/{test_precuration.id}/reject",
        json={"reason": "Narrow the disease"},
        headers=auth_headers(reviewer),
    )
    assert response.status_code == 200, response.text
    db_session.refresh(test_precuration)
    assert test_precuration.workflow_stage == WorkflowStage.PRECURATION
    assert test_precuration.computed_fields["rejection_reason"] == "Narrow the disease"
    # #399: the curator sees who sent it back, as on the curation feedback panel
    detail = client.get(
        f"/api/v1/precurations/{test_precuration.id}",
        headers=auth_headers(test_user_curator),
    )
    assert detail.json()["rejected_by_name"] == "Bob Jones"


def test_submit_endpoint_direct(
    db_session: Session, test_precuration: PrecurationNew, test_user_curator: UserNew
):
    from app.api.v1.endpoints.precurations import submit_precuration
    from app.schemas.precuration import PrecurationSubmit

    result = submit_precuration(
        precuration_id=test_precuration.id,
        submit_in=PrecurationSubmit(lock_version=test_precuration.lock_version),
        db=db_session,
        current_user=test_user_curator,
    )
    assert result.workflow_stage == "review"
    assert result.status == "submitted"
    assert result.is_draft is False


@pytest.mark.parametrize("action", ["approve", "reject", "complete"])
def test_viewer_endpoint_direct(
    db_session: Session,
    test_precuration: PrecurationNew,
    test_user_viewer: UserNew,
    action: str,
):
    from fastapi import HTTPException

    from app.api.v1.endpoints import precurations

    test_precuration.status = (
        CurationStatus.SUBMITTED if action != "complete" else CurationStatus.DRAFT
    )
    db_session.commit()
    endpoint = getattr(precurations, f"{action}_precuration")
    kwargs = (
        {"rejection_data": PrecurationReject(reason="Needs changes")}
        if action == "reject"
        else {"request": Request({"type": "http", "headers": []})}
        if action == "approve"
        else {}
    )
    with pytest.raises(HTTPException) as error:
        endpoint(
            precuration_id=test_precuration.id,
            db=db_session,
            current_user=test_user_viewer,
            **kwargs,
        )
    assert error.value.status_code == 403


@pytest.mark.parametrize(
    ("action", "role", "expected"),
    [
        ("approve", "reviewer", CurationStatus.APPROVED),
        ("reject", "reviewer", CurationStatus.REJECTED),
    ],
)
def test_authorized_precuration_decision_direct(
    db_session: Session,
    test_precuration: PrecurationNew,
    action: str,
    role: str,
    expected: CurationStatus,
):
    from app.api.v1.endpoints import precurations
    from app.models import Scope

    user = make_user(db_session)
    make_member(
        db_session, db_session.get(Scope, test_precuration.scope_id), user, role
    )
    test_precuration.status = (
        CurationStatus.DRAFT if action == "complete" else CurationStatus.SUBMITTED
    )
    db_session.commit()
    kwargs = (
        {"rejection_data": PrecurationReject(reason="Needs changes")}
        if action == "reject"
        else {"request": Request({"type": "http", "headers": []})}
        if action == "approve"
        else {}
    )
    getattr(precurations, f"{action}_precuration")(
        precuration_id=test_precuration.id, db=db_session, current_user=user, **kwargs
    )
    db_session.refresh(test_precuration)
    assert test_precuration.status == expected


@pytest.mark.parametrize("as_admin", [False, True])
def test_complete_submits_for_review_never_approves(
    client: TestClient,
    db_session: Session,
    test_precuration: PrecurationNew,
    test_user_curator: UserNew,
    as_admin: bool,
):
    """D1: nobody approves their own work, admins included; "complete" only submits."""
    if as_admin:
        test_user_curator.role = "admin"
        db_session.commit()
    response = client.post(
        f"/api/v1/precurations/{test_precuration.id}/complete",
        headers=auth_headers(test_user_curator),
    )
    assert response.status_code == 200, response.text
    db_session.refresh(test_precuration)
    assert test_precuration.status == CurationStatus.SUBMITTED
    assert test_precuration.workflow_stage == WorkflowStage.REVIEW


def test_complete_by_another_curator_is_refused(
    client: TestClient, db_session: Session, test_precuration: PrecurationNew
):
    from app.models import Scope

    other = make_user(db_session)
    make_member(
        db_session, db_session.get(Scope, test_precuration.scope_id), other, "curator"
    )
    response = client.post(
        f"/api/v1/precurations/{test_precuration.id}/complete",
        headers=auth_headers(other),
    )
    assert response.status_code == 403
    db_session.refresh(test_precuration)
    assert test_precuration.status == CurationStatus.DRAFT


def test_complete_unknown_precuration_is_404(
    client: TestClient, test_user_curator: UserNew
):
    from uuid import uuid4

    response = client.post(
        f"/api/v1/precurations/{uuid4()}/complete",
        headers=auth_headers(test_user_curator),
    )
    assert response.status_code == 404


@pytest.mark.parametrize(("length", "expected"), [(2000, 200), (2001, 422)])
def test_reject_reason_is_bounded_like_review_text(
    client: TestClient,
    test_precuration: PrecurationNew,
    test_user_admin: UserNew,
    length: int,
    expected: int,
):
    response = client.post(
        f"/api/v1/precurations/{test_precuration.id}/reject",
        json={"reason": "x" * length},
        headers=auth_headers(test_user_admin),
    )
    assert response.status_code == expected, response.text


def test_self_approval_by_curator_names_the_4_eyes_rule(
    client: TestClient,
    db_session: Session,
    test_precuration: PrecurationNew,
    test_user_curator: UserNew,
):
    """#393: the creator learns why (4-eyes), not a generic scope denial."""
    assert test_precuration.created_by == test_user_curator.id
    test_precuration.status = CurationStatus.SUBMITTED
    db_session.commit()
    response = client.post(
        f"/api/v1/precurations/{test_precuration.id}/approve",
        headers=auth_headers(test_user_curator),
    )
    assert response.status_code == 403
    assert "4-eyes" in response.json()["detail"]
    db_session.refresh(test_precuration)
    assert test_precuration.status == CurationStatus.SUBMITTED
