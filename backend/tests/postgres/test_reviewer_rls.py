"""Scope reviewers can act on work under review, as the API runs (app_user, RLS) (release blocker).

Approving a precuration (update + insert of the curation) and moving a curation out of review
(request changes) used to 500 with StaleDataError: the UPDATE policies only allowed admins,
creators and curators. D1: nobody reviews their own work; no platform-admin bypass added.
"""

import json
import os
from collections.abc import Generator
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
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
    frank: UUID = field(default_factory=uuid4)  # not a member of the scope
    ann: UUID = field(default_factory=uuid4)  # scope admin
    pat: UUID = field(default_factory=uuid4)  # platform admin, scope reviewer
    pete: UUID = field(
        default_factory=uuid4
    )  # pending (unaccepted) reviewer invitation
    root: UUID = field(default_factory=uuid4)  # platform admin, no membership here
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
            (x.frank, "frank"),
            (x.ann, "ann"),
            (x.pat, "pat"),
            (x.pete, "pete"),
            (x.root, "root"),
        ):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    str(uid),
                    f"{name}-{tag}@rlsrev.org",
                    get_password_hash("pw"),
                    name,
                    "admin" if uid in (x.pat, x.root) else "user",
                ),
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
            (x.ann, "admin"),
            (x.pat, "reviewer"),
        ):
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, %s, %s, now())",
                (str(x.scope), str(uid), role, str(x.alice)),
            )
        cur.execute(
            "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by) "
            "VALUES (%s, %s, 'reviewer', %s)",
            (str(x.scope), str(x.pete), str(x.alice)),
        )
        cur.execute(
            "SELECT id, precuration_schema_id FROM workflow_pairs WHERE is_active LIMIT 1"
        )
        pair, schema = cur.fetchone()
        # seeded pairs share precuration schemas; approval needs the scope default (#448)
        cur.execute(
            "UPDATE scopes SET default_workflow_pair_id = %s WHERE id = %s",
            (str(pair), str(x.scope)),
        )
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
    users = [
        str(u)
        for u in (
            x.alice,
            x.bob,
            x.carol,
            x.dave,
            x.frank,
            x.ann,
            x.pat,
            x.pete,
            x.root,
        )
    ]
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


def _activate_curation(w: W) -> None:
    """The gene's fixture curation is open; approval only drafts a curation when none is."""
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE curations SET status = 'active', workflow_stage = 'active' "
            "WHERE id = %s",
            (str(w.cur),),
        )


def test_reviewer_approves_precuration_and_the_curation_is_created(
    client: TestClient, w: W
) -> None:
    _activate_curation(w)
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
    # the feedback is stored (as bob's review decision) and alice, as app_user, reads it back
    trail = client.get(
        f"/api/v1/workflow/curation/{w.cur}/audit-trail", headers=_h(w.alice)
    )
    assert trail.status_code == 200, trail.text
    assert trail.json()["entries"][-1]["notes"] == "needs work"


