"""The precuration author sees who requested changes, as app_user under RLS (#399)."""

import pytest
from fastapi.testclient import TestClient

from tests.postgres.test_reviewer_rls import (  # noqa: F401 (fixtures)
    W,
    _h,
    client,
    w,
)

pytestmark = pytest.mark.postgres


def test_author_sees_the_reviewer_who_sent_the_precuration_back(
    client: TestClient,  # noqa: F811
    w: W,  # noqa: F811
) -> None:
    r = client.post(
        f"/api/v1/precurations/{w.pre}/reject",
        json={"reason": "out of scope"},
        headers=_h(w.bob),
    )
    assert r.status_code == 200, r.text
    detail = client.get(f"/api/v1/precurations/{w.pre}", headers=_h(w.alice))
    assert detail.status_code == 200, detail.text
    assert detail.json()["rejected_by_name"] == "bob"
