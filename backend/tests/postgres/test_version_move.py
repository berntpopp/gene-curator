"""Move to version as app_user on PostgreSQL (#591, migration 078).

A platform admin (no scope membership) moves an active curation whose class changes:
the approved row stays active and exported while an open copy on the new version is in
review (078 lets the admin insert it), every row is audit-logged and a second run
changes nothing. Re-pinning back to an older version is still refused.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from tests.postgres.conftest import set_test_user_context
from tests.postgres.test_methodology_versions import W, _h, _owner, client, w

pytestmark = pytest.mark.postgres
__all__ = ["client", "w"]


def test_admin_moves_a_curation_to_the_next_version(
    client: TestClient, w: W, db: Session
) -> None:
    r = client.post(
        "/api/v1/curations/",
        json={
            "gene_id": str(w.genes[0]),
            "scope_id": str(w.scope),
            "workflow_pair_id": w.pair,
            "evidence_data": {},
        },
        headers=_h(w.alice),
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    with _owner() as conn, conn.cursor() as cur:  # approved earlier as "definitive"
        cur.execute(
            "UPDATE curations SET status = 'active', workflow_stage = 'active', "
            "is_draft = false, computed_verdict = 'definitive' WHERE id = %s",
            (cid,),
        )
        cur.execute(
            "INSERT INTO active_curations (gene_id, scope_id, curation_id) "
            "VALUES (%s, %s, %s)",
            (str(w.genes[0]), str(w.scope), cid),
        )
    v2 = client.post(
        f"/api/v1/schemas/curation-schemas/{w.schema}/versions", headers=_h(w.admin)
    )
    assert v2.status_code == 201, v2.text
    url = f"/api/v1/schemas/curation-schemas/{w.schema}/move-to-version"

    plan = client.post(url, headers=_h(w.admin))
    assert plan.status_code == 200, plan.text
    (item,) = plan.json()["items"]
    assert (item["from_version"], item["to_version"], item["back_to"]) == (
        1,
        2,
        "review",
    )
    assert client.post(f"{url}?dry_run=false", headers=_h(w.alice)).status_code == 403

    r = client.post(f"{url}?dry_run=false", headers=_h(w.admin))
    assert r.status_code == 200, r.text
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id = %s, methodology_version_id, status, computed_verdict "
            "FROM curations WHERE gene_id = %s ORDER BY created_at",
            (cid, str(w.genes[0])),
        )
        rows = cur.fetchall()
        cur.execute(
            "SELECT changes->>'old_class', new_status FROM audit_log "
            "WHERE change_type = 'version_move' AND changes->>'id' = %s",
            (cid,),
        )
        audit = cur.fetchall()
    (active, copy) = rows
    assert active == (True, w.v1, "active", "definitive")  # untouched
    assert (copy[0], str(copy[1]), copy[2]) == (False, v2.json()["id"], "in_review")
    assert copy[3] != "definitive"
    assert audit == [("definitive", "in_review")]

    # during the review the export still shows the approved result
    export = client.get("/api/v1/export/curations", headers=_h(w.alice))
    assert export.status_code == 200, export.text
    (item,) = [i for i in export.json()["items"] if i["curation_id"] == cid]
    assert (item["computed_verdict"], item["status"]) == ("definitive", "active")

    again = client.post(f"{url}?dry_run=false", headers=_h(w.admin))
    assert again.status_code == 200 and again.json()["items"] == []

    # 078 still refuses moving back, for admins too
    set_test_user_context(db, str(w.admin))
    with pytest.raises(DBAPIError, match="pinned"), db.begin_nested():
        db.execute(
            text(
                "UPDATE curations SET methodology_version_id = :v "
                "WHERE gene_id = :g AND status = 'in_review'"
            ),
            {"v": w.v1, "g": w.genes[0]},
        )


def test_inactive_scope_rows_are_skipped_in_plan_and_apply(
    client: TestClient, w: W
) -> None:
    """RLS (054) refuses updates in an inactive scope: plan and apply skip them alike."""
    other, gene = uuid4(), w.genes[1]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, is_active, "
            "created_by) VALUES (%s, %s, 'Old', false, false, %s)",
            (str(other), f"old-{other}", str(w.alice)),
        )
        cur.execute(
            "INSERT INTO curations (gene_id, scope_id, workflow_pair_id, evidence_data, "
            "created_by) VALUES (%s, %s, %s, '{}', %s) RETURNING id",
            (str(gene), str(other), w.pair, str(w.alice)),
        )
        cid = str(cur.fetchone()[0])
    try:
        assert (
            client.post(
                f"/api/v1/schemas/curation-schemas/{w.schema}/versions",
                headers=_h(w.admin),
            ).status_code
            == 201
        )
        url = f"/api/v1/schemas/curation-schemas/{w.schema}/move-to-version"
        plan = client.post(url, headers=_h(w.admin))
        applied = client.post(f"{url}?dry_run=false", headers=_h(w.admin))
        assert applied.status_code == 200, applied.text
        (item,) = plan.json()["items"]
        assert (item["id"], item["skipped"]) == (
            cid,
            "This scope is inactive; its curations are read-only",
        )
        assert applied.json()["items"] == plan.json()["items"]
        with _owner() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT methodology_version_id FROM curations WHERE id = %s", (cid,)
            )
            assert str(cur.fetchone()[0]) == w.v1
    finally:
        with _owner() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM scopes WHERE id = %s", (str(other),))
