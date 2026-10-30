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
    WorkflowStage,
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
    w.entity_key, d.entity_key = "MONDO:2|AD", "MONDO:3|AD"  # one open per entity
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
    assert c.status == "draft"  # back with the curator, editable
    body = _get(client, curator)
    assert [i["kind"] for i in body["items"]] == ["changes_requested"]
    assert body["counts"] == {"needs_you": 1, "waiting": 0, "done": 0}

    # a new round clears the label: resubmitted, it is waiting again
    WorkflowEngine().execute_transition(
        db_session, c.id, "curation", WorkflowStage.REVIEW, curator.id
    )
    assert _kinds(client, curator) == ["waiting"]
    assert _kinds(client, reviewer) == ["review"]  # new round: old decision is stale


def test_rejected_curation_needs_the_curator(client, db_session: Session):
    scope = make_scope(db_session)
    curator, reviewer = make_user(db_session), make_user(db_session)
    make_member(db_session, scope, curator, "curator")
    make_member(db_session, scope, reviewer, "reviewer")
    c = _in_review(db_session, scope, curator)
    engine = WorkflowEngine()
    r = engine.assign_peer_reviewer(
        db_session, c.id, "curation", reviewer.id, curator.id
    )
    engine.submit_peer_review(db_session, r.review_id, reviewer.id, "reject")
    body = _get(client, curator)
    assert [i["kind"] for i in body["items"]] == ["changes_requested"]
    assert _kinds(client, reviewer) == []


def test_reassigned_reviewer_and_other_reviewers_after_request_changes(
    client, db_session: Session
):
    scope = make_scope(db_session)
    curator, rev, other = (make_user(db_session) for _ in range(3))
    make_member(db_session, scope, curator, "curator")
    make_member(db_session, scope, rev, "reviewer")
    make_member(db_session, scope, other, "reviewer")
    c = _in_review(db_session, scope, curator)
    engine = WorkflowEngine()
    r = engine.assign_peer_reviewer(db_session, c.id, "curation", rev.id, curator.id)
    engine.submit_peer_review(db_session, r.review_id, rev.id, "request_changes")
    assert _kinds(client, other) == []  # curator owns the next move
    # curator resubmits: the earlier reviewer is re-assigned automatically
    engine.execute_transition(
        db_session, c.id, "curation", WorkflowStage.REVIEW, curator.id
    )
    assert _kinds(client, rev) == ["review"]


def test_stale_round_does_not_inflate_dashboard_or_my_work(client, db_session: Session):
    scope = make_scope(db_session)
    curator, a, b = (make_user(db_session) for _ in range(3))
    make_member(db_session, scope, curator, "curator")
    for u in (a, b):
        make_member(db_session, scope, u, "reviewer")
    c = _in_review(db_session, scope, curator)
    engine = WorkflowEngine()
    ra = engine.assign_peer_reviewer(db_session, c.id, "curation", a.id, curator.id)
    engine.assign_peer_reviewer(db_session, c.id, "curation", b.id, curator.id)

    def pending(user) -> int:
        token = create_access_token(data={"sub": str(user.id), "email": user.email})
        r = client.get(
            "/api/v1/workflow/dashboard", headers={"Authorization": f"Bearer {token}"}
        )
        return r.json()["my_pending_reviews"]

    assert pending(b) == 1
    engine.submit_peer_review(db_session, ra.review_id, a.id, "request_changes")
    assert pending(b) == 0  # B's review belongs to the closed round
    engine.execute_transition(
        db_session, c.id, "curation", WorkflowStage.REVIEW, curator.id
    )
    assert pending(b) == 1  # re-assigned in the new round
    assert _kinds(client, b) == ["review"]  # unassigned in the new round
    assert _kinds(client, a) == ["review"]  # A's old decision does not hide it


def test_rejected_precuration_needs_the_curator(
    client, db_session: Session, test_scope, test_user_curator, test_precuration
):
    test_precuration.status = "rejected"  # reviewer requested changes
    db_session.commit()
    (item,) = _get(client, test_user_curator)["items"]
    assert item["kind"] == "changes_requested"
    assert item["item_type"] == "precuration"
    assert item["link"] == f"/scopes/{test_scope.id}/precurations/{test_precuration.id}"


def test_reviewer_done_counts_own_approvals(client, db_session: Session):
    """#391: a reviewer's approvals land in Done; rejections and others' do not."""
    from app.crud.precuration import precuration_crud
    from tests.api.scopes.factories import make_precuration

    scope = make_scope(db_session)
    curator, bob, other = (make_user(db_session) for _ in range(3))
    make_member(db_session, scope, curator, "curator")
    make_member(db_session, scope, bob, "reviewer")
    make_member(db_session, scope, other, "reviewer")
    engine = WorkflowEngine()
    approved = _in_review(db_session, scope, curator)
    sent_back = _in_review(db_session, scope, curator)
    for c, decision in ((approved, "approve"), (sent_back, "request_changes")):
        r = engine.assign_peer_reviewer(
            db_session, c.id, "curation", bob.id, curator.id
        )
        engine.submit_peer_review(db_session, r.review_id, bob.id, decision)
    p = make_precuration(
        db_session, scope=scope, gene=make_gene(db_session), creator=curator
    )
    p.status = "submitted"
    db_session.commit()
    precuration_crud.approve_and_create_curation(
        db_session, db_obj=p, approver_id=bob.id, create_curation=False
    )

    body = _get(client, bob)
    done = {i["item_id"]: i for i in body["items"] if i["kind"] == "done"}
    assert set(done) == {str(approved.id), str(p.id)}
    assert done[str(p.id)]["verb"] == "Approved precuration"
    assert body["counts"]["done"] == 2
    assert _get(client, other)["counts"]["done"] == 0


def test_rows_carry_disease_moi_stage_and_classification(
    client, db_session: Session, test_scope, test_gene, test_workflow_pair,
    test_user_curator, test_precuration,
):  # fmt: skip
    """#277: rows say which disease, MOI, stage and classification they are about."""
    test_precuration.evidence_data = {
        "entity_definition": {"disease_name": "Foo syndrome"},
        "mode_of_inheritance": "AD",
    }
    c = _cur(test_scope, test_gene, test_workflow_pair, test_user_curator, "draft")
    c.precuration_id = test_precuration.id  # disease comes from the linked precuration
    c.computed_verdict = "moderate"
    db_session.add(c)
    db_session.commit()
    items = {i["item_type"]: i for i in _get(client, test_user_curator)["items"]}
    cur, pre = items["curation"], items["precuration"]
    assert (cur["disease_name"], cur["mode_of_inheritance"]) == ("Foo syndrome", "AD")
    assert (cur["stage"], cur["classification"]) == ("curation", "moderate")
    assert (pre["disease_name"], pre["stage"], pre["classification"]) == (
        "Foo syndrome",
        "precuration",
        None,
    )
