"""Methodology version API: admins publish and derive, every active user reads (#265, #271).

Pinning and immutability are database triggers; tests/postgres/test_methodology_versions.py
covers those.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.schema_repository import schema_crud
from app.models import UserNew
from tests.api.schema_api_support import auth, insert_schema

pytestmark = pytest.mark.unit

BASE = "/api/v1/schemas/curation-schemas"
VERSIONS = "/api/v1/schemas/methodology-versions"


def test_admin_publishes_numbered_snapshots_and_lists_them_newest_first(
    client: TestClient, db_session: Session, admin_token: str
) -> None:
    schema = insert_schema(
        db_session, scoring_configuration={"engine": "clingen_sop_v11"}
    )

    first = client.post(f"{BASE}/{schema.id}/versions", headers=auth(admin_token))
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["version"] == 1
    assert body["published_at"] and body["created_by"]
    assert body["snapshot"]["field_definitions"] == schema.field_definitions
    assert body["snapshot"]["scoring_configuration"] == {"engine": "clingen_sop_v11"}

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
        json={"field_definitions": {"other": {"type": "text"}}, "lock_version": 0},
        headers=auth(admin_token),
    )
    assert r.status_code == 200, r.text
    got = client.get(f"{VERSIONS}/{v1['id']}", headers=auth(admin_token))
    assert got.json()["snapshot"] == v1["snapshot"]


def test_admin_derives_inactive_schema_whose_v1_points_at_the_source(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    test_user_admin: UserNew,
) -> None:
    schema = insert_schema(
        db_session, scoring_configuration={"engine": "clingen_sop_v11"}
    )
    v1 = client.post(f"{BASE}/{schema.id}/versions", headers=auth(admin_token)).json()
    r = client.post(
        f"{BASE}/{schema.id}/versions/{v1['id']}/derive",
        json={"name": "Derived", "version": "1.0"},
        headers=auth(admin_token),
    )
    assert r.status_code == 201, r.text
    derived = r.json()
    assert derived["id"] != str(schema.id)
    assert (derived["name"], derived["is_active"]) == ("Derived", False)
    assert derived["created_by"] == str(test_user_admin.id)
    assert derived["scoring_configuration"] == {"engine": "clingen_sop_v11"}

    versions = client.get(
        f"{BASE}/{derived['id']}/versions", headers=auth(admin_token)
    ).json()
    assert len(versions) == 1
    assert versions[0]["version"] == 1
    assert versions[0]["derived_from_version_id"] == v1["id"]
    assert versions[0]["created_by"] == str(test_user_admin.id)
    assert versions[0]["snapshot"] == v1["snapshot"]


def test_derive_refusals(
    client: TestClient, db_session: Session, admin_token: str, curator_token: str
) -> None:
    schema = insert_schema(db_session, name="Taken", version="2")
    other = insert_schema(db_session, name="Other")
    vid = client.post(f"{BASE}/{schema.id}/versions", headers=auth(admin_token)).json()[
        "id"
    ]
    body = {"name": "New", "version": "1"}

    def derive(sid: object, v: object, token: str, json: object = body) -> int:
        url = f"{BASE}/{sid}/versions/{v}/derive"
        return client.post(url, json=json, headers=auth(token)).status_code

    assert derive(schema.id, vid, curator_token) == 403
    assert derive(schema.id, uuid4(), admin_token) == 404
    assert derive(other.id, vid, admin_token) == 404  # version of another schema
    assert derive(schema.id, vid, admin_token, {"name": "Taken", "version": "2"}) == 400
    assert derive(schema.id, vid, admin_token, {"name": "", "version": "1"}) == 422


def test_derive_losing_a_race_gets_the_same_400(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#432: the check passed, a concurrent create took the name; the constraint decides."""
    schema = insert_schema(db_session, name="Taken", version="2")
    vid = client.post(f"{BASE}/{schema.id}/versions", headers=auth(admin_token)).json()[
        "id"
    ]
    monkeypatch.setattr(schema_crud, "get_by_name_and_version", lambda *a, **k: None)

    r = client.post(
        f"{BASE}/{schema.id}/versions/{vid}/derive",
        json={"name": "Taken", "version": "2"},
        headers=auth(admin_token),
    )

    assert r.status_code == 400
    assert r.json()["detail"] == "Schema with this name and version already exists"


def test_unknown_schema_is_404(client: TestClient, admin_token: str) -> None:
    for method in (client.post, client.get):
        r = method(f"{BASE}/{uuid4()}/versions", headers=auth(admin_token))
        assert r.status_code == 404
