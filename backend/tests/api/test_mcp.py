"""MCP server (#462): tool list, parity with the API per role, auth, channel, errors."""

import asyncio
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.deps import PAT_BLOCKED_OPERATIONS
from app.core.security import get_password_hash
from app.crud import personal_access_token as pat_crud
from app.main import app
from app.mcp.audit import (
    ChannelHeaderMiddleware,
    error_code,
    mark_internal,
    request_channel,
)
from app.mcp.server import EXCLUDED_OPERATIONS, tool_names
from app.models import CurationNew, Gene, PrecurationNew, Scope, UserNew
from app.schemas.personal_access_token import PersonalAccessTokenCreate

pytestmark = pytest.mark.unit

SNAPSHOT = Path(__file__).with_name("mcp_tools.snapshot")
ACCEPT = {"Accept": "application/json, text/event-stream"}


def pat(db: Session, user: UserNew, scopes: list[str] | None = None) -> str:
    obj = PersonalAccessTokenCreate(
        name="claude code",
        expires_at=datetime.now(UTC) + timedelta(days=1),
        scopes=scopes or ["read", "write"],
    )
    return pat_crud.create(db, user_id=user.id, obj_in=obj)[1]


def rpc(client: TestClient, token: str | None, method: str, params: dict) -> Any:
    headers = {**ACCEPT, **({"Authorization": f"Bearer {token}"} if token else {})}
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    return client.post("/mcp", json=body, headers=headers)


def call(client: TestClient, token: str, name: str, **args: Any) -> dict:
    r = rpc(client, token, "tools/call", {"name": name, "arguments": args})
    assert r.status_code == 200, r.text
    return r.json()["result"]


def status_of(result: dict) -> int:
    """HTTP status behind a tool result (200 for any success)."""
    if not result.get("isError"):
        return 200
    match = re.search(r"HTTP (\d{3})", result["content"][0]["text"])
    assert match, result
    return int(match.group(1))


def _api_operations() -> list[tuple[str, str, dict]]:
    return [
        (method.upper(), path, op)
        for path, ops in app.openapi()["paths"].items()
        if path.startswith("/api/v1/")
        for method, op in ops.items()
    ]


def test_tool_list_matches_snapshot(
    client: TestClient, db_session: Session, test_user_admin: UserNew
) -> None:
    tools = rpc(client, pat(db_session, test_user_admin), "tools/list", {}).json()
    lines = sorted(
        f"{t['name']} read_only={t['annotations']['readOnlyHint']} "
        f"destructive={t['annotations']['destructiveHint']}"
        for t in tools["result"]["tools"]
    )
    assert lines == SNAPSHOT.read_text().splitlines()


def test_every_api_operation_has_a_tool_except_documented_exclusions(
    client: TestClient, db_session: Session, test_user_admin: UserNew
) -> None:
    tools = rpc(client, pat(db_session, test_user_admin), "tools/list", {}).json()
    listed = {t["name"] for t in tools["result"]["tools"]}
    names = tool_names(app.openapi())
    expected = {
        names[op["operationId"]]
        for method, path, op in _api_operations()
        if (method, path) not in EXCLUDED_OPERATIONS
    }
    assert listed == expected
    assert set(PAT_BLOCKED_OPERATIONS) <= set(EXCLUDED_OPERATIONS)
    assert all(reason for reason in EXCLUDED_OPERATIONS.values())


# Routes that call HGNC, PubMed, HPO or OMIM: tests never hit the network
_NETWORK = re.compile(r"/(external-validation|ontology|publications)\b|/genes/resolve")


@pytest.mark.parametrize("role", ["admin", "curator", "viewer", "outsider"])
def test_each_role_gets_the_same_status_through_mcp_and_api(
    role: str,
    client: TestClient,
    db_session: Session,
    test_user_admin: UserNew,
    test_user_curator: UserNew,
    test_user_viewer: UserNew,
    test_scope: Scope,
    test_gene: Gene,
    test_curation: CurationNew,
    test_precuration: PrecurationNew,
) -> None:
    outsider = UserNew(
        id=uuid4(),
        email="outsider@test.com",
        hashed_password=get_password_hash("x"),
        name="Outsider",
        role="user",
        is_active=True,
    )
    db_session.add(outsider)
    db_session.commit()
    users = {
        "admin": test_user_admin,
        "curator": test_user_curator,
        "viewer": test_user_viewer,
        "outsider": outsider,
    }
    token = pat(db_session, users[role])
    ids = {
        "scope_id": test_scope.id,
        "gene_id": test_gene.id,
        "curation_id": test_curation.id,
        "precuration_id": test_precuration.id,
        "user_id": test_user_curator.id,
        "curator_id": test_user_curator.id,
        "item_type": "curation",
        "item_id": test_curation.id,
        "engine_name": "clingen_sop_v11",
        "symbol": "BRCA1",
    }
    names = tool_names(app.openapi())
    raw = TestClient(app, raise_server_exceptions=False)  # SQLite-only 500s compare too
    mismatches = []
    for method, path, op in _api_operations():
        if (method, path) in EXCLUDED_OPERATIONS or _NETWORK.search(path):
            continue
        params = re.findall(r"\{(\w+)\}", path)
        # Reads use real rows; writes target missing rows so no call changes state
        args = {
            p: str(ids[p] if method == "GET" and p in ids else uuid4()) for p in params
        }
        if "item_type" in args:
            args["item_type"] = "curation"
        url = path.format(**args)
        # Same request both ways: path parameters only, no body or query
        api = raw.request(method, url, headers={"Authorization": f"Bearer {token}"})
        tool = status_of(call(client, token, names[op["operationId"]], **args))
        api_status = 200 if api.status_code < 300 else api.status_code
        if api_status != tool:
            mismatches.append((method, path, api.status_code, tool))
    assert mismatches == []


