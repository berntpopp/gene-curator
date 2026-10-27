"""Curation policy hardening under real RLS (app_user); data is committed by the owner role.

#376: in a public scope, non-members see only ACTIVE curations at the database level, so an
endpoint relying on RLS alone cannot leak work in progress; the same holds for precurations
(only those behind a visible active curation) and for deactivated public scopes.
#394: a reviewer archives an active curation only while the scope is active.
"""

import os
from collections.abc import Generator
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import database
from app.core.security import create_access_token, get_password_hash
from app.main import app

pytestmark = pytest.mark.postgres


@dataclass
class W:
    scope: UUID = field(default_factory=uuid4)  # public
    curator: UUID = field(default_factory=uuid4)  # member, author
    viewer: UUID = field(default_factory=uuid4)  # member
    reviewer: UUID = field(default_factory=uuid4)  # member
    outsider: UUID = field(default_factory=uuid4)  # not a member
    gene: UUID = field(default_factory=uuid4)
    draft: UUID = field(default_factory=uuid4)
    active: UUID = field(default_factory=uuid4)
    pre_open: UUID = field(default_factory=uuid4)  # precuration with no active curation
    pre_done: UUID = field(default_factory=uuid4)  # precuration of the active curation


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.scope)[:8]
    users = [x.curator, x.viewer, x.reviewer, x.outsider]
    with _owner() as conn, conn.cursor() as cur:
        for uid in users:
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, 'u', 'user')",
                (str(uid), f"{uid}@sel376.org", get_password_hash("pw")),
            )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, 'Pub', true, %s)",
            (str(x.scope), f"sel-{x.scope}", str(x.curator)),
        )
        for uid, role in (
            (x.curator, "curator"),
            (x.viewer, "viewer"),
            (x.reviewer, "reviewer"),
        ):
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, %s, %s, now())",
                (str(x.scope), str(uid), role, str(x.curator)),
            )
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (%s, %s, %s, %s)",
            (str(x.gene), f"HGNC:{x.gene.int % 10**9}", f"SEL{tag}", x.gene.hex * 2),
        )
        cur.execute(
            "SELECT id, precuration_schema_id FROM workflow_pairs WHERE is_active LIMIT 1"
        )
        pair, schema = cur.fetchone()
        for pid, status in ((x.pre_open, "draft"), (x.pre_done, "approved")):
            cur.execute(
                "INSERT INTO precurations (id, gene_id, scope_id, precuration_schema_id, "
                "status, created_by, evidence_data) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    str(pid),
                    str(x.gene),
                    str(x.scope),
                    str(schema),
                    status,
                    str(x.curator),
                    f'{{"p": "{status}"}}',
                ),
            )
        for cid, status in ((x.draft, "draft"), (x.active, "active")):
            cur.execute(
                "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, status, "
                "workflow_stage, is_draft, created_by, evidence_data, precuration_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    str(cid),
                    str(x.gene),
                    str(x.scope),
                    str(pair),
                    status,
                    "active" if status == "active" else "curation",
                    status == "draft",
                    str(x.curator),
                    f'{{"status": "{status}"}}',  # distinct record_hash
                    str(x.pre_done) if status == "active" else None,
                ),
            )
    yield x
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(x.scope),))
        cur.execute("DELETE FROM genes WHERE id = %s", (str(x.gene),))
        cur.execute(
            "DELETE FROM audit_log WHERE scope_id = %s OR user_id = ANY(%s::uuid[])",
            (str(x.scope), [str(u) for u in users]),
        )
        cur.execute(
            "DELETE FROM users WHERE id = ANY(%s::uuid[])", ([str(u) for u in users],)
        )


def _seen(db: Session, user: UUID | None, w: W) -> set[UUID]:
    db.execute(
        text("SELECT set_config('app.current_user_id', :u, true)"),
        {"u": str(user) if user else ""},
    )
    rows = db.execute(
        text("SELECT id FROM curations WHERE scope_id = :s"), {"s": str(w.scope)}
    )
    return {r[0] for r in rows}


@pytest.mark.parametrize(
    ("who", "sees_draft"),
    [("curator", True), ("viewer", True), ("outsider", False), (None, False)],
)
def test_non_members_see_only_active_curations_of_a_public_scope(
    db: Session, w: W, who: str | None, sees_draft: bool
) -> None:
    seen = _seen(db, getattr(w, who) if who else None, w)
    assert w.active in seen
    assert (w.draft in seen) is sees_draft


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _h(uid: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(uid)})}"}


