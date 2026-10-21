"""Migration 037 under real RLS (app_user): review_item_comments policies and the diff (#279).

Only accepted, active memberships count. There is deliberately no platform-admin bypass.
Data is committed by the owner role; every assertion runs as app_user.
"""

import json
import os
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core import database
from app.core.security import create_access_token, get_password_hash
from app.main import app

pytestmark = pytest.mark.postgres

MIGRATION = Path(__file__).parents[3] / "database/sql/037_review_item_comments.sql"


@dataclass
class World:
    scope: UUID
    scope_off: UUID
    curation: UUID
    curation_off: UUID
    curator: UUID  # created the curation
    other_curator: UUID
    reviewer: UUID
    scope_admin: UUID
    viewer: UUID
    pending: UUID  # reviewer, invitation not accepted
    outsider: UUID
    platform_admin: UUID  # not a member of the scope
    comment: UUID  # authored by reviewer


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def world() -> Generator[World, None, None]:
    ids = {
        name: uuid4()
        for name in [
            "scope",
            "scope_off",
            "curation",
            "curation_off",
            "curator",
            "other_curator",
            "reviewer",
            "scope_admin",
            "viewer",
            "pending",
            "outsider",
            "platform_admin",
            "comment",
            "gene",
        ]
    }
    tag = uuid4().hex[:6]
    w = World(**{k: v for k, v in ids.items() if k != "gene"})
    with _owner() as conn, conn.cursor() as cur:
        for name in [
            "curator",
            "other_curator",
            "reviewer",
            "scope_admin",
            "viewer",
            "pending",
            "outsider",
            "platform_admin",
        ]:
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    str(ids[name]),
                    f"{name}-{tag}@rls037.org",
                    get_password_hash("pw"),
                    name,
                    "admin" if name == "platform_admin" else "user",
                ),
            )
        for key, active in (("scope", True), ("scope_off", False)):
            cur.execute(
                "INSERT INTO scopes (id, name, display_name, is_public, is_active, created_by) "
                "VALUES (%s, %s, %s, false, %s, %s)",
                (
                    str(ids[key]),
                    f"rls037-{ids[key]}",
                    key,
                    active,
                    str(ids["scope_admin"]),
                ),
            )
        members = (
            ("curator", "curator", True),
            ("other_curator", "curator", True),
            ("reviewer", "reviewer", True),
            ("scope_admin", "admin", True),
            ("viewer", "viewer", True),
            ("pending", "reviewer", False),
        )
        for scope_key in ("scope", "scope_off"):
            for name, role, accepted in members:
                cur.execute(
                    "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                    "accepted_at) VALUES (%s, %s, %s, %s, CASE WHEN %s THEN now() END)",
                    (
                        str(ids[scope_key]),
                        str(ids[name]),
                        role,
                        str(ids["scope_admin"]),
                        accepted,
                    ),
                )
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (%s, %s, %s, %s)",
            (
                str(ids["gene"]),
                f"HGNC:9{int(tag, 16)}",
                f"ZR{tag.upper()}",
                uuid4().hex * 2,
            ),
        )
        cur.execute("SELECT id FROM workflow_pairs LIMIT 1")
        pair = cur.fetchone()[0]
        for key, scope_key in (("curation", "scope"), ("curation_off", "scope_off")):
            cur.execute(
                "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, created_by, "
                "evidence_data) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    str(ids[key]),
                    str(ids["gene"]),
                    str(ids[scope_key]),
                    str(pair),
                    str(ids["curator"]),
                    json.dumps({"score": 1}),
                ),
            )
        cur.execute(
            "INSERT INTO review_item_comments (id, curation_id, item_path, body, author_id) "
            "VALUES (%s, %s, 'score', 'Why 1?', %s)",
            (str(ids["comment"]), str(ids["curation"]), str(ids["reviewer"])),
        )
    yield w
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM review_item_comments WHERE curation_id = ANY(%s::uuid[])",
            ([str(w.curation), str(w.curation_off)],),
        )
        cur.execute(
            "DELETE FROM curations WHERE id = ANY(%s::uuid[])",
            ([str(w.curation), str(w.curation_off)],),
        )
        cur.execute("DELETE FROM genes WHERE id = %s", (str(ids["gene"]),))
        cur.execute(
            "DELETE FROM scopes WHERE id = ANY(%s::uuid[])",
            ([str(w.scope), str(w.scope_off)],),
        )
        users = [
            str(ids[n])
            for n in [
                "curator",
                "other_curator",
                "reviewer",
                "scope_admin",
                "viewer",
                "pending",
                "outsider",
                "platform_admin",
            ]
        ]
        cur.execute(
            "DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[]) OR entity_id = ANY(%s::uuid[])",
            (users, [str(w.curation), str(w.curation_off)]),
        )
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (users,))


