"""Direct member add and default workflow pair (MCP study round 1, F6), SQLite."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.models.models import (
    AuditLogNew,
    NotificationNew,
    NotificationType,
    Scope,
    ScopeMembership,
    UserNew,
)
from tests.api.scopes.factories import (
    auth_headers,
    make_member,
    make_user,
    make_workflow_pair,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _audit_ids_on_sqlite() -> Iterator[None]:
    """SQLite does not autoincrement the BigInteger audit_log id."""

    def assign_id(mapper: Any, connection: Any, target: AuditLogNew) -> None:
        target.id = target.id or 1 + connection.scalar(
            select(func.coalesce(func.max(AuditLogNew.id), 0))
        )

    event.listen(AuditLogNew, "before_insert", assign_id)
    yield
    event.remove(AuditLogNew, "before_insert", assign_id)


def _add(
    client: TestClient,
    scope: Scope,
    actor: UserNew,
    user: UserNew,
    role: str = "curator",
):
    return client.post(
        f"/api/v1/scopes/{scope.id}/members",
        json={"user_id": str(user.id), "role": role},
        headers=auth_headers(actor),
    )


@pytest.mark.parametrize("actor_name", ["owner", "app_admin"])
def test_admin_adds_accepted_member_audited_and_notified(
    request: pytest.FixtureRequest,
    client: TestClient,
    db_session: Session,
    scope_with_admin: Scope,
    actor_name: str,
) -> None:
    actor: UserNew = request.getfixturevalue(actor_name)
    user = make_user(db_session)

    response = _add(client, scope_with_admin, actor, user, "reviewer")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["is_pending"] is False
    assert body["accepted_at"] is not None
    assert body["role"] == "reviewer"
    audit = db_session.scalar(
        select(AuditLogNew).where(AuditLogNew.entity_id == body["id"])
    )
    assert audit is not None
    assert (audit.operation, audit.user_id) == ("DIRECT_ADD", actor.id)
    note = db_session.scalar(
        select(NotificationNew).where(NotificationNew.user_id == user.id)
    )
    assert note is not None
    assert note.type == NotificationType.SCOPE_MEMBERSHIP_ADDED
    assert "reviewer" in note.message


def test_curator_cannot_add(
    client: TestClient, db_session: Session, scope_with_admin: Scope, curator: UserNew
) -> None:
    assert (
        _add(client, scope_with_admin, curator, make_user(db_session)).status_code
        == 403
    )


def test_nobody_adds_themselves(
    client: TestClient, db_session: Session, scope_with_admin: Scope, app_admin: UserNew
) -> None:
    response = _add(client, scope_with_admin, app_admin, app_admin, "admin")

    assert response.status_code == 403
    assert (
        db_session.scalar(
            select(ScopeMembership).where(ScopeMembership.user_id == app_admin.id)
        )
        is None
    )


@pytest.mark.parametrize(
    "accepted,is_active", [(False, True), (True, False), (False, False)]
)
def test_pending_expired_or_removed_row_is_taken_over(
    client: TestClient,
    db_session: Session,
    scope_with_admin: Scope,
    owner: UserNew,
    accepted: bool,
    is_active: bool,
) -> None:
    user = make_user(db_session)
    old = make_member(
        db_session,
        scope_with_admin,
        user,
        "viewer",
        accepted=accepted,
        is_active=is_active,
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )

    response = _add(client, scope_with_admin, owner, user, "reviewer")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"] == str(old.id)
    assert (body["role"], body["is_pending"], body["is_active"]) == (
        "reviewer",
        False,
        True,
    )
    assert db_session.scalar(select(AuditLogNew).where(AuditLogNew.entity_id == old.id))


def test_active_member_is_400(
    client: TestClient, db_session: Session, scope_with_admin: Scope, owner: UserNew
) -> None:
    user = make_user(db_session)
    make_member(db_session, scope_with_admin, user, "viewer")

    response = _add(client, scope_with_admin, owner, user)

    assert response.status_code == 400
    assert "already a member" in response.json()["detail"]


def test_create_scope_without_pair_uses_the_default(
    client: TestClient, db_session: Session, owner: UserNew
) -> None:
    make_workflow_pair(db_session)
    default = make_workflow_pair(db_session)
    default.is_default = True
    db_session.commit()

    response = client.post(
        "/api/v1/scopes/",
        json={"name": "default-pair", "display_name": "D", "description": "d"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 201, response.text
    assert response.json()["default_workflow_pair_id"] == str(default.id)
    from app.main import app

    assert (
        "is_default"
        in app.openapi()["components"]["schemas"]["WorkflowPair"]["properties"]
    )
