"""MCP study round trips agents named (token-efficiency plan item 2)."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    CurationNew,
    CurationStatus,
    NotificationNew,
    PrecurationNew,
    Review,
    Scope,
    UserNew,
    WorkflowStage,
)
from tests.api.scopes.factories import (
    auth_headers,
    make_curation,
    make_gene,
    make_precuration,
    make_scope,
    make_user,
)


def test_list_rows_carry_lock_version(
    client: TestClient,
    curator_token: str,
    test_curation: CurationNew,
    test_precuration: PrecurationNew,
) -> None:
    """A save needs lock_version; the list row has it, so no GET just for it."""
    h = {"Authorization": f"Bearer {curator_token}"}
    (c,) = client.get("/api/v1/curations/", headers=h).json()["curations"]
    (p,) = client.get("/api/v1/precurations/", headers=h).json()["precurations"]
    assert c["lock_version"] == test_curation.lock_version
    assert p["lock_version"] == test_precuration.lock_version


def test_scope_name_replaces_scope_id(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
) -> None:
    """List, create and reviewer lookups take the scope name; no list_scopes first."""
    h = auth_headers(curator)
    name = scope_with_admin.name.upper()  # any case
    gene = make_gene(db_session)
    created = client.post(
        "/api/v1/precurations/",
        json={
            "gene_id": str(gene.id),
            "scope_name": name,
            "precuration_schema_id": None,
        },
        headers=h,
    )
    # the scope has no workflow pair: the scope resolved, the default schema did not
    assert created.status_code == 400, created.text
    assert "precuration_schema_id" in created.text
    make_precuration(db_session, scope=scope_with_admin, gene=gene, creator=curator)

    listed = client.get("/api/v1/precurations/", params={"scope_name": name}, headers=h)
    reviewers = client.get(
        "/api/v1/workflow/peer-reviewers", params={"scope_name": name}, headers=h
    )
    assert listed.json()["total"] == 1
    assert str(reviewer.id) in {r["id"] for r in reviewers.json()}


def test_unknown_or_hidden_scope_name_is_404_with_suggestions(
    client: TestClient, db_session: Session, curator: UserNew, scope_with_admin: Scope
) -> None:
    hidden = make_scope(db_session, name="hidden-team")  # curator is no member
    h = auth_headers(curator)
    typo = client.get(
        "/api/v1/curations/",
        params={"scope_name": scope_with_admin.name[:-1]},
        headers=h,
    )
    assert typo.status_code == 404
    assert typo.json()["detail"]["suggestions"] == [scope_with_admin.name]

    secret = client.get(
        "/api/v1/precurations/", params={"scope_name": hidden.name}, headers=h
    )
    assert secret.status_code == 404
    assert secret.json()["detail"]["suggestions"] == []  # hidden scopes never leak

    clash = client.get(
        "/api/v1/curations/",
        params={"scope_name": scope_with_admin.name, "scope_id": str(hidden.id)},
        headers=h,
    )
    assert clash.status_code == 404
    missing = client.post(
        "/api/v1/precurations/",
        json={"gene_id": str(make_gene(db_session).id)},
        headers=h,
    )
    assert missing.status_code == 422


def _draft_curation(db: Session, scope: Scope, creator: UserNew) -> CurationNew:
    return make_curation(
        db,
        scope=scope,
        gene=make_gene(db),
        creator=creator,
        stage=WorkflowStage.CURATION,
        status=CurationStatus.DRAFT,
    )


def _reviews(db: Session, item_id: UUID) -> list[UUID]:
    return list(
        db.scalars(select(Review.reviewer_id).where(Review.curation_id == item_id))
    )


def test_submit_curation_assigns_reviewer_in_one_call(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
) -> None:
    c = _draft_curation(db_session, scope_with_admin, curator)
    r = client.post(
        f"/api/v1/curations/{c.id}/submit",
        json={"lock_version": c.lock_version, "reviewer_id": str(reviewer.id)},
        headers=auth_headers(curator),
    )
    assert r.status_code == 200, r.text
    assert _reviews(db_session, c.id) == [reviewer.id]
    note = db_session.scalars(
        select(NotificationNew).where(NotificationNew.user_id == reviewer.id)
    ).one()
    assert str(c.id) in note.link


@pytest.mark.parametrize("who", ["author", "viewer", "stranger"])
def test_submit_with_bad_reviewer_changes_nothing(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    viewer: UserNew,
    scope_with_admin: Scope,
    who: str,
) -> None:
    """D1 and the reviewer rules hold; a refused reviewer rolls the submit back too."""
    reviewer_id = {"author": curator.id, "viewer": viewer.id, "stranger": uuid4()}[who]
    c = _draft_curation(db_session, scope_with_admin, curator)
    p = make_precuration(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator
    )
    for kind, item in (("curations", c), ("precurations", p)):
        r = client.post(
            f"/api/v1/{kind}/{item.id}/submit",
            json={"lock_version": item.lock_version, "reviewer_id": str(reviewer_id)},
            headers=auth_headers(curator),
        )
        assert r.status_code == 400, r.text
        db_session.expire_all()
        assert item.status == CurationStatus.DRAFT
    assert _reviews(db_session, c.id) == []
    assert db_session.scalars(select(NotificationNew)).all() == []


def test_submit_precuration_and_transition_route_to_reviewer(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
) -> None:
    p = make_precuration(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator
    )
    r = client.post(
        f"/api/v1/precurations/{p.id}/submit",
        json={"lock_version": p.lock_version, "reviewer_id": str(reviewer.id)},
        headers=auth_headers(curator),
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "submitted"
    c = _draft_curation(db_session, scope_with_admin, curator)
    t = client.post(
        f"/api/v1/workflow/curation/{c.id}/transition",
        json={"target_stage": "review", "reviewer_id": str(reviewer.id)},
        headers=auth_headers(curator),
    )
    assert t.status_code == 200, t.text
    assert _reviews(db_session, c.id) == [reviewer.id]
    links = db_session.scalars(
        select(NotificationNew.link).where(NotificationNew.user_id == reviewer.id)
    ).all()
    assert {str(p.id) in link for link in links} == {True, False}


def test_resubmit_with_the_earlier_reviewer_succeeds(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
) -> None:
    """A resubmit reassigns earlier reviewers itself; naming the same one is no conflict."""
    c = _draft_curation(db_session, scope_with_admin, curator)
    url = f"/api/v1/curations/{c.id}"
    h = auth_headers(curator)
    for _ in range(2):
        lock = client.get(url, headers=h).json()["lock_version"]
        r = client.post(
            f"{url}/submit",
            json={"lock_version": lock, "reviewer_id": str(reviewer.id)},
            headers=h,
        )
        assert r.status_code == 200, r.text
        back = client.post(
            f"/api/v1/workflow/curation/{c.id}/transition",
            json={"target_stage": "curation", "notes": "Add segregation data"},
            headers=auth_headers(reviewer),
        )
        assert back.status_code == 200, back.text
    statuses = db_session.scalars(
        select(Review.status).where(Review.curation_id == c.id)
    ).all()
    assert len(statuses) == 2  # one review per round, none duplicated


def test_submit_names_the_reviewer_by_email(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    viewer: UserNew,
    scope_with_admin: Scope,
) -> None:
    """Only the scope's reviewers match an email; others are refused and nothing changes."""
    outsider = make_user(db_session)
    c = _draft_curation(db_session, scope_with_admin, curator)
    p = make_precuration(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator
    )
    for kind, item in (("curations", c), ("precurations", p)):
        url = f"/api/v1/{kind}/{item.id}/submit"
        for bad in (viewer.email, outsider.email, curator.email):
            r = client.post(
                url,
                json={"lock_version": item.lock_version, "reviewer_email": bad},
                headers=auth_headers(curator),
            )
            assert r.status_code == 400, r.text
        r = client.post(
            url,
            json={
                "lock_version": item.lock_version,
                "reviewer_email": reviewer.email.upper(),
            },
            headers=auth_headers(curator),
        )
        assert r.status_code == 200, r.text
    assert _reviews(db_session, c.id) == [reviewer.id]
