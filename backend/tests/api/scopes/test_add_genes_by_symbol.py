"""Add genes to a scope by HGNC symbol in one call (MCP study, plan item 2c). HGNC is mocked."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Gene, GeneScopeAssignment, Scope, UserNew
from app.schemas.validation import HGNCGeneSearchResult, HGNCSearchResponse
from app.services.validators import HGNCValidator
from tests.api.scopes.factories import auth_headers, make_gene

pytestmark = pytest.mark.unit

URL = "/api/v1/scopes/genes"
PKD1 = HGNCGeneSearchResult(hgnc_id="HGNC:9008", symbol="PKD1", name="polycystin 1")
GHOST = HGNCGeneSearchResult(hgnc_id="HGNC:3", symbol="GHOST")  # fetch finds nothing
AMB = [
    HGNCGeneSearchResult(hgnc_id="HGNC:1", symbol="AAA1", alias_symbols=["DUP"]),
    HGNCGeneSearchResult(hgnc_id="HGNC:2", symbol="BBB2", alias_symbols=["DUP"]),
]


@pytest.fixture(autouse=True)
def hgnc(monkeypatch: pytest.MonkeyPatch) -> None:
    async def search(
        _: HGNCValidator, query: str, limit: int = 10
    ) -> HGNCSearchResponse:
        hits = {"PKD1": [PKD1], "DUP": AMB, "GHOST": [GHOST]}.get(query.upper(), [])
        return HGNCSearchResponse(query=query, total_results=len(hits), results=hits)

    async def fetch(_: HGNCValidator, hgnc_id: str) -> HGNCGeneSearchResult | None:
        return PKD1 if hgnc_id == PKD1.hgnc_id else None

    monkeypatch.setattr(HGNCValidator, "search", search)
    monkeypatch.setattr(HGNCValidator, "fetch_gene_by_id", fetch)
    monkeypatch.setattr(HGNCValidator, "close", AsyncMock())


def test_curator_adds_known_new_and_unknown_symbols_in_one_call(
    client: TestClient, db_session: Session, curator: UserNew, scope_with_admin: Scope
) -> None:
    local = make_gene(db_session)
    r = client.post(
        URL,
        json={
            "scope_name": scope_with_admin.name,
            "symbols": [local.approved_symbol.lower(), "PKD1", "DUP", "NOPE1", "PKD1"],
        },
        headers=auth_headers(curator),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert [(i["status"], i["created"]) for i in body["items"]] == [
        ("added", False),
        ("added", True),
        ("ambiguous", False),
        ("not_found", False),
        ("already_in_scope", False),
    ]
    assert body["added"] == 2
    assert {c["symbol"] for c in body["items"][2]["candidates"]} == {"AAA1", "BBB2"}
    pkd1 = db_session.scalars(select(Gene).where(Gene.hgnc_id == "HGNC:9008")).one()
    assert body["items"][1]["gene_id"] == str(pkd1.id)
    assigned = db_session.scalars(
        select(GeneScopeAssignment.gene_id).where(
            GeneScopeAssignment.scope_id == scope_with_admin.id
        )
    ).all()
    assert set(assigned) == {local.id, pkd1.id}

    again = client.post(
        URL,
        json={"scope_id": str(scope_with_admin.id), "symbols": ["PKD1"]},
        headers=auth_headers(curator),
    )
    assert again.json()["items"][0]["status"] == "already_in_scope"


def test_viewer_cannot_add_and_scope_is_required(
    client: TestClient, viewer: UserNew, scope_with_admin: Scope
) -> None:
    denied = client.post(
        URL,
        json={"scope_id": str(scope_with_admin.id), "symbols": ["PKD1"]},
        headers=auth_headers(viewer),
    )
    assert denied.status_code == 403
    missing = client.post(URL, json={"symbols": ["PKD1"]}, headers=auth_headers(viewer))
    assert missing.status_code == 422


def test_symbol_hgnc_cannot_verify_is_not_found(
    client: TestClient, curator: UserNew, scope_with_admin: Scope
) -> None:
    r = client.post(
        URL,
        json={"scope_id": str(scope_with_admin.id), "symbols": ["GHOST"]},
        headers=auth_headers(curator),
    )
    (item,) = r.json()["items"]
    assert (item["status"], item["gene_id"], item["hgnc_id"]) == (
        "not_found",
        None,
        "HGNC:3",
    )
    assert r.json()["added"] == 0