# alice: the curator who wrote it (D1); carol: viewer; dave: another curator
@pytest.mark.parametrize("who", ["alice", "carol", "dave"])
def test_only_another_reviewer_approves_precurations(
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


def test_non_member_is_denied_not_a_500(client: TestClient, w: W) -> None:
    """RLS hides work in progress from outsiders (404, like every hidden row), in a public
    scope too (054); either way nothing changes."""
    approve = f"/api/v1/precurations/{w.pre}/approve"
    move = f"/api/v1/workflow/curation/{w.cur}/transition"
    body = {"target_stage": "curation"}
    assert client.post(approve, headers=_h(w.frank)).status_code == 404
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("UPDATE scopes SET is_public = true WHERE id = %s", (str(w.scope),))
    r = client.post(approve, headers=_h(w.frank))
    assert r.status_code == 404, r.text
    r = client.post(move, json=body, headers=_h(w.frank))
    assert r.status_code in (400, 403), r.text
    assert (
        _owner_scalar("SELECT status::text FROM precurations WHERE id = %s", str(w.pre))
        == "submitted"
    )
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
        db.rollback()
    # ...but nothing else is a reviewer's to change (allowlist guard)
    for column, value in (
        ("evidence_data", '{"x": 1}'),
        ("computed_verdict", "Definitive"),
        ("computed_scores", '{"total": 18}'),
    ):
        with Session(database.engine) as db:
            set_rls_context(db, db.get_one(UserNew, w.bob))
            with pytest.raises(DBAPIError) as err:
                db.execute(
                    text(f"UPDATE curations SET {column} = :v WHERE id = :i"),
                    {"v": value, "i": w.cur},
                )
            assert isinstance(err.value.orig, psycopg2.errors.InsufficientPrivilege)
    # work that is not under review is not a reviewer's to touch: 0 rows, silently
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


def _active_curation(w: W) -> UUID:
    """alice's earlier curation of the same gene, already ACTIVE."""
    old = uuid4()
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, status, "
            "workflow_stage, is_draft, created_by) SELECT %s, gene_id, scope_id, "
            "workflow_pair_id, 'active', 'active', false, created_by "
            "FROM curations WHERE id = %s",
            (str(old), str(w.cur)),
        )
    return old


def test_reviewer_activates_a_recuration_and_archives_the_previous(
    client: TestClient, w: W
) -> None:
    old = _active_curation(w)
    r = client.post(
        f"/api/v1/workflow/curation/{w.cur}/transition",
        json={"target_stage": "active"},
        headers=_h(w.bob),
    )
    assert r.status_code == 200, r.text
    status = "SELECT status::text FROM curations WHERE id = %s"
    assert _owner_scalar(status, str(w.cur)) == "active"
    assert _owner_scalar(status, str(old)) == "archived"


@pytest.mark.parametrize(
    "change", ["status = 'draft'", "status = 'approved'", "computed_verdict = 'x'"]
)
def test_reviewer_may_only_archive_an_active_curation(w: W, change: str) -> None:
    old = _active_curation(w)
    with Session(database.engine) as db:
        set_rls_context(db, db.get_one(UserNew, w.bob))
        with pytest.raises(DBAPIError) as err:
            db.execute(
                text(f"UPDATE curations SET {change} WHERE id = :i"),
                {"i": old},
            )
        assert isinstance(err.value.orig, psycopg2.errors.InsufficientPrivilege)


def _insert_curation_as(uid: UUID, w: W, **overrides: object) -> None:
    """INSERT the curation an approval creates, as app_user in uid's session."""
    values: dict[str, object] = {"id": uuid4(), "author": w.alice, "pre": w.pre}
    values.update(overrides)
    with Session(database.engine) as db:
        set_rls_context(db, db.get_one(UserNew, uid))
        db.execute(
            text(
                "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, "
                "precuration_id, status, workflow_stage, is_draft, evidence_data, "
                "created_by) SELECT :id, p.gene_id, p.scope_id, wp.id, p.id, 'draft', "
                "'curation', true, '{}', :author FROM precurations p JOIN workflow_pairs "
                "wp ON wp.precuration_schema_id = p.precuration_schema_id "
                "WHERE p.id = :pre AND wp.is_active LIMIT 1"
            ),
            values,
        )
        db.commit()


def test_reviewer_cannot_insert_forged_curations(client: TestClient, w: W) -> None:
    def denied(**overrides: object) -> None:
        with pytest.raises(DBAPIError) as err:
            _insert_curation_as(w.bob, w, **overrides)
        assert isinstance(err.value.orig, psycopg2.errors.InsufficientPrivilege)

    denied()  # the precuration is not approved
    _activate_curation(w)
    assert client.post(
        f"/api/v1/precurations/{w.pre}/approve", headers=_h(w.bob)
    ).is_success
    denied()  # a second curation for the same precuration
    denied(author=w.dave)  # someone else as author


