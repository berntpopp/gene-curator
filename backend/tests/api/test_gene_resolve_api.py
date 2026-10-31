"""POST /genes/resolve: batch resolution of pasted gene identifiers (#281).

Local genes table first; HGNC is mocked at the class level and never hit.
"""

import hashlib
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy.orm import Session

from app.models.models import Gene, UserNew
from app.schemas.validation import HGNCGeneSearchResult, HGNCSearchResponse
from app.services.validators import HGNCValidator

pytestmark = pytest.mark.unit

URL = "/api/v1/genes/resolve"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _gene(
    db: Session,
    owner: UserNew,
    hgnc_id: str,
    symbol: str,
    previous: list[str] | None = None,
    alias: list[str] | None = None,
) -> Gene:
    gene = Gene(
        id=uuid4(),
        hgnc_id=hgnc_id,
        approved_symbol=symbol,
        record_hash=hashlib.sha256(hgnc_id.encode()).hexdigest(),
        previous_symbols=previous or [],
        alias_symbols=alias or [],
        created_by=owner.id,
        updated_by=owner.id,
    )
    db.add(gene)
    db.commit()
    return gene


@pytest.fixture(autouse=True)
def hgnc_offline(monkeypatch: MonkeyPatch) -> AsyncMock:
    """Any HGNC lookup returns nothing unless a test overrides it."""
    mock = AsyncMock(
        return_value=HGNCSearchResponse(query="", total_results=0, results=[])
    )
    monkeypatch.setattr(HGNCValidator, "search", mock)
    return mock


@pytest.fixture
def genes(db_session: Session, test_user_admin: UserNew) -> dict[str, Gene]:
    o = test_user_admin
    return {
        "PKD1": _gene(db_session, o, "HGNC:9008", "PKD1"),
        "PKD1-AS1": _gene(db_session, o, "HGNC:50000", "PKD1-AS1"),
        "BRCA1": _gene(
            db_session, o, "HGNC:1100", "BRCA1", previous=["BRCC1"], alias=["RNF53"]
        ),
        "OLD": _gene(db_session, o, "HGNC:1", "NEWA", previous=["SHARED"]),
        "OLD2": _gene(db_session, o, "HGNC:2", "NEWB", previous=["SHARED"]),
        "ALIASY": _gene(db_session, o, "HGNC:3", "ZZZ1", alias=["PKD1"]),
    }


def _post(client: TestClient, token: str, symbols: list[str]):
    return client.post(URL, json={"symbols": symbols}, headers=_auth(token))


def test_requires_authentication(client: TestClient) -> None:
    assert client.post(URL, json={"symbols": ["A"]}).status_code in (401, 403)


def test_exact_symbol_wins_over_alias_and_keeps_input_order(
    client: TestClient, curator_token: str, genes: dict[str, Gene]
) -> None:
    body = _post(client, curator_token, ["brca1", "PKD1", "HGNC:1100"]).json()
    items = body["items"]
    assert [i["input"] for i in items] == ["brca1", "PKD1", "HGNC:1100"]
    assert [i["index"] for i in items] == [0, 1, 2]
    # PKD1 is an exact symbol of one gene and an alias of another: the symbol tier wins.
    assert items[1]["status"] == "resolved"
    assert items[1]["match_type"] == "symbol"
    assert [c["hgnc_id"] for c in items[1]["candidates"]] == ["HGNC:9008"]
    assert items[1]["candidates"][0]["gene_id"] == str(genes["PKD1"].id)
    assert items[0]["match_type"] == "symbol"
    assert items[2]["match_type"] == "hgnc_id"
    assert body["counts"] == {"resolved": 3, "ambiguous": 0, "not_found": 0}


def test_previous_symbol_alias_and_bare_hgnc_number(
    client: TestClient, curator_token: str, genes: dict[str, Gene]
) -> None:
    items = _post(client, curator_token, ["BRCC1", "RNF53", "1100"]).json()["items"]
    assert [i["match_type"] for i in items] == ["previous_symbol", "alias", "hgnc_id"]
    assert all(i["candidates"][0]["symbol"] == "BRCA1" for i in items)


