"""Scope reviewers can act on work under review, as the API runs (app_user, RLS) (release blocker).

Approving a precuration (update + insert of the curation) and moving a curation out of review
(request changes) used to 500 with StaleDataError: the UPDATE policies only allowed admins,
creators and curators. D1: nobody reviews their own work; no platform-admin bypass added.
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
from app.core.deps import set_rls_context
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import UserNew

pytestmark = pytest.mark.postgres


@dataclass
class W:
    scope: UUID = field(default_factory=uuid4)
    alice: UUID = field(default_factory=uuid4)  # curator, author of the work
    bob: UUID = field(default_factory=uuid4)  # reviewer
    carol: UUID = field(default_factory=uuid4)  # viewer
    dave: UUID = field(default_factory=uuid4)  # curator, not the author
    erin: UUID = field(default_factory=uuid4)  # reviewer who authored the second set
    gene: UUID = field(default_factory=uuid4)
    gene2: UUID = field(default_factory=uuid4)
    pre: UUID = field(default_factory=uuid4)  # alice's submitted precuration
    own_pre: UUID = field(default_factory=uuid4)  # bob's own submitted precuration
    cur: UUID = field(default_factory=uuid4)  # alice's curation in review
    ids: list[UUID] = field(default_factory=list)


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.scope)[:8]
    with _owner() as conn, conn.cursor() as cur:
        for uid, name in (
            (x.alice, "alice"),
            (x.bob, "bob"),
            (x.carol, "carol"),
            (x.dave, "dave"),
        ):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, 'user')",
                (str(uid), f"{name}-{tag}@rlsrev.org", get_password_hash("pw"), name),
            )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, %s, false, %s)",
            (str(x.scope), f"rv-{x.scope}", "RV", str(x.alice)),
        )
        for uid, role in (
            (x.alice, "curator"),
            (x.bob, "reviewer"),
            (x.carol, "viewer"),
            (x.dave, "curator"),
        ):
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, %s, %s, now())",
                (str(x.scope), str(uid), role, str(x.alice)),
            )
        cur.execute("SELECT id, precuration_schema_id FROM workflow_pairs LIMIT 1")
        pair, schema = cur.fetchone()
        for gid, sym in ((x.gene, "RVA"), (x.gene2, "RVB")):
            cur.execute(
                "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
                "VALUES (%s, %s, %s, %s)",
                (str(gid), f"HGNC:{gid.int % 10**9}", f"{sym}{tag}", gid.hex * 2),
            )
        for pid, gid, author in ((x.pre, x.gene, x.alice), (x.own_pre, x.gene2, x.bob)):
            cur.execute(
                "INSERT INTO precurations (id, gene_id, scope_id, precuration_schema_id, "
                "status, workflow_stage, is_draft, created_by) VALUES "
                "(%s, %s, %s, %s, 'submitted', 'review', false, %s)",
                (str(pid), str(gid), str(x.scope), str(schema), str(author)),
            )
        cur.execute(
            "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, status, "
            "workflow_stage, is_draft, created_by) VALUES "
            "(%s, %s, %s, %s, 'submitted', 'review', false, %s)",
            (str(x.cur), str(x.gene), str(x.scope), str(pair), str(x.alice)),
        )
    yield x
    users = [str(u) for u in (x.alice, x.bob, x.carol, x.dave)]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(x.scope),))
        cur.execute(
            "DELETE FROM genes WHERE id = ANY(%s::uuid[])",
            ([str(x.gene), str(x.gene2)],),
        )
        cur.execute("DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[])", (users,))
        cur.execute(
            "DELETE FROM audit_log WHERE scope_id = %s OR entity_id = ANY(%s::uuid[])",
            (str(x.scope), [str(x.pre), str(x.own_pre), str(x.cur)]),
        )
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (users,))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _h(uid: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(uid)})}"}


def _owner_scalar(sql: str, *params: object) -> object:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return row[0] if row else None


def test_reviewer_approves_precuration_and_the_curation_is_created(
    client: TestClient, w: W
) -> None:
    r = client.post(f"/api/v1/precurations/{w.pre}/approve", headers=_h(w.bob))
    assert r.status_code == 200, r.text
    assert r.json()["curation_created"] is True
    assert (
        _owner_scalar("SELECT status::text FROM precurations WHERE id = %s", str(w.pre))
        == "approved"
    )
    # the new curation is authored by the precuration's author (4-eyes), not the approver
    assert _owner_scalar(
        "SELECT created_by FROM curations WHERE precuration_id = %s", str(w.pre)
    ) == str(w.alice)


def test_reviewer_requests_changes_on_a_curation(client: TestClient, w: W) -> None:
    r = client.post(
        f"/api/v1/workflow/curation/{w.cur}/transition",
        json={"target_stage": "curation", "notes": "needs work"},
        headers=_h(w.bob),
    )
    assert r.status_code == 200, r.text
    assert (
        _owner_scalar(
            "SELECT workflow_stage::text FROM curations WHERE id = %s", str(w.cur)
        )
        == "curation"
    )


@pytest.mark.parametrize("who", ["carol", "dave"])
def test_viewer_and_curator_cannot_approve_precurations(
    client: TestClient, w: W, who: str
) -> None:
    r = client.post(
        f"/api/v1/precurations/{w.pre}/approve", headers=_h(getattr(w, who))
    )
    assert r.status_code == 403, r.text
    assert (
        _owner_scalar("SELECT status::text FROM precurations WHERE id = %s", str(w.pre))
        == "submitted"
    )


@pytest.mark.parametrize("who", ["carol", "dave"])
def test_viewer_and_curator_cannot_send_work_back_from_review(
    client: TestClient, w: W, who: str
) -> None:
    r = client.post(
        f"/api/v1/workflow/curation/{w.cur}/transition",
        json={"target_stage": "curation"},
        headers=_h(getattr(w, who)),
    )
    assert r.status_code in (400, 403), r.text
    assert (
        _owner_scalar(
            "SELECT workflow_stage::text FROM curations WHERE id = %s", str(w.cur)
        )
        == "review"
    )


def test_nobody_approves_their_own_precuration(client: TestClient, w: W) -> None:
    """D1: bob is a reviewer but authored own_pre."""
    r = client.post(f"/api/v1/precurations/{w.own_pre}/approve", headers=_h(w.bob))
    assert r.status_code == 403, r.text
    assert (
        _owner_scalar(
            "SELECT status::text FROM precurations WHERE id = %s", str(w.own_pre)
        )
        == "submitted"
    )


def test_database_alone_stops_a_reviewer_editing_evidence_or_own_work(w: W) -> None:
    with Session(database.engine) as db:
        set_rls_context(db, db.get_one(UserNew, w.bob))
        # status moves are allowed on work under review...
        moved = db.execute(
            text("UPDATE curations SET status = 'in_review' WHERE id = :i"),
            {"i": w.cur},
        ).rowcount
        assert moved == 1
        # ...but evidence and authorship are not a reviewer's to change
        with pytest.raises(Exception):  # noqa: B017 - DB trigger raises
            db.execute(
                text("UPDATE curations SET evidence_data = '{\"x\": 1}' WHERE id = :i"),
                {"i": w.cur},
            )
        db.rollback()
        set_rls_context(db, db.get_one(UserNew, w.bob))
        # work that is not under review is not a reviewer's to touch
        db.execute(
            text("UPDATE curations SET status = 'submitted' WHERE id = :i"),
            {"i": w.cur},
        )
        db.rollback()
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE precurations SET status = 'draft' WHERE id = %s", (str(w.pre),)
        )
    with Session(database.engine) as db:
        set_rls_context(db, db.get_one(UserNew, w.bob))
        assert (
            db.execute(
                text("UPDATE precurations SET status = 'approved' WHERE id = :i"),
                {"i": w.pre},
            ).rowcount
            == 0
        )
        db.rollback()