def test_mcp_requires_a_live_personal_access_token(
    client: TestClient, db_session: Session, test_user_admin: UserNew, admin_token: str
) -> None:
    assert rpc(client, None, "tools/list", {}).status_code == 401
    assert rpc(client, admin_token, "tools/list", {}).status_code == 401  # no JWTs
    assert rpc(client, "gc_pat_unknown", "tools/list", {}).status_code == 401


def test_tool_acts_as_the_token_owner_and_read_only_tokens_cannot_write(
    client: TestClient, db_session: Session, test_user_curator: UserNew
) -> None:
    me = call(client, pat(db_session, test_user_curator), "read_users_me")
    assert me["structuredContent"]["id"] == str(test_user_curator.id)

    result = call(
        client,
        pat(db_session, test_user_curator, ["read"]),
        "mark_all_notifications_read",
    )
    assert result["isError"] is True
    assert result["content"][0]["text"] == (
        "forbidden: HTTP 403: This token is read-only"
    )


def test_not_found_maps_to_a_closed_error_code(
    client: TestClient, db_session: Session, test_user_admin: UserNew
) -> None:
    result = call(
        client,
        pat(db_session, test_user_admin),
        "get_scope_details",
        scope_id=str(uuid4()),
    )
    assert result["content"][0]["text"].startswith("not_found: HTTP 404")


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (400, "invalid_input"),
        (401, "forbidden"),
        (403, "forbidden"),
        (404, "not_found"),
        (409, "conflict"),
        (422, "invalid_input"),
        (429, "rate_limited"),
        (500, "internal"),
        (503, "upstream_unavailable"),
    ],
)
def test_error_codes_are_a_closed_set(status: int, code: str) -> None:
    assert error_code(status) == code


def test_destructive_tools_are_flagged(
    client: TestClient, db_session: Session, test_user_admin: UserNew
) -> None:
    tools = rpc(client, pat(db_session, test_user_admin), "tools/list", {}).json()
    by_name = {t["name"]: t for t in tools["result"]["tools"]}
    for name in (
        "delete_scope",
        "approve_precuration",
        "submit_peer_review",
        "publish_methodology_version",
        "execute_workflow_transition",
    ):
        assert by_name[name]["annotations"]["destructiveHint"] is True, name
        assert by_name[name]["description"].startswith("Destructive")
    assert by_name["list_scopes"]["annotations"]["readOnlyHint"] is True
    assert by_name["save_draft_curations"]["annotations"]["destructiveHint"] is False


def test_only_in_process_calls_may_carry_the_channel_headers() -> None:
    seen: list[tuple[dict, object]] = []

    async def inner(scope: Any, receive: Any, send: Any) -> None:
        seen.append((dict(scope["headers"]), request_channel.get()))

    guarded = ChannelHeaderMiddleware(inner)
    scope = {
        "type": "http",
        "headers": [
            (b"x-gc-channel", b"mcp"),
            (b"x-gc-client", b"a%20b"),
            (b"x", b"1"),
        ],
    }
    asyncio.run(guarded(scope, None, None))  # type: ignore[arg-type]
    asyncio.run(mark_internal(guarded)(scope, None, None))  # type: ignore[arg-type]

    assert seen[0] == ({b"x": b"1"}, None)  # spoofed from outside: dropped
    assert seen[1][1] == ("mcp", "a b")


def test_personal_access_tokens_share_their_owners_rate_limit_bucket(
    client: TestClient,
    db_session: Session,
    test_user_curator: UserNew,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.api_config import FeatureFlagsConfig, RateLimitConfig

    monkeypatch.setattr(
        "app.middleware.rate_limit.get_feature_flags",
        lambda: FeatureFlagsConfig(enable_rate_limiting=True),
    )
    tiers = {
        "default": RateLimitConfig(requests_per_minute=1, burst_size=100),
        "authenticated": RateLimitConfig(requests_per_minute=1, burst_size=3),
    }
    monkeypatch.setattr(
        "app.middleware.rate_limit.get_rate_limit", lambda tier: tiers[tier]
    )
    monkeypatch.setattr(app, "middleware_stack", None)  # rebuilt: fresh buckets
    first, second = (
        pat(db_session, test_user_curator),
        pat(db_session, test_user_curator),
    )

    # One MCP tool call costs one request: its in-process API call is not counted again
    assert not call(client, first, "read_users_me").get("isError")
    me = {"Authorization": f"Bearer {second}"}
    codes = [client.get("/api/v1/auth/me", headers=me).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    assert client.get("/").status_code == 200  # the IP bucket is separate