def test_reviewer_rejects_a_precuration_but_not_a_draft(
    client: TestClient, w: W
) -> None:
    url = f"/api/v1/precurations/{w.pre}/reject"
    r = client.post(url, json={"reason": "out of scope"}, headers=_h(w.bob))
    assert r.status_code == 200, r.text
    assert r.json()["computed_fields"]["rejection_reason"] == "out of scope"
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE precurations SET status = 'draft' WHERE id = %s", (str(w.pre),)
        )
    r = client.post(url, json={"reason": "x"}, headers=_h(w.bob))
    assert r.status_code == 403, r.text


def test_peer_review_in_an_inactive_scope_is_409_not_500(
    client: TestClient, w: W
) -> None:
    review = uuid4()
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE curations SET status = 'in_review', submitted_at = now() - "
            "interval '1 hour' WHERE id = %s",
            (str(w.cur),),
        )
        cur.execute(
            "INSERT INTO reviews (id, curation_id, reviewer_id, assigned_by) "
            "VALUES (%s, %s, %s, %s)",
            (str(review), str(w.cur), str(w.bob), str(w.alice)),
        )
        cur.execute(
            "UPDATE scopes SET is_active = false WHERE id = %s", (str(w.scope),)
        )
    r = client.post(
        f"/api/v1/workflow/reviews/{review}/submit",
        json={"decision": "request_changes"},
        headers=_h(w.bob),
    )
    assert r.status_code == 409, r.text
    assert (
        _owner_scalar("SELECT status::text FROM reviews WHERE id = %s", str(review))
        == "pending"
    )


def test_scope_admin_approves_others_work(client: TestClient, w: W) -> None:
    r = client.post(f"/api/v1/precurations/{w.pre}/approve", headers=_h(w.ann))
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("who", ["ann", "pat"])
def test_admins_cannot_approve_their_own_work(
    client: TestClient, w: W, who: str
) -> None:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE precurations SET created_by = %s WHERE id = %s",
            (str(getattr(w, who)), str(w.pre)),
        )
    r = client.post(
        f"/api/v1/precurations/{w.pre}/approve", headers=_h(getattr(w, who))
    )
    assert r.status_code == 403, r.text


# pending invitee: RLS hides the private scope's work (404); inactive scope: 403
@pytest.mark.parametrize(("who", "code"), [("pete", 404), ("bob", 403)])
def test_pending_invitation_and_inactive_scope_get_nothing(
    client: TestClient, w: W, who: str, code: int
) -> None:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE scopes SET is_active = %s WHERE id = %s",
            (who != "bob", str(w.scope)),
        )
    r = client.post(
        f"/api/v1/precurations/{w.pre}/approve", headers=_h(getattr(w, who))
    )
    assert r.status_code == code, r.text
    assert (
        _owner_scalar("SELECT status::text FROM precurations WHERE id = %s", str(w.pre))
        == "submitted"
    )


# alice resubmits her own curation; dave, a co-curator, advances it through the workflow
@pytest.mark.parametrize("who", ["alice", "dave"])
def test_curator_resubmits_after_changes_requested_and_reviewer_approves(
    client: TestClient, w: W, who: str
) -> None:
    """Monkey test: the resubmit re-requests bob's review as the curator; RLS denied it (403)."""
    move = f"/api/v1/workflow/curation/{w.cur}/transition"
    r = client.post(
        move, json={"target_stage": "curation", "notes": "fix"}, headers=_h(w.bob)
    )
    assert r.status_code == 200, r.text
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE curations SET evidence_data = %s WHERE id = %s",
            (
                json.dumps(
                    {
                        "notes": "x",
                        "entity_definition": {
                            "mondo_id": "MONDO:0000001",
                            "disease_name": "disease",
                            "mode_of_inheritance": "AD",
                        },
                    }
                ),
                str(w.cur),
            ),
        )
    if who == "alice":
        lock = _owner_scalar(
            "SELECT lock_version FROM curations WHERE id = %s", str(w.cur)
        )
        r = client.post(
            f"/api/v1/curations/{w.cur}/submit",
            json={"lock_version": lock},
            headers=_h(w.alice),
        )
    else:
        r = client.post(move, json={"target_stage": "review"}, headers=_h(w.dave))
    assert r.status_code == 200, r.text
    review = _owner_scalar(
        "SELECT id FROM reviews WHERE curation_id = %s AND status = 'pending' "
        "AND reviewer_id = %s AND assigned_by = %s",
        str(w.cur),
        str(w.bob),
        str(getattr(w, who)),
    )
    assert review is not None
    r = client.post(
        f"/api/v1/workflow/reviews/{review}/submit",
        json={"decision": "approve"},
        headers=_h(w.bob),
    )
    assert r.status_code == 200, r.text
    assert (
        _owner_scalar("SELECT status::text FROM curations WHERE id = %s", str(w.cur))
        == "active"
    )


