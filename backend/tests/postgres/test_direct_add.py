"""Direct member add and the default workflow pair through the API as app_user (062, F6).

Platform and scope admins add an existing user as an accepted member in one step
(audited, notified); a curator cannot; nobody adds themselves; a pending invitation
still grants nothing; at most one workflow pair is the default and create_scope uses it;
a removed member cannot reactivate their own row, not even by moving it (066).
"""

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
    padmin: UUID = field(default_factory=uuid4)  # platform admin, not a member
    sadmin: UUID = field(default_factory=uuid4)  # scope admin
    cur: UUID = field(default_factory=uuid4)  # scope curator
    a: UUID = field(default_factory=uuid4)
    b: UUID = field(default_factory=uuid4)
    c: UUID = field(default_factory=uuid4)

    def ids(self) -> list[str]:
        return [
            str(u) for u in (self.padmin, self.sadmin, self.cur, self.a, self.b, self.c)
        ]


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.scope)[:8]
    with _owner() as conn, conn.cursor() as cur:
        for uid in x.ids():
            role = "admin" if uid == str(x.padmin) else "user"
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, 'u', %s)",
                (uid, f"{uid[:8]}-{tag}@da.org", get_password_hash("pw"), role),
            )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, 'DA', false, %s)",
            (str(x.scope), f"da-{x.scope}", str(x.sadmin)),
        )
        for uid, role in ((x.sadmin, "admin"), (x.cur, "curator")):
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, %s, %s, now())",
                (str(x.scope), str(uid), role, str(x.sadmin)),
            )
    yield x
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM scopes WHERE id = %s OR created_by = ANY(%s::uuid[])",
            (str(x.scope), x.ids()),
        )
        cur.execute("DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[])", (x.ids(),))
        cur.execute(
            "DELETE FROM notifications WHERE user_id = ANY(%s::uuid[])", (x.ids(),)
        )
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (x.ids(),))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _h(uid: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(uid)})}"}


def _add(client: TestClient, w: W, by: UUID, user: UUID, role: str = "curator"):
    return client.post(
        f"/api/v1/scopes/{w.scope}/members",
        json={"user_id": str(user), "role": role},
        headers=_h(by),
    )


def test_platform_and_scope_admin_add_accepted_members(
    client: TestClient, w: W
) -> None:
    for by, user, role in ((w.padmin, w.a, "reviewer"), (w.sadmin, w.b, "admin")):
        r = _add(client, w, by, user, role)
        assert r.status_code == 201, r.text
        assert r.json()["is_pending"] is False
        # the role takes effect at once: the new member reads the scope's members
        members = client.get(f"/api/v1/scopes/{w.scope}/members", headers=_h(user))
        assert members.status_code == 200, members.text
        notes = client.get("/api/v1/notifications/", headers=_h(user))
        assert "scope_membership_added" in notes.text
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT m.invitation_status, a.user_id FROM scope_memberships m "
            "JOIN audit_log a ON a.entity_id = m.id AND a.operation = 'DIRECT_ADD' "
            "WHERE m.scope_id = %s ORDER BY a.id",
            (str(w.scope),),
        )
        assert cur.fetchall() == [
            ("accepted", str(w.padmin)),
            ("accepted", str(w.sadmin)),
        ]


def test_curator_cannot_add_and_nobody_adds_themselves(
    client: TestClient, w: W
) -> None:
    assert _add(client, w, w.cur, w.a).status_code == 403
    assert _add(client, w, w.padmin, w.padmin, "admin").status_code == 403
    assert (
        client.get(f"/api/v1/scopes/{w.scope}/members", headers=_h(w.a)).status_code
        == 403
    )


def test_pending_invitation_still_grants_nothing(client: TestClient, w: W) -> None:
    r = client.post(
        f"/api/v1/scopes/{w.scope}/invitations",
        json={"user_id": str(w.c), "role": "curator"},
        headers=_h(w.sadmin),
    )
    assert r.status_code == 201, r.text
    assert r.json()["is_pending"] is True
    assert (
        client.get(f"/api/v1/scopes/{w.scope}/members", headers=_h(w.c)).status_code
        == 403
    )
    added = _add(client, w, w.sadmin, w.c, "reviewer")  # takes over the invitation
    assert added.status_code == 201, added.text
    assert added.json()["id"] == r.json()["id"]
    assert (
        client.get(f"/api/v1/scopes/{w.scope}/members", headers=_h(w.c)).status_code
        == 200
    )