def as_user(db: Session, user: UUID) -> Session:
    db.execute(
        text("SELECT set_config('app.current_user_id', :u, true)"), {"u": str(user)}
    )
    return db


def _visible(db: Session, user: UUID, curation: UUID) -> list[str]:
    as_user(db, user)
    rows = db.execute(
        text("SELECT id::text FROM review_item_comments WHERE curation_id = :c"),
        {"c": str(curation)},
    )
    return [r[0] for r in rows]


def _insert(
    db: Session, user: UUID, curation: UUID, author: UUID | None = None
) -> bool:
    """True if the insert is allowed; the savepoint keeps the session usable after a denial."""
    as_user(db, user)
    try:
        with db.begin_nested():
            db.execute(
                text(
                    "INSERT INTO review_item_comments (curation_id, item_path, body, author_id) "
                    "VALUES (:c, 'score', 'x', :a)"
                ),
                {"c": str(curation), "a": str(author or user)},
            )
        return True
    except DBAPIError:
        return False


@pytest.mark.parametrize(
    ("who", "sees"),
    [
        ("curator", True),
        ("other_curator", True),
        ("reviewer", True),
        ("scope_admin", True),
        ("viewer", True),
        ("pending", False),
        ("outsider", False),
        ("platform_admin", False),  # no admin bypass
    ],
)
def test_select_is_for_accepted_members_only(
    world: World, db: Session, who: str, sees: bool
) -> None:
    got = _visible(db, getattr(world, who), world.curation)
    assert (str(world.comment) in got) is sees


@pytest.mark.parametrize(
    ("who", "allowed"),
    [
        ("reviewer", True),
        ("scope_admin", True),
        ("curator", True),  # created the curation
        ("other_curator", False),
        ("viewer", False),
        ("pending", False),
        ("outsider", False),
        ("platform_admin", False),
    ],
)
def test_insert_by_reviewers_admins_and_the_curations_curator(
    world: World, db: Session, who: str, allowed: bool
) -> None:
    assert _insert(db, getattr(world, who), world.curation) is allowed


def test_insert_cannot_claim_another_author(world: World, db: Session) -> None:
    assert (
        _insert(db, world.reviewer, world.curation, author=world.scope_admin) is False
    )


def test_insert_into_an_inactive_scope_is_denied(world: World, db: Session) -> None:
    assert _insert(db, world.reviewer, world.curation_off) is False
    assert _visible(db, world.reviewer, world.curation_off) == []


def _update(db: Session, user: UUID, comment: UUID, sets: str, **params: str) -> int:
    as_user(db, user)
    try:
        with db.begin_nested():
            result = db.execute(
                text(f"UPDATE review_item_comments SET {sets} WHERE id = :id"),
                {"id": str(comment), **params},
            )
        return result.rowcount
    except DBAPIError:
        return -1


def test_author_edits_text_but_not_authorship(world: World, db: Session) -> None:
    assert _update(db, world.reviewer, world.comment, "body = 'Better?'") == 1
    assert (
        _update(
            db, world.reviewer, world.comment, "author_id = :a", a=str(world.curator)
        )
        == -1
    )
    assert _update(db, world.reviewer, world.comment, "item_path = 'other'") == -1


def test_non_author_cannot_change_the_text(world: World, db: Session) -> None:
    for who in (world.curator, world.scope_admin, world.other_curator):
        assert _update(db, who, world.comment, "body = 'hijack'") in (0, -1)
    as_user(db, world.reviewer)
    body = db.execute(
        text("SELECT body FROM review_item_comments WHERE id = :i"),
        {"i": str(world.comment)},
    ).scalar_one()
    assert body == "Why 1?"


