"""Transition responses agree with persisted stages and notifications."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.workflow_engine import workflow_engine
from app.models import ActiveCuration, CurationStatus, Scope, UserNew, WorkflowStage
from app.models.models import NotificationNew
from tests.api.scopes.factories import auth_headers, make_curation, make_gene

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("notification_fails", [False, True])
def test_approve_is_atomic(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
    notification_fails: bool,
):
    curation = make_curation(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator
    )
    emit = workflow_engine._emit_transition_notification

    def emit_then_fail(*args):
        emit(*args)
        if notification_fails:
            raise ValueError("Notification storage failed")

    with patch.object(
        workflow_engine, "_emit_transition_notification", side_effect=emit_then_fail
    ):
        response = client.post(
            f"/api/v1/workflow/curation/{curation.id}/transition",
            json={"target_stage": "active"},
            headers=auth_headers(reviewer),
        )
    db_session.refresh(curation)
    notifications = db_session.scalars(select(NotificationNew)).all()
    if notification_fails:
        assert response.status_code == 400
        assert response.json()["detail"] == "Notification storage failed"
        assert curation.workflow_stage == WorkflowStage.REVIEW
        assert curation.status == CurationStatus.IN_REVIEW
        assert notifications == []
        assert db_session.scalars(select(ActiveCuration)).all() == []
    else:
        assert response.status_code == 200, response.text
        assert curation.workflow_stage == WorkflowStage.ACTIVE
        assert len(notifications) == 1
        assert notifications[0].user_id == curator.id
        assert (
            notifications[0].link
            == f"/scopes/{scope_with_admin.id}/curations/{curation.id}"
        )
