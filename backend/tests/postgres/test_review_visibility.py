"""Review visibility for `reviewers_required: 2`, as the API runs (app_user, RLS) (#430).

After approving, a reviewer gets can_review=false with has_approved and the remaining count; a
repeated approval is not counted; request changes + resubmit starts a new round where earlier
decisions do not count. The author (a platform admin) and a platform admin without membership
never review (D1).
"""

import json
import os
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any
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
    alice: UUID = field(default_factory=uuid4)  # platform admin + scope curator, author
    bob: UUID = field(default_factory=uuid4)  # reviewer
    carol: UUID = field(default_factory=uuid4)  # reviewer
    dave: UUID = field(default_factory=uuid4)  # platform admin, no membership
    gene: UUID = field(default_factory=uuid4)
    cur: UUID = field(default_factory=uuid4)
    schema: str = ""
    pair: str = ""


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.scope)[:8]
    users = ((x.alice, "admin"), (x.bob, "user"), (x.carol, "user"), (x.dave, "admin"))
    with _owner() as conn, conn.cursor() as cur:
        for uid, role in users:
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, 'u', %s)",
                (
                    str(uid),
                    f"{uid.hex[:8]}-{tag}@rv.org",
                    get_password_hash("pw"),
                    role,
                ),
            )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, 'RV', false, %s)",
            (str(x.scope), f"rv-{x.scope}", str(x.alice)),
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
            "INSERT INTO curation_schemas (name, version, schema_type, field_definitions, "
            "validation_rules, scoring_configuration, workflow_states, ui_configuration, "
            "schema_hash, created_by) SELECT %s, version, schema_type, field_definitions, "
            "validation_rules, scoring_configuration, workflow_states || %s::jsonb, "
            "ui_configuration, schema_hash, %s FROM curation_schemas WHERE id = "
            "(SELECT curation_schema_id FROM workflow_pairs WHERE is_active LIMIT 1) "
            "RETURNING id",
            (
                f"rv-{tag}",
                json.dumps({"review": {"reviewers_required": 2}}),
                str(x.alice),
            ),
        )
        x.schema = str(cur.fetchone()[0])
        cur.execute(
            "INSERT INTO workflow_pairs (name, version, curation_schema_id) "
            "VALUES (%s, '1', %s) RETURNING id",
            (f"rv-{tag}", x.schema),
        )
        x.pair = str(cur.fetchone()[0])
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (%s, %s, %s, %s)",
            (str(x.gene), f"HGNC:{x.gene.int % 10**9}", f"RV{tag}", x.gene.hex * 2),
        )
        cur.execute(
            "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, status, "
            "workflow_stage, is_draft, evidence_data, created_by) VALUES "
            "(%s, %s, %s, %s, 'draft', 'curation', true, %s, %s)",
            (
                str(x.cur),
                str(x.gene),
                str(x.scope),
                x.pair,
                json.dumps({"summary": "ok"}),
                str(x.alice),
            ),
        )
    yield x
    ids = [str(u) for u, _ in users]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(x.scope),))
        cur.execute("DELETE FROM genes WHERE id = %s", (str(x.gene),))
        cur.execute(
            "DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[]) OR scope_id = %s "
            "OR workflow_pair_id = %s OR schema_id = %s",
            (ids, str(x.scope), x.pair, x.schema),
        )
        cur.execute("DELETE FROM workflow_pairs WHERE id = %s", (x.pair,))
        cur.execute("DELETE FROM curation_schemas WHERE id = %s", (x.schema,))
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (ids,))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _h(uid: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(uid)})}"}


def _view(client: TestClient, w: W, who: UUID) -> tuple[Any, ...]:
    r = client.get(f"/api/v1/curations/{w.cur}", headers=_h(who))
    assert r.status_code == 200, r.text
    body = r.json()
    return body["can_review"], body["has_approved"], body["approvals_remaining"]


def _submit(client: TestClient, w: W) -> None:
    lock = client.get(f"/api/v1/curations/{w.cur}", headers=_h(w.alice)).json()
    r = client.post(
        f"/api/v1/curations/{w.cur}/submit",
        json={"lock_version": lock["lock_version"]},
        headers=_h(w.alice),
    )
    assert r.status_code == 200, r.text


def _move(client: TestClient, w: W, who: UUID, stage: str) -> Any:
    return client.post(
        f"/api/v1/workflow/curation/{w.cur}/transition",
        json={"target_stage": stage, "notes": "x"},
        headers=_h(who),
    )


def test_approver_sees_count_until_the_second_reviewer_completes(
    client: TestClient, w: W
) -> None:
    _submit(client, w)
    assert _view(client, w, w.bob) == (True, False, 2)
    # D1: the author (platform admin) and a non-member platform admin never review
    for who in (w.alice, w.dave):
        assert _view(client, w, who) == (False, False, 2)
        assert _move(client, w, who, "active").status_code == 400
    assert _move(client, w, w.bob, "active").json()["to_stage"] == "review"
    assert _view(client, w, w.bob) == (False, True, 1)
    # approving again is not counted
    assert _move(client, w, w.bob, "active").json()["to_stage"] == "review"
    assert _view(client, w, w.carol) == (True, False, 1)
    assert _move(client, w, w.carol, "active").json()["to_stage"] == "active"
    assert _view(client, w, w.bob) == (False, False, None)


def test_resubmit_starts_a_new_approval_round(client: TestClient, w: W) -> None:
    _submit(client, w)
    assert _move(client, w, w.bob, "active").status_code == 200
    assert _move(client, w, w.carol, "curation").status_code == 200
    _submit(client, w)
    # bob's approval belongs to the earlier round
    assert _view(client, w, w.bob) == (True, False, 2)
    assert _move(client, w, w.bob, "active").json()["to_stage"] == "review"
    assert _view(client, w, w.bob) == (False, True, 1)
    assert _view(client, w, w.carol) == (True, False, 1)
