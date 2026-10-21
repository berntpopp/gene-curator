"""pending_review is the single server-side definition of "needs my review"."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import CurationNew, ScopeMembership


def _in_review(scope, gene, pair, creator_id) -> CurationNew:
    return CurationNew(
        id=uuid4(),
        scope_id=scope.id,
        gene_id=gene.id,
        workflow_pair_id=pair.id,
        workflow_stage="review",
        status="in_review",
        evidence_data={},
        created_by=creator_id,
    )


def _totals(client: TestClient, token: str) -> tuple[int, int]:
    h = {"Authorization": f"Bearer {token}"}
    c = client.get(
        "/api/v1/curations/?curation_status=in_review&limit=1&pending_review=true",
        headers=h,
    ).json()
    p = client.get(
        "/api/v1/precurations/?precuration_status=submitted&limit=1&pending_review=true",
        headers=h,
    ).json()
    assert len(c["curations"]) <= 1
    return c["total"], p["total"]


def test_pending_review_filters_by_role_and_creator(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    test_scope,
    test_gene,
    test_workflow_pair,
    test_user_curator,
    test_user_admin,
    test_user_viewer,
    test_precuration,
):
    db_session.add_all(
        [
            _in_review(test_scope, test_gene, test_workflow_pair, test_user_curator.id),
            _in_review(test_scope, test_gene, test_workflow_pair, test_user_admin.id),
        ]
    )
    test_precuration.status = "submitted"
    db_session.commit()

    # Admin: someone else's items count, own do not
    assert _totals(client, admin_token) == (1, 1)

    # Viewer cannot review anything
    viewer_token = create_access_token(
        data={"sub": str(test_user_viewer.id), "email": test_user_viewer.email}
    )
    assert _totals(client, viewer_token) == (0, 0)

    # Promoted to reviewer: sees the same queue; the curator's own items stay hidden
    db_session.query(ScopeMembership).filter(
        ScopeMembership.user_id == test_user_viewer.id
    ).update({"role": "reviewer"})
    db_session.commit()
    assert _totals(client, viewer_token) == (2, 1)
    curator_token = create_access_token(
        data={"sub": str(test_user_curator.id), "email": test_user_curator.email}
    )
    assert _totals(client, curator_token) == (0, 0)  # curators do not review


def test_pending_review_with_scope_filter(
    client: TestClient, admin_token: str, test_scope
):
    h = {"Authorization": f"Bearer {admin_token}"}
    url = f"/api/v1/curations/?pending_review=true&scope_id={uuid4()}"
    assert client.get(url, headers=h).json()["total"] == 0
    url = f"/api/v1/precurations/?pending_review=true&scope_id={test_scope.id}"
    assert client.get(url, headers=h).status_code == 200