def test_api_outsider_cannot_read_a_draft_of_a_public_scope(
    client: TestClient, w: W
) -> None:
    assert client.get(
        f"/api/v1/curations/{w.draft}", headers=_h(w.outsider)
    ).status_code in (
        403,
        404,
    )
    member = client.get(f"/api/v1/curations/{w.draft}", headers=_h(w.viewer))
    assert member.status_code == 200, member.text


@pytest.mark.parametrize(("scope_active", "archived"), [(True, 1), (False, 0)])
def test_reviewer_archives_only_in_an_active_scope(
    w: W, db: Session, scope_active: bool, archived: int
) -> None:
    """#394: the archive policy needs an active scope, like the other reviewer policies."""
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE scopes SET is_active = %s WHERE id = %s",
            (scope_active, str(w.scope)),
        )
    db.execute(
        text("SELECT set_config('app.current_user_id', :u, true)"),
        {"u": str(w.reviewer)},
    )
    n = db.execute(
        text("UPDATE curations SET status = 'archived' WHERE id = :i"),
        {"i": str(w.active)},
    ).rowcount
    assert n == archived


def _visible_precurations(db: Session, user: UUID | None, w: W) -> set[UUID]:
    db.execute(
        text("SELECT set_config('app.current_user_id', :u, true)"),
        {"u": str(user) if user else ""},
    )
    rows = db.execute(
        text("SELECT id FROM precurations WHERE scope_id = :s"), {"s": str(w.scope)}
    )
    return {r[0] for r in rows}


@pytest.mark.parametrize(
    ("who", "sees_open"), [("viewer", True), ("outsider", False), (None, False)]
)
def test_outsiders_see_only_precurations_behind_an_active_curation(
    db: Session, w: W, who: str | None, sees_open: bool
) -> None:
    seen = _visible_precurations(db, getattr(w, who) if who else None, w)
    assert w.pre_done in seen
    assert (w.pre_open in seen) is sees_open


def test_api_progress_without_scope_hides_open_work_from_outsiders(
    client: TestClient, w: W
) -> None:
    r = client.get(f"/api/v1/genes/{w.gene}/progress", headers=_h(w.outsider))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["precuration_status_counts"] == {"approved": 1}
    assert body["curation_status_counts"] == {"active": 1}


def test_outsiders_see_nothing_of_a_deactivated_public_scope(w: W, db: Session) -> None:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE scopes SET is_active = false WHERE id = %s", (str(w.scope),)
        )
    assert _seen(db, w.outsider, w) == set()
    assert _visible_precurations(db, w.outsider, w) == set()
    assert w.active in _seen(db, w.viewer, w)


@pytest.mark.parametrize("who", ["curator", "reviewer"])
def test_nobody_updates_curations_of_an_inactive_scope(
    w: W, db: Session, who: str
) -> None:
    """#394: the permissive creator/curator/admin update policy is no way around it either."""
    for active, expected in ((True, 1), (False, 0)):
        with _owner() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE scopes SET is_active = %s WHERE id = %s", (active, str(w.scope))
            )
        db.execute(
            text("SELECT set_config('app.current_user_id', :u, true)"),
            {"u": str(getattr(w, who))},
        )
        savepoint = db.begin_nested()
        n = db.execute(
            text("UPDATE curations SET status = 'archived' WHERE id = :i"),
            {"i": str(w.active)},
        ).rowcount
        savepoint.rollback()  # keep the row active, and release its lock, for the next round
        assert n == expected, (who, active)


def test_api_admin_delete_in_inactive_scope_is_409_not_500(
    client: TestClient, w: W
) -> None:
    """#483: the 054 policy made the archive UPDATE match no row (StaleDataError -> 500)."""
    admin = uuid4()
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (id, email, hashed_password, name, role) "
            "VALUES (%s, %s, %s, 'a', 'admin')",
            (str(admin), f"{admin}@sel483.org", get_password_hash("pw")),
        )
        cur.execute(
            "UPDATE scopes SET is_active = false WHERE id = %s", (str(w.scope),)
        )
    try:
        r = client.delete(f"/api/v1/curations/{w.draft}", headers=_h(admin))
        assert r.status_code == 409, r.text
        r = client.post(
            f"/api/v1/workflow/curation/{w.draft}/transition",
            headers=_h(w.curator),
            json={"target_stage": "review"},
        )
        assert r.status_code == 409, r.text
        detail = client.get(f"/api/v1/curations/{w.draft}", headers=_h(admin)).json()
        assert detail["status"] == "draft"
        assert detail["can_delete"] is False
    finally:
        with _owner() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM audit_log WHERE user_id = %s", (str(admin),))
            cur.execute("DELETE FROM users WHERE id = %s", (str(admin),))
