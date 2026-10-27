"""Publication validation service using Europe PMC API

This service provides PMID validation and publication data retrieval using
the Europe PMC RESTful API (https://www.ebi.ac.uk/europepmc/webservices/rest/).

Design Principles:
- Single Responsibility: Handles publication operations only
- Caching: Stores validated publications in database to reduce API calls
- Graceful degradation: Returns meaningful errors on API failures
"""

import asyncio
import contextlib
import re
from datetime import UTC, datetime as dt
from typing import Any, cast

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.logging import get_logger, timed_operation
from app.models.models import Publication
from app.schemas.validation import (
    PMIDValidationResponse,
    PMIDValidationResult,
    PublicationData,
)

logger = get_logger(__name__)

# Europe PMC API base URL
EUROPE_PMC_API_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"


class PublicationService:
    """Service for validating PMIDs and retrieving publication data

    Uses Europe PMC API which provides:
    - No authentication required
    - Comprehensive publication metadata
    - Includes abstracts and citation counts
    - Fast response times
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize with database session for caching"""
        self._db = db
        self._client = httpx.AsyncClient(
            base_url=EUROPE_PMC_API_BASE,
            headers={"Accept": "application/json"},
            timeout=15.0,
        )

    async def close(self) -> None:
        """Close HTTP client"""
        await self._client.aclose()

    def _parse_publication_response(
        self, data: dict[str, Any], pmid: str
    ) -> PublicationData | None:
        """Parse Europe PMC API response into PublicationData

        Args:
            data: API response data
            pmid: The requested PMID

        Returns:
            PublicationData if parsing successful, None otherwise
        """
        result = data.get("result", {})
        if not result:
            return None

        # Extract authors list
        authors = []
        author_list = result.get("authorList", {}).get("author", [])
        for author in author_list:
            full_name = author.get("fullName", "")
            if full_name:
                authors.append(full_name)

        # Extract year from various date fields
        year = None
        pub_year = result.get("pubYear")
        if pub_year:
            with contextlib.suppress(ValueError, TypeError):
                year = int(pub_year)

        return PublicationData(
            pmid=pmid,
            title=result.get("title", ""),
            authors=authors,
            author_string=result.get("authorString"),
            journal=result.get("journalTitle")
            or result.get("journalInfo", {}).get("journal", {}).get("title")
            or "Unknown",
            journal_abbrev=result.get("journalIssueId"),
            year=year,
            volume=result.get("journalVolume"),
            issue=result.get("issue"),
            pages=result.get("pageInfo"),
            doi=result.get("doi"),
            pmcid=result.get("pmcid"),
            abstract=result.get("abstractText"),
            pub_type=result.get("pubTypeList", {}).get("pubType", [None])[0]
            if result.get("pubTypeList")
            else None,
            is_open_access=result.get("isOpenAccess") == "Y",
            cited_by_count=result.get("citedByCount"),
            publication_date=result.get("firstPublicationDate"),
        )

    @timed_operation("pmid_fetch", warning_threshold_ms=3000)
    async def fetch_publication(self, pmid: str) -> PMIDValidationResult:
        """Fetch publication data from Europe PMC API

        Args:
            pmid: PubMed ID to validate

        Returns:
            PMIDValidationResult with publication data or error
        """
        # Normalize PMID (remove prefix if present)
        clean_pmid = pmid.strip().upper()
        if clean_pmid.startswith("PMID:"):
            clean_pmid = clean_pmid[5:]
        clean_pmid = clean_pmid.strip()

        try:
            response = await self._client.get(
                f"/article/MED/{clean_pmid}",
                params={"format": "json"},
            )

            if response.status_code == 404:
                return PMIDValidationResult(
                    pmid=pmid,
                    is_valid=False,
                    publication=None,
                    error=f"Publication not found: {pmid}",
                )

            if response.status_code != 200:
                logger.error(
                    "Europe PMC API error",
                    status_code=response.status_code,
                    pmid=pmid,
                )
                return PMIDValidationResult(
                    pmid=pmid,
                    is_valid=False,
                    publication=None,
                    error=f"API error: HTTP {response.status_code}",
                )

            data = response.json()
            publication = self._parse_publication_response(data, clean_pmid)

            if publication is None:
                return PMIDValidationResult(
                    pmid=pmid,
                    is_valid=False,
                    publication=None,
                    error="Publication not found or invalid response",
                )

            logger.info(
                "Publication fetched",
                pmid=clean_pmid,
                title=publication.title[:50] if publication.title else None,
            )

            return PMIDValidationResult(
                pmid=clean_pmid,
                is_valid=True,
                publication=publication,
                error=None,
            )

        except httpx.TimeoutException:
            logger.error("Europe PMC API timeout", pmid=pmid)
            return PMIDValidationResult(
                pmid=pmid,
                is_valid=False,
                publication=None,
                error="API timeout",
            )
        except Exception as e:
            logger.error("Publication fetch error", pmid=pmid, error=e)
            return PMIDValidationResult(
                pmid=pmid,
                is_valid=False,
                publication=None,
                error=str(e),
            )

    @timed_operation("pmid_validate_batch", warning_threshold_ms=10000)
    async def validate_pmids(
        self, pmids: list[str], user_id: str | None = None
    ) -> PMIDValidationResponse:
        """Validate multiple PMIDs and cache results

        Checks database cache first, then fetches missing publications from API.
        Stores valid publications in database for future use.

        Args:
            pmids: List of PubMed IDs to validate
            user_id: Optional user ID for tracking who added publications

        Returns:
            PMIDValidationResponse with all validation results
        """
        normalized = [p.strip().upper().removeprefix("PMID:").strip() for p in pmids]
        results: dict[str, PMIDValidationResult] = {}
        try:
            async with asyncio.timeout(
                8.0
            ):  # leave room under the browser's 10s timeout
                for pmid in dict.fromkeys(normalized):
                    cached = await self._get_cached_publication(pmid)
                    if cached:
                        results[pmid] = PMIDValidationResult(
                            pmid=pmid, is_valid=True, publication=cached
                        )
                fetched = await self.fetch_many(
                    [p for p in dict.fromkeys(normalized) if p not in results]
                )
                results.update((r.pmid, r) for r in fetched)
                # Only pure HTTP work runs concurrently; the cache session remains serial.
                for result in fetched:
                    if result.is_valid and result.publication:
                        await self._cache_publication(result.publication, user_id)
        except TimeoutError:
            await self._db.rollback()
        ordered = [results.get(p) or _timed_out(p) for p in normalized]
        valid = sum(r.is_valid for r in ordered)
        return PMIDValidationResponse(
            total_requested=len(pmids),
            valid_count=valid,
            invalid_count=len(pmids) - valid,
            results=ordered,
        )

    async def fetch_many(self, pmids: list[str]) -> list[PMIDValidationResult]:
        """Bound HTTP concurrency and total time; retain each completed answer."""
        if not pmids:
            return []
        gate = asyncio.Semaphore(LOOKUP_CONCURRENCY)

        async def one(pmid: str) -> PMIDValidationResult:
            async with gate:
                return await self.fetch_publication(pmid)

        tasks = {p: asyncio.create_task(one(p)) for p in dict.fromkeys(pmids)}
        try:
            _, pending = await asyncio.wait(tasks.values(), timeout=LOOKUP_TIMEOUT_S)
            if pending:
                logger.warning("PMID lookup timed out", pmids=pmids)
            return [
                tasks[p].result() if tasks[p].done() else _timed_out(p) for p in pmids
            ]
        finally:
            for task in tasks.values():
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks.values(), return_exceptions=True)

    async def _get_cached_publication(self, pmid: str) -> PublicationData | None:
        """Get publication from database cache

        Args:
            pmid: PubMed ID to look up

        Returns:
            PublicationData if found, None otherwise
        """
        stmt = select(Publication).where(Publication.pmid == pmid)
        result = await self._db.execute(stmt)
        pub = result.scalar_one_or_none()

        if pub is None:
            return None

        return PublicationData(
            pmid=pub.pmid,
            title=pub.title,
            authors=pub.authors or [],
            author_string=pub.author_string,
            journal=pub.journal,
            journal_abbrev=pub.journal_abbrev,
            year=pub.pub_year,
            volume=pub.volume,
            issue=pub.issue,
            pages=pub.pages,
            doi=pub.doi,
            pmcid=pub.pmcid,
            abstract=pub.abstract,
            pub_type=pub.pub_type,
            is_open_access=pub.is_open_access,
            cited_by_count=pub.cited_by_count,
            publication_date=pub.pub_date,
        )

    async def _cache_publication(
        self, data: PublicationData, user_id: str | None = None
    ) -> Publication | None:
        """Store publication in database cache

        Args:
            data: Publication data to cache
            user_id: Optional user ID for tracking

        Returns:
            Publication model instance, or None if caching failed
        """
        try:
            # Check if already exists
            stmt = select(Publication).where(Publication.pmid == data.pmid)
            result = await self._db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing record
                existing.title = data.title
                existing.authors = data.authors
                existing.author_string = data.author_string
                existing.journal = data.journal
                existing.journal_abbrev = data.journal_abbrev
                existing.volume = data.volume
                existing.issue = data.issue
                existing.pages = data.pages
                existing.pub_year = data.year
                existing.pub_date = data.publication_date
                existing.doi = data.doi
                existing.pmcid = data.pmcid
                existing.abstract = data.abstract
                existing.pub_type = data.pub_type
                existing.is_open_access = data.is_open_access
                existing.cited_by_count = data.cited_by_count
                existing.last_fetched_at = dt.now(UTC)
                await self._db.commit()
                logger.debug("Publication updated in cache", pmid=data.pmid)
                return existing

            # Create new record
            from uuid import UUID

            pub = Publication(
                **publication_row(data),
                added_by=UUID(user_id) if user_id else None,
            )

            self._db.add(pub)
            await self._db.commit()
            await self._db.refresh(pub)

            logger.info("Publication cached", pmid=data.pmid, title=data.title[:50])
            return pub

        except Exception as e:
            logger.error("Failed to cache publication", pmid=data.pmid, error=e)
            await self._db.rollback()
            return None

    async def get_publication(self, pmid: str) -> PublicationData | None:
        """Get a publication by PMID, fetching from API if not cached

        Args:
            pmid: PubMed ID

        Returns:
            PublicationData if found, None otherwise
        """
        # Normalize PMID
        clean_pmid = pmid.strip().upper()
        if clean_pmid.startswith("PMID:"):
            clean_pmid = clean_pmid[5:]
        clean_pmid = clean_pmid.strip()

        # Check cache first
        cached = await self._get_cached_publication(clean_pmid)
        if cached:
            return cached

        # Fetch from API
        result = await self.fetch_publication(clean_pmid)
        if result.is_valid and result.publication:
            await self._cache_publication(result.publication)
            return result.publication

        return None


