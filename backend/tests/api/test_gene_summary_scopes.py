"""Per-scope rows of the gene summary: curation link, disease, stage, score and visibility.

Active curations are produced by the real review flow (assign reviewer, approve).
"""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.workflow_engine import WorkflowEngine
from app.models.models import (
    ActiveCuration,
    CurationNew,
    Gene,
    Scope,
    UserNew,
)
from tests.api.scopes.factories import (
    auth_headers,
    make_curation,
    make_gene,
    make_member,
    make_scope,
    make_user,
)

ENGINE = WorkflowEngine()


def _scored(c: CurationNew, verdict: str, total: float, db: Session) -> CurationNew:
    c.computed_verdict = verdict
    c.computed_scores = {"total_score": total, "genetic_evidence_total": total}
    c.evidence_data = {"disease_name": "Renal disease", "mode_of_inheritance": "AD"}
    db.commit()
    return c


def _active(db: Session, scope: Scope, gene: Gene, verdict: str, total: float):
    """Curation that went through peer review and activation."""
    creator, reviewer = make_user(db), make_user(db)
    make_member(db, scope, creator, "curator")
    make_member(db, scope, reviewer, "reviewer")
    c = _scored(
        make_curation(db, scope=scope, gene=gene, creator=creator), verdict, total, db
    )
    r = ENGINE.assign_peer_reviewer(db, c.id, "curation", reviewer.id, creator.id)
    ENGINE.submit_peer_review(db, r.review_id, reviewer.id, "approve")
    db.refresh(c)
    assert c.status == "active"
    return c


def _draft(db: Session, scope: Scope, gene: Gene, creator: UserNew) -> CurationNew:
    return _scored(
        make_curation(
            db, scope=scope, gene=gene, creator=creator,
            stage="curation", status="draft",
        ),
        "limited", 2, db,
    )  # fmt: skip


def _full(client: TestClient, user: UserNew, gene: Gene) -> dict:
    r = client.get(f"/api/v1/genes/{gene.id}/summary/full", headers=auth_headers(user))
    assert r.status_code == 200, r.text
    return r.json()


def _rows(body: dict) -> dict[str, dict]:
    return {r["curation_id"]: r for r in body["scope_summaries"]}


def test_member_gets_curation_link_disease_stage_score_and_in_progress(
    client: TestClient, db_session: Session
):
    gene, scope = make_gene(db_session), make_scope(db_session)
    active = _active(db_session, scope, gene, "definitive", 12)
    member = make_user(db_session)
    make_member(db_session, scope, member, "viewer")
    draft = _draft(db_session, scope, gene, member)

    body = _full(client, member, gene)
    rows = _rows(body)
    a = rows[str(active.id)]
    assert (a["disease_name"], a["mode_of_inheritance"]) == ("Renal disease", "AD")
    assert (a["classification"], a["total_score"], a["in_progress"]) == (
        "definitive",
        12,
        False,
    )
    d = rows[str(draft.id)]
    assert (d["stage"], d["in_progress"], d["total_score"]) == ("curation", True, 2)
    assert d["classification"] == "limited"  # the proposal: nobody approved it (#613)
    # active rows come first, then in-progress; deterministic
    assert [r["in_progress"] for r in body["scope_summaries"]] == [False, True]
    # in-progress work does not change the consensus
    assert body["classification_summary"] == {"definitive": 1}
    assert body["has_conflicts"] is False


