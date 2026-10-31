"""Scope-admin endpoints must work on Postgres (role literals must be valid scope_role values)."""

import os
from collections.abc import Generator
from dataclasses import dataclass
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
    admin: UUID
    curator: UUID
    scope: UUID
    genes: list[UUID]
    assignment: UUID


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W(uuid4(), uuid4(), uuid4(), [uuid4(), uuid4()], uuid4())
    tag = str(x.scope)[:8]
    with _owner() as conn, conn.cursor() as cur:
        for uid, name in ((x.admin, "sadmin"), (x.curator, "scur")):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, 'user')",
                (
                    str(uid),
                    f"{name}-{tag}@roles-test.org",
                    get_password_hash("pw"),
                    name,
                ),
            )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, %s, false, %s)",
            (str(x.scope), f"roles-{x.scope}", "Roles", str(x.admin)),
        )
        for uid, role in ((x.admin, "admin"), (x.curator, "curator")):
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, %s, %s, now())",
                (str(x.scope), str(uid), role, str(x.admin)),
            )
        for i, gid in enumerate(x.genes):
            cur.execute(
                "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
                "VALUES (%s, %s, %s, %s)",
                (
                    str(gid),
                    f"HGNC:{gid.int % 10**9}",
                    f"RG{tag}{i}",
                    f"{gid}".replace("-", "") * 2,
                ),
            )
        cur.execute(
            "INSERT INTO gene_scope_assignments (id, gene_id, scope_id) "
            "VALUES (%s, %s, %s)",
            (str(x.assignment), str(x.genes[0]), str(x.scope)),
        )
    yield x
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(x.scope),))
        cur.execute(
            "DELETE FROM genes WHERE id = ANY(%s::uuid[])", ([str(g) for g in x.genes],)
        )
        users = [str(x.admin), str(x.curator)]
        cur.execute("DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[])", (users,))
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (users,))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _auth(uid: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(uid)})}"}


def _calls(w: W) -> list[tuple[str, str, dict[str, object]]]:
    base = "/api/v1/gene-assignments"
    return [
        ("put", f"{base}/{w.assignment}", {"assignment_notes": "n"}),
        (
            "post",
            f"{base}/bulk",
            {"gene_ids": [str(w.genes[1])], "scope_id": str(w.scope)},
        ),
        (
            "post",
            f"{base}/{w.assignment}/assign-curator",
            {"curator_id": str(w.curator)},
        ),
    ]


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_curator_gets_403(client: TestClient, w: W, idx: int) -> None:
    method, url, body = _calls(w)[idx]
    r = client.request(method, url, json=body, headers=_auth(w.curator))
    assert r.status_code == 403, r.text


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_scope_admin_succeeds(client: TestClient, w: W, idx: int) -> None:
    method, url, body = _calls(w)[idx]
    r = client.request(method, url, json=body, headers=_auth(w.admin))
    assert r.status_code == 200, r.text


def test_workflow_and_permission_paths_run_on_postgres(w: W) -> None:
    from app.core.deps import set_rls_context
    from app.crud.workflow_engine import WorkflowEngine
    from app.models import UserNew
    from app.services.scope_permissions import ScopePermissionService

    db = next(database.get_db())
    try:
        user = db.get(UserNew, w.admin)
        assert user is not None
        set_rls_context(db, user)
        # Both filter scope_memberships.role IN (...) on the scope_role enum
        assert ScopePermissionService.has_scope_access(
            db, user, w.scope, required_roles=["admin", "curator"]
        )
        reviewers = WorkflowEngine().get_eligible_peer_reviewers(db, scope_id=w.scope)
        assert {r["id"] if "id" in r else r.get("user_id") for r in reviewers}
    finally:
        db.close()
