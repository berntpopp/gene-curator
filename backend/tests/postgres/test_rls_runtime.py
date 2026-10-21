"""The API as it runs in production: connected as app_user, isolated by RLS (#156).

DATABASE_URL is app_user (no superuser, no BYPASSRLS); seed data is committed through
OWNER_DATABASE_URL and removed afterwards, because every request opens its own session.
"""

import os
from collections.abc import Generator
from dataclasses import dataclass
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core import database
from app.core.deps import set_rls_context
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import NotificationNew, Scope, ScopeMembership, UserNew
from app.models.models import NotificationType

pytestmark = pytest.mark.postgres


@dataclass
class World:
    alice: UUID  # viewer in scope A
    bob: UUID  # curator in scope B
    carol: UUID  # pending invitation to scope A
    scope_a: UUID
    scope_b: UUID


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def world() -> Generator[World, None, None]:
    w = World(uuid4(), uuid4(), uuid4(), uuid4(), uuid4())
    tag = str(w.scope_a)[:8]
    with _owner() as conn, conn.cursor() as cur:
        for uid, name in ((w.alice, "alice"), (w.bob, "bob"), (w.carol, "carol")):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, 'user')",
                (str(uid), f"{name}-{tag}@rls-test.org", get_password_hash("pw"), name),
            )
        for sid, owner in ((w.scope_a, w.alice), (w.scope_b, w.bob)):
            cur.execute(
                "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
                "VALUES (%s, %s, %s, false, %s)",
                (str(sid), f"rls-{sid}", f"RLS {sid}", str(owner)),
            )
        for sid, uid, role, accepted in (
            (w.scope_a, w.alice, "viewer", True),
            (w.scope_b, w.bob, "curator", True),
            (w.scope_a, w.carol, "viewer", False),
        ):
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, %s, %s, CASE WHEN %s THEN now() END)",
                (str(sid), str(uid), role, str(w.bob), accepted),
            )
    yield w
    with _owner() as conn, conn.cursor() as cur:
        users = [str(w.alice), str(w.bob), str(w.carol)]
        cur.execute(
            "DELETE FROM scopes WHERE id IN (%s, %s)", (str(w.scope_a), str(w.scope_b))
        )
        cur.execute("DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[])", (users,))
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (users,))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    # Fresh pool, so the leak test knows which connection is reused.
    database.engine.dispose()
    with TestClient(app) as test_client:
        yield test_client
    database.engine.dispose()


def _auth(user_id: UUID) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(data={'sub': str(user_id)})}"
    }


def test_runtime_role_is_not_privileged() -> None:
    with database.engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT current_user, rolsuper, rolbypassrls, rolcreaterole, "
                "has_schema_privilege('public', 'CREATE'), "
                "has_table_privilege('schema_migrations', 'INSERT'), "
                "has_table_privilege('scopes', 'TRUNCATE') "
                "FROM pg_roles WHERE rolname = current_user"
            )
        ).one()
    assert tuple(row) == ("app_user", False, False, False, False, False, False)


def test_member_sees_only_own_scope_via_api(client: TestClient, world: World) -> None:
    listed = client.get("/api/v1/scopes/", headers=_auth(world.alice))
    assert listed.status_code == 200
    ids = {item["id"] for item in listed.json()}
    assert str(world.scope_a) in ids
    assert str(world.scope_b) not in ids
    assert (
        client.get(
            f"/api/v1/scopes/{world.scope_a}", headers=_auth(world.alice)
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/scopes/{world.scope_b}", headers=_auth(world.alice)
        ).status_code
        == 404
    )


