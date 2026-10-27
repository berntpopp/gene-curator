"""MCP tools run the real API as app_user under RLS, with the caller's own token (#462)."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from tests.postgres.test_reviewer_rls import (  # noqa: F401 (fixtures)
    W,
    _activate_curation,
    _h,
    _owner,
    _owner_scalar,
    client,
    w,
)

pytestmark = pytest.mark.postgres


def _pat(tc: TestClient, uid: UUID) -> str:
    expires = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    r = tc.post(
        "/api/v1/me/tokens/",
        json={"name": "claude code", "expires_at": expires},
        headers=_h(uid),
    )
    assert r.status_code == 201, r.text
    return str(r.json()["token"])


def _tool(tc: TestClient, token: str, name: str, **args: Any) -> dict:
    r = tc.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": args},
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
        },
    )
    assert r.status_code == 200, r.text
    return dict(r.json()["result"])


def _error(result: dict) -> str:
    assert result.get("isError") is True, result
    return str(result["content"][0]["text"])


def test_outsider_cannot_read_a_draft(client: TestClient, w: W) -> None:  # noqa: F811
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE curations SET status = 'draft', workflow_stage = 'curation', "
            "is_draft = true WHERE id = %s",
            (str(w.cur),),
        )
    frank = _pat(client, w.frank)

    assert _error(
        _tool(client, frank, "get_curation", curation_id=str(w.cur))
    ).startswith("not_found: HTTP 404")
    listed = _tool(client, frank, "list_curations", scope_id=str(w.scope))
    assert str(w.cur) not in str(listed)
    # The author still reads it through MCP: the token carries her own identity
    alice = _tool(client, _pat(client, w.alice), "get_curation", curation_id=str(w.cur))
    assert json.loads(alice["content"][0]["text"])["id"] == str(w.cur)


def test_nobody_approves_their_own_work(client: TestClient, w: W) -> None:  # noqa: F811
    _activate_curation(w)
    alice = _tool(
        client, _pat(client, w.alice), "approve_precuration", precuration_id=str(w.pre)
    )
    assert _error(alice).startswith("forbidden: HTTP 403")
    bob_own = _tool(
        client,
        _pat(client, w.bob),
        "approve_precuration",
        precuration_id=str(w.own_pre),
    )
    assert _error(bob_own).startswith("forbidden: HTTP 403")
    for pre in (w.pre, w.own_pre):
        status = _owner_scalar(
            "SELECT status::text FROM precurations WHERE id = %s", str(pre)
        )
        assert status == "submitted"


def test_reviewer_approves_someone_elses_work_audited_as_mcp(
    client: TestClient,  # noqa: F811
    w: W,  # noqa: F811
) -> None:
    _activate_curation(w)
    result = _tool(
        client, _pat(client, w.bob), "approve_precuration", precuration_id=str(w.pre)
    )
    assert not result.get("isError"), result
    assert json.loads(result["content"][0]["text"])["curation_created"] is True

    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT user_id, change_metadata FROM audit_log "
            "WHERE entity_id = %s AND operation = 'UPDATE'",
            (str(w.pre),),
        )
        rows = cur.fetchall()
    assert rows
    assert all(
        str(uid) == str(w.bob)
        and meta["channel"] == "mcp"
        and meta["client"] == "claude code"
        for uid, meta in rows
    )


def test_api_writes_are_not_marked_as_mcp(client: TestClient, w: W) -> None:  # noqa: F811
    _activate_curation(w)
    r = client.post(
        f"/api/v1/precurations/{w.pre}/approve",
        headers={**_h(w.bob), "X-GC-Channel": "mcp", "X-GC-Client": "spoofed"},
    )
    assert r.status_code == 200, r.text
    channels = _owner_scalar(
        "SELECT count(*) FROM audit_log WHERE entity_id = %s "
        "AND change_metadata ? 'channel'",
        str(w.pre),
    )
    assert channels == 0


def test_inactive_scope_refuses_writes_with_409(client: TestClient, w: W) -> None:  # noqa: F811
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE scopes SET is_active = false WHERE id = %s", (str(w.scope),)
        )
    root = _pat(client, w.root)  # platform admin: no bypass for inactive scopes

    result = _tool(client, root, "delete_curation", curation_id=str(w.cur))
    assert _error(result).startswith("conflict: HTTP 409")
    api = client.delete(
        f"/api/v1/curations/{w.cur}", headers={"Authorization": f"Bearer {root}"}
    )
    assert api.status_code == 409
