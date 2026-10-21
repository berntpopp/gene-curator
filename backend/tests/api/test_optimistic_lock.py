"""Two tabs, one record: a stale save must be refused, never silently overwrite (release blocker).

Covers draft PATCH and PUT for curations and precurations.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.models import CurationNew, PrecurationNew

pytestmark = pytest.mark.unit

KINDS = ["curations", "precurations"]


@pytest.fixture
def record(
    request: pytest.FixtureRequest,
    test_curation: CurationNew,
    test_precuration: PrecurationNew,
) -> Any:
    return test_curation if request.param == "curations" else test_precuration


def _url(kind: str, record: Any, tail: str = "") -> str:
    return f"/api/v1/{kind}/{record.id}{tail}"


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _save(
    client: TestClient, token: str, kind: str, record: Any, data: dict, version: int
):
    return client.patch(
        _url(kind, record, "/draft"),
        json={"evidence_data": data, "lock_version": version},
        headers=_h(token),
    )


@pytest.mark.parametrize("record", KINDS, indirect=True)
def test_fresh_save_succeeds_and_bumps_the_version_once(
    client: TestClient, admin_token: str, record: Any
) -> None:
    kind = "curations" if isinstance(record, CurationNew) else "precurations"
    first = _save(client, admin_token, kind, record, {"a": 1}, record.lock_version)
    assert first.status_code == 200, first.text
    v1 = first.json()["lock_version"]
    assert v1 == 1
    second = _save(client, admin_token, kind, record, {"a": 2}, v1)
    assert second.status_code == 200
    assert second.json()["lock_version"] == 2


@pytest.mark.parametrize("record", KINDS, indirect=True)
def test_two_tabs_the_stale_save_is_refused_and_the_newer_one_survives(
    client: TestClient, admin_token: str, db_session: Session, record: Any
) -> None:
    kind = "curations" if isinstance(record, CurationNew) else "precurations"
    loaded = record.lock_version  # both tabs loaded this version
    tab_b = _save(client, admin_token, kind, record, {"who": "B"}, loaded)
    assert tab_b.status_code == 200

    tab_a = _save(client, admin_token, kind, record, {"who": "A"}, loaded)

    assert tab_a.status_code == 409
    detail = tab_a.json()["detail"]
    assert detail["current_lock_version"] == loaded + 1
    assert detail["your_lock_version"] == loaded
    db_session.refresh(record)
    assert record.evidence_data == {"who": "B"}
    assert record.lock_version == loaded + 1


@pytest.mark.parametrize("record", KINDS, indirect=True)
def test_put_with_a_stale_version_is_refused_too(
    client: TestClient, admin_token: str, db_session: Session, record: Any
) -> None:
    kind = "curations" if isinstance(record, CurationNew) else "precurations"
    loaded = record.lock_version
    assert (
        _save(client, admin_token, kind, record, {"who": "B"}, loaded).status_code
        == 200
    )
    stale = client.put(
        _url(kind, record),
        json={"evidence_data": {"who": "A"}, "lock_version": loaded},
        headers=_h(admin_token),
    )
    assert stale.status_code == 409
    fresh = client.put(
        _url(kind, record),
        json={"evidence_data": {"who": "A"}, "lock_version": loaded + 1},
        headers=_h(admin_token),
    )
    assert fresh.status_code == 200
    assert fresh.json()["lock_version"] == loaded + 2


@pytest.mark.parametrize("record", KINDS, indirect=True)
def test_the_compare_is_atomic_in_the_update_not_just_on_the_loaded_row(
    client: TestClient, admin_token: str, db_session: Session, record: Any
) -> None:
    """Someone commits between this request's read and its write: the in-memory row still shows
    the client's version, but the UPDATE ... WHERE lock_version = ? must match nothing."""
    kind = "curations" if isinstance(record, CurationNew) else "precurations"
    model = type(record)
    loaded = record.lock_version
    db_session.execute(
        update(model)
        .where(model.id == record.id)
        .values(lock_version=loaded + 1, evidence_data={"who": "B"}),
        execution_options={"synchronize_session": False},
    )
    db_session.commit()
    # record in the session still believes lock_version == loaded
    record.__dict__["lock_version"] = loaded

    stale = _save(client, admin_token, kind, record, {"who": "A"}, loaded)

    assert stale.status_code == 409
    db_session.expire_all()
    assert db_session.get(model, record.id).evidence_data == {"who": "B"}


@pytest.mark.parametrize("record", KINDS, indirect=True)
def test_a_save_without_a_version_is_rejected(
    client: TestClient, admin_token: str, record: Any
) -> None:
    kind = "curations" if isinstance(record, CurationNew) else "precurations"
    response = client.patch(
        _url(kind, record, "/draft"),
        json={"evidence_data": {"a": 1}},
        headers=_h(admin_token),
    )
    assert response.status_code == 422
