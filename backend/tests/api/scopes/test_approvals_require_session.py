"""approvals_require_session: with it on, tokens and MCP calls comment, request changes
and reject, but only a signed-in person approves (#560)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.deps import is_session_request
from app.models import PrecurationNew, Review
from app.models.models import CurationStatus, Scope, UserNew, WorkflowStage as S
from tests.api.scopes.factories import (
    auth_headers,
    make_curation,
    make_gene,
    make_precuration,
    make_user,
)

pytestmark = pytest.mark.unit

BASE = "/api/v1/workflow"
SIGNED_IN = "Approvals in this scope need a signed-in person"


def _pat(client: TestClient, user: UserNew) -> dict[str, str]:
    expires = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    r = client.post(
        "/api/v1/me/tokens/",
        json={"name": "judge agent", "expires_at": expires},
        headers=auth_headers(user),
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _gate(db: Session, scope: Scope, on: bool = True) -> None:
    scope.approvals_require_session = on
    db.commit()


def _pre(db: Session, scope: Scope, creator: UserNew) -> PrecurationNew:
    pre = make_precuration(
        db, scope=scope, gene=make_gene(db), creator=creator, stage=S.REVIEW
    )
    pre.status = CurationStatus.SUBMITTED
    db.commit()
    return pre


def test_token_cannot_approve_but_can_reject_and_request_changes(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
) -> None:
    _gate(db_session, scope_with_admin)
    pat = _pat(client, reviewer)
    pre = _pre(db_session, scope_with_admin, curator)

    for r in (
        client.post(f"/api/v1/precurations/{pre.id}/approve", headers=pat),
        client.post(
            f"{BASE}/precuration/{pre.id}/transition",
            json={"target_stage": "curation"},
            headers=pat,
        ),
    ):
        assert r.status_code == 403, r.text
        assert r.json()["detail"].startswith(SIGNED_IN)
    db_session.refresh(pre)
    assert pre.status == CurationStatus.SUBMITTED
    rejected = client.post(
        f"/api/v1/precurations/{pre.id}/reject", json={"reason": "no"}, headers=pat
    )
    assert rejected.status_code == 200, rejected.text

    cur = make_curation(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator
    )
    review = Review(id=uuid4(), curation_id=cur.id, reviewer_id=reviewer.id)
    db_session.add(review)
    db_session.commit()
    submit = f"{BASE}/reviews/{review.id}/submit"
    approve = client.post(submit, json={"decision": "approve"}, headers=pat)
    assert approve.status_code == 403 and SIGNED_IN in approve.json()["detail"]
    to_active = client.post(
        f"{BASE}/curation/{cur.id}/transition",
        json={"target_stage": "active"},
        headers=pat,
    )
    assert to_active.status_code == 403, to_active.text
    changes = client.post(
        submit, json={"decision": "request_changes", "comments": "x"}, headers=pat
    )
    assert changes.status_code == 200, changes.text


def test_signed_in_reviewer_approves_and_option_off_changes_nothing(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
) -> None:
    _gate(db_session, scope_with_admin)
    body = {"target_stage": "curation"}
    pre = _pre(db_session, scope_with_admin, curator)
    by_session = client.post(
        f"{BASE}/precuration/{pre.id}/transition",
        json=body,
        headers=auth_headers(reviewer),
    )
    assert by_session.status_code == 200, by_session.text

    _gate(db_session, scope_with_admin, on=False)
    pre = _pre(db_session, scope_with_admin, curator)
    by_token = client.post(
        f"{BASE}/precuration/{pre.id}/transition",
        json=body,
        headers=_pat(client, reviewer),
    )
    assert by_token.status_code == 200, by_token.text


def test_bulk_approval_by_token_fails_per_item(
    client: TestClient,
    db_session: Session,
    app_admin: UserNew,
    curator: UserNew,
    scope_with_admin: Scope,
) -> None:
    _gate(db_session, scope_with_admin)
    cur = make_curation(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator
    )
    r = client.post(
        f"{BASE}/bulk-transition",
        json={
            "item_ids": [str(cur.id)],
            "item_type": "curation",
            "target_stage": "active",
        },
        headers=_pat(client, app_admin),
    )
    assert r.status_code == 200, r.text
    assert r.json()["successful_transitions"] == []
    assert SIGNED_IN in r.json()["failed_transitions"][0]["error"]


def test_only_a_signed_in_scope_admin_changes_the_option(
    client: TestClient,
    db_session: Session,
    owner: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
) -> None:
    url = f"/api/v1/scopes/{scope_with_admin.id}"
    on = {"approvals_require_session": True}
    assert client.patch(url, json=on, headers=auth_headers(reviewer)).status_code == 403
    assert client.patch(url, json=on, headers=_pat(client, owner)).status_code == 403
    r = client.patch(url, json=on, headers=auth_headers(owner))
    assert r.status_code == 200 and r.json()["approvals_require_session"] is True
    # a token may still edit other settings, or resend the current value
    same = {**on, "description": "agents comment"}
    assert client.patch(url, json=same, headers=_pat(client, owner)).status_code == 200
    off = {"approvals_require_session": False}
    assert client.patch(url, json=off, headers=_pat(client, owner)).status_code == 403


def test_an_mcp_call_is_never_a_session() -> None:
    def req(**scope: object) -> Request:
        return Request({"type": "http", "headers": [], **scope})

    assert is_session_request(req())
    assert not is_session_request(req(**{"gene_curator.mcp_internal": True}))
    assert not is_session_request(req(state={"personal_access_token": True}))


def test_precuration_straight_to_active_is_an_approval_too(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
) -> None:
    _gate(db_session, scope_with_admin)
    pre = _pre(db_session, scope_with_admin, curator)
    r = client.post(
        f"{BASE}/precuration/{pre.id}/transition",
        json={"target_stage": "active"},
        headers=_pat(client, reviewer),
    )
    assert r.status_code == 403 and r.json()["detail"].startswith(SIGNED_IN)


def test_a_token_cannot_add_or_promote_members_when_the_option_is_on(
    client: TestClient,
    db_session: Session,
    owner: UserNew,
    viewer: UserNew,
    scope_with_admin: Scope,
) -> None:
    """Else a scope admin token could add an account it controls as a reviewer (#560)."""
    members = f"/api/v1/scopes/{scope_with_admin.id}"
    newcomer = {"user_id": str(make_user(db_session).id), "role": "reviewer"}
    promote = f"{members}/members/{viewer.id}"
    pat = _pat(client, owner)
    _gate(db_session, scope_with_admin)
    for r in (
        client.post(f"{members}/members", json=newcomer, headers=pat),
        client.post(f"{members}/invitations", json=newcomer, headers=pat),
        client.patch(promote, json={"role": "reviewer"}, headers=pat),
    ):
        assert r.status_code == 403, r.text
        assert r.json()["detail"].startswith("Member changes in this scope need")
    # notes or a viewer role stay open to the token; a signed-in admin does the rest
    assert (
        client.patch(promote, json={"role": "viewer"}, headers=pat).status_code == 200
    )
    session = auth_headers(owner)
    assert (
        client.patch(promote, json={"role": "reviewer"}, headers=session).status_code
        == 200
    )
    # successful adds write audit_log rows: covered in the Postgres lane
