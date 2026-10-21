"""GET /search: command-palette hits, same visibility as the list endpoints (#273)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CurationNew, Gene, Scope, WorkflowPair
from tests.api.scopes.factories import auth_headers, make_member, make_user

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def no_rls_on_sqlite():
    with patch("app.core.deps.set_rls_context"):
        yield


def _search(client, user, q, **params):
    return client.get(
        "/api/v1/search", params={"q": q, **params}, headers=auth_headers(user)
    )


def _gene(db: Session, symbol: str, n: int) -> Gene:
    gene = Gene(
        hgnc_id=f"HGNC:9{n:04d}",
        approved_symbol=symbol,
        record_hash=f"{n:064d}",
        previous_symbols=[],
        alias_symbols=[],
        details={},
    )
    db.add(gene)
    db.commit()
    return gene


def _curation(db, scope, gene, wp, user) -> CurationNew:
    c = CurationNew(
        scope_id=scope.id,
        gene_id=gene.id,
        workflow_pair_id=wp.id,
        workflow_stage="curation",
        evidence_data={},
        created_by=user.id,
    )
    db.add(c)
    db.commit()
    return c


def test_requires_authentication(client: TestClient):
    assert client.get("/api/v1/search", params={"q": "abc"}).status_code in (401, 403)


@pytest.mark.parametrize("q", ["", " a ", "x" * 101])
def test_rejects_bad_query(client, db_session, q):
    assert _search(client, make_user(db_session), q).status_code == 422


def test_genes_exact_first_then_prefix_then_alphabetical(client, db_session):
    for n, s in enumerate(["BRCA2", "ABRCA1", "BRCA1", "BRCA10"]):
        _gene(db_session, s, n)
    body = _search(client, make_user(db_session), "brca1").json()
    assert [g["symbol"] for g in body["genes"]] == ["BRCA1", "BRCA10", "ABRCA1"]


def test_wildcards_are_literal(client, db_session):
    _gene(db_session, "AB_C", 1)
    _gene(db_session, "ABXC", 2)
    user = make_user(db_session)
    assert [g["symbol"] for g in _search(client, user, "B_C").json()["genes"]] == [
        "AB_C"
    ]
    assert _search(client, user, "A%C").json()["genes"] == []


def test_limit_per_group(client, db_session):
    for n in range(8):
        _gene(db_session, f"GENE{n}", n)
    body = _search(client, make_user(db_session), "gene", limit=3).json()
    assert len(body["genes"]) == 3


def test_curations_and_scopes_only_from_accepted_memberships(
    client, db_session, test_scope: Scope, test_workflow_pair: WorkflowPair
):
    other = Scope(name="kidney-secret", display_name="Kidney Secret", is_active=True)
    db_session.add(other)
    db_session.commit()
    gene = _gene(db_session, "PKD1", 1)
    owner = make_user(db_session)
    mine = _curation(db_session, test_scope, gene, test_workflow_pair, owner)
    theirs = _curation(db_session, other, gene, test_workflow_pair, owner)
    member, pending, outsider = (make_user(db_session) for _ in range(3))
    make_member(db_session, test_scope, member, "viewer")
    make_member(db_session, test_scope, pending, "viewer", accepted=False)

    got = _search(client, member, "pkd").json()
    assert [c["id"] for c in got["curations"]] == [str(mine.id)]
    assert got["curations"][0]["gene_symbol"] == "PKD1"
    assert _search(client, member, "kidney").json()["scopes"] == []
    for user in (pending, outsider):
        got = _search(client, user, "pkd").json()
        assert got["curations"] == []
    admin = make_user(db_session, role="admin")
    ids = {c["id"] for c in _search(client, admin, "pkd").json()["curations"]}
    assert ids == {str(mine.id), str(theirs.id)}
    assert [
        s["name"] for s in _search(client, admin, "kidney-secret").json()["scopes"]
    ] == ["kidney-secret"]


def test_member_finds_own_scope_by_name(client, db_session, test_scope: Scope):
    user = make_user(db_session)
    make_member(db_session, test_scope, user, "viewer")
    got = _search(client, user, test_scope.name[:4]).json()
    assert [s["id"] for s in got["scopes"]] == [str(test_scope.id)]


def test_query_count_is_bounded(client, db_session, test_scope: Scope):
    from sqlalchemy import event

    user = make_user(db_session)
    make_member(db_session, test_scope, user, "viewer")
    for n in range(10):
        _gene(db_session, f"CNT{n}", n)
    seen: list[str] = []
    engine = db_session.get_bind()
    listener = lambda *a: seen.append(a[2])  # noqa: E731
    event.listen(engine, "before_cursor_execute", listener)
    try:
        assert _search(client, user, "cnt", limit=10).status_code == 200
    finally:
        event.remove(engine, "before_cursor_execute", listener)
    assert len(seen) <= 6  # auth + 3 searches (+ token/user lookups)
