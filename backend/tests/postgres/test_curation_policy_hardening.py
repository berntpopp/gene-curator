"""Curation policy hardening under real RLS (app_user); data is committed by the owner role.

#376: in a public scope, non-members see only ACTIVE curations at the database level, so an
endpoint relying on RLS alone cannot leak work in progress.
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
        cur.execute("SELECT id FROM workflow_pairs WHERE is_active LIMIT 1")
        pair = cur.fetchone()[0]
        for cid, status in ((x.draft, "draft"), (x.active, "active")):
            cur.execute(
                "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, status, "
                "workflow_stage, is_draft, created_by, evidence_data) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
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