LOOKUP_CONCURRENCY = 5  # parallel Europe PMC requests per submit
LOOKUP_TIMEOUT_S = 5.0  # whole HTTP batch; frontend requests time out after 10s

# pmid_format as the forms accept it: optional "PMID:" prefix, 1-9 digits
PMID_FORMAT = re.compile(r"^(?:PMID:?\s*)?(\d{1,9})$", re.IGNORECASE)


def publication_row(data: PublicationData) -> dict[str, Any]:
    """Publication columns for one Europe PMC record."""
    return {
        "pmid": data.pmid,
        "title": data.title,
        "authors": data.authors,
        "author_string": data.author_string,
        "journal": data.journal,
        "journal_abbrev": data.journal_abbrev,
        "volume": data.volume,
        "issue": data.issue,
        "pages": data.pages,
        "pub_year": data.year,
        "pub_date": data.publication_date,
        "doi": data.doi,
        "pmcid": data.pmcid,
        "abstract": data.abstract,
        "pub_type": data.pub_type,
        "is_open_access": data.is_open_access,
        "cited_by_count": data.cited_by_count,
    }


def _fit(row: dict[str, Any]) -> dict[str, Any]:
    """Strings cut to their column's length (Europe PMC pages or dates can be longer)."""
    columns = Publication.__table__.c
    return {
        key: value[:length]
        if isinstance(value, str)
        and (length := getattr(columns[key].type, "length", None))
        else value
        for key, value in row.items()
    }


