"""approvals_require_session (074, #560) through the real API as app_user under RLS:
agents (PAT, MCP OAuth token) comment and request changes, a signed-in person approves."""

from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.postgres.test_mcp_flows import _error, _pat, _tool
from tests.postgres.test_mcp_oauth_flow import _oauth
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

SIGNED_IN = "Approvals in this scope need a signed-in person"


@pytest.fixture
def clients() -> Generator[list[str], None, None]:
    registered: list[str] = []
    yield registered
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM oauth_clients WHERE client_id = ANY(%s)", (registered,)
        )


def _status(x: W) -> object:
    return _owner_scalar(
        "SELECT status::text FROM precurations WHERE id = %s", str(x.pre)
    )


def _review(x: W) -> str:
    review = str(uuid4())
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE curations SET status = 'in_review', submitted_at = now() - "
            "interval '1 hour' WHERE id = %s",
            (str(x.cur),),
        )
        cur.execute(
            "INSERT INTO reviews (id, curation_id, reviewer_id, assigned_by) "
            "VALUES (%s, %s, %s, %s)",
            (review, str(x.cur), str(x.bob), str(x.alice)),
        )
    return review


def test_option_on_agents_comment_and_a_signed_in_reviewer_approves(
    client: TestClient,  # noqa: F811
    w: W,  # noqa: F811
    clients: list[str],
) -> None:
    on = client.patch(
        f"/api/v1/scopes/{w.scope}",
        json={"approvals_require_session": True},
        headers=_h(w.ann),
    )
    assert on.status_code == 200, on.text
    pat = _pat(client, w.bob)
    _, oauth = _oauth(client, w.bob, clients)

    r = client.post(
        f"/api/v1/precurations/{w.pre}/approve",
        headers={"Authorization": f"Bearer {pat}"},
    )
    assert r.status_code == 403 and r.json()["detail"].startswith(SIGNED_IN)
    for token in (pat, oauth["access_token"]):
        result = _tool(client, token, "approve_precuration", precuration_id=str(w.pre))
        assert SIGNED_IN in _error(result)
    assert _status(w) == "submitted"

    # the agent still comments and requests changes on the curation in review
    comment = _tool(
        client,
        pat,
        "create_review_comment",
        curation_id=str(w.cur),
        item_path="evidence_data.summary",
        body="check this row",
    )
    assert not comment.get("isError"), comment
    review = _review(w)
    approve = _tool(
        client, pat, "submit_peer_review", review_id=review, decision="approve"
    )
    assert SIGNED_IN in _error(approve)
    changes = _tool(
        client, pat, "submit_peer_review", review_id=review, decision="request_changes"
    )
    assert not changes.get("isError"), changes

    _activate_curation(w)
    by_person = client.post(f"/api/v1/precurations/{w.pre}/approve", headers=_h(w.bob))
    assert by_person.status_code == 200, by_person.text
    assert _status(w) == "approved"


def test_option_off_a_token_approves_as_before(
    client: TestClient,  # noqa: F811
    w: W,  # noqa: F811
) -> None:
    _activate_curation(w)
    r = client.post(
        f"/api/v1/precurations/{w.pre}/approve",
        headers={"Authorization": f"Bearer {_pat(client, w.bob)}"},
    )
    assert r.status_code == 200, r.text
    assert _status(w) == "approved"


def test_option_on_a_token_cannot_add_or_promote_a_reviewer(
    client: TestClient,  # noqa: F811
    w: W,  # noqa: F811
) -> None:
    """A scope-admin token adding an account it controls would lift the gate (#560)."""
    members = f"/api/v1/scopes/{w.scope}/members"
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE scopes SET approvals_require_session = true WHERE id = %s",
            (str(w.scope),),
        )
    pat = {"Authorization": f"Bearer {_pat(client, w.ann)}"}
    newcomer = {"user_id": str(w.frank), "role": "reviewer"}

    added = client.post(members, json=newcomer, headers=pat)
    assert added.status_code == 403, added.text
    promoted = client.patch(
        f"{members}/{w.carol}", json={"role": "reviewer"}, headers=pat
    )
    assert promoted.status_code == 403, promoted.text
    role = (
        "SELECT role::text FROM scope_memberships WHERE scope_id = %s AND user_id = %s"
    )
    assert _owner_scalar(role, str(w.scope), str(w.frank)) is None
    assert _owner_scalar(role, str(w.scope), str(w.carol)) == "viewer"

    by_person = client.post(members, json=newcomer, headers=_h(w.ann))
    assert by_person.status_code == 201, by_person.text
    assert _owner_scalar(role, str(w.scope), str(w.frank)) == "reviewer"


def test_option_on_a_token_cannot_remove_a_reviewer(
    client: TestClient,  # noqa: F811
    w: W,  # noqa: F811
) -> None:
    """An agent removing the human reviewers would lift the gate as well (#560)."""
    member = f"/api/v1/scopes/{w.scope}/members/{w.bob}"
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE scopes SET approvals_require_session = true WHERE id = %s",
            (str(w.scope),),
        )
    token = _pat(client, w.ann)
    removed = client.delete(member, headers={"Authorization": f"Bearer {token}"})
    assert removed.status_code == 403, removed.text
    r = client.post(
        "/mcp/full",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "remove_member",
                "arguments": {"scope_id": str(w.scope), "user_id": str(w.bob)},
            },
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
        },
    )
    assert r.status_code == 200, r.text
    assert "Member changes in this scope need" in _error(r.json()["result"])
    active = (
        "SELECT is_active FROM scope_memberships WHERE scope_id = %s AND user_id = %s"
    )
    assert _owner_scalar(active, str(w.scope), str(w.bob)) is True

    by_person = client.delete(member, headers=_h(w.ann))
    assert by_person.status_code == 204, by_person.text
    assert _owner_scalar(active, str(w.scope), str(w.bob)) is False
    back = client.patch(
        member, json={"is_active": True}, headers={"Authorization": f"Bearer {token}"}
    )
    assert back.status_code == 403, back.text
    assert _owner_scalar(active, str(w.scope), str(w.bob)) is False