@pytest.mark.parametrize(
    ("reviewer", "status", "change"),
    [
        ("bob", "pending", None),  # control: the legitimate re-request
        ("dave", "pending", None),  # never reviewed this curation
        ("alice", "pending", None),  # herself (4-eyes)
        ("bob", "approved", None),  # a decision, not a pending request
        ("bob", "pending", "UPDATE scope_memberships SET role = 'viewer'"),  # demoted
        ("bob", "pending", "UPDATE scope_memberships SET is_active = false"),
        ("bob", "pending", "future"),  # dated into later rounds
    ],
)
def test_curator_cannot_forge_reviews(
    w: W, reviewer: str, status: str, change: str | None
) -> None:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE curations SET status = 'in_review' WHERE id = %s", (str(w.cur),)
        )
        cur.execute(
            "INSERT INTO reviews (curation_id, reviewer_id, assigned_by, status) "
            "VALUES (%s, %s, %s, 'needs_revision')",
            (str(w.cur), str(w.bob), str(w.bob)),
        )
        if change and change != "future":
            cur.execute(
                f"{change} WHERE scope_id = %s AND user_id = %s",
                (str(w.scope), str(w.bob)),
            )
    insert = text(
        "INSERT INTO reviews (curation_id, reviewer_id, assigned_by, status, "
        "assigned_at) VALUES (:c, :r, :a, CAST(:s AS review_status), "
        "now() + CAST(:ahead AS interval))"
    )
    values = {
        "c": w.cur,
        "r": getattr(w, reviewer),
        "a": w.alice,
        "s": status,
        "ahead": "1 day" if change == "future" else "0",
    }
    with Session(database.engine) as db:
        set_rls_context(db, db.get_one(UserNew, w.alice))
        if (reviewer, status, change) == ("bob", "pending", None):
            assert db.execute(insert, values).rowcount == 1
            return
        with pytest.raises(DBAPIError) as err:
            db.execute(insert, values)
        assert isinstance(err.value.orig, psycopg2.errors.InsufficientPrivilege)


def test_platform_admin_without_membership_gets_403_not_500_on_create(
    client: TestClient, w: W
) -> None:
    pair, schema = (
        _owner_scalar(
            "SELECT id FROM workflow_pairs WHERE is_active ORDER BY id LIMIT 1"
        ),
        _owner_scalar(
            "SELECT precuration_schema_id FROM workflow_pairs WHERE is_active "
            "ORDER BY id LIMIT 1"
        ),
    )
    body = {"gene_id": str(w.gene2), "scope_id": str(w.scope), "evidence_data": {}}
    r = client.post(
        "/api/v1/precurations/",
        json={**body, "precuration_schema_id": str(schema)},
        headers=_h(w.root),
    )
    assert r.status_code == 403, r.text
    assert "accepted curator membership" in r.json()["detail"]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE precurations SET status = 'approved' WHERE id = %s", (str(w.pre),)
        )
        # The gene's open curation would refuse the create (409) before RLS is reached
        cur.execute(
            "UPDATE curations SET status = 'archived' WHERE id = %s", (str(w.cur),)
        )
    r = client.post(
        "/api/v1/curations/",
        json={**body, "gene_id": str(w.gene), "workflow_pair_id": str(pair)},
        headers=_h(w.root),
    )
    assert r.status_code == 403, r.text
    assert "accepted curator membership" in r.json()["detail"]
