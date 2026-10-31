"""Saved catalogue view: per user, own only, validated (#276)."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit

URL = "/api/v1/me/views/catalogue"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_saves_and_restores_in_order_per_user(
    client: TestClient, admin_token: str, curator_token: str
) -> None:
    assert client.get(URL, headers=_bearer(admin_token)).json() == {"scope_ids": []}
    ids = [str(uuid4()) for _ in range(3)]
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
