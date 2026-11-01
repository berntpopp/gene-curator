"""#639: agent accounts and the per-scope review_policy (human | ai | ai_then_human)."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CurationNew, PrecurationNew, Review
from app.models.models import CurationStatus, Scope, UserNew, WorkflowStage as S
from tests.api.scopes.factories import (
    PASSWORD,
    auth_headers,
    make_curation,
    make_gene,
    make_member,
    make_precuration,
    make_user,
)
from tests.api.test_mcp import call, pat

pytestmark = pytest.mark.unit

BASE = "/api/v1/workflow"
MODEL = "claude-opus-5-5"


def _agent(db: Session, scope: Scope, role: str, name: str) -> UserNew:
    user = make_user(db, name=name)
    user.is_agent = True
    db.commit()
    make_member(db, scope, user, role)
    return user


def _policy(db: Session, scope: Scope, policy: str) -> None:
    scope.review_policy = policy
    db.commit()


def _review(db: Session, curation: CurationNew, reviewer: UserNew) -> Review:
    review = Review(id=uuid4(), curation_id=curation.id, reviewer_id=reviewer.id)
    db.add(review)
    db.commit()
    return review


def _approve_over_mcp(
    client: TestClient, db: Session, review: Review, by: UserNew
) -> Any:
    return call(
        client,
        pat(db, by),
        "submit_peer_review",
        review_id=str(review.id),
        decision="approve",
        agent={"model": MODEL, "agent": "judge"},
    )


def _exported(client: TestClient, user: UserNew, cid: object) -> dict[str, Any]:
    r = client.get("/api/v1/export/curations", headers=auth_headers(user))
    assert r.status_code == 200, r.text
    [item] = [i for i in r.json()["items"] if i["curation_id"] == str(cid)]
    return item  # type: ignore[no-any-return]


def test_human_scope_refuses_every_agent_review_and_approval(
    client: TestClient, db_session: Session, curator: UserNew, scope_with_admin: Scope
) -> None:
    judge = _agent(db_session, scope_with_admin, "reviewer", "Judge agent")
    pre = make_precuration(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator,
        stage=S.REVIEW,
    )  # fmt: skip
    pre.status = CurationStatus.SUBMITTED
    db_session.commit()
    cur = make_curation(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator
    )
    review = _review(db_session, cur, judge)
    h = auth_headers(judge)
    for r in (
        client.post(f"/api/v1/precurations/{pre.id}/approve", headers=h),
        client.post(
            f"{BASE}/precuration/{pre.id}/transition",
            json={"target_stage": "curation"},
            headers=h,
        ),
        client.post(
            f"{BASE}/reviews/{review.id}/submit",
            json={"decision": "approve"},
            headers=h,
        ),
        client.post(
            f"{BASE}/curation/{cur.id}/transition",
            json={"target_stage": "active"},
            headers=h,
        ),
    ):
        assert r.status_code == 403, r.text
        assert "review_policy human" in r.text
    db_session.refresh(cur)
    assert cur.status == CurationStatus.IN_REVIEW
    # nor is the agent offered as the scope's reviewer (#640 warning, MCP routing)
    from app.services.review_assignment import missing_reviewer

    assert missing_reviewer(db_session, scope_with_admin.id, curator.id) == []  # owner


def test_ai_scope_agent_judge_approves_and_the_export_says_ai(
    client: TestClient, db_session: Session, owner: UserNew, scope_with_admin: Scope
) -> None:
    _policy(db_session, scope_with_admin, "ai")
    author = _agent(db_session, scope_with_admin, "curator", "Curator agent")
    judge = _agent(db_session, scope_with_admin, "reviewer", "Judge agent")
    cur = make_curation(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=author
    )
    result = _approve_over_mcp(
        client, db_session, _review(db_session, cur, judge), judge
    )
    assert not result.get("isError"), result
    db_session.refresh(cur)
    assert cur.status == CurationStatus.ACTIVE
    assert (cur.approval_kind, cur.approval_model, cur.approved_by) == (
        "ai",
        MODEL,
        judge.id,
    )
    item = _exported(client, owner, cur.id)
    assert (item["approval_kind"], item["approval_model"]) == ("ai", MODEL)
    [approver] = [
        c for c in item["contributions"] if c["activityType"]["name"] == "approver"
    ]
    [made] = [
        c for c in item["contributions"] if c["activityType"]["name"] == "curator"
    ]
    assert made["contributor"]["agentType"] == "software"  # credited to the agent
    assert (approver["contributor"]["name"], approver["contributor"]["agentType"]) == (
        "Judge agent",
        "software",
    )


def test_ai_then_human_keeps_an_agent_approval_provisional(
    client: TestClient,
    db_session: Session,
    owner: UserNew,
    reviewer: UserNew,
    curator: UserNew,
    scope_with_admin: Scope,
) -> None:
    _policy(db_session, scope_with_admin, "ai_then_human")
    judge = _agent(db_session, scope_with_admin, "reviewer", "Judge agent")
    cur = make_curation(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator
    )
    first = _approve_over_mcp(
        client, db_session, _review(db_session, cur, judge), judge
    )
    assert not first.get("isError"), first
    db_session.refresh(cur)
    assert cur.status == CurationStatus.IN_REVIEW  # provisional: no person yet
    direct = client.post(
        f"{BASE}/curation/{cur.id}/transition",
        json={"target_stage": "active"},
        headers=auth_headers(judge),
    )
    assert direct.status_code == 403 and "ai_then_human" in direct.text

    second = client.post(
        f"{BASE}/reviews/{_review(db_session, cur, reviewer).id}/submit",
        json={"decision": "approve"},
        headers=auth_headers(reviewer),
    )
    assert second.status_code == 200, second.text
    db_session.refresh(cur)
    assert (cur.status, cur.approval_kind, cur.approval_model) == (
        CurationStatus.ACTIVE,
        "human",
        None,
    )
    item = _exported(client, owner, cur.id)
    assessors = {
        c["contributor"]["agentType"]
        for c in item["contributions"]
        if c["activityType"]["name"] == "assessor"
    }
    assert (item["approval_kind"], assessors) == ("human", {"software", "person"})


def test_agent_accounts_sign_in_by_token_only_and_never_administer(
    client: TestClient, db_session: Session, app_admin: UserNew, scope_with_admin: Scope
) -> None:
    agent = _agent(db_session, scope_with_admin, "admin", "Agent")
    login = client.post(
        "/api/v1/auth/login", json={"email": agent.email, "password": PASSWORD}
    )
    assert login.status_code == 401, login.text

    admin = auth_headers(app_admin)
    body = {"email": "bot@example.org", "name": "Bot", "password": "x" * 12}
    made = client.post(
        "/api/v1/users/",
        json={**body, "is_agent": True, "role": "admin"},
        headers=admin,
    )
    assert made.status_code == 422, made.text
    promoted = client.put(
        f"/api/v1/users/{agent.id}", json={"role": "admin"}, headers=admin
    )
    assert promoted.status_code == 400, promoted.text

    expires = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    token = client.post(
        f"/api/v1/users/{agent.id}/tokens",
        json={"name": "judge", "expires_at": expires},
        headers=admin,
    )
    assert token.status_code == 201, token.text
    as_agent = {"Authorization": f"Bearer {token.json()['token']}"}
    me = client.get("/api/v1/auth/me", headers=as_agent)
    assert me.status_code == 200 and me.json()["is_agent"] is True
    person = client.post(
        f"/api/v1/users/{app_admin.id}/tokens",
        json={"name": "x", "expires_at": expires},
        headers=admin,
    )
    assert person.status_code == 404, person.text

    # a scope admin membership grants no member or scope management to an agent
    members = client.get(
        f"/api/v1/scopes/{scope_with_admin.id}/members", headers=as_agent
    )
    renamed = client.patch(
        f"/api/v1/scopes/{scope_with_admin.id}",
        json={"review_policy": "ai"},
        headers=as_agent,
    )
    assert members.status_code == 200 and renamed.status_code == 403, renamed.text


def test_a_scope_admin_sets_the_review_policy(
    client: TestClient, db_session: Session, owner: UserNew, scope_with_admin: Scope
) -> None:
    url, h = f"/api/v1/scopes/{scope_with_admin.id}", auth_headers(owner)
    assert (
        client.patch(url, json={"review_policy": "robots"}, headers=h).status_code
        == 422
    )
    r = client.patch(url, json={"review_policy": "ai_then_human"}, headers=h)
    assert r.status_code == 200 and r.json()["review_policy"] == "ai_then_human", r.text
    db_session.refresh(scope_with_admin)
    assert scope_with_admin.review_policy == "ai_then_human"


def test_precuration_approval_by_an_agent_in_an_ai_scope(
    client: TestClient, db_session: Session, curator: UserNew, scope_with_admin: Scope
) -> None:
    _policy(db_session, scope_with_admin, "ai")
    judge = _agent(db_session, scope_with_admin, "reviewer", "Judge agent")
    pre: PrecurationNew = make_precuration(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator,
        stage=S.REVIEW,
    )  # fmt: skip
    pre.status = CurationStatus.SUBMITTED
    db_session.commit()
    r = client.post(
        f"/api/v1/precurations/{pre.id}/approve", headers=auth_headers(judge)
    )
    assert r.status_code == 200, r.text
