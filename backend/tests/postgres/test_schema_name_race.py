"""Schema name races on real PostgreSQL, through the API as app_user (#432).

Two admins create (or derive) the same name/version at once: both pass the duplicate check,
the UNIQUE(name, version) constraint from 001 picks the winner and the loser gets the same 400
the check gives. A rename onto a taken name/version gets it too.
"""

import os
import threading
from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.core import database
from app.core.security import create_access_token
from app.crud.schema_repository import schema_crud
from app.main import app

pytestmark = pytest.mark.postgres

BASE = "/api/v1/schemas/curation-schemas"
DUPLICATE = "Schema with this name and version already exists"


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


def _h(uid: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(uid)})}"}


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


@pytest.fixture
def tag() -> Generator[str, None, None]:
    """Unique name prefix; every schema created under it is removed afterwards."""
    name = f"race-{uuid4().hex[:8]}"
    yield name
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM audit_log WHERE schema_id IN "
            "(SELECT id FROM curation_schemas WHERE name LIKE %s)",
            (f"{name}%",),
        )
        cur.execute("DELETE FROM curation_schemas WHERE name LIKE %s", (f"{name}%",))


def _seeded() -> tuple[UUID, UUID, UUID, str]:
    """(admin, curator, a published source schema, its latest version id)."""
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT (SELECT id FROM users WHERE role = 'admin' AND is_active LIMIT 1), "
            "(SELECT id FROM users WHERE role = 'user' AND is_active LIMIT 1)"
        )
        admin, curator = cur.fetchone()
        cur.execute(
            "SELECT schema_id, id FROM methodology_versions "
            "ORDER BY schema_id, version DESC LIMIT 1"
        )
        schema, version = cur.fetchone()
    return admin, curator, schema, str(version)


def _count(name: str) -> int:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM curation_schemas WHERE name = %s", (name,))
        n: int = cur.fetchone()[0]
        return n


def _race(monkeypatch: pytest.MonkeyPatch, *calls: Callable[[], Response]) -> list[Any]:
    """Run the calls at once; each waits after its duplicate check until all have checked."""
    barrier = threading.Barrier(len(calls), timeout=15)
    check = schema_crud.get_by_name_and_version

    def checked(*args: Any, **kwargs: Any) -> Any:
        found = check(*args, **kwargs)
        barrier.wait()
        return found

    monkeypatch.setattr(schema_crud, "get_by_name_and_version", checked)
    with ThreadPoolExecutor(len(calls)) as pool:
        return [f.result() for f in [pool.submit(c) for c in calls]]


@pytest.mark.parametrize("first", ["create", "derive"])
def test_concurrent_same_name_has_one_winner_and_a_400(
    client: TestClient, tag: str, first: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin, curator, schema, version = _seeded()
    source = client.get(f"{BASE}/{schema}", headers=_h(admin)).json()
    body = {**source, "name": tag, "schema_hash": None}

    def create() -> Response:
        return client.post(BASE, json=body, headers=_h(admin))

    def derive() -> Response:
        return client.post(
            f"{BASE}/{schema}/versions/{version}/derive",
            json={"name": tag, "version": source["version"]},
            headers=_h(admin),
        )

    # platform admin only, also when racing
    assert client.post(BASE, json=body, headers=_h(curator)).status_code == 403

    results = _race(monkeypatch, create if first == "create" else derive, create)

    codes = sorted(r.status_code for r in results)
    assert codes[0] in (200, 201) and codes[1] == 400, [r.text for r in results]
    loser = next(r for r in results if r.status_code == 400)
    assert loser.json()["detail"] == DUPLICATE
    assert _count(tag) == 1


def test_rename_onto_a_taken_name_is_400_and_changes_nothing(
    client: TestClient, tag: str
) -> None:
    admin, _, schema, _ = _seeded()
    source = client.get(f"{BASE}/{schema}", headers=_h(admin)).json()
    ids = []
    for name in (tag, f"{tag}-b"):
        r = client.post(
            BASE, json={**source, "name": name, "schema_hash": None}, headers=_h(admin)
        )
        assert r.status_code == 200, r.text
        ids.append(r.json()["id"])

    r = client.put(
        f"{BASE}/{ids[1]}", json={"name": tag, "lock_version": 0}, headers=_h(admin)
    )

    assert r.status_code == 400, r.text
    assert r.json()["detail"] == DUPLICATE
    assert (
        client.get(f"{BASE}/{ids[1]}", headers=_h(admin)).json()["name"] == f"{tag}-b"
    )


def test_null_active_update_cannot_make_a_schema_unreadable(
    client: TestClient, tag: str
) -> None:
    admin, _, schema, _ = _seeded()
    source = client.get(f"{BASE}/{schema}", headers=_h(admin)).json()
    created = client.post(
        BASE, json={**source, "name": tag, "schema_hash": None}, headers=_h(admin)
    )
    assert created.status_code == 200, created.text
    url = f"{BASE}/{created.json()['id']}"
    disabled = client.put(
        url, json={"is_active": False, "lock_version": 0}, headers=_h(admin)
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["is_active"] is False

    rejected = client.put(
        url, json={"is_active": None, "lock_version": 1}, headers=_h(admin)
    )

    assert rejected.status_code == 422, rejected.text
    kept = client.get(url, headers=_h(admin))
    assert kept.status_code == 200, kept.text
    assert kept.json()["is_active"] is False
    listing = client.get(BASE, params={"active_only": False}, headers=_h(admin))
    assert listing.status_code == 200, listing.text
    assert any(row["id"] == created.json()["id"] for row in listing.json())
