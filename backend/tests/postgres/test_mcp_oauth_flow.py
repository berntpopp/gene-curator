"""MCP OAuth runs the real flow as app_user under RLS; tokens get the PAT treatment (#462)."""

from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core import database
from tests.api.test_mcp_oauth import (
    approve,
    authorize,
    exchange,
    pkce,
    refresh,
    register,
    whoami,
)
from tests.postgres.test_mcp_flows import _error, _tool
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


@pytest.fixture
def clients() -> Generator[list[str], None, None]:
    registered: list[str] = []
    yield registered
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM oauth_clients WHERE client_id = ANY(%s)", (registered,)
        )


def _oauth(tc: TestClient, uid: UUID, clients: list[str]) -> tuple[str, dict[str, str]]:
    session = _h(uid)["Authorization"].removeprefix("Bearer ")
    client_id = register(tc)["client_id"]
    clients.append(client_id)
    verifier, challenge = pkce()
    code = approve(tc, session, authorize(tc, client_id, challenge))
    r = exchange(tc, client_id, code, verifier)
    assert r.status_code == 200, r.text
    return client_id, r.json()


def test_full_flow_rotation_revocation_and_expiry(
    client: TestClient,  # noqa: F811
    w: W,  # noqa: F811
    clients: list[str],
) -> None:
    client_id, tokens = _oauth(client, w.alice, clients)
    assert whoami(client, tokens["access_token"]).status_code == 200
    # nothing secret at rest: only hashes
    stored = _owner_scalar(
        "SELECT count(*) FROM oauth_grants WHERE user_id = %s AND code_hash IS NULL "
        "AND refresh_token_hash IS NOT NULL",
        str(w.alice),
    )
    assert stored == 1

    rotated = refresh(client, client_id, tokens["refresh_token"]).json()
    assert whoami(client, tokens["access_token"]).status_code == 401
    assert whoami(client, rotated["access_token"]).status_code == 200

    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE personal_access_tokens SET expires_at = NOW() - INTERVAL '1 second' "
            "WHERE user_id = %s",
            (str(w.alice),),
        )
    assert whoami(client, rotated["access_token"]).status_code == 401  # expired
    again = refresh(client, client_id, rotated["refresh_token"]).json()
    assert whoami(client, again["access_token"]).status_code == 200

    pat_id = _owner_scalar(
        "SELECT id FROM personal_access_tokens WHERE user_id = %s", str(w.alice)
    )
    r = client.delete(f"/api/v1/me/tokens/{pat_id}", headers=_h(w.alice))
    assert r.status_code == 204, r.text
    assert whoami(client, again["access_token"]).status_code == 401  # revoked
    assert refresh(client, client_id, again["refresh_token"]).status_code == 401


def test_oauth_calls_keep_rls_and_d1(
    client: TestClient,  # noqa: F811
    w: W,  # noqa: F811
    clients: list[str],
) -> None:
    _activate_curation(w)
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE curations SET status = 'draft', workflow_stage = 'curation', "
            "is_draft = true WHERE id = %s",
            (str(w.cur),),
        )
    frank = _oauth(client, w.frank, clients)[1]["access_token"]
    assert _error(
        _tool(client, frank, "get_curation", curation_id=str(w.cur))
    ).startswith("not_found: HTTP 404")

    alice = _oauth(client, w.alice, clients)[1]["access_token"]
    own = _tool(client, alice, "approve_precuration", precuration_id=str(w.pre))
    assert _error(own).startswith("forbidden: HTTP 403")
    # the account-operation block applies to OAuth tokens as to PATs
    r = client.post(
        "/api/v1/me/tokens/",
        json={"name": "x", "expires_at": "2099-01-01T00:00:00Z"},
        headers={"Authorization": f"Bearer {alice}"},
    )
    assert r.status_code == 403

    bob = _oauth(client, w.bob, clients)[1]["access_token"]
    ok = _tool(client, bob, "approve_precuration", precuration_id=str(w.pre))
    assert not ok.get("isError"), ok
    meta = _owner_scalar(
        "SELECT change_metadata FROM audit_log WHERE entity_id = %s "
        "AND operation = 'UPDATE' AND user_id = %s LIMIT 1",
        str(w.pre),
        str(w.bob),
    )
    assert isinstance(meta, dict)
    assert meta["channel"] == "mcp" and meta["client"] == "OAuth: Claude Code"


def test_a_user_sees_no_one_elses_grants(
    client: TestClient,  # noqa: F811
    w: W,  # noqa: F811
    clients: list[str],
) -> None:
    _oauth(client, w.alice, clients)
    with database.engine.connect() as conn:  # app_user
        database.apply_rls_user(conn, str(w.bob))
        seen = conn.execute(
            text("SELECT count(*) FROM oauth_grants WHERE user_id IS NOT NULL")
        ).scalar()
        changed = conn.execute(
            text("UPDATE oauth_grants SET user_id = :b WHERE user_id = :a"),
            {"a": str(w.alice), "b": str(w.bob)},
        ).rowcount
        conn.rollback()
    assert seen == 0 and changed == 0
