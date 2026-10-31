"""Schema editor saves as app_user through the API (081, #282): a stale save is 409."""

import pytest
from fastapi.testclient import TestClient

from tests.postgres.test_methodology_versions import W, _h, client, w

pytestmark = pytest.mark.postgres
__all__ = ["client", "w"]  # fixtures shared with the methodology version tests


def test_second_save_of_the_same_copy_is_409(client: TestClient, w: W) -> None:
    url = f"/api/v1/schemas/curation-schemas/{w.schema}"
    loaded = client.get(url, headers=_h(w.admin)).json()["lock_version"]

    first = client.put(
        url,
        json={"description": "first", "lock_version": loaded},
        headers=_h(w.admin),
    )
    assert first.status_code == 200, first.text
    assert first.json()["lock_version"] == loaded + 1

    stale = client.put(
        url,
        json={"description": "second", "lock_version": loaded},
        headers=_h(w.admin),
    )
    assert stale.status_code == 409, stale.text
    after = client.get(url, headers=_h(w.admin)).json()
    assert (after["description"], after["lock_version"]) == ("first", loaded + 1)
