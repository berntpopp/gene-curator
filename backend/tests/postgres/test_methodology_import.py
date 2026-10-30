"""Methodology bundle import as app_user on PostgreSQL (#575).

The 042 trigger publishes v1 of a new schema (no second v1 from the import), the same
bundle again writes nothing, changed content publishes v2 and the scope default is set
under RLS.
"""

from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_password_hash
from tests.api.schema_api_support import schema_payload
from tests.postgres.test_methodology_versions import _h, _owner, client

pytestmark = pytest.mark.postgres
__all__ = ["client"]

URL = "/api/v1/schemas/methodologies/import"


@pytest.fixture
def admin_scope() -> Generator[tuple[UUID, str, str], None, None]:
    admin, scope, tag = uuid4(), uuid4(), uuid4().hex[:8]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (id, email, hashed_password, name, role) "
            "VALUES (%s, %s, %s, 'admin', 'admin')",
            (str(admin), f"imp-{tag}@mi.org", get_password_hash("pw")),
        )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, 'MI', false, %s)",
            (str(scope), f"mi-{tag}", str(admin)),
        )
    yield admin, f"mi-{tag}", tag
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(scope),))
        cur.execute("DELETE FROM workflow_pairs WHERE name = %s", (f"pair-{tag}",))
        cur.execute("DELETE FROM curation_schemas WHERE name LIKE %s", (f"%-{tag}",))
        cur.execute("DELETE FROM audit_log WHERE user_id = %s", (str(admin),))
        cur.execute("DELETE FROM users WHERE id = %s", (str(admin),))


def _bundle(tag: str, scope_name: str, label: str = "Gene") -> dict[str, object]:
    cur = schema_payload(f"cur-{tag}", "1")
    cur["field_definitions"] = {"gene": {"type": "text", "label": label}}
    return {
        "schemas": [schema_payload(f"pre-{tag}", "1", schema_type="precuration"), cur],
        "workflow_pairs": [
            {
                "name": f"pair-{tag}",
                "version": "1",
                "precuration_schema": f"pre-{tag}",
                "curation_schema": f"cur-{tag}",
            }
        ],
        "scope_default": {"scope_name": scope_name, "workflow_pair": f"pair-{tag}"},
    }


def _versions(tag: str) -> list[tuple[str, int]]:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT s.name, v.version FROM methodology_versions v "
            "JOIN curation_schemas s ON s.id = v.schema_id WHERE s.name LIKE %s "
            "ORDER BY s.name, v.version",
            (f"%-{tag}",),
        )
        return [(name, version) for name, version in cur.fetchall()]


def test_import_is_idempotent_and_versions_changes(
    client: TestClient, admin_scope: tuple[UUID, str, str]
) -> None:
    admin, scope_name, tag = admin_scope
    r = client.post(URL, json=_bundle(tag, scope_name), headers=_h(admin))
    assert r.status_code == 200, r.text
    assert _versions(tag) == [(f"cur-{tag}", 1), (f"pre-{tag}", 1)]
    pair_id = r.json()["items"][2]["id"]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT default_workflow_pair_id FROM scopes WHERE name = %s", (scope_name,)
        )
        assert str(cur.fetchone()[0]) == pair_id

    again = client.post(URL, json=_bundle(tag, scope_name), headers=_h(admin))
    assert {i["action"] for i in again.json()["items"]} == {"unchanged"}

    r = client.post(URL, json=_bundle(tag, scope_name, "HGNC"), headers=_h(admin))
    assert r.status_code == 200, r.text
    assert _versions(tag) == [(f"cur-{tag}", 1), (f"cur-{tag}", 2), (f"pre-{tag}", 1)]