def test_re_add_after_removal(client: TestClient, w: W) -> None:
    assert _add(client, w, w.sadmin, w.a).status_code == 201
    gone = client.delete(
        f"/api/v1/scopes/{w.scope}/members/{w.a}", headers=_h(w.sadmin)
    )
    assert gone.status_code == 204, gone.text
    assert (
        client.get(f"/api/v1/scopes/{w.scope}/members", headers=_h(w.a)).status_code
        == 403
    )
    again = _add(client, w, w.padmin, w.a, "viewer")
    assert again.status_code == 201, again.text
    assert again.json()["role"] == "viewer"
    assert (
        client.get(f"/api/v1/scopes/{w.scope}/members", headers=_h(w.a)).status_code
        == 200
    )


def test_exactly_one_default_pair_used_by_create_scope(
    client: TestClient, w: W
) -> None:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM workflow_pairs WHERE is_default")
        defaults = cur.fetchall()
        assert len(defaults) == 1
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cur.execute(
                "UPDATE workflow_pairs SET is_default = true WHERE NOT is_default "
                "AND id = (SELECT id FROM workflow_pairs WHERE NOT is_default LIMIT 1)"
            )
    pairs = client.get("/api/v1/schemas/workflow-pairs", headers=_h(w.cur)).json()
    assert [p["id"] for p in pairs if p["is_default"]] == [str(defaults[0][0])]
    r = client.post(
        "/api/v1/scopes/",
        json={"name": f"da2-{w.scope}", "display_name": "D", "description": "d"},
        headers=_h(w.cur),
    )
    assert r.status_code == 201, r.text
    assert r.json()["default_workflow_pair_id"] == str(defaults[0][0])


def _as_app_user(uid: UUID, sql: str, *args: str) -> None:
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        cur.execute("SELECT set_config('app.current_user_id', %s, true)", (str(uid),))
        cur.execute(sql, args)


def test_member_cannot_change_own_role_but_can_accept(client: TestClient, w: W) -> None:
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        _as_app_user(
            w.cur,
            "UPDATE scope_memberships SET role = 'admin' WHERE user_id = %s AND scope_id = %s",
            str(w.cur),
            str(w.scope),
        )
    r = client.post(
        f"/api/v1/scopes/{w.scope}/invitations",
        json={"user_id": str(w.c), "role": "viewer"},
        headers=_h(w.sadmin),
    )
    assert r.status_code == 201, r.text
    ok = client.post(
        f"/api/v1/scopes/{w.scope}/invitations/{r.json()['id']}/accept",
        headers=_h(w.c),
    )
    assert ok.status_code == 200, ok.text
    r = client.post(
        f"/api/v1/scopes/{w.scope}/invitations",
        json={"user_id": str(w.b), "role": "viewer"},
        headers=_h(w.sadmin),
    )
    no = client.post(f"/api/v1/invitations/{r.json()['id']}/decline", headers=_h(w.b))
    assert no.status_code == 204, no.text  # declining (is_active -> false) still works
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT role FROM scope_memberships WHERE user_id = %s AND scope_id = %s",
            (str(w.cur), str(w.scope)),
        )
        assert cur.fetchone() == ("curator",)


def test_removed_member_cannot_reactivate_own_row(client: TestClient, w: W) -> None:
    other = uuid4()  # a scope w.cur administers, so RLS alone would accept the move
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, 'DA2', false, %s)",
            (str(other), f"da-{other}", str(w.cur)),
        )
        cur.execute(
            "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
            "accepted_at) VALUES (%s, %s, 'admin', %s, now())",
            (str(other), str(w.cur), str(w.cur)),
        )
    gone = client.delete(
        f"/api/v1/scopes/{w.scope}/members/{w.cur}", headers=_h(w.sadmin)
    )
    assert gone.status_code == 204, gone.text
    for sql, args in (
        ("UPDATE scope_memberships SET is_active = true", ()),
        (
            "UPDATE scope_memberships SET is_active = true, scope_id = %s, user_id = %s",
            (str(other), str(w.a)),
        ),
    ):
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            _as_app_user(
                w.cur,
                sql + " WHERE user_id = %s AND scope_id = %s",
                *args,
                str(w.cur),
                str(w.scope),
            )
    assert (
        client.get(f"/api/v1/scopes/{w.scope}/members", headers=_h(w.cur)).status_code
        == 403
    )
