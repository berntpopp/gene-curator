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
    make_member(db_session, test_scope, test_user_admin, "admin")
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


# --- review visibility and the real request-changes flow -------------------
from datetime import timedelta  # noqa: E402

from app.crud.workflow_engine import WorkflowEngine  # noqa: E402
from tests.api.scopes.factories import (  # noqa: E402
    make_curation,
    make_gene,
    make_member,
    make_scope,
    make_user,
)


def _kinds(client, user) -> list[str]:
    return sorted(i["kind"] for i in _get(client, user)["items"])


def _in_review(db, scope, creator):
    return make_curation(db, scope=scope, gene=make_gene(db), creator=creator)


def test_review_visibility_rules(client, db_session: Session):
    scope, other = make_scope(db_session), make_scope(db_session)
    curator = make_user(db_session)
    make_member(db_session, scope, curator, "curator")
    reviewer = make_user(db_session)
    make_member(db_session, scope, reviewer, "reviewer")
    admin = make_user(db_session, role="admin")  # platform admin, no membership
    pending = make_user(db_session)
    make_member(db_session, scope, pending, "reviewer", accepted=False)

    _in_review(db_session, scope, curator)  # someone else's item
    _in_review(db_session, other, curator)  # scope nobody here belongs to
    assert _kinds(client, reviewer) == ["review"]
    assert _kinds(client, curator) == ["waiting"]  # curators do not review
    assert _kinds(client, admin) == []  # not a member: nothing, even as platform admin
    assert _kinds(client, pending) == []  # pending invitation grants nothing

    # own IN_REVIEW item is waiting, never a review item (reviewer and admin member)
    own_r = _in_review(db_session, scope, reviewer)
    make_member(db_session, scope, admin, "admin")
    own_a = _in_review(db_session, scope, admin)
    assert _kinds(client, reviewer) == ["review", "review", "waiting"]
    assert own_r.id not in {
        i["item_id"] for i in _get(client, admin)["items"] if i["kind"] == "review"
    }
    assert _kinds(client, admin) == [
        "review",
        "review",
        "waiting",
    ]  # curator's + reviewer's
    assert own_a.id not in {
        i["item_id"] for i in _get(client, admin)["items"] if i["kind"] == "review"
    }


def test_reviewer_assignment_is_respected(client, db_session: Session):
    scope = make_scope(db_session)
    curator = make_user(db_session)
    make_member(db_session, scope, curator, "curator")
    me, them = make_user(db_session), make_user(db_session)
    make_member(db_session, scope, me, "reviewer")
    make_member(db_session, scope, them, "reviewer")
    engine = WorkflowEngine()
    unassigned = _in_review(db_session, scope, curator)
    to_them = _in_review(db_session, scope, curator)
    to_me = _in_review(db_session, scope, curator)
    decided = _in_review(db_session, scope, curator)
    engine.assign_peer_reviewer(db_session, to_them.id, "curation", them.id, curator.id)
    engine.assign_peer_reviewer(db_session, to_me.id, "curation", me.id, curator.id)
    r = engine.assign_peer_reviewer(
        db_session, decided.id, "curation", me.id, curator.id
    )
    engine.submit_peer_review(db_session, r.review_id, me.id, "approve")
    ids = {i["item_id"] for i in _get(client, me)["items"] if i["kind"] == "review"}
    assert ids == {str(unassigned.id), str(to_me.id)}


def test_request_changes_via_workflow_moves_to_needs_you(client, db_session: Session):
    scope = make_scope(db_session)
    curator, reviewer = make_user(db_session), make_user(db_session)
    make_member(db_session, scope, curator, "curator")
    make_member(db_session, scope, reviewer, "reviewer")
    c = _in_review(db_session, scope, curator)
    engine = WorkflowEngine()
    r = engine.assign_peer_reviewer(
        db_session, c.id, "curation", reviewer.id, curator.id
    )
    assert _kinds(client, curator) == ["waiting"]
    engine.submit_peer_review(
        db_session, r.review_id, reviewer.id, "request_changes", "fix"
    )
    db_session.refresh(c)
    assert c.status == "in_review"  # the real flow leaves it IN_REVIEW
    body = _get(client, curator)
    assert [i["kind"] for i in body["items"]] == ["changes_requested"]
    assert body["counts"] == {"needs_you": 1, "waiting": 0, "done": 0}

    # only the latest decision counts: a newer approval clears the label
    later = Review(
        curation_id=c.id, reviewer_id=reviewer.id, status="approved",
        assigned_at=datetime.now(UTC) + timedelta(minutes=5),
    )  # fmt: skip
    db_session.add(later)
    db_session.commit()
    assert _kinds(client, curator) == ["waiting"]