def test_ambiguous_lists_every_candidate(
    client: TestClient, curator_token: str, genes: dict[str, Gene]
) -> None:
    item = _post(client, curator_token, ["SHARED"]).json()["items"][0]
    assert item["status"] == "ambiguous"
    assert item["match_type"] == "previous_symbol"
    assert sorted(c["symbol"] for c in item["candidates"]) == ["NEWA", "NEWB"]


def test_duplicates_point_at_first_occurrence(
    client: TestClient, curator_token: str, genes: dict[str, Gene]
) -> None:
    items = _post(
        client, curator_token, ["BRCA1", "brca1", "HGNC:1100", "PKD1"]
    ).json()["items"]
    assert [i["duplicate_of"] for i in items] == [None, 0, 0, None]


def test_unknown_input_falls_back_to_hgnc_exact_match_only(
    client: TestClient,
    curator_token: str,
    genes: dict[str, Gene],
    hgnc_offline: AsyncMock,
) -> None:
    async def fake(query: str, limit: int = 10) -> HGNCSearchResponse:
        hits = {
            "TP53": [
                HGNCGeneSearchResult(hgnc_id="HGNC:11998", symbol="TP53-AS1"),
                HGNCGeneSearchResult(
                    hgnc_id="HGNC:11998", symbol="TP53", name="tumor protein p53"
                ),
            ],
            "TP5": [HGNCGeneSearchResult(hgnc_id="HGNC:11998", symbol="TP53")],
        }
        found = hits.get(query, [])
        return HGNCSearchResponse(query=query, total_results=len(found), results=found)

    hgnc_offline.side_effect = fake
    items = _post(client, curator_token, ["TP53", "TP5", "NOPE"]).json()["items"]
    assert items[0]["status"] == "resolved"
    assert items[0]["source"] == "hgnc"
    assert items[0]["candidates"][0]["gene_id"] is None
    # A prefix hit is not a resolution.
    assert items[1]["status"] == "not_found"
    assert items[2]["status"] == "not_found"
    assert items[2]["candidates"] == []


def test_local_hits_never_call_hgnc(
    client: TestClient,
    curator_token: str,
    genes: dict[str, Gene],
    hgnc_offline: AsyncMock,
) -> None:
    _post(client, curator_token, ["BRCA1", "BRCC1", "HGNC:1100"])
    hgnc_offline.assert_not_awaited()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"symbols": []},
        {"symbols": ["x" * 257]},
        {"symbols": ["A"] * 1001},
        {"symbols": "BRCA1"},
        {"symbols": [1]},
    ],
)
def test_rejects_bad_input_at_the_boundary(
    client: TestClient, curator_token: str, payload: dict[str, object]
) -> None:
    assert (
        client.post(URL, json=payload, headers=_auth(curator_token)).status_code == 422
    )


def test_accepts_the_maximum_list_size(client: TestClient, curator_token: str) -> None:
    response = _post(client, curator_token, ["NOPE"] * 1000)
    assert response.status_code == 200
    assert response.json()["counts"]["not_found"] == 1000


def test_hgnc_fallback_is_capped(
    client: TestClient, curator_token: str, hgnc_offline: AsyncMock
) -> None:
    symbols = [f"UNK{i}" for i in range(1000)]
    items = _post(client, curator_token, symbols).json()["items"]
    assert hgnc_offline.await_count <= 50
    assert [i["input"] for i in items] == symbols
    assert all(i["status"] == "not_found" for i in items)
    assert sum(i["reason"] == "lookup_cap" for i in items) == 950


