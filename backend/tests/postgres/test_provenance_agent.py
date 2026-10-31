"""#593 on PostgreSQL as app_user: an MCP write's agent block lands in audit_log (080)
with the person it acted for; a REST write carries none; the ClinGen bundle with
source cells imports as a new version of the seeded schema."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.postgres.test_mcp_flows import _pat, _tool
from tests.postgres.test_reviewer_rls import (  # noqa: F401 (fixtures)
    W,
    _h,
    _owner,
    _owner_scalar,
    client,
    w,
)

pytestmark = pytest.mark.postgres

AGENT = {"model": "claude-opus-5-5", "agent": "Claude Code", "tools_used": ["x"]}
ROW = {"id": "r1", "label": "L", "sources": [{"kind": "pmid", "id": "123"}]}


def _draft(w: W) -> None:  # noqa: F811
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE curations SET status = 'draft', workflow_stage = 'curation', "
            "is_draft = true WHERE id = %s",
            (str(w.cur),),
        )


def _lock(w: W) -> int:  # noqa: F811
    return int(
        _owner_scalar("SELECT lock_version FROM curations WHERE id = %s", str(w.cur))
    )


def test_agent_block_lands_in_audit_log(client: TestClient, w: W) -> None:  # noqa: F811
    _draft(w)
    result = _tool(
        client,
        _pat(client, w.alice),
        "save_draft_curations",
        curation_id=str(w.cur),
        lock_version=_lock(w),
        evidence_data={"rows": [ROW]},
        agent=AGENT,
    )
    assert not result.get("isError"), result
    meta = _owner_scalar(
        "SELECT change_metadata FROM audit_log WHERE entity_id = %s "
        "AND change_metadata ? 'agent' ORDER BY id DESC LIMIT 1",
        str(w.cur),
    )
    assert meta["channel"] == "mcp"
    assert meta["agent"] == {**AGENT, "actedOnBehalfOf": str(w.alice)}
    stored = _owner_scalar(
        "SELECT row_provenance FROM curations WHERE id = %s", str(w.cur)
    )
    assert stored["rows#r1"]["added_by"]["agent"] == AGENT

    # A REST write, and an MCP write without the block, record no agent
    r = client.patch(
        f"/api/v1/curations/{w.cur}/draft",
        json={"evidence_data": {"rows": []}, "lock_version": _lock(w)},
        headers=_h(w.alice),
    )
    assert r.status_code == 200, r.text
    plain = _tool(
        client,
        _pat(client, w.alice),
        "save_draft_curations",
        curation_id=str(w.cur),
        lock_version=_lock(w),
        evidence_data={"rows": [ROW]},
    )
    assert not plain.get("isError"), plain
    agents = _owner_scalar(
        "SELECT count(*) FROM audit_log WHERE entity_id = %s "
        "AND change_metadata ? 'agent'",
        str(w.cur),
    )
    assert agents == 1


def test_clingen_bundle_imports_as_a_new_version(client: TestClient, w: W) -> None:  # noqa: F811
    bundle = json.loads(
        (
            Path(__file__).parents[3] / "docs/schemas/clingen/clingen-methodology.json"
        ).read_text()
    )
    r = client.post(
        "/api/v1/schemas/methodologies/import?dry_run=true",
        json=bundle,
        headers=_h(w.root),
    )
    assert r.status_code == 200, r.text
    actions = {i["name"]: i["action"] for i in r.json()["items"]}
    assert actions["ClinGen Gene-Disease Validity SOP"] == "new_version"
    assert actions["ClinGen Precuration"] == "unchanged"
