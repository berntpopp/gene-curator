"""Workflow from the pinned methodology version, as the API runs (app_user, RLS) (#268).

045 drops trigger_manage_workflow_transitions, so the columns the engine sets are the ones
stored. A schema with `review.reviewers_required: 2` activates only after two approvals, the
author never counts (D1, admins included), and a forbidden edge changes nothing.
"""

import json
import os
from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient

from app.core import database
from app.core.security import create_access_token, get_password_hash
from app.main import app

pytestmark = pytest.mark.postgres

MIGRATION = Path(__file__).parents[3] / "database/sql/045_drop_workflow_trigger.sql"


@dataclass
class W:
    scope: UUID = field(default_factory=uuid4)
    alice: UUID = field(default_factory=uuid4)  # platform admin + scope curator, author
    bob: UUID = field(default_factory=uuid4)  # reviewer
    carol: UUID = field(default_factory=uuid4)  # reviewer
    gene: UUID = field(default_factory=uuid4)
    gene2: UUID = field(default_factory=uuid4)
    cur: UUID = field(default_factory=uuid4)  # two-reviewer workflow
    locked: UUID = field(default_factory=uuid4)  # workflow without curation -> review
    schemas: list[str] = field(default_factory=list)
    pairs: list[str] = field(default_factory=list)


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


def _pair(cur: Any, w: W, seeded: str, states: dict[str, Any]) -> str:
    """Copy of the seeded ClinGen schema with `states` merged into workflow_states."""
    tag = uuid4().hex[:8]
    cur.execute(
        "INSERT INTO curation_schemas (name, version, schema_type, field_definitions, "
        "validation_rules, scoring_configuration, workflow_states, ui_configuration, "
        "schema_hash, created_by) SELECT %s, version, schema_type, field_definitions, "
        "validation_rules, scoring_configuration, workflow_states || %s::jsonb, "
        "ui_configuration, schema_hash, %s FROM curation_schemas WHERE id = %s RETURNING id",
        (f"wf-{tag}", json.dumps(states), str(w.alice), seeded),
    )
    schema = str(cur.fetchone()[0])
    cur.execute(
        "INSERT INTO workflow_pairs (name, version, curation_schema_id) "
        "VALUES (%s, '1', %s) RETURNING id",
        (f"wf-{tag}", schema),
    )
    pair = str(cur.fetchone()[0])
    w.schemas.append(schema)
    w.pairs.append(pair)
    return pair


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.scope)[:8]
    with _owner() as conn, conn.cursor() as cur:
        for uid, name, role in (
            (x.alice, "alice", "admin"),
            (x.bob, "bob", "user"),
            (x.carol, "carol", "user"),
        ):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    str(uid),
                    f"{name}-{tag}@wfc.org",
                    get_password_hash("pw"),
                    name,
                    role,
                ),
            )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, 'WF', false, %s)",
            (str(x.scope), f"wf-{x.scope}", str(x.alice)),
        )
        for uid, role in (
            (x.alice, "curator"),
            (x.bob, "reviewer"),
            (x.carol, "reviewer"),
        ):
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, %s, %s, now())",
                (str(x.scope), str(uid), role, str(x.alice)),
            )
        cur.execute(
            "SELECT curation_schema_id FROM workflow_pairs WHERE is_active LIMIT 1"
        )
        seeded = cur.fetchone()[0]
        two = _pair(cur, x, seeded, {"review": {"reviewers_required": 2}})
        locked = _pair(
            cur, x, seeded, {"curation": {"allowed_transitions": ["precuration"]}}
        )
        for gid, cid, pair in ((x.gene, x.cur, two), (x.gene2, x.locked, locked)):
            cur.execute(
                "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
                "VALUES (%s, %s, %s, %s)",
                (str(gid), f"HGNC:{gid.int % 10**9}", f"WF{gid.hex[:6]}", gid.hex * 2),
            )
            cur.execute(
                "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, status, "
                "workflow_stage, is_draft, evidence_data, created_by) VALUES "
                "(%s, %s, %s, %s, 'draft', 'curation', true, %s, %s)",
                (
                    str(cid),
                    str(gid),
                    str(x.scope),
                    pair,
                    json.dumps(
                        {
                            "summary": "ok",
                            "entity_definition": {
                                "mondo_id": "MONDO:0000001",
                                "disease_name": "disease",
                                "mode_of_inheritance": "AD",
                            },
                        }
                    ),
                    str(x.alice),
                ),
            )
    yield x
    users = [str(x.alice), str(x.bob), str(x.carol)]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(x.scope),))
        cur.execute(
            "DELETE FROM genes WHERE id = ANY(%s::uuid[])",
            ([str(x.gene), str(x.gene2)],),
        )
        cur.execute(
            "DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[]) OR scope_id = %s "
            "OR workflow_pair_id = ANY(%s::uuid[]) OR schema_id = ANY(%s::uuid[])",
            (users, str(x.scope), x.pairs, x.schemas),
        )
        cur.execute("DELETE FROM workflow_pairs WHERE id = ANY(%s::uuid[])", (x.pairs,))
        cur.execute(
            "DELETE FROM curation_schemas WHERE id = ANY(%s::uuid[])", (x.schemas,)
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


def _row(cid: UUID) -> tuple[Any, ...]:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT workflow_stage::text, status::text, submitted_at, is_draft "
            "FROM curations WHERE id = %s",
            (str(cid),),
        )
        return tuple(cur.fetchone())