def test_hgnc_fallback_times_out(
    client: TestClient,
    curator_token: str,
    hgnc_offline: AsyncMock,
    monkeypatch: MonkeyPatch,
) -> None:
    import asyncio

    from app.services import gene_resolver

    async def slow(query: str, limit: int = 10) -> HGNCSearchResponse:
        await asyncio.sleep(5)
        return HGNCSearchResponse(query=query, total_results=0, results=[])

    hgnc_offline.side_effect = slow
    monkeypatch.setattr(gene_resolver, "_HGNC_BUDGET_S", 0.05)
    items = _post(client, curator_token, ["AAA1", "BBB2"]).json()["items"]
    assert [i["reason"] for i in items] == ["lookup_timeout"] * 2


def test_hgnc_hit_fills_gene_id_of_local_row(
    client: TestClient,
    curator_token: str,
    db_session: Session,
    test_user_admin: UserNew,
    hgnc_offline: AsyncMock,
) -> None:
    local = _gene(db_session, test_user_admin, "HGNC:26837", "FAM123A")
    hgnc_offline.return_value = HGNCSearchResponse(
        query="AMER1",
        total_results=1,
        results=[HGNCGeneSearchResult(hgnc_id="HGNC:26837", symbol="AMER1")],
    )
    item = _post(client, curator_token, ["AMER1"]).json()["items"][0]
    assert item["source"] == "hgnc"
    assert item["candidates"][0]["gene_id"] == str(local.id)


@pytest.mark.parametrize(
    "token",
    [
        "ÄÖÜ",
        "%_",
        "😀",
        "",
        "   ",
        "A B",
        "x" * 51,
        "A'; DROP TABLE genes;--",
        "a\x00b",
    ],
)
def test_one_invalid_token_does_not_reject_the_list(
    client: TestClient,
    db_session: Session,
    test_user_admin: UserNew,
    curator_token: str,
    token: str,
) -> None:
    _gene(db_session, test_user_admin, "HGNC:9008", "PKD1")
    items = _post(client, curator_token, ["PKD1", token, "NOTAGENE"]).json()["items"]
    assert [i["status"] for i in items] == ["resolved", "not_found", "not_found"]
    assert items[1]["reason"] == "invalid_identifier"
    assert items[1]["input"] == token.strip()
    assert items[2]["reason"] is None


def test_invalid_tokens_are_never_looked_up_at_hgnc(
    client: TestClient, curator_token: str, hgnc_offline: AsyncMock
) -> None:
    _post(client, curator_token, ["ÄÖÜ", "%_"])
    hgnc_offline.assert_not_called()


def test_scope_id_flags_candidates_already_in_the_scope(
    client: TestClient, db_session: Session, genes: dict[str, Gene]
) -> None:
    """#587 polish: the intake resolve step names genes already in the scope and their
    curator, in the same call; a non-member of the scope is refused."""
    from app.models.models import GeneScopeAssignment
    from tests.api.scopes.factories import (
        auth_headers,
        make_member,
        make_scope,
        make_user,
    )

    scope, alice, outsider = (
        make_scope(db_session),
        make_user(db_session),
        make_user(db_session),
    )
    alice.name = "Alice Smith"
    make_member(db_session, scope, alice, "curator")
    for gene, curator in ((genes["PKD1"], alice.id), (genes["BRCA1"], None)):
        db_session.add(
            GeneScopeAssignment(
                gene_id=gene.id, scope_id=scope.id, assigned_curator_id=curator,
                is_active=True,
            )
        )  # fmt: skip
    db_session.commit()
    body = {"symbols": ["PKD1", "BRCA1", "NEWA"], "scope_id": str(scope.id)}

    items = client.post(URL, json=body, headers=auth_headers(alice)).json()["items"]
    flags = [
        (c["in_scope"], c["in_scope_curator"]) for i in items for c in i["candidates"]
    ]
    assert flags == [(True, "Alice Smith"), (True, None), (False, None)]
    assert (
        client.post(URL, json=body, headers=auth_headers(outsider)).status_code == 403
    )
