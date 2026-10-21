"""Methodology version API: admins publish and derive, every active user reads (#265, #271).

Pinning and immutability are database triggers; tests/postgres/test_methodology_versions.py
covers those.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.api.schema_api_support import auth, insert_schema

pytestmark = pytest.mark.unit

BASE = "/api/v1/schemas/curation-schemas"
VERSIONS = "/api/v1/schemas/methodology-versions"


def test_admin_publishes_numbered_snapshots_and_lists_them_newest_first(
    client: TestClient, db_session: Session, admin_token: str
) -> None:
    schema = insert_schema(db_session, scoring_configuration={"engine": "x"})

    first = client.post(f"{BASE}/{schema.id}/versions", headers=auth(admin_token))
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["version"] == 1
    assert body["published_at"] and body["created_by"]
    assert body["snapshot"]["field_definitions"] == schema.field_definitions
    assert body["snapshot"]["scoring_configuration"] == {"engine": "x"}

    schema.field_definitions = {"changed": {"type": "text"}}
    db_session.commit()
    second = client.post(f"{BASE}/{schema.id}/versions", headers=auth(admin_token))
    assert second.json()["version"] == 2
    assert second.json()["snapshot"]["field_definitions"] == {
        "changed": {"type": "text"}
    }

    listed = client.get(f"{BASE}/{schema.id}/versions", headers=auth(admin_token))
    assert listed.status_code == 200
    assert [v["version"] for v in listed.json()] == [2, 1]
    assert listed.json()[1]["snapshot"]["field_definitions"] == {
        "gene": {"type": "text", "label": "Gene"}
    }


def test_non_admins_cannot_publish_but_can_read(
    client: TestClient, db_session: Session, curator_token: str, admin_token: str
) -> None:
    schema = insert_schema(db_session)
    url = f"{BASE}/{schema.id}/versions"
    assert client.post(url, headers=auth(curator_token)).status_code == 403
    v1 = client.post(url, headers=auth(admin_token)).json()

    listed = client.get(url, headers=auth(curator_token))
    assert listed.status_code == 200
    assert [v["id"] for v in listed.json()] == [v1["id"]]
    got = client.get(f"{VERSIONS}/{v1['id']}", headers=auth(curator_token))
    assert got.status_code == 200
    assert got.json()["snapshot"] == v1["snapshot"]
    assert (
        client.get(f"{VERSIONS}/{uuid4()}", headers=auth(curator_token)).status_code
        == 404
    )


def test_put_on_schema_leaves_published_snapshot_unchanged(
    client: TestClient, db_session: Session, admin_token: str
) -> None:
    schema = insert_schema(db_session)
    v1 = client.post(f"{BASE}/{schema.id}/versions", headers=auth(admin_token)).json()
    r = client.put(
        f"{BASE}/{schema.id}",
        json={"field_definitions": {"other": {"type": "text"}}},
        headers=auth(admin_token),
    )
    assert r.status_code == 200, r.text
    got = client.get(f"{VERSIONS}/{v1['id']}", headers=auth(admin_token))
    assert got.json()["snapshot"] == v1["snapshot"]


def test_unknown_schema_is_404(client: TestClient, admin_token: str) -> None:
    for method in (client.post, client.get):
        r = method(f"{BASE}/{uuid4()}/versions", headers=auth(admin_token))
        assert r.status_code == 404
