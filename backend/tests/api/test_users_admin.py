"""Admin user-management guards and login timestamp (#211, #214)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.user import user_crud
from app.models.models import UserNew
from tests.api.scopes.factories import auth_headers, make_user

pytestmark = pytest.mark.unit

URL = "/api/v1/users"


def test_admin_cannot_demote_self(client: TestClient, test_user_admin: UserNew) -> None:
    r = client.put(
        f"{URL}/{test_user_admin.id}",
        json={"role": "user"},
        headers=auth_headers(test_user_admin),
    )
    assert r.status_code == 400
    assert "own" in r.json()["detail"]


def test_admin_cannot_deactivate_self_via_update(
    client: TestClient, test_user_admin: UserNew
) -> None:
    r = client.put(
        f"{URL}/{test_user_admin.id}",
        json={"is_active": False},
        headers=auth_headers(test_user_admin),
    )
    assert r.status_code == 400


def test_admin_can_demote_another_admin(
    client: TestClient, db_session: Session, test_user_admin: UserNew
) -> None:
    other = make_user(db_session, role="admin")
    r = client.put(
        f"{URL}/{other.id}",
        json={"role": "user"},
        headers=auth_headers(test_user_admin),
    )
    assert r.status_code == 200
    assert r.json()["role"] == "user"


def test_admin_can_edit_own_name(client: TestClient, test_user_admin: UserNew) -> None:
    r = client.put(
        f"{URL}/{test_user_admin.id}",
        json={"name": "Renamed", "role": "admin", "is_active": True},
        headers=auth_headers(test_user_admin),
    )
    assert r.status_code == 200


def test_last_login_is_timezone_aware_utc(db_session: Session) -> None:
    user = make_user(db_session)
    assert user_crud.update_last_login(db_session, str(user.id))
    db_session.refresh(user)
    stamp = user.last_login.replace(tzinfo=user.last_login.tzinfo or UTC)
    assert abs(datetime.now(UTC) - stamp) < timedelta(seconds=5)
