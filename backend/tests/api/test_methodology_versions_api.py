"""Admin-only methodology version API: publish snapshots a schema, list shows them (#265).

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


def test_non_admins_cannot_publish_or_list(
    client: TestClient, db_session: Session, curator_token: str
) -> None:
    schema = insert_schema(db_session)
    for method in (client.post, client.get):
        r = method(f"{BASE}/{schema.id}/versions", headers=auth(curator_token))
        assert r.status_code == 403


def test_unknown_schema_is_404(client: TestClient, admin_token: str) -> None:
    for method in (client.post, client.get):
        r = method(f"{BASE}/{uuid4()}/versions", headers=auth(admin_token))
        assert r.status_code == 404
