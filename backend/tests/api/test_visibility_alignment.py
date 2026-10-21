"""Old catalogue and GET /genes/{id}/scopes follow the same visibility rule as the matrix,
search and summaries: public active scope or accepted membership, no platform-admin bypass (#367)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import Gene, Scope
from tests.api.scopes.factories import (
    auth_headers,
    make_gene,
    make_member,
    make_scope,
    make_user,
)
from tests.api.test_gene_summary_scopes import _active, _draft

pytestmark = pytest.mark.unit

ROLES = ["anonymous", "member", "pending", "outsider", "platform_admin"]


@pytest.fixture
def world(db_session: Session):
    """Gene with an active curation in a public and a private scope, plus a draft in the public one."""
    gene = make_gene(db_session)
    public, private = make_scope(db_session), make_scope(db_session)
    public.is_public = True
    db_session.commit()
    _active(db_session, public, gene, "definitive", 12)
    _active(db_session, private, gene, "strong", 9)
    drafter = make_user(db_session)
    make_member(db_session, public, drafter, "curator")
    _draft(db_session, public, gene, drafter)
    return gene, public, private


def _headers(db: Session, who: str, private: Scope, public: Scope):
    if who == "anonymous":
        return {}
    user = make_user(db, role="admin" if who == "platform_admin" else "user")
    if who == "member":
        make_member(db, private, user, "viewer")
    elif who == "pending":
        make_member(db, private, user, "viewer", accepted=False)
    return auth_headers(user)


def _expected(who: str, public: Scope, private: Scope) -> set[str]:
    return {str(public.id), str(private.id)} if who == "member" else {str(public.id)}


@pytest.mark.parametrize("who", ROLES)
def test_old_catalogue_shows_only_visible_scopes(
    client: TestClient, db_session, world, who
):
    gene, public, private = world
    headers = _headers(db_session, who, private, public)

    body = client.get(
        "/api/v1/gene-catalogue/",
        params={"search": gene.approved_symbol},
        headers=headers,
    ).json()
    scopes = {sc["scope_id"] for e in body["entries"] for sc in e["scope_curations"]}
    assert scopes == _expected(who, public, private)
    assert body["entries"][0]["total_curations"] == len(scopes)

    filters = client.get(
        "/api/v1/gene-catalogue/filters/scopes", headers=headers
    ).json()
    assert {s["id"] for s in filters} >= {str(public.id)}
    assert (str(private.id) in {s["id"] for s in filters}) == (who == "member")


@pytest.mark.parametrize("who", ROLES)
def test_old_catalogue_summary_counts_only_visible_scopes(
    client: TestClient, db_session, world, who
):
    _, public, private = world
    headers = _headers(db_session, who, private, public)
    stats = client.get("/api/v1/gene-catalogue/", headers=headers).json()["summary"]
    visible = 2 if who == "member" else 1
    assert stats["total_curations"] >= visible
    all_ids = {
        s["id"]
        for s in client.get(
            "/api/v1/gene-catalogue/filters/scopes", headers=headers
        ).json()
    }
    assert (str(private.id) in all_ids) == (who == "member")


@pytest.mark.parametrize("param", ["search", "disease"])
def test_old_catalogue_search_treats_wildcards_literally(
    client: TestClient, db_session: Session, world, param
):
    for text in ("%", "_", "a%", "\\"):
        body = client.get("/api/v1/gene-catalogue/", params={param: text}).json()
        assert body["entries"] == [], text


@pytest.mark.parametrize("param", ["search", "disease"])
@pytest.mark.parametrize("bad", ["a\x00b", "x" * 101])
def test_old_catalogue_rejects_nul_and_long_input(client: TestClient, param, bad):
    assert client.get("/api/v1/gene-catalogue/", params={param: bad}).status_code == 422


def _scopes(client: TestClient, gene: Gene, headers: dict):
    r = client.get(f"/api/v1/genes/{gene.id}/scopes", headers=headers)
    assert r.status_code == 200, r.text
    return {s["scope_id"]: s["curation_count"] for s in r.json()}


@pytest.mark.parametrize("who", ROLES)
def test_gene_scopes_visibility_and_draft_counts(
    client: TestClient, db_session, world, who
):
    gene, public, private = world
    got = _scopes(client, gene, _headers(db_session, who, private, public))
    assert set(got) == _expected(who, public, private)
    assert got[str(public.id)] == 1  # the draft is not counted for non-members


def test_gene_scopes_counts_drafts_for_members_of_that_scope(
    client: TestClient, db_session, world
):
    gene, public, _ = world
    user = make_user(db_session)
    make_member(db_session, public, user, "viewer")
    assert _scopes(client, gene, auth_headers(user))[str(public.id)] == 2


def test_gene_scopes_hides_inactive_scopes(client: TestClient, db_session, world):
    gene, public, _ = world
    public.is_active = False
    db_session.commit()
    assert _scopes(client, gene, {}) == {}
