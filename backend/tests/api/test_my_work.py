"""GET /me/work: inbox grouped by next action, scoped to accepted memberships."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import (
    CurationNew,
    GeneScopeAssignment,
    Review,
    ScopeMembership,
)


def _get(client: TestClient, user) -> dict:
    token = create_access_token(data={"sub": str(user.id), "email": user.email})
    r = client.get("/api/v1/me/work", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    return r.json()


def _cur(scope, gene, pair, creator, status, stage="curation") -> CurationNew:
    return CurationNew(
        id=uuid4(), scope_id=scope.id, gene_id=gene.id, workflow_pair_id=pair.id,
        workflow_stage=stage, status=status, evidence_data={}, created_by=creator.id,
    )  # fmt: skip


def test_unauthenticated(client: TestClient):
    assert client.get("/api/v1/me/work").status_code in (401, 403)


def test_assignment_then_started(
    client,
    db_session: Session,
    test_scope,
    test_gene,
    test_user_curator,
    test_precuration,
):
    a = GeneScopeAssignment(
        gene_id=test_gene.id, scope_id=test_scope.id,
        assigned_curator_id=test_user_curator.id, is_active=True,
    )  # fmt: skip
    db_session.add(a)
    db_session.commit()
    # test_precuration already started by the curator: draft, not assignment
    kinds = [i["kind"] for i in _get(client, test_user_curator)["items"]]
    assert kinds == ["draft"]
    db_session.delete(test_precuration)
    db_session.commit()
    body = _get(client, test_user_curator)
    (item,) = body["items"]
    assert item["kind"] == "assignment"
    assert (
        item["link"] == f"/scopes/{test_scope.id}/genes/{test_gene.id}/precuration/new"
    )
    assert body["counts"] == {"needs_you": 1, "waiting": 0, "done": 0}


def test_changes_requested_waiting_done(
    client, db_session: Session, test_scope, test_gene, test_workflow_pair,
    test_user_curator, test_user_admin,
):  # fmt: skip
    c = _cur(test_scope, test_gene, test_workflow_pair, test_user_curator, "draft")
    w = _cur(
        test_scope,
        test_gene,
        test_workflow_pair,
        test_user_curator,
        "in_review",
        "review",
    )
    d = _cur(
        test_scope,
        test_gene,
        test_workflow_pair,
        test_user_curator,
        "approved",
        "active",
    )
    d.updated_at = datetime.now(UTC)
    db_session.add_all([c, w, d])
    db_session.flush()
    db_session.add(
        Review(
            curation_id=c.id, reviewer_id=test_user_admin.id, status="needs_revision"
        )
    )
    db_session.commit()
    body = _get(client, test_user_curator)
    assert {i["kind"] for i in body["items"]} == {
        "changes_requested",
        "waiting",
        "done",
    }
    assert body["counts"] == {"needs_you": 1, "waiting": 1, "done": 1}
    # reviewer (admin) sees the in-review one under needs_you, not own/other drafts
    adm = _get(client, test_user_admin)
    assert [i["kind"] for i in adm["items"]] == ["review"]
    assert adm["items"][0]["link"] == f"/scopes/{test_scope.id}/curations/{w.id}"


def test_pending_membership_grants_nothing(
    client,
    db_session: Session,
    test_scope,
    test_gene,
    test_workflow_pair,
    test_user_curator,
):
    db_session.add(
        _cur(test_scope, test_gene, test_workflow_pair, test_user_curator, "draft")
    )
    db_session.query(ScopeMembership).filter(
        ScopeMembership.user_id == test_user_curator.id
    ).update({"accepted_at": None})
    db_session.commit()
    assert _get(client, test_user_curator)["items"] == []