def _submit(client: TestClient, w: W, cid: UUID) -> Any:
    lock = client.get(f"/api/v1/curations/{cid}", headers=_h(w.alice))
    assert lock.status_code == 200, lock.text
    return client.post(
        f"/api/v1/curations/{cid}/submit?detail=true",
        json={"lock_version": lock.json()["lock_version"]},
        headers=_h(w.alice),
    )


def _approve(client: TestClient, w: W, who: UUID) -> Any:
    return client.post(
        f"/api/v1/workflow/curation/{w.cur}/transition",
        json={"target_stage": "active", "notes": "ok"},
        headers=_h(who),
    )


def test_two_reviewers_activate_and_the_author_never_counts(
    client: TestClient, w: W
) -> None:
    r = _submit(client, w, w.cur)
    assert r.status_code == 200, r.text
    stage, status, submitted_at, is_draft = _row(w.cur)
    assert (stage, status, is_draft) == ("review", "in_review", False)
    # exactly what the engine set: no trigger rewrote it
    assert submitted_at == datetime.fromisoformat(r.json()["submitted_at"])

    # D1: the author, a platform admin, cannot approve
    assert _approve(client, w, w.alice).status_code == 403
    first = _approve(client, w, w.bob)
    assert first.status_code == 200, first.text
    assert first.json()["to_stage"] == "review"
    assert _row(w.cur) == ("review", "in_review", submitted_at, False)

    second = _approve(client, w, w.carol)
    assert second.status_code == 200, second.text
    assert second.json()["to_stage"] == "active"
    assert _row(w.cur)[:2] == ("active", "active")


def test_approvals_of_an_earlier_round_do_not_count(client: TestClient, w: W) -> None:
    assert _submit(client, w, w.cur).status_code == 200
    assert _approve(client, w, w.bob).status_code == 200
    back = client.post(
        f"/api/v1/workflow/curation/{w.cur}/transition",
        json={"target_stage": "curation", "notes": "fix"},
        headers=_h(w.carol),
    )
    assert back.status_code == 200, back.text
    assert _submit(client, w, w.cur).status_code == 200
    assert _approve(client, w, w.carol).json()["to_stage"] == "review"
    assert _row(w.cur)[:2] == ("review", "in_review")
    assert _approve(client, w, w.bob).json()["to_stage"] == "active"
    assert _row(w.cur)[:2] == ("active", "active")


def test_reject_returns_a_draft_without_the_trigger(client: TestClient, w: W) -> None:
    assert _submit(client, w, w.cur).status_code == 200
    a = client.post(
        f"/api/v1/workflow/curation/{w.cur}/assign-reviewer",
        json={"reviewer_id": str(w.bob)},
        headers=_h(w.alice),
    )
    assert a.status_code == 200, a.text
    r = client.post(
        f"/api/v1/workflow/reviews/{a.json()['review_id']}/submit",
        json={"decision": "reject", "comments": "no"},
        headers=_h(w.bob),
    )
    assert r.status_code == 200, r.text
    stage, status, _, is_draft = _row(w.cur)
    assert (stage, status, is_draft) == ("curation", "rejected", True)


def test_forbidden_edge_is_refused_and_changes_nothing(
    client: TestClient, w: W
) -> None:
    before = _row(w.locked)
    r = _submit(client, w, w.locked)
    assert r.status_code == 409, r.text
    assert "Invalid transition from curation to review" in r.text
    assert _row(w.locked) == before


def test_migration_045_drops_the_trigger_idempotently() -> None:
    sql = MIGRATION.read_text()
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(sql)
        cur.execute(sql)
        cur.execute(
            "SELECT count(*) FROM pg_trigger "
            "WHERE tgname = 'trigger_manage_workflow_transitions'"
        )
        assert cur.fetchone()[0] == 0
        cur.execute(
            "SELECT count(*) FROM pg_proc WHERE proname = 'manage_workflow_transitions'"
        )
        assert cur.fetchone()[0] == 0
        cur.execute(
            "SELECT count(*) FROM schema_migrations "
            "WHERE filename = '045_drop_workflow_trigger.sql'"
        )
        assert cur.fetchone()[0] == 1
