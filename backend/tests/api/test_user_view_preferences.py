"""Saved catalogue view: per user, own only, validated (#276)."""

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import UserNew, UserViewPreference
from tests.api.scopes.factories import make_scope


def _public(db: Session, n: int) -> list[str]:
    scopes = [make_scope(db) for _ in range(n)]
    for scope in scopes:
        scope.is_public = True
    db.commit()
    return [str(s.id) for s in scopes]


pytestmark = pytest.mark.unit

URL = "/api/v1/me/views/catalogue"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_saves_and_restores_in_order_per_user(
    client: TestClient, db_session: Session, admin_token: str, curator_token: str
) -> None:
    assert client.get(URL, headers=_bearer(admin_token)).json() == {"scope_ids": []}
    ids = _public(db_session, 3)
    r = client.put(URL, json={"scope_ids": ids}, headers=_bearer(admin_token))
    assert r.status_code == 200 and r.json()["scope_ids"] == ids
    reordered = ids[::-1]
    client.put(URL, json={"scope_ids": reordered}, headers=_bearer(admin_token))
    assert (
        client.get(URL, headers=_bearer(admin_token)).json()["scope_ids"] == reordered
    )
    # another user has their own view
    assert client.get(URL, headers=_bearer(curator_token)).json() == {"scope_ids": []}


def test_requires_sign_in_and_validates(client: TestClient, admin_token: str) -> None:
    assert client.get(URL).status_code == 401
    assert client.put(URL, json={"scope_ids": []}).status_code == 401
    too_many = [str(uuid4()) for _ in range(51)]
    for body in ({"scope_ids": too_many}, {"scope_ids": ["not-a-uuid"]}):
        assert (
            client.put(URL, json=body, headers=_bearer(admin_token)).status_code == 422
        )


def test_a_save_racing_the_first_one_updates_instead_of_failing(
    client: TestClient,
    admin_token: str,
    test_user_admin: UserNew,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Another request inserted the row after this one looked: still a 200 (#276)."""
    db_session.add(
        UserViewPreference(
            user_id=test_user_admin.id, view="catalogue", value={"scope_ids": []}
        )
    )
    db_session.commit()
    real_get = Session.get

    def blind_get(self: Session, entity: Any, *a: Any, **k: Any) -> Any:
        return None if entity is UserViewPreference else real_get(self, entity, *a, **k)

    ids = _public(db_session, 1)
    monkeypatch.setattr(Session, "get", blind_get)
    r = client.put(URL, json={"scope_ids": ids}, headers=_bearer(admin_token))
    assert r.status_code == 200, r.text
    monkeypatch.undo()
    db_session.expire_all()
    pref = db_session.get(UserViewPreference, (test_user_admin.id, "catalogue"))
    assert pref is not None and pref.value == {"scope_ids": ids}


def test_unknown_hidden_and_duplicate_ids_are_dropped(
    client: TestClient, db_session: Session, curator_token: str
) -> None:
    """W11 A7: only scopes you can see, each once, in your order."""
    shown = _public(db_session, 2)
    hidden = str(make_scope(db_session).id)  # private, not a member
    body = {"scope_ids": [shown[1], str(uuid4()), hidden, shown[0], shown[1]]}
    r = client.put(URL, json=body, headers=_bearer(curator_token))
    assert r.status_code == 200, r.text
    assert r.json()["scope_ids"] == [shown[1], shown[0]]
    assert client.get(URL, headers=_bearer(curator_token)).json() == r.json()