def test_rls_alone_isolates_scopes_and_views(world: World) -> None:
    """No Python permission checks here: only the database decides."""
    with Session(database.engine) as db:
        set_rls_context(db, db.get_one(UserNew, world.alice))
        scopes = set(
            db.scalars(
                select(Scope.id).where(Scope.id.in_([world.scope_a, world.scope_b]))
            )
        )
        assert scopes == {world.scope_a}
        assert world.scope_b not in set(db.scalars(select(ScopeMembership.scope_id)))
        stats = (
            db.execute(text("SELECT scope_id FROM scope_statistics")).scalars().all()
        )
        assert world.scope_b not in stats
        assert world.scope_a in stats
        db.commit()  # context survives commit: the next transaction re-applies it
        assert (
            db.scalar(select(Scope.id).where(Scope.id == world.scope_a))
            == world.scope_a
        )


def test_pending_invitation_grants_nothing(client: TestClient, world: World) -> None:
    carol = _auth(world.carol)
    invitations = client.get("/api/v1/me/invitations", headers=carol).json()
    assert [i["scope_id"] for i in invitations["invitations"]] == [str(world.scope_a)]
    assert invitations["invitations"][0]["scope_name"] == f"rls-{world.scope_a}"
    assert client.get("/api/v1/scopes/", headers=carol).json() == []
    assert (
        client.get(f"/api/v1/scopes/{world.scope_a}", headers=carol).status_code == 404
    )
    assert client.get(
        f"/api/v1/scopes/{world.scope_a}/members", headers=carol
    ).status_code in (403, 404)
    with Session(database.engine) as db:
        set_rls_context(db, db.get_one(UserNew, world.carol))
        # Only the invitation itself; no other member, no membership rights.
        memberships = db.scalars(
            select(ScopeMembership.user_id).where(
                ScopeMembership.scope_id == world.scope_a
            )
        )
        assert list(memberships) == [world.carol]
        assert (
            db.scalar(text("SELECT is_scope_member(:s)"), {"s": world.scope_a}) is False
        )


def test_no_rls_context_leaks_to_the_next_request(
    client: TestClient, world: World
) -> None:
    assert client.get("/api/v1/scopes/", headers=_auth(world.alice)).status_code == 200
    assert database.engine.pool.checkedin() == 1  # the next checkout reuses it
    with database.engine.connect() as conn:
        assert conn.execute(
            text("SELECT current_setting('app.current_user_id', true)")
        ).scalar() in ("", None)
        assert (
            conn.execute(
                text("SELECT count(*) FROM scopes WHERE id = :a"), {"a": world.scope_a}
            ).scalar()
            == 0
        )
    # Anonymous public endpoint on the same pooled connection still works and sees no private data.
    catalogue = client.get(f"/api/v1/gene-catalogue/?scope_id={world.scope_a}")
    assert catalogue.status_code == 200
    assert catalogue.json()["total"] == 0


def test_endpoints_without_explicit_context_still_see_own_rows(
    client: TestClient, world: World
) -> None:
    """notifications.py never calls set_rls_context; the auth dependency does it centrally."""
    with Session(database.engine) as db:
        # A workflow transition by bob notifies alice: insert for another user.
        set_rls_context(db, db.get_one(UserNew, world.bob))
        db.add(
            NotificationNew(
                user_id=world.alice,
                type=NotificationType.REVIEW_ASSIGNED,
                title="t",
                message="m",
            )
        )
        db.commit()
    alice = client.get("/api/v1/notifications/", headers=_auth(world.alice)).json()
    assert alice["total"] == 1
    assert (
        client.get("/api/v1/notifications/", headers=_auth(world.bob)).json()["total"]
        == 0
    )


def test_unauthenticated_endpoints_work_as_app_user(
    client: TestClient, world: World
) -> None:
    assert client.get("/api/v1/health/").status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"alice-{str(world.scope_a)[:8]}@rls-test.org",
            "password": "pw",
        },
    )
    assert login.status_code == 200, login.text


def test_score_backfill_sees_every_curation_as_app_user() -> None:
    from app.services.recompute_scores import recompute_all_scores

    with _owner() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM curations")
        (total,) = cur.fetchone()
    with Session(database.engine) as db:
        assert recompute_all_scores(db) == total