def _cache_found(db: Session, results: list[PMIDValidationResult]) -> None:
    """Store found PMIDs so later saves, previews and submits skip Europe PMC. Best effort:
    a failed insert rolls back only its savepoint, never the caller's save."""
    rows = [
        _fit(publication_row(r.publication))
        for r in results
        if r.is_valid and r.publication
    ]
    if not rows:
        return
    insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
    try:
        with db.begin_nested():
            db.execute(
                insert(Publication)
                .values(rows)
                .on_conflict_do_nothing(index_elements=["pmid"])
            )
    except SQLAlchemyError as e:
        logger.warning(
            "PMID cache insert failed",
            pmids=[row["pmid"] for row in rows],
            error=str(e),
        )


def evidence_pmids(evidence: Any) -> set[str]:
    """Every well-formed PMID under a "pmid" key, at any depth (all evidence tables)."""
    if isinstance(evidence, list):
        return set().union(*(evidence_pmids(v) for v in evidence))
    if not isinstance(evidence, dict):
        return set()
    found = set().union(*(evidence_pmids(v) for v in evidence.values()))
    match = PMID_FORMAT.match(str(evidence.get("pmid") or "").strip())
    return found | {match.group(1)} if match else found


def unknown_pmids(db: Session, pmids: set[str]) -> list[str]:
    """PMIDs Europe PMC reports as not found. Cached ones are known; a failed lookup
    (offline, timeout) does not count as unknown, same rule as the forms."""
    unknown, failed = lookup_pmids(db, pmids)
    if failed:
        logger.warning("PMID lookup failed, not blocking submit", pmids=failed)
    return unknown


