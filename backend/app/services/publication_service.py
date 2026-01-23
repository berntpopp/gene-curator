"""Publication validation service using Europe PMC API

This service provides PMID validation and publication data retrieval using
the Europe PMC RESTful API (https://www.ebi.ac.uk/europepmc/webservices/rest/).

Design Principles:
- Single Responsibility: Handles publication operations only
- Caching: Stores validated publications in database to reduce API calls
- Graceful degradation: Returns meaningful errors on API failures
"""

import contextlib
from datetime import datetime as dt, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
            journal=result.get("journalTitle", "Unknown"),
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
        results: list[PMIDValidationResult] = []
        valid_count = 0
        invalid_count = 0

        for pmid in pmids:
            # Normalize PMID
            clean_pmid = pmid.strip().upper()
            if clean_pmid.startswith("PMID:"):
                clean_pmid = clean_pmid[5:]
            clean_pmid = clean_pmid.strip()

            # Check database cache first
            cached = await self._get_cached_publication(clean_pmid)
            if cached:
                results.append(
                    PMIDValidationResult(
                        pmid=clean_pmid,
                        is_valid=True,
                        publication=cached,
                        error=None,
                    )
                )
                valid_count += 1
                logger.debug("Publication found in cache", pmid=clean_pmid)
                continue

            # Fetch from API
            result = await self.fetch_publication(clean_pmid)
            results.append(result)

            if result.is_valid and result.publication:
                valid_count += 1
                # Cache the publication
                await self._cache_publication(result.publication, user_id)
            else:
                invalid_count += 1

        return PMIDValidationResponse(
            total_requested=len(pmids),
            valid_count=valid_count,
            invalid_count=invalid_count,
            results=results,
        )

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
                existing.last_fetched_at = dt.now(timezone.utc)
                await self._db.commit()
                logger.debug("Publication updated in cache", pmid=data.pmid)
                return existing

            # Create new record
            from uuid import UUID

            pub = Publication(
                pmid=data.pmid,
                title=data.title,
                authors=data.authors,
                author_string=data.author_string,
                journal=data.journal,
                journal_abbrev=data.journal_abbrev,
                volume=data.volume,
                issue=data.issue,
                pages=data.pages,
                pub_year=data.year,
                pub_date=data.publication_date,
                doi=data.doi,
                pmcid=data.pmcid,
                abstract=data.abstract,
                pub_type=data.pub_type,
                is_open_access=data.is_open_access,
                cited_by_count=data.cited_by_count,
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
