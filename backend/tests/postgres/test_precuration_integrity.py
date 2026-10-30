"""Precuration integrity through the API as app_user: one open precuration per disease
entity (#567), who may archive one (#284), and the scope admin's audited disease
correction of a legacy curation (#453)."""

import json
from collections.abc import Callable, Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_password_hash
from tests.postgres.test_split_entities import (
    A,
    W,
    _h,
    _owner,
    _rows,
    _submitted,
    client,
    w,
)

pytestmark = pytest.mark.postgres
# A legacy record: its disease entity started but empty, no linked precuration
LEGACY = {"summary": "ok", "entity_definition": {"lumping_splitting_rationale": "one"}}
__all__ = ["client", "w"]  # fixtures


@pytest.fixture
def member(w: W) -> Generator[Callable[[str], UUID], None, None]:
    """Adds an accepted member with this scope role; removed afterwards."""
    made: list[str] = []

    def add(role: str) -> UUID:
        uid = uuid4()
        made.append(str(uid))
        with _owner() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, 'user')",
                (str(uid), f"{uid}@integrity.org", get_password_hash("pw"), role),
            )
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, %s, %s, now())",
                (str(w.scope), str(uid), role, str(w.alice)),
            )
        return uid

    yield add
    with _owner() as conn, conn.cursor() as cur:
        # the scope first: its rows name these users (w's teardown finds it gone)
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(w.scope),))
        cur.execute(
            "DELETE FROM scope_memberships WHERE user_id = ANY(%s::uuid[])", (made,)
        )
        cur.execute("DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[])", (made,))
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (made,))


def _create(client: TestClient, w: W, evidence: dict, user: UUID) -> tuple[int, dict]:
    r = client.post(
        "/api/v1/precurations/",
        json={
            "gene_id": str(w.gene),
            "scope_id": str(w.scope),
            "precuration_schema_id": w.schema,
            "evidence_data": evidence,
        },
        headers=_h(user),
    )
    return r.status_code, r.json()


def test_an_entity_in_review_refuses_a_second_precuration(
    client: TestClient, w: W
) -> None:
    first = _submitted(w, A)
    code, body = _create(client, w, {**A, "mondo_id": " mondo:0000001 "}, w.alice)
    assert code == 409, body
    assert body["detail"]["precuration_id"] == first

    code, sus = _create(
        client, w, {**A, "relationship_type": "susceptibility"}, w.alice
    )
    assert code == 201, sus

    # A blank draft cannot be saved onto the entity in review either
    code, blank = _create(client, w, {}, w.alice)
    assert code == 201, blank
    r = client.patch(
        f"/api/v1/precurations/{blank['id']}/draft",
        json={"evidence_data": A, "lock_version": blank["lock_version"]},
        headers=_h(w.alice),
    )
    assert r.status_code == 409 and r.json()["detail"]["precuration_id"] == first
    assert _rows(
        "SELECT entity_key, lock_version FROM precurations WHERE id = %s", blank["id"]
    ) == [("", blank["lock_version"])]
    assert _rows(
        "SELECT count(*) FROM precurations WHERE gene_id = %s AND entity_key = %s",
        str(w.gene),
        "MONDO:0000001|AD",
    ) == [(1,)]


def test_only_the_creator_or_a_scope_admin_archives_a_precuration(
    client: TestClient, w: W, member: Callable[[str], UUID]
) -> None:
    carol, dana = member("curator"), member("admin")
    drafts = [
        _create(client, w, {"mondo_id": f"MONDO:000000{i}"}, w.alice)[1]["id"]
        for i in (1, 2)
    ]

    def status(pid: str) -> str:
        return str(
            _rows("SELECT status::text FROM precurations WHERE id = %s", pid)[0][0]
        )

    r = client.delete(f"/api/v1/precurations/{drafts[0]}", headers=_h(carol))
    assert r.status_code == 403 and status(drafts[0]) == "draft"
    for pid, user in zip(drafts, (w.alice, dana), strict=True):
        r = client.delete(f"/api/v1/precurations/{pid}", headers=_h(user))
        assert r.status_code == 204, r.text
        assert status(pid) == "archived"


