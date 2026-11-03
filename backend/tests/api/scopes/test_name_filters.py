"""MCP study finding 7: find review assignments and curations by gene and scope name."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CurationNew, Scope, UserNew
from tests.api.scopes.factories import (
    auth_headers,
    make_curation,
    make_gene,
    make_precuration,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def two_in_review(
    db_session: Session, curator: UserNew, scope_with_admin: Scope
) -> list[CurationNew]:
    return [
        make_curation(
            db_session,
            scope=scope_with_admin,
            gene=make_gene(db_session),
            creator=curator,
        )
        for _ in range(2)
    ]


def test_my_assignments_carry_names_and_filter_by_them(
    client: TestClient,
    curator: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
    two_in_review: list[CurationNew],
) -> None:
    for curation in two_in_review:
        assigned = client.post(
            f"/api/v1/workflow/curation/{curation.id}/assign-reviewer",
            json={"reviewer_id": str(reviewer.id)},
            headers=auth_headers(curator),
        )
        assert assigned.status_code == 200
    symbol = two_in_review[0].gene.approved_symbol
    url = "/api/v1/workflow/reviews/my-assignments"

    by_gene = client.get(
        url, params={"gene_symbol": symbol.lower()}, headers=auth_headers(reviewer)
    )
    by_scope = client.get(
        url,
        params={"scope_name": scope_with_admin.name},
        headers=auth_headers(reviewer),
    )
    other = client.get(
        url, params={"scope_name": "no-such-scope"}, headers=auth_headers(reviewer)
    )

    assert by_gene.status_code == 200
    assert [
        (r["item_id"], r["gene_symbol"], r["scope_name"]) for r in by_gene.json()
    ] == [(str(two_in_review[0].id), symbol, scope_with_admin.name)]
    assert len(by_scope.json()) == 2
    assert other.json() == []


def test_list_curations_filters_by_gene_symbol_and_scope_name(
    client: TestClient,
    curator: UserNew,
    scope_with_admin: Scope,
    two_in_review: list[CurationNew],
) -> None:
    symbol = two_in_review[1].gene.approved_symbol
    url = "/api/v1/curations/"

    by_gene = client.get(
        url, params={"gene_symbol": symbol.lower()}, headers=auth_headers(curator)
    )
    by_scope = client.get(
        url, params={"scope_name": scope_with_admin.name}, headers=auth_headers(curator)
    )
    unknown = client.get(
        url, params={"gene_symbol": "NOPE1"}, headers=auth_headers(curator)
    )

    clash = client.get(
        url,
        params={"gene_symbol": symbol, "gene_id": str(two_in_review[0].gene_id)},
        headers=auth_headers(curator),
    )

    assert clash.json()["total"] == 0
    assert [c["id"] for c in by_gene.json()["curations"]] == [str(two_in_review[1].id)]
    assert by_scope.json()["total"] == 2
    assert unknown.json() == {"curations": [], "total": 0, "skip": 0, "limit": 50}


@pytest.mark.parametrize("kind", ["curations", "precurations"])
def test_both_lists_filter_by_gene_symbol_and_hgnc_id(
    client: TestClient, db_session: Session, curator: UserNew, scope_with_admin: Scope,
    kind: str,
) -> None:  # fmt: skip
    """#651: agents found a gene's precurations only by paging the whole scope."""
    genes = [make_gene(db_session) for _ in range(2)]
    make = make_precuration if kind == "precurations" else make_curation
    items = [
        make(db_session, scope=scope_with_admin, gene=g, creator=curator) for g in genes
    ]
    url, h = f"/api/v1/{kind}/", auth_headers(curator)
    gene = genes[1]

    def ids(**params: str) -> list[str]:
        r = client.get(
            url, params={"scope_name": scope_with_admin.name, **params}, headers=h
        )
        assert r.status_code == 200, r.text
        return [i["id"] for i in r.json()[kind]]

    want = [str(items[1].id)]
    assert ids(gene_symbol=gene.approved_symbol.lower()) == want
    assert ids(hgnc_id=gene.hgnc_id.lower()) == want
    assert ids(gene_symbol=gene.approved_symbol, hgnc_id=genes[0].hgnc_id) == []
    assert ids(gene_symbol="NOPE1") == []
    assert len(ids()) == 2
