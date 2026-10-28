"""Behaviour tests for PublicationService (Europe PMC mocked via MockTransport).

The async DB session is a mock: aiosqlite is not installed, and the cache logic
under test is the query/commit sequence rather than PostgreSQL behaviour.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import httpx
import pytest

from app.models.models import Publication
from app.services.publication_service import EUROPE_PMC_API_BASE, PublicationService

ARTICLE = {
    "result": {
        "title": "A gene and a disease",
        "authorList": {
            "author": [{"fullName": "Smith J"}, {"fullName": ""}, {"lastName": "X"}]
        },
        "authorString": "Smith J",
        "journalTitle": "Genet Med",
        "journalIssueId": "GenMed",
        "pubYear": "2021",
        "journalVolume": "23",
        "issue": "4",
        "pageInfo": "100-110",
        "doi": "10.1/abc",
        "pmcid": "PMC123",
        "abstractText": "Abstract.",
        "pubTypeList": {"pubType": ["Journal Article", "Review"]},
        "isOpenAccess": "Y",
        "citedByCount": 7,
        "firstPublicationDate": "2021-02-01",
    }
}


def _db() -> MagicMock:
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    db.add = MagicMock()
    return db


def _no_row(db: MagicMock) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result


def _row(db: MagicMock, pub: Publication | None) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = pub
    db.execute.return_value = result


def _service(handler: Any, db: MagicMock | None = None) -> PublicationService:
    svc = PublicationService(db or _db())
    svc._client = httpx.AsyncClient(
        base_url=EUROPE_PMC_API_BASE, transport=httpx.MockTransport(handler)
    )
    return svc


def _publication(pmid: str = "123") -> Publication:
    return Publication(
        pmid=pmid,
        title="Cached title",
        authors=["Doe J"],
        author_string="Doe J",
        journal="J",
        journal_abbrev="J",
        volume="1",
        issue="2",
        pages="3-4",
        pub_year=2020,
        pub_date="2020-01-01",
        doi="10.1/x",
        pmcid=None,
        abstract=None,
        pub_type="Journal Article",
        is_open_access=False,
        cited_by_count=0,
    )


def test_parse_full_publication_record() -> None:
    svc = _service(lambda request: httpx.Response(200))
    data = svc._parse_publication_response(ARTICLE, "123")

    assert data is not None
    assert data.pmid == "123"
    assert data.authors == ["Smith J"]  # blank and name-less entries dropped
    assert data.year == 2021
    assert data.pub_type == "Journal Article"
    assert data.is_open_access is True
    assert data.cited_by_count == 7
    assert data.publication_date == "2021-02-01"


def test_parse_handles_sparse_and_invalid_records() -> None:
    svc = _service(lambda request: httpx.Response(200))

    assert svc._parse_publication_response({}, "1") is None
    assert svc._parse_publication_response({"result": {}}, "1") is None

    sparse = svc._parse_publication_response(
        {"result": {"title": "T", "pubYear": "not-a-year", "isOpenAccess": "N"}}, "1"
    )
    assert sparse is not None
    assert sparse.year is None
    assert sparse.pub_type is None
    assert sparse.authors == []
    assert sparse.journal == "Unknown"
    assert sparse.is_open_access is False


@pytest.mark.asyncio
async def test_fetch_publication_normalises_prefix_and_parses_success() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json=ARTICLE)

    svc = _service(handler)
    result = await svc.fetch_publication(" pmid:123 ")
    await svc.close()

    assert seen == ["/europepmc/webservices/rest/article/MED/123"]
    assert result.is_valid is True
    assert result.publication is not None
    assert result.pmid == "123"
    assert result.error is None


@pytest.mark.asyncio
async def test_fetch_publication_error_shapes() -> None:
    svc = _service(lambda request: httpx.Response(404))
    not_found = await svc.fetch_publication("999")
    assert not_found.is_valid is False
    assert "not found" in (not_found.error or "")

    svc = _service(lambda request: httpx.Response(500))
    http_error = await svc.fetch_publication("999")
    assert http_error.error == "API error: HTTP 500"

    svc = _service(lambda request: httpx.Response(200, json={"result": {}}))
    empty = await svc.fetch_publication("999")
    assert empty.error == "Publication not found or invalid response"

    svc = _service(lambda request: httpx.Response(200, text="not json"))
    bad_body = await svc.fetch_publication("999")
    assert bad_body.is_valid is False
    assert bad_body.error

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    svc = _service(timeout)
    timed_out = await svc.fetch_publication("999")
    await svc.close()
    assert timed_out.error == "API timeout"


@pytest.mark.asyncio
async def test_fetch_publication_reports_unexpected_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    svc = _service(handler)
    result = await svc.fetch_publication("123")
    await svc.close()

    assert result.is_valid is False
    assert "refused" in (result.error or "")


@pytest.mark.asyncio
async def test_validate_pmids_serves_cache_then_fetches_and_caches() -> None:
    db = _db()
    cached = _publication("1")
    hit = MagicMock()
    hit.scalar_one_or_none.return_value = cached
    miss = MagicMock()
    miss.scalar_one_or_none.return_value = None
    # PMID 1: cache hit. PMID 2: cache miss, fetch, then existence check before insert.
    db.execute.side_effect = [hit, miss, miss]

    svc = _service(lambda request: httpx.Response(200, json=ARTICLE), db)
    response = await svc.validate_pmids(["PMID:1", "2"], user_id=str(UUID(int=5)))
    await svc.close()

    assert response.total_requested == 2
    assert response.valid_count == 2
    assert response.invalid_count == 0
    assert response.results[0].publication is not None
    assert response.results[0].publication.title == "Cached title"
    db.add.assert_called_once()  # PMID 2 was fetched and cached
    added = db.add.call_args.args[0]
    assert added.pmid == "2"
    assert added.added_by == UUID(int=5)


@pytest.mark.asyncio
async def test_validate_pmids_counts_invalid_entries() -> None:
    db = _db()
    _no_row(db)
    svc = _service(lambda request: httpx.Response(404), db)
    response = await svc.validate_pmids(["404", "405"])
    await svc.close()

    assert response.valid_count == 0
    assert response.invalid_count == 2
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_get_cached_publication_maps_model_fields() -> None:
    db = _db()
    _row(db, _publication("77"))
    svc = _service(lambda request: httpx.Response(200), db)
    data = await svc._get_cached_publication("77")
    await svc.close()

    assert data is not None
    assert data.pmid == "77"
    assert data.year == 2020
    assert data.publication_date == "2020-01-01"
    assert data.authors == ["Doe J"]


@pytest.mark.asyncio
async def test_get_cached_publication_missing_returns_none() -> None:
    db = _db()
    _no_row(db)
    svc = _service(lambda request: httpx.Response(200), db)
    assert await svc._get_cached_publication("1") is None
    await svc.close()


@pytest.mark.asyncio
async def test_cache_publication_inserts_new_record_with_user() -> None:
    db = _db()
    _no_row(db)
    svc = _service(lambda request: httpx.Response(200), db)
    data = svc._parse_publication_response(ARTICLE, "123")
    assert data is not None

    pub = await svc._cache_publication(data, user_id=str(UUID(int=9)))
    await svc.close()

    assert pub is not None
    db.add.assert_called_once()
    assert db.add.call_args.args[0].added_by == UUID(int=9)
    db.commit.assert_awaited()
    db.refresh.assert_awaited()


@pytest.mark.asyncio
async def test_cache_publication_updates_existing_record() -> None:
    db = _db()
    existing = _publication("123")
    _row(db, existing)
    svc = _service(lambda request: httpx.Response(200), db)
    data = svc._parse_publication_response(ARTICLE, "123")
    assert data is not None

    pub = await svc._cache_publication(data)
    await svc.close()

    assert pub is existing
    assert existing.title == "A gene and a disease"
    assert existing.last_fetched_at is not None
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_cache_publication_invalid_user_id_rolls_back() -> None:
    db = _db()
    _no_row(db)
    svc = _service(lambda request: httpx.Response(200), db)
    data = svc._parse_publication_response(ARTICLE, "123")
    assert data is not None

    pub = await svc._cache_publication(data, user_id="not-a-uuid")
    await svc.close()

    assert pub is None
    db.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_get_publication_cache_then_api_then_none() -> None:
    db = _db()
    _row(db, _publication("5"))
    svc = _service(lambda request: httpx.Response(500), db)
    hit = await svc.get_publication("5")
    assert hit is not None and hit.title == "Cached title"

    db = _db()
    _no_row(db)
    svc = _service(lambda request: httpx.Response(200, json=ARTICLE), db)
    fetched = await svc.get_publication("PMID:123")
    await svc.close()
    assert fetched is not None and fetched.pmid == "123"
    db.add.assert_called_once()

    db = _db()
    _no_row(db)
    svc = _service(lambda request: httpx.Response(404), db)
    missing = await svc.get_publication("123")
    await svc.close()
    assert missing is None