def test_non_members_see_no_private_scope_data(client: TestClient, db_session: Session):
    gene, private = make_gene(db_session), make_scope(db_session)
    public = make_scope(db_session)
    public.is_public = True
    db_session.commit()
    _active(db_session, private, gene, "definitive", 12)
    _active(db_session, public, gene, "refuted", 1)  # disagreement across scopes
    creator = make_user(db_session)
    make_member(db_session, private, creator, "curator")
    make_member(db_session, public, creator, "curator")
    _draft(db_session, private, gene, creator)
    _draft(db_session, public, gene, creator)

    outsider = make_user(db_session)
    admin = make_user(db_session, role="admin")  # platform admin, no memberships
    pending = make_user(db_session)
    make_member(db_session, private, pending, "curator", accepted=False)
    for user in (outsider, admin, pending):
        body = _full(client, user, gene)
        assert [r["scope_id"] for r in body["scope_summaries"]] == [str(public.id)]
        assert body["scope_summaries"][0]["in_progress"] is False  # no drafts
        # aggregates only reflect what this caller may see: no hidden disagreement
        assert body["classification_summary"] == {"refuted": 1}
        assert body["has_conflicts"] is False
        assert (body["total_scopes_curated"], body["private_scopes_count"]) == (1, 0)

    pub = client.get(f"/api/v1/genes/{gene.id}/summary").json()
    assert [r["scope_id"] for r in pub["scope_summaries"]] == [str(public.id)]
    assert pub["classification_summary"] == {"refuted": 1}
    assert pub["has_conflicts"] is False
    assert pub["scope_summaries"][0]["curation_id"]
    # signed-out visitors get the display name too, not only the slug (W9 monkey)
    assert pub["scope_summaries"][0]["scope_display_name"] == public.display_name


def test_member_of_both_sees_disagreement_in_stable_order(
    client: TestClient, db_session: Session
):
    gene = make_gene(db_session)
    s1, s2 = make_scope(db_session, name="aaa"), make_scope(db_session, name="bbb")
    _active(db_session, s2, gene, "refuted", 1)
    _active(db_session, s1, gene, "definitive", 12)
    user = make_user(db_session)
    make_member(db_session, s1, user, "viewer")
    make_member(db_session, s2, user, "viewer")
    body = _full(client, user, gene)
    assert body["has_conflicts"] is True
    assert [r["scope_name"] for r in body["scope_summaries"]] == ["aaa", "bbb"]


def _public(db: Session) -> Scope:
    scope = make_scope(db)
    scope.is_public = True
    db.commit()
    return scope


def test_public_summary_drops_scope_made_private_immediately(
    client: TestClient, db_session: Session
):
    gene, scope = make_gene(db_session), _public(db_session)
    _active(db_session, scope, gene, "definitive", 12)
    assert client.get(f"/api/v1/genes/{gene.id}/summary").status_code == 200
    scope.is_public = False
    db_session.commit()
    # a known gene without public curations is an empty result, not a 404 (signed-out page)
    r = client.get(f"/api/v1/genes/{gene.id}/summary")
    assert (r.status_code, r.json()) == (200, None)
    assert client.get(f"/api/v1/genes/{uuid4()}/summary").status_code == 404


def test_archived_only_curation_leaves_empty_summary(
    client: TestClient, db_session: Session
):
    gene, scope = make_gene(db_session), _public(db_session)
    c = _active(db_session, scope, gene, "definitive", 12)
    assert client.get(f"/api/v1/genes/{gene.id}/summary").status_code == 200
    ac = db_session.query(ActiveCuration).filter_by(curation_id=c.id).one()
    ac.archived_at = datetime.now(UTC)
    c.status = "archived"
    db_session.commit()
    assert client.get(f"/api/v1/genes/{gene.id}/summary").json() is None
    user = make_user(db_session)
    body = _full(client, user, gene)
    assert body["scope_summaries"] == []
    assert body["total_scopes_curated"] == 0


def test_rejected_curation_is_not_in_progress(client: TestClient, db_session: Session):
    gene, scope = make_gene(db_session), make_scope(db_session)
    creator, reviewer = make_user(db_session), make_user(db_session)
    make_member(db_session, scope, creator, "curator")
    make_member(db_session, scope, reviewer, "reviewer")
    c = _draft(db_session, scope, gene, creator)
    c.status, c.workflow_stage = "in_review", "review"
    db_session.commit()
    r = ENGINE.assign_peer_reviewer(
        db_session, c.id, "curation", reviewer.id, creator.id
    )
    ENGINE.submit_peer_review(db_session, r.review_id, reviewer.id, "reject")
    db_session.refresh(c)
    c.status = "rejected"  # the end state the review UI shows for a rejected curation
    db_session.commit()
    assert _full(client, creator, gene)["scope_summaries"] == []
