"""API tests for /api/v1/workflow endpoints (transitions, peer review, config, analytics)."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import (
    ActiveCuration,
    CurationNew,
    CurationStatus,
    GeneScopeAssignment,
    Scope,
    UserNew,
    WorkflowStage as S,
)
from tests.api.scopes.factories import (
    auth_headers,
    make_curation,
    make_gene,
    make_precuration,
    make_user,
)

pytestmark = pytest.mark.unit

BASE = "/api/v1/workflow"


@pytest.fixture
def curation_in_curation(
    db_session: Session, curator: UserNew, scope_with_admin: Scope
) -> CurationNew:
    return make_curation(
        db_session,
        scope=scope_with_admin,
        gene=make_gene(db_session),
        creator=curator,
        stage=S.CURATION,
        status=CurationStatus.DRAFT,
    )


@pytest.fixture
def curation_in_review(
    db_session: Session, curator: UserNew, scope_with_admin: Scope
) -> CurationNew:
    return make_curation(
        db_session,
        scope=scope_with_admin,
        gene=make_gene(db_session),
        creator=curator,
        stage=S.REVIEW,
    )


# -----------------------------------------------------------------------------
# State and validation
# -----------------------------------------------------------------------------


def test_state_endpoint_returns_stage_and_transitions(
    client: TestClient, curator: UserNew, curation_in_curation: CurationNew
) -> None:
    response = client.get(
        f"{BASE}/curation/{curation_in_curation.id}/state",
        headers=auth_headers(curator),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["current_stage"] == "curation"
    assert "review" in body["available_transitions"]


def test_state_endpoint_unknown_item_is_404(
    client: TestClient, curator: UserNew
) -> None:
    response = client.get(
        f"{BASE}/curation/{uuid4()}/state", headers=auth_headers(curator)
    )

    assert response.status_code == 404


def test_validate_transition_reports_authorization_failure(
    client: TestClient,
    db_session: Session,
    curation_in_curation: CurationNew,
) -> None:
    stranger = make_user(db_session)

    response = client.post(
        f"{BASE}/curation/{curation_in_curation.id}/validate-transition",
        json={"target_stage": "review"},
        headers=auth_headers(stranger),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is False
    assert any("not authorized" in e for e in body["errors"])


def test_validate_transition_unknown_item_is_404(
    client: TestClient, curator: UserNew
) -> None:
    response = client.post(
        f"{BASE}/curation/{uuid4()}/validate-transition",
        json={"target_stage": "review"},
        headers=auth_headers(curator),
    )

    assert response.status_code == 404


def test_validate_transition_rejects_unknown_stage(
    client: TestClient, curator: UserNew, curation_in_curation: CurationNew
) -> None:
    response = client.post(
        f"{BASE}/curation/{curation_in_curation.id}/validate-transition",
        json={"target_stage": "published"},
        headers=auth_headers(curator),
    )

    assert response.status_code == 422


# -----------------------------------------------------------------------------
# Transitions
# -----------------------------------------------------------------------------


def test_curator_submits_curation_for_review(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    curation_in_curation: CurationNew,
) -> None:
    response = client.post(
        f"{BASE}/curation/{curation_in_curation.id}/transition",
        json={"target_stage": "review", "notes": "ready"},
        headers=auth_headers(curator),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["from_stage"] == "curation"
    assert body["to_stage"] == "review"
    db_session.refresh(curation_in_curation)
    assert curation_in_curation.workflow_stage == S.REVIEW


def test_invalid_transition_is_400(
    client: TestClient, curator: UserNew, curation_in_curation: CurationNew
) -> None:
    response = client.post(
        f"{BASE}/curation/{curation_in_curation.id}/transition",
        json={"target_stage": "active"},
        headers=auth_headers(curator),
    )

    assert response.status_code == 400
    assert "Invalid transition" in response.json()["detail"]


def test_viewer_cannot_transition(
    client: TestClient,
    viewer: UserNew,
    curation_in_curation: CurationNew,
) -> None:
    response = client.post(
        f"{BASE}/curation/{curation_in_curation.id}/transition",
        json={"target_stage": "review"},
        headers=auth_headers(viewer),
    )

    assert response.status_code == 400
    assert "not authorized" in response.json()["detail"]


def test_creator_cannot_approve_own_curation(
    client: TestClient, curator: UserNew, curation_in_review: CurationNew
) -> None:
    response = client.post(
        f"{BASE}/curation/{curation_in_review.id}/transition",
        json={"target_stage": "active"},
        headers=auth_headers(curator),
    )

    assert response.status_code == 400
    assert "4-eyes" in response.json()["detail"]


def test_reviewer_approves_and_activates_curation(
    client: TestClient,
    db_session: Session,
    reviewer: UserNew,
    curation_in_review: CurationNew,
) -> None:
    response = client.post(
        f"{BASE}/curation/{curation_in_review.id}/transition",
        json={"target_stage": "active"},
        headers=auth_headers(reviewer),
    )

    assert response.status_code == 200
    active = (
        db_session.query(ActiveCuration)
        .filter_by(curation_id=curation_in_review.id)
        .one()
    )
    assert active.activated_by == reviewer.id


def test_transition_request_rejects_overlong_notes(
    client: TestClient, curator: UserNew, curation_in_curation: CurationNew
) -> None:
    response = client.post(
        f"{BASE}/curation/{curation_in_curation.id}/transition",
        json={"target_stage": "review", "notes": "x" * 1001},
        headers=auth_headers(curator),
    )

    assert response.status_code == 422


def test_bulk_transition_requires_application_admin(
    client: TestClient, curator: UserNew, curation_in_curation: CurationNew
) -> None:
    response = client.post(
        f"{BASE}/bulk-transition",
        json={
            "item_ids": [str(curation_in_curation.id)],
            "item_type": "curation",
            "target_stage": "review",
        },
        headers=auth_headers(curator),
    )

    assert response.status_code == 403


def test_bulk_transition_reports_partial_failures(
    client: TestClient,
    app_admin: UserNew,
    curation_in_curation: CurationNew,
) -> None:
    missing = uuid4()

    response = client.post(
        f"{BASE}/bulk-transition",
        json={
            "item_ids": [str(curation_in_curation.id), str(missing)],
            "item_type": "curation",
            "target_stage": "review",
        },
        headers=auth_headers(app_admin),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_processed"] == 2
    assert body["total_successful"] == 1
    assert body["total_failed"] == 1
    assert body["failed_transitions"][0]["item_id"] == str(missing)


# -----------------------------------------------------------------------------
# Peer review
# -----------------------------------------------------------------------------


def test_assign_reviewer_then_reviewer_submits_approval(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    curation_in_review: CurationNew,
) -> None:
    assigned = client.post(
        f"{BASE}/curation/{curation_in_review.id}/assign-reviewer",
        json={"reviewer_id": str(reviewer.id)},
        headers=auth_headers(curator),
    )
    assert assigned.status_code == 200
    review_id = assigned.json()["review_id"]

    mine = client.get(f"{BASE}/reviews/my-assignments", headers=auth_headers(reviewer))
    assert [r["review_id"] for r in mine.json()] == [review_id]

    submitted = client.post(
        f"{BASE}/reviews/{review_id}/submit",
        json={"decision": "approve", "comments": "looks good"},
        headers=auth_headers(reviewer),
    )

    assert submitted.status_code == 200
    assert submitted.json()["auto_transitioned"] is True


def test_assign_reviewer_to_creator_is_400(
    client: TestClient,
    curator: UserNew,
    curation_in_review: CurationNew,
) -> None:
    response = client.post(
        f"{BASE}/curation/{curation_in_review.id}/assign-reviewer",
        json={"reviewer_id": str(curator.id)},
        headers=auth_headers(curator),
    )

    assert response.status_code == 400
    assert "Cannot assign original creator" in response.json()["detail"]


def test_assign_reviewer_to_precuration_is_400(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
) -> None:
    precuration = make_precuration(
        db_session,
        scope=scope_with_admin,
        gene=make_gene(db_session),
        creator=curator,
        stage=S.REVIEW,
    )

    response = client.post(
        f"{BASE}/precuration/{precuration.id}/assign-reviewer",
        json={"reviewer_id": str(reviewer.id)},
        headers=auth_headers(curator),
    )

    assert response.status_code == 400


def test_submit_review_by_wrong_user_is_400(
    client: TestClient,
    curator: UserNew,
    reviewer: UserNew,
    curation_in_review: CurationNew,
) -> None:
    review_id = client.post(
        f"{BASE}/curation/{curation_in_review.id}/assign-reviewer",
        json={"reviewer_id": str(reviewer.id)},
        headers=auth_headers(curator),
    ).json()["review_id"]

    response = client.post(
        f"{BASE}/reviews/{review_id}/submit",
        json={"decision": "approve"},
        headers=auth_headers(curator),
    )

    assert response.status_code == 400


def test_submit_review_rejects_unknown_decision(
    client: TestClient,
    curator: UserNew,
    reviewer: UserNew,
    curation_in_review: CurationNew,
) -> None:
    review_id = client.post(
        f"{BASE}/curation/{curation_in_review.id}/assign-reviewer",
        json={"reviewer_id": str(reviewer.id)},
        headers=auth_headers(curator),
    ).json()["review_id"]

    response = client.post(
        f"{BASE}/reviews/{review_id}/submit",
        json={"decision": "maybe"},
        headers=auth_headers(reviewer),
    )

    assert response.status_code == 422


def test_my_assignments_filters_and_validates_status(
    client: TestClient, reviewer: UserNew
) -> None:
    ok = client.get(
        f"{BASE}/reviews/my-assignments",
        params={"status": "pending"},
        headers=auth_headers(reviewer),
    )
    bad = client.get(
        f"{BASE}/reviews/my-assignments",
        params={"status": "bogus"},
        headers=auth_headers(reviewer),
    )

    assert ok.status_code == 200
    assert ok.json() == []
    assert bad.status_code == 400


def test_peer_reviewers_excludes_caller_and_lists_scope_members(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
) -> None:
    response = client.get(
        f"{BASE}/peer-reviewers",
        params={"scope_id": str(scope_with_admin.id)},
        headers=auth_headers(curator),
    )

    assert response.status_code == 200
    ids = [r["id"] for r in response.json()]
    assert str(reviewer.id) in ids
    assert str(curator.id) not in ids


# -----------------------------------------------------------------------------
# Scope access on monitoring endpoints
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/statistics",
        "/dashboard",
        "/analytics",
    ],
)
def test_monitoring_endpoints_forbid_non_member_scope(
    client: TestClient,
    db_session: Session,
    scope_with_admin: Scope,
    path: str,
) -> None:
    stranger = make_user(db_session)

    response = client.get(
        f"{BASE}{path}",
        params={"scope_id": str(scope_with_admin.id)},
        headers=auth_headers(stranger),
    )

    assert response.status_code == 403


def test_statistics_and_dashboard_for_member(
    client: TestClient, curator: UserNew, scope_with_admin: Scope
) -> None:
    stats = client.get(
        f"{BASE}/statistics",
        params={"scope_id": str(scope_with_admin.id), "days": 7},
        headers=auth_headers(curator),
    )
    dashboard = client.get(
        f"{BASE}/dashboard",
        params={"scope_id": str(scope_with_admin.id)},
        headers=auth_headers(curator),
    )

    assert stats.status_code == 200
    assert stats.json()["time_period_days"] == 7
    assert dashboard.status_code == 200
    assert dashboard.json()["my_pending_reviews"] == 0


def test_dashboard_my_assignments_count_is_exact(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    scope_with_admin: Scope,
) -> None:
    other = make_user(db_session)
    for owner in (curator, curator, other, other, other):
        db_session.add(
            GeneScopeAssignment(
                gene_id=make_gene(db_session).id,
                scope_id=scope_with_admin.id,
                assigned_curator_id=owner.id,
            )
        )
    db_session.commit()

    dashboard = client.get(
        f"{BASE}/dashboard",
        params={"scope_id": str(scope_with_admin.id)},
        headers=auth_headers(curator),
    )

    assert dashboard.json()["my_assignments"]["total"] == 2


def test_analytics_rejects_period_below_minimum(
    client: TestClient, curator: UserNew
) -> None:
    response = client.get(
        f"{BASE}/analytics", params={"days": 3}, headers=auth_headers(curator)
    )

    assert response.status_code == 422


def test_audit_trail_returns_item_envelope(
    client: TestClient, curator: UserNew
) -> None:
    item = uuid4()

    response = client.get(
        f"{BASE}/curation/{item}/audit-trail", headers=auth_headers(curator)
    )

    assert response.status_code == 200
    assert response.json()["item_id"] == str(item)
    assert response.json()["entries"] == []


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------


def test_configuration_visible_to_members_only(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    scope_with_admin: Scope,
) -> None:
    member = client.get(
        f"{BASE}/configuration/{scope_with_admin.id}",
        headers=auth_headers(curator),
    )
    stranger = client.get(
        f"{BASE}/configuration/{scope_with_admin.id}",
        headers=auth_headers(make_user(db_session)),
    )

    assert member.status_code == 200
    assert member.json()["require_peer_review"] is True
    assert stranger.status_code == 403


def test_configuration_update_requires_application_admin(
    client: TestClient,
    app_admin: UserNew,
    curator: UserNew,
    scope_with_admin: Scope,
) -> None:
    payload = {
        "scope_id": str(scope_with_admin.id),
        "require_peer_review": True,
        "min_reviewers": 2,
        "allow_self_review": False,
        "auto_transition_on_approval": True,
        "require_all_reviews_complete": True,
        "notify_on_assignment": True,
        "notify_on_transition": True,
        "escalation_enabled": False,
    }

    denied = client.put(
        f"{BASE}/configuration/{scope_with_admin.id}",
        json=payload,
        headers=auth_headers(curator),
    )
    allowed = client.put(
        f"{BASE}/configuration/{scope_with_admin.id}",
        json=payload,
        headers=auth_headers(app_admin),
    )

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["min_reviewers"] == 2


def test_activating_second_curation_archives_the_first(
    client: TestClient,
    db_session: Session,
    reviewer: UserNew,
    curator: UserNew,
    scope_with_admin: Scope,
) -> None:
    gene = make_gene(db_session)
    first, second = (
        make_curation(
            db_session,
            scope=scope_with_admin,
            gene=gene,
            creator=curator,
            stage=S.REVIEW,
        )
        for _ in range(2)
    )
    for curation in (first, second):
        response = client.post(
            f"{BASE}/curation/{curation.id}/transition",
            json={"target_stage": "active"},
            headers=auth_headers(reviewer),
        )
        assert response.status_code == 200

    rows = db_session.query(ActiveCuration).filter_by(gene_id=gene.id).all()
    current = [r for r in rows if r.archived_at is None]
    assert [r.curation_id for r in current] == [second.id]
    assert len(rows) == 2
