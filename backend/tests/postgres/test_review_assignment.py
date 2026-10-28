"""Routing work to a reviewer through the API as app_user (MCP study round 1, findings 1, 4).

A scope curator assigning a reviewer to her submitted curation got a 500 (review insert
denied by RLS, fixed in 061); a submitted precuration could not be routed at all. Both now
work; a viewer gets 403, never a 500; D1 holds (the author is never the reviewer).
"""

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
    bob: UUID = field(default_factory=uuid4)  # reviewer
    vic: UUID = field(default_factory=uuid4)  # viewer
    gene: UUID = field(default_factory=uuid4)
    cur: UUID = field(default_factory=uuid4)
    pre: UUID = field(default_factory=uuid4)


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.scope)[:8]
    members = ((x.alice, "curator"), (x.bob, "reviewer"), (x.vic, "viewer"))
    ids = [str(u) for u, _ in members]
    with _owner() as conn, conn.cursor() as cur:
        for uid, _ in members:
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, 'u', 'user')",
                (str(uid), f"{uid.hex[:8]}-{tag}@ra.org", get_password_hash("pw")),
            )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, 'RA', false, %s)",
            (str(x.scope), f"ra-{x.scope}", str(x.alice)),
        )
        for uid, role in members:
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, %s, %s, now())",
                (str(x.scope), str(uid), role, str(x.alice)),
            )
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (%s, %s, %s, %s)",
            (str(x.gene), f"HGNC:{x.gene.int % 10**9}", f"RA{tag}", x.gene.hex * 2),
        )
        cur.execute(
            "INSERT INTO precurations (id, gene_id, scope_id, precuration_schema_id, "
            "status, workflow_stage, is_draft, created_by) SELECT %s, %s, %s, "
            "precuration_schema_id, 'submitted', 'precuration', false, %s "
            "FROM workflow_pairs WHERE is_active AND precuration_schema_id IS NOT NULL "
            "LIMIT 1",
            (str(x.pre), str(x.gene), str(x.scope), str(x.alice)),
        )
        cur.execute(
            "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, status, "
            "workflow_stage, is_draft, evidence_data, created_by) SELECT %s, %s, %s, id, "
            "'draft', 'curation', true, %s, %s FROM workflow_pairs WHERE is_active LIMIT 1",
            (
                str(x.cur),
                str(x.gene),
                str(x.scope),
                json.dumps(
                    {
                        "summary": "ok",
                        "entity_definition": {
                            "mondo_id": "MONDO:0000001",
                            "disease_name": "Test disease",
                            "mode_of_inheritance": "Autosomal dominant",
                        },
                    }
                ),
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


def _assign(client: TestClient, kind: str, item: UUID, who: UUID, by: UUID) -> int:
    r = client.post(
        f"/api/v1/workflow/{kind}/{item}/assign-reviewer",
        json={"reviewer_id": str(who)},
        headers=_h(by),
    )
    return r.status_code


def test_curator_assigns_reviewer_to_submitted_curation(
    client: TestClient, w: W
) -> None:
    lock = client.get(f"/api/v1/curations/{w.cur}", headers=_h(w.alice)).json()
    r = client.post(
        f"/api/v1/curations/{w.cur}/submit",
        json={"lock_version": lock["lock_version"]},
        headers=_h(w.alice),
    )
    assert r.status_code == 200, r.text

    assert _assign(client, "curation", w.cur, w.alice, w.alice) == 400  # D1
    assert _assign(client, "curation", w.cur, w.bob, w.vic) == 403
    assert _assign(client, "curation", w.cur, w.bob, w.alice) == 200
    mine = client.get(
        "/api/v1/workflow/reviews/my-assignments", headers=_h(w.bob)
    ).json()
    assert [a["item_id"] for a in mine] == [str(w.cur)]


def test_curator_routes_submitted_precuration_and_reviewer_approves(
    client: TestClient, w: W
) -> None:
    assert _assign(client, "precuration", w.pre, w.alice, w.alice) == 400  # D1
    assert _assign(client, "precuration", w.pre, w.bob, w.vic) == 403
    assert _assign(client, "precuration", w.pre, w.bob, w.alice) == 200
    notes = client.get("/api/v1/notifications/", headers=_h(w.bob))
    assert notes.status_code == 200, notes.text
    assert str(w.pre) in notes.text

    r = client.post(f"/api/v1/precurations/{w.pre}/approve", headers=_h(w.bob))
    assert r.status_code == 200, r.text


def _reviewers(cur: UUID) -> list[str]:
    with _owner() as conn, conn.cursor() as c:
        c.execute(
            "SELECT reviewer_id::text FROM reviews WHERE curation_id = %s", (str(cur),)
        )
        return [r[0] for r in c.fetchall()]


def test_submit_with_reviewer_routes_it_in_the_same_transaction(
    client: TestClient, w: W
) -> None:
    """Submit-and-assign as app_user: D1 refuses the author and rolls the submit back."""
    lock = client.get(f"/api/v1/curations/{w.cur}", headers=_h(w.alice)).json()
    url = f"/api/v1/curations/{w.cur}/submit"
    for bad in (w.alice, w.vic):  # the author (D1), a viewer
        r = client.post(
            url,
            json={"lock_version": lock["lock_version"], "reviewer_id": str(bad)},
            headers=_h(w.alice),
        )
        assert r.status_code == 400, r.text
    after = client.get(f"/api/v1/curations/{w.cur}", headers=_h(w.alice)).json()
    assert (after["status"], after["lock_version"]) == ("draft", lock["lock_version"])
    assert _reviewers(w.cur) == []

    r = client.post(
        url,
        json={"lock_version": lock["lock_version"], "reviewer_id": str(w.bob)},
        headers=_h(w.alice),
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "in_review"
    assert _reviewers(w.cur) == [str(w.bob)]
    mine = client.get(
        "/api/v1/workflow/reviews/my-assignments", headers=_h(w.bob)
    ).json()
    assert [a["item_id"] for a in mine] == [str(w.cur)]


PRECURATION = {
    "entity_definition": {
        "mondo_id": "MONDO:0000001",
        "disease_name": "Test disease",
        "mode_of_inheritance": "autosomal_dominant",
    },
    "lumping_splitting": {"decision": "lump", "rationale": "r" * 60},
    "initial_assessment": {"literature_search_strategy": "PubMed"},
}


def test_submit_precuration_with_reviewer_notifies_them(
    client: TestClient, w: W
) -> None:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE precurations SET status = 'draft', is_draft = true, "
            "evidence_data = %s WHERE id = %s",
            (json.dumps(PRECURATION), str(w.pre)),
        )
    lock = client.get(f"/api/v1/precurations/{w.pre}", headers=_h(w.alice)).json()
    r = client.post(
        f"/api/v1/precurations/{w.pre}/submit",
        json={"lock_version": lock["lock_version"], "reviewer_id": str(w.bob)},
        headers=_h(w.alice),
    )
    assert r.status_code == 200, r.text
    notes = client.get("/api/v1/notifications/", headers=_h(w.bob))
    assert str(w.pre) in notes.text


def test_review_read_lists_the_request_for_changes_before_and_after_resubmit(
    client: TestClient, w: W
) -> None:
    """Round 5: previous_reviews was empty after request_changes (DB-clock reviewed_at is
    later than the submission). As app_user: the decision shows while the curation is
    back with its curator, and again on the resubmission."""
    url = f"/api/v1/curations/{w.cur}"

    def submit() -> None:
        lock = client.get(url, headers=_h(w.alice)).json()["lock_version"]
        r = client.post(
            f"{url}/submit",
            json={"lock_version": lock, "reviewer_id": str(w.bob)},
            headers=_h(w.alice),
        )
        assert r.status_code == 200, r.text

    submit()
    (review,) = client.get(
        "/api/v1/workflow/reviews/my-assignments", headers=_h(w.bob)
    ).json()
    sent = client.post(
        f"/api/v1/workflow/reviews/{review['review_id']}/submit",
        json={"decision": "request_changes", "comments": "Cite the case report"},
        headers=_h(w.bob),
    )
    assert sent.status_code == 200, sent.text
    back = client.get(f"{url}/review", headers=_h(w.alice)).json()
    assert [p["comments"] for p in back["previous_reviews"]] == ["Cite the case report"]

    submit()
    again = client.get(f"{url}/review", headers=_h(w.bob)).json()
    assert again["first_submission"] is False
    assert [p["comments"] for p in again["previous_reviews"]] == [
        "Cite the case report"
    ]
