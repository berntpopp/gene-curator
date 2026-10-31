"""RLS matches the capability matrix (#284), as the API runs (app_user, real policies).

role_capabilities is seeded with DEFAULT_MATRIX; the SQL helpers answer like require();
a scope admin derives a methodology, publishes it, creates a workflow and allows it for their
own scope through the API and gets 403 for another scope; direct writes outside the matrix
are refused by RLS.
"""

import os
from collections.abc import Generator
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient

from app.core import capabilities as caps, database
from app.core.enums import ScopeRole
from app.core.security import create_access_token, get_password_hash
from app.main import app

pytestmark = pytest.mark.postgres

ROLES = ("viewer", "curator", "reviewer", "admin")


@dataclass
class W:
    scope: UUID = field(default_factory=uuid4)
    other: UUID = field(default_factory=uuid4)
    users: dict[str, UUID] = field(default_factory=dict)
    pre: str = ""
    cur: str = ""
    version: str = ""


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


def _scalar(sql: str, *params: object) -> object:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return row[0] if row else None


def _as(user: UUID, sql: str, *params: object) -> object:
    """Run one statement as app_user with the API's RLS context."""
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.current_user_id', %s, true)", (str(user),)
            )
            cur.execute(sql, params)
            return cur.fetchone()[0] if cur.description else cur.rowcount
    finally:
        conn.close()


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.scope)[:8]
    names = [*ROLES, "other_admin", "platform"]
    x.users = {name: uuid4() for name in names}
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT precuration_schema_id, curation_schema_id FROM workflow_pairs "
            "WHERE is_active AND owner_scope_id IS NULL LIMIT 1"
        )
        pre, cur_id = cur.fetchone()
        x.pre, x.cur = str(pre), str(cur_id)
        cur.execute(
            "SELECT id FROM methodology_versions WHERE schema_id = %s "
            "ORDER BY version DESC LIMIT 1",
            (x.cur,),
        )
        x.version = str(cur.fetchone()[0])
        for name, uid in x.users.items():
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    str(uid),
                    f"{name}-{tag}@caps.org",
                    get_password_hash("pw"),
                    name,
                    "admin" if name == "platform" else "user",
                ),
            )
        for sid in (x.scope, x.other):
            cur.execute(
                "INSERT INTO scopes (id, name, display_name, is_public) "
                "VALUES (%s, %s, 'Caps', false)",
                (str(sid), f"caps-{sid}"),
            )
        members = [(x.scope, x.users[r], r) for r in ROLES]
        members.append((x.other, x.users["other_admin"], "admin"))
        for sid, uid, role in members:
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, accepted_at) "
                "VALUES (%s, %s, %s, now())",
                (str(sid), str(uid), role),
            )
    yield x
    users = [str(u) for u in x.users.values()]
    scopes = [str(x.scope), str(x.other)]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM workflow_pairs WHERE owner_scope_id = ANY(%s::uuid[])",
            (scopes,),
        )
        cur.execute(
            "DELETE FROM curation_schemas WHERE owner_scope_id = ANY(%s::uuid[])",
            (scopes,),
        )
        cur.execute("DELETE FROM scopes WHERE id = ANY(%s::uuid[])", (scopes,))
        cur.execute("DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[])", (users,))
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (users,))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _h(uid: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(uid)})}"}


def test_seed_is_the_default_matrix() -> None:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("SELECT role::text, capability FROM role_capabilities")
        rows = set(cur.fetchall())
    assert rows == {
        (role.value, cap) for role, held in caps.DEFAULT_MATRIX.items() for cap in held
    }


@pytest.mark.parametrize("role", ROLES)
def test_rls_helpers_answer_like_require(w: W, role: str) -> None:
    uid = w.users[role]
    held = caps.DEFAULT_MATRIX[ScopeRole(role)]
    every = {c for granted in caps.DEFAULT_MATRIX.values() for c in granted}
    for cap in every:
        sql = "SELECT has_scope_capability(%s, %s)"
        assert _as(uid, sql, str(w.scope), cap) is (cap in held), cap
        assert _as(uid, sql, str(w.other), cap) is False
    assert _as(uid, "SELECT can_curate_in_scope(%s)", str(w.scope)) is (
        caps.EDIT in held
    )
    assert _as(uid, "SELECT can_review_in_scope(%s)", str(w.scope)) is (
        caps.REVIEW in held
    )
    assert _as(uid, "SELECT is_scope_admin(%s)", str(w.scope)) is (
        caps.MANAGE_MEMBERS in held
    )


def test_platform_admin_configures_globally_but_reviews_only_by_membership(
    w: W,
) -> None:
    """D1: no review capability without a membership; global configuration is theirs."""
    root = w.users["platform"]
    sql = "SELECT has_scope_capability(%s, %s)"
    assert _as(root, sql, str(w.scope), caps.REVIEW) is False
    assert _as(root, "SELECT can_review_in_scope(%s)", str(w.scope)) is False
    config = "SELECT can_manage_config(NULL, %s)"
    assert _as(root, config, caps.METHODOLOGY_EDIT) is True
    assert _as(w.users["admin"], config, caps.METHODOLOGY_EDIT) is False


