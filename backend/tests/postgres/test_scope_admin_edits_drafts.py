"""W11 A9 as app_user (#284 matrix): a scope admin saves another member's draft in their
scope; another curator of the scope cannot."""

import json
import os
from collections.abc import Generator
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient

from app.core import database
from app.core.security import create_access_token, get_password_hash
from app.main import app

pytestmark = pytest.mark.postgres


@dataclass
class W:
    scope: UUID = field(default_factory=uuid4)
    alice: UUID = field(default_factory=uuid4)  # curator, author
    sadmin: UUID = field(default_factory=uuid4)  # scope admin
    carl: UUID = field(default_factory=uuid4)  # another curator
    gene: UUID = field(default_factory=uuid4)
    cur: UUID = field(default_factory=uuid4)


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.scope)[:8]
    members = ((x.alice, "curator"), (x.sadmin, "admin"), (x.carl, "curator"))
    ids = [str(u) for u, _ in members]
    with _owner() as conn, conn.cursor() as cur:
        for uid, _ in members:
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, 'u', 'user')",
                (str(uid), f"{uid.hex[:8]}-{tag}@sa.org", get_password_hash("pw")),
            )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, 'SA', false, %s)",
            (str(x.scope), f"sa-{x.scope}", str(x.sadmin)),
        )
        for uid, role in members:
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, %s, %s, now())",
                (str(x.scope), str(uid), role, str(x.sadmin)),
            )
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (%s, %s, %s, %s)",
            (str(x.gene), f"HGNC:{x.gene.int % 10**9}", f"SA{tag}", x.gene.hex * 2),
        )
        cur.execute(
            "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, status, "
            "workflow_stage, is_draft, evidence_data, created_by) SELECT %s, %s, %s, id, "
            "'draft', 'curation', true, %s, %s FROM workflow_pairs WHERE is_active LIMIT 1",
            (
                str(x.cur),
                str(x.gene),
                str(x.scope),
                json.dumps({"summary": "ok"}),
                str(x.alice),
            ),
        )
    yield x
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(x.scope),))
        cur.execute("DELETE FROM genes WHERE id = %s", (str(x.gene),))
        cur.execute(
            "DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[]) OR scope_id = %s",
            (ids, str(x.scope)),
        )
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (ids,))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _h(uid: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(uid)})}"}


def test_scope_admin_saves_another_members_draft(client: TestClient, w: W) -> None:
    url = f"/api/v1/curations/{w.cur}"
    lock = client.get(url, headers=_h(w.alice)).json()["lock_version"]
    body = {"evidence_data": {"summary": "fixed"}, "merge": True, "lock_version": lock}
    refused = client.patch(f"{url}/draft", json=body, headers=_h(w.carl))
    assert refused.status_code == 403, refused.text
    r = client.patch(f"{url}/draft", json=body, headers=_h(w.sadmin))
    assert r.status_code == 200, r.text
    saved = client.get(url, headers=_h(w.alice)).json()
    assert saved["evidence_data"]["summary"] == "fixed"
    assert saved["lock_version"] > lock
    # D1 (#609 review): the edit is the admin's work too; app_user wrote the marker row
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM audit_log WHERE entity_id = %s AND user_id = %s "
            "AND change_type = 'draft_edit'",
            (str(w.cur), str(w.sadmin)),
        )
        assert cur.fetchone()[0] == 1
        cur.execute(
            "UPDATE curations SET status = 'in_review', workflow_stage = 'review', "
            "submitted_at = now() WHERE id = %s",
            (str(w.cur),),
        )
    r = client.post(
        f"/api/v1/workflow/curation/{w.cur}/transition",
        json={"target_stage": "active"},
        headers=_h(w.sadmin),
    )
    assert r.status_code == 403, r.text


def test_admin_edits_a_precuration_then_may_not_approve_it(
    client: TestClient, w: W
) -> None:
    """#609 delta review as app_user: the precuration edit is the admin's work too."""
    pre = uuid4()
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO precurations (id, gene_id, scope_id, precuration_schema_id, "
            "status, workflow_stage, is_draft, created_by) SELECT %s, %s, %s, "
            "precuration_schema_id, 'draft', 'precuration', true, %s FROM workflow_pairs "
            "WHERE is_active AND precuration_schema_id IS NOT NULL LIMIT 1",
            (str(pre), str(w.gene), str(w.scope), str(w.alice)),
        )
    url = f"/api/v1/precurations/{pre}"
    lock = client.get(url, headers=_h(w.alice)).json()["lock_version"]
    body = {"evidence_data": {"note": "x"}, "merge": True, "lock_version": lock}
    assert (
        client.patch(f"{url}/draft", json=body, headers=_h(w.carl)).status_code == 403
    )
    r = client.patch(f"{url}/draft", json=body, headers=_h(w.sadmin))
    assert r.status_code == 200, r.text
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE precurations SET status = 'submitted', workflow_stage = 'review' "
            "WHERE id = %s",
            (str(pre),),
        )
    r = client.post(f"{url}/approve", headers=_h(w.sadmin))
    assert r.status_code == 403, r.text
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM precurations WHERE id = %s", (str(pre),))