@pytest.mark.parametrize(
    ("who", "allowed"),
    [
        ("curator", True),
        ("reviewer", True),
        ("scope_admin", True),
        ("other_curator", False),
        ("viewer", False),
        ("pending", False),
        ("platform_admin", False),
    ],
)
def test_resolve_by_the_curator_or_a_reviewer(
    world: World, db: Session, who: str, allowed: bool
) -> None:
    rows = _update(db, getattr(world, who), world.comment, "status = 'resolved'")
    assert (rows == 1) is allowed


def test_status_is_open_or_resolved_only(world: World, db: Session) -> None:
    assert _update(db, world.reviewer, world.comment, "status = 'done'") == -1


def test_nobody_deletes(world: World, db: Session) -> None:
    for who in (world.reviewer, world.scope_admin, world.curator):
        as_user(db, who)
        with db.begin_nested():
            n = db.execute(
                text("DELETE FROM review_item_comments WHERE id = :i"),
                {"i": str(world.comment)},
            ).rowcount
        assert n == 0


def test_app_user_cannot_see_comments_without_a_user_context(
    world: World, db: Session
) -> None:
    db.execute(text("SELECT set_config('app.current_user_id', '', true)"))
    assert (
        db.execute(text("SELECT count(*) FROM review_item_comments")).scalar_one() == 0
    )


def test_migration_is_idempotent_and_self_recording() -> None:
    sql = MIGRATION.read_text()
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(sql)
        cur.execute(sql)
        cur.execute(
            "SELECT count(*) FROM schema_migrations WHERE filename = '037_review_item_comments.sql'"
        )
        assert cur.fetchone()[0] == 1
        cur.execute(
            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
            "WHERE relname = 'review_item_comments'"
        )
        assert cur.fetchone() == (True, True)
        cur.execute(
            "SELECT cmd FROM pg_policies WHERE tablename = 'review_item_comments' ORDER BY cmd"
        )
        assert {r[0] for r in cur.fetchall()} == {"SELECT", "INSERT", "UPDATE"}


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as test_client:
        yield test_client
    database.engine.dispose()


def _auth(user: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(user)})}"}


def test_api_comment_round_trip_under_rls(client: TestClient, world: World) -> None:
    url = f"/api/v1/curations/{world.curation}/review-comments"
    made = client.post(
        url,
        json={"item_path": "score", "body": "Source?"},
        headers=_auth(world.scope_admin),
    )
    assert made.status_code == 201, made.text
    listed = client.get(url, headers=_auth(world.viewer)).json()
    assert {c["body"] for c in listed} == {"Why 1?", "Source?"}
    # RLS hides the curation itself from a pending member, so this is a 404, not a 403
    assert client.get(url, headers=_auth(world.pending)).status_code == 404
    # a platform admin passes the capability check but RLS gives no rows and no insert
    assert client.get(url, headers=_auth(world.platform_admin)).json() == []
    denied = client.post(
        url,
        json={"item_path": "score", "body": "x"},
        headers=_auth(world.platform_admin),
    )
    assert denied.status_code == 403
    resolved = client.patch(
        f"{url}/{world.comment}",
        json={"status": "resolved"},
        headers=_auth(world.curator),
    )
    assert resolved.status_code == 200, resolved.text


def test_diff_after_real_submit_and_edit_transitions(
    client: TestClient, world: World
) -> None:
    """Submit then edit through plain UPDATEs; the audit trigger writes the snapshot."""
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE curations SET status = 'submitted', evidence_data = %s WHERE id = %s",
            (json.dumps({"score": 2, "keep": 1}), str(world.curation)),
        )
        cur.execute(
            "UPDATE curations SET evidence_data = %s WHERE id = %s",
            (json.dumps({"score": 5, "keep": 1, "extra": "y"}), str(world.curation)),
        )
    body = client.get(
        f"/api/v1/curations/{world.curation}/diff", headers=_auth(world.reviewer)
    ).json()
    got = {i["path"]: i for i in body["items"]}
    assert got["score"]["before"] == 2 and got["score"]["after"] == 5
    assert got["extra"]["change"] == "added"
    assert "keep" not in got