def test_a_scope_admin_corrects_a_legacy_disease_gap(
    client: TestClient, w: W, member: Callable[[str], UUID]
) -> None:
    """No own disease answers, no linked precuration: submit is refused and changes
    nothing; a curator may not correct it, a scope admin may (audited), then it submits."""
    cid = str(uuid4())
    with _owner() as conn, conn.cursor() as cur:
        # the seeded ClinGen SOP v11 curation form, which requires the disease entity
        cur.execute(
            "SELECT id FROM workflow_pairs WHERE name = 'ClinGen_Complete_Workflow'"
        )
        pair = str(cur.fetchone()[0])
        cur.execute(
            "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, status, "
            "workflow_stage, is_draft, created_by, evidence_data) VALUES "
            "(%s, %s, %s, %s, 'draft', 'curation', true, %s, %s)",
            (
                cid,
                str(w.gene),
                str(w.scope),
                pair,
                str(w.alice),
                json.dumps(LEGACY),
            ),
        )
    state = "SELECT evidence_data, status::text, workflow_stage::text, lock_version, entity_key FROM curations WHERE id = %s"
    before = _rows(state, cid)
    check = client.post(
        f"/api/v1/workflow/curation/{cid}/validate-transition",
        json={"target_stage": "review"},
        headers=_h(w.alice),
    )
    assert set(check.json()["missing_fields"]) == {
        "entity_definition.disease_name",
        "entity_definition.mondo_id",
        "entity_definition.mode_of_inheritance",
    }, check.text
    submit = client.post(
        f"/api/v1/curations/{cid}/submit",
        json={"lock_version": before[0][3]},
        headers=_h(w.alice),
    )
    assert submit.status_code == 400, submit.text
    assert _rows(state, cid) == before

    fix = {
        "disease_name": "a",
        "mondo_id": "MONDO:0000001",
        "mode_of_inheritance": "AD",
        "reason": "legacy import lost the disease",
        "lock_version": before[0][3],
    }
    url = f"/api/v1/curations/{cid}/disease-correction"
    carol, dana = member("curator"), member("admin")
    assert client.post(url, json=fix, headers=_h(carol)).status_code == 403
    assert _rows(state, cid) == before
    r = client.post(url, json=fix, headers=_h(dana))
    assert r.status_code == 200, r.text
    assert _rows(state, cid)[0][4] == "MONDO:0000001|AD"
    audit = _rows(
        "SELECT user_id::text, changes->>'reason', old_values->>'entity_key', "
        "new_values->>'mondo_id' FROM audit_log WHERE entity_id = %s "
        "AND change_type = 'disease_correction'",
        cid,
    )
    assert audit == [(str(dana), fix["reason"], "", "MONDO:0000001")]

    lock = r.json()["lock_version"]
    submit = client.post(
        f"/api/v1/curations/{cid}/submit",
        json={"lock_version": lock},
        headers=_h(w.alice),
    )
    assert submit.status_code == 200, submit.text

    # D1: the scope admin who corrected it cannot approve it; nothing moves
    under_review = _rows(state, cid)
    r = client.post(
        f"/api/v1/workflow/curation/{cid}/transition",
        json={"target_stage": "active", "notes": "ok"},
        headers=_h(dana),
    )
    assert r.status_code >= 400 and "your own work" in r.text, r.text
    assert _rows(state, cid) == under_review

    # ...nor be assigned, nor submit a peer review (an assignment from before is refused)
    r = client.post(
        f"/api/v1/workflow/curation/{cid}/assign-reviewer",
        json={"reviewer_id": str(dana)},
        headers=_h(w.alice),
    )
    assert r.status_code == 400 and "4-eyes" in r.text, r.text
    rid = str(uuid4())
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO reviews (id, curation_id, reviewer_id, assigned_by, status) "
            "VALUES (%s, %s, %s, %s, 'pending')",
            (rid, cid, str(dana), str(w.alice)),
        )
    r = client.post(
        f"/api/v1/workflow/reviews/{rid}/submit",
        json={"decision": "approve"},
        headers=_h(dana),
    )
    assert r.status_code == 400 and "corrected" in r.text, r.text
    assert _rows("SELECT status::text FROM reviews WHERE id = %s", rid) == [
        ("pending",)
    ]
    assert _rows(state, cid) == under_review
