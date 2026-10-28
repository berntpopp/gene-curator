"""PubMed search from MCP (search_pubmed): Europe PMC is mocked, records are cached."""

from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Publication

pytestmark = pytest.mark.unit

URL = "/api/v1/publications/search"
ROW = {
    "id": "31558469",
    "source": "MED",
    "pmid": "31558469",
    "title": "PKD1 variants in ADPKD",
    "journalInfo": {"journal": {"title": "Kidney International"}},
    "pubYear": "2019",
    "abstractText": "A" * 400,
    "pubTypeList": {"pubType": ["Journal Article", "Case Reports"]},
}


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    seen: list[dict[str, Any]] = []

    async def get(_: httpx.AsyncClient, url: str, **kw: Any) -> httpx.Response:
        seen.append({"url": url, **kw["params"]})
        body = {"hitCount": 42, "resultList": {"result": [ROW, {"id": "PMC1"}]}}
        return httpx.Response(200, json=body, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    return seen


def test_search_by_gene_and_disease_returns_short_rows_and_caches_them(
    client: TestClient, db_session: Session, curator_token: str, calls: list
) -> None:
    r = client.get(
        URL,
        params={"gene_symbol": "PKD1", "disease": "polycystic kidney", "limit": 5},
        headers={"Authorization": f"Bearer {curator_token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["query"] == (
        "(PKD1) AND (polycystic kidney) AND SRC:MED "
        'NOT (PUB_TYPE:"review" NOT PUB_TYPE:"case reports")'
    )  # a gene search leaves reviews out by default
    assert body["total"] == 42
    (hit,) = body["results"]  # the record without a PMID is not PubMed
    assert hit == {
        "pmid": "31558469",
        "title": "PKD1 variants in ADPKD",
        "journal": "Kidney International",
        "year": 2019,
        "abstract_snippet": "A" * 300,
        "pub_type": "Case Reports",
    }
    assert calls[0]["pageSize"] == 5
    assert "sort" not in calls[0]  # Europe PMC's default order is relevance
    cached = db_session.scalars(select(Publication.pmid)).all()
    assert cached == ["31558469"]


def test_search_needs_a_term_and_reports_upstream_failure(
    client: TestClient, curator_token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = {"Authorization": f"Bearer {curator_token}"}
    assert client.get(URL, params={"query": " "}, headers=h).status_code == 422

    async def down(*_: Any, **__: Any) -> httpx.Response:
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx.AsyncClient, "get", down)
    r = client.get(URL, params={"query": "PKD1"}, headers=h)
    assert r.status_code == 503


def test_reviews_sort_and_a_full_page_stays_under_8_kb(
    client: TestClient,
    curator_token: str,
    calls: list,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h = {"Authorization": f"Bearer {curator_token}"}
    r = client.get(
        URL,
        params={"gene_symbol": "PKD1", "exclude_reviews": "false", "sort": "cited"},
        headers=h,
    )
    assert r.json()["query"] == "(PKD1) AND SRC:MED"
    assert calls[-1]["sort"] == "CITED desc"
    assert calls[-1]["pageSize"] == 10  # default
    assert (
        client.get(URL, params={"query": "x", "limit": 11}, headers=h).status_code
        == 422
    )

    async def full(_: httpx.AsyncClient, url: str, **kw: Any) -> httpx.Response:
        rows = [
            {**ROW, "pmid": str(30000000 + i), "title": "T" * 250} for i in range(10)
        ]
        body = {"hitCount": 900, "resultList": {"result": rows}}
        return httpx.Response(200, json=body, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", full)
    page = client.get(URL, params={"query": "PKD1 cohort"}, headers=h)
    assert len(page.json()["results"]) == 10
    assert len(page.content) < 8000, len(page.content)
