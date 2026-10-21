"""An UPDATE that RLS turns into zero rows is a 403, never a 500 (StaleDataError)."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.crud.workflow_engine import WorkflowEngine
from app.models.models import CurationStatus, PrecurationNew, Scope, WorkflowStage
from tests.api.scopes.factories import auth_headers, make_member, make_user

pytestmark = pytest.mark.unit


class _PgError(Exception):
    def __init__(self, pgcode: str) -> None:
        self.pgcode = pgcode


@pytest.fixture(autouse=True)
def no_rls_on_sqlite():
    with patch("app.api.v1.endpoints.precurations.set_rls_context"):
        yield


def test_precuration_approve_maps_denied_update_to_403(
    client: TestClient, db_session: Session, test_precuration: PrecurationNew
):
    reviewer = make_user(db_session)
    make_member(
        db_session,
        db_session.get(Scope, test_precuration.scope_id),
        reviewer,
        "reviewer",
    )
    test_precuration.status = CurationStatus.SUBMITTED
    db_session.commit()
    with patch(
        "app.api.v1.endpoints.precurations.precuration_crud.approve_and_create_curation",
        side_effect=StaleDataError("0 rows matched"),
    ):
        r = client.post(
            f"/api/v1/precurations/{test_precuration.id}/approve",
            headers=auth_headers(reviewer),
        )
    assert r.status_code == 403, r.text
    with (
        patch(
            "app.api.v1.endpoints.precurations.precuration_crud.approve_and_create_curation",
            side_effect=DBAPIError("UPDATE", {}, _PgError("23505")),
        ),
        pytest.raises(DBAPIError),
    ):
        client.post(
            f"/api/v1/precurations/{test_precuration.id}/approve",
            headers=auth_headers(reviewer),
        )


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (StaleDataError("0 rows matched"), HTTPException),
        (DBAPIError("UPDATE", {}, _PgError("42501")), HTTPException),
        # anything but insufficient_privilege is a real failure, not a 403
        (DBAPIError("UPDATE", {}, _PgError("23505")), DBAPIError),
    ],
)
def test_engine_transition_maps_only_denials_to_403(
    db_session: Session, test_curation, error: Exception, expected: type
):
    engine = WorkflowEngine()
    user = make_user(db_session)
    make_member(
        db_session, db_session.get(Scope, test_curation.scope_id), user, "reviewer"
    )
    test_curation.workflow_stage = WorkflowStage.REVIEW
    db_session.commit()
    with (
        patch.object(db_session, "commit", side_effect=error),
        pytest.raises(expected) as raised,
    ):
        engine.execute_transition(
            db_session, test_curation.id, "curation", WorkflowStage.CURATION, user.id
        )
    if expected is HTTPException:
        assert raised.value.status_code == 403