def lookup_pmids(db: Session, pmids: set[str]) -> tuple[list[str], list[str]]:
    """(not found, lookup failed) among the PMIDs that are not cached."""
    cached = set(
        db.scalars(select(Publication.pmid).where(Publication.pmid.in_(pmids)))
    )
    missing = sorted(pmids - cached)
    if not missing:
        return [], []
    results = asyncio.run(_fetch_all(missing))
    _cache_found(db, results)
    unknown = [
        r.pmid for r in results if (r.error or "").startswith("Publication not found")
    ]
    failed = [r.pmid for r in results if not r.is_valid and r.pmid not in unknown]
    return unknown, failed


def _timed_out(pmid: str) -> PMIDValidationResult:
    return PMIDValidationResult(
        pmid=pmid, is_valid=False, error="API timeout; retry lookup"
    )


async def _fetch_all(pmids: list[str]) -> list[PMIDValidationResult]:
    """Pure bounded HTTP work; no database session is shared by network tasks."""
    service = PublicationService(cast(AsyncSession, None))
    try:
        return await service.fetch_many(pmids)
    finally:
        await service.close()


SEARCH_TIMEOUT_S = 8.0  # one Europe PMC search request


def search_term(*parts: str | None) -> str:
    """Europe PMC query: every given part must match, PubMed records only."""
    return " AND ".join(
        [f"({p.strip()})" for p in parts if p and p.strip()] + ["SRC:MED"]
    )


async def _search(term: str, limit: int) -> tuple[int, list[PublicationData]]:
    service = PublicationService(cast(AsyncSession, None))
    try:
        response = await asyncio.wait_for(
            service._client.get(
                "/search",
                params={
                    "query": term,
                    "resultType": "core",
                    "pageSize": limit,
                    "format": "json",
                },
            ),
            SEARCH_TIMEOUT_S,
        )
        response.raise_for_status()
        data = response.json()
    finally:
        await service.close()
    found = [
        pub
        for row in data.get("resultList", {}).get("result", [])
        if row.get("pmid")
        and (pub := service._parse_publication_response({"result": row}, row["pmid"]))
    ]
    return int(data.get("hitCount") or 0), found


def search_publications(
    db: Session, term: str, limit: int
) -> tuple[int, list[PublicationData]]:
    """(hit count, top records) from Europe PMC; the records are cached like validated PMIDs.
    Raises httpx.HTTPError or TimeoutError when Europe PMC is unavailable."""
    total, found = asyncio.run(_search(term, limit))
    _cache_found(
        db,
        [
            PMIDValidationResult(pmid=p.pmid, is_valid=True, publication=p)
            for p in found
        ],
    )
    db.commit()
    return total, found
