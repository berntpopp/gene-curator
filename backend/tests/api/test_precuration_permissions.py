"""Only scope curators/admins and platform admins may create or edit work."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.endpoints import precurations
from app.crud.workflow_engine import WorkflowEngine
from app.models import PrecurationNew, Scope, WorkflowStage
from app.schemas.precuration import (
    PrecurationCreate,
    PrecurationSubmit,
    PrecurationUpdate,
)
from tests.api.scopes.factories import auth_headers, make_member, make_user

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def no_rls_on_sqlite():
    with patch("app.api.v1.endpoints.precurations.set_rls_context"):
        yield


@pytest.mark.parametrize(
    "scope_role",
    ["curator", "admin", "reviewer", "viewer", "outsider", "platform_admin"],
)
@pytest.mark.parametrize("action", ["create", "update", "draft", "submit"])
def test_precuration_write_roles_direct(
    db_session: Session, test_precuration: PrecurationNew, scope_role: str, action: str
):
    user = make_user(
        db_session, role="admin" if scope_role == "platform_admin" else "user"
    )
    scope = db_session.get(Scope, test_precuration.scope_id)
    if scope_role not in ["outsider", "platform_admin"]:
        make_member(db_session, scope, user, scope_role)
    # A former curator remains the creator after their role changes.
    test_precuration.created_by = user.id
    db_session.commit()
    kwargs = {"db": db_session, "current_user": user}
    if action == "create":
        endpoint = precurations.create_precuration
        kwargs["precuration_in"] = PrecurationCreate(
            gene_id=test_precuration.gene_id,
            scope_id=scope.id,
            precuration_schema_id=test_precuration.precuration_schema_id,
        )
    else:
        kwargs["precuration_id"] = test_precuration.id
        if action == "update":
            endpoint = precurations.update_precuration
            kwargs["precuration_in"] = PrecurationUpdate(
                evidence_data={"notes": "changed"}
            )
        elif action == "draft":
            endpoint = precurations.save_draft
            kwargs["draft_data"] = {"evidence_data": {"notes": "changed"}}
        else:
            endpoint = precurations.submit_precuration
            kwargs["submit_in"] = PrecurationSubmit()
    if scope_role in ["curator", "admin", "platform_admin"]:
        result = endpoint(**kwargs)
        assert result.scope_id == scope.id
    else:
        with pytest.raises(HTTPException) as error:
            endpoint(**kwargs)
        assert error.value.status_code == 403


@pytest.mark.parametrize("scope_role", ["reviewer", "viewer"])
def test_read_only_scope_roles_cannot_create_via_api(
    client: TestClient,
    db_session: Session,
    test_precuration: PrecurationNew,
    scope_role: str,
):
    user = make_user(db_session)
    scope = db_session.get(Scope, test_precuration.scope_id)
    make_member(db_session, scope, user, scope_role)
    response = client.post(
        "/api/v1/precurations/",
        headers=auth_headers(user),
        json={
            "gene_id": str(test_precuration.gene_id),
            "scope_id": str(scope.id),
            "precuration_schema_id": str(test_precuration.precuration_schema_id),
        },
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (WorkflowStage.ENTRY, WorkflowStage.PRECURATION),
        (WorkflowStage.PRECURATION, WorkflowStage.CURATION),
        (WorkflowStage.PRECURATION, WorkflowStage.REVIEW),
    ],
)
def test_reviewer_cannot_start_work_via_workflow_direct(
    db_session: Session,
    test_precuration: PrecurationNew,
    source: WorkflowStage,
    target: WorkflowStage,
):
    reviewer = make_user(db_session)
    scope = db_session.get(Scope, test_precuration.scope_id)
    make_member(db_session, scope, reviewer, "reviewer")
    test_precuration.workflow_stage = source
    db_session.commit()
    result = WorkflowEngine().validate_transition(
        db_session, source, target, reviewer.id, test_precuration.id, "precuration"
    )
    assert result.is_valid is False
    assert any("not authorized" in error for error in result.errors)


def test_viewer_cannot_delete_precuration(
    client: TestClient, db_session: Session, test_precuration: PrecurationNew
):
    user = make_user(db_session)
    scope = db_session.get(Scope, test_precuration.scope_id)
    make_member(db_session, scope, user, "viewer")
    response = client.delete(
        f"/api/v1/precurations/{test_precuration.id}", headers=auth_headers(user)
    )
    assert response.status_code == 403