def test_scope_admin_configures_own_scope_only(client: TestClient, w: W) -> None:
    admin, other = _h(w.users["admin"]), _h(w.users["other_admin"])
    derive = f"/api/v1/schemas/curation-schemas/{w.cur}/versions/{w.version}/derive"
    body = {"name": f"own-{w.scope}", "version": "1", "owner_scope_id": str(w.scope)}
    assert client.post(derive, json=body, headers=other).status_code == 403
    assert (
        client.post(derive, json=body, headers=_h(w.users["curator"])).status_code
        == 403
    )
    derived = client.post(derive, json=body, headers=admin)
    assert derived.status_code == 201, derived.text
    sid = derived.json()["id"]
    assert derived.json()["owner_scope_id"] == str(w.scope)
    # v1 (published by the 042 trigger) belongs to the scope too (082 trigger)
    owner = "SELECT owner_scope_id::text FROM methodology_versions WHERE schema_id = %s"
    assert _scalar(owner, sid) == str(w.scope)

    publish = f"/api/v1/schemas/curation-schemas/{sid}/versions"
    assert client.post(publish, headers=other).status_code == 403
    published = client.post(publish, headers=admin)
    assert published.status_code == 201, published.text
    assert published.json()["owner_scope_id"] == str(w.scope)

    pair = {
        "name": f"wf-{w.scope}",
        "version": "1",
        "precuration_schema_id": w.pre,
        "curation_schema_id": w.cur,
        "owner_scope_id": str(w.scope),
    }
    pairs = "/api/v1/schemas/workflow-pairs"
    assert client.post(pairs, json=pair, headers=other).status_code == 403
    created = client.post(pairs, json=pair, headers=admin)
    assert created.status_code == 200, created.text
    pid = created.json()["id"]

    allow = f"/api/v1/scopes/{w.scope}/workflow-pairs"
    ids = {"workflow_pair_ids": [pid]}
    assert client.put(allow, json=ids, headers=other).status_code == 403
    allowed = client.put(allow, json=ids, headers=admin)
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["allowed_workflow_pair_ids"] == [pid]
    # MUI-01: the scope read as app_user keeps them (get_with_statistics dropped them)
    read = client.get(f"/api/v1/scopes/{w.scope}", headers=admin)
    assert read.status_code == 200, read.text
    assert read.json()["allowed_workflow_pair_ids"] == [pid]
    # every one of these is audited with actor, capability and scope
    audited = (
        "SELECT array_agg(operation ORDER BY id) FROM audit_log "
        "WHERE user_id = %s AND scope_id = %s"
    )
    assert _scalar(audited, str(w.users["admin"]), str(w.scope)) == [
        caps.METHODOLOGY_DERIVE,
        caps.METHODOLOGY_PUBLISH,
        caps.WORKFLOW_CREATE,
        caps.WORKFLOW_ASSIGN,
    ]


def test_rls_refuses_configuration_writes_outside_the_matrix(w: W) -> None:
    insert = (
        "INSERT INTO curation_schemas (name, version, schema_type, field_definitions, "
        "validation_rules, workflow_states, ui_configuration, schema_hash, "
        "owner_scope_id) SELECT %s, '1', schema_type, field_definitions, "
        "validation_rules, workflow_states, ui_configuration, schema_hash, %s "
        "FROM curation_schemas WHERE id = %s RETURNING id"
    )
    for name, owner in (("curator", w.scope), ("other_admin", w.scope)):
        with pytest.raises(psycopg2.Error, match="row-level security"):
            _as(w.users[name], insert, f"x-{uuid4()}", str(owner), w.cur)
    # a scope admin may not create a global template (owner NULL)
    with pytest.raises(psycopg2.Error, match="row-level security"):
        _as(w.users["admin"], insert, f"x-{uuid4()}", None, w.cur)
    own = _as(w.users["admin"], insert, f"own-{uuid4()}", str(w.scope), w.cur)
    # another scope's admin cannot touch it; global templates are not the scope admin's
    update = "UPDATE curation_schemas SET description = 'x' WHERE id = %s"
    assert _as(w.users["other_admin"], update, str(own)) == 0
    assert _as(w.users["admin"], update, w.cur) == 0
    assert _as(w.users["admin"], update, str(own)) == 1
    # nor turn its own methodology into a global template
    with pytest.raises(psycopg2.Error, match="row-level security"):
        _as(
            w.users["admin"],
            "UPDATE curation_schemas SET owner_scope_id = NULL WHERE id = %s",
            str(own),
        )

    allow = (
        "INSERT INTO scope_workflow_pairs (scope_id, workflow_pair_id) SELECT %s, id "
    )
    allow += "FROM workflow_pairs WHERE curation_schema_id = %s LIMIT 1"
    for name in ("curator", "other_admin"):
        with pytest.raises(psycopg2.Error, match="row-level security"):
            _as(w.users[name], allow, str(w.scope), w.cur)
    assert _as(w.users["admin"], allow, str(w.scope), w.cur) == 1
