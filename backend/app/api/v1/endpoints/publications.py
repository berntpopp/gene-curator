"""Publication validation and retrieval endpoints

Provides PMID validation using Europe PMC API with database caching.
Publications are stored locally to reduce API calls and enable association
with curations and evidence items.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_async_db, get_current_active_user
from app.core.logging import api_endpoint, get_logger
from app.core.search_text import SearchText, escape_like
from app.models.models import Publication, UserNew
from app.schemas.validation import (
    PMIDValidationRequest,
    PMIDValidationResponse,
    PublicationData,
    PublicationSearchHit,
    PublicationSearchResponse,
)
from app.services.publication_service import (
    PublicationService,
    gene_names,
    mentions,
    search_publications,
    search_term,
)

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/validate",
    response_model=PMIDValidationResponse,
    summary="Validate PMIDs",
)
@api_endpoint()
async def validate_pmids(
    *,
    request: PMIDValidationRequest,
    current_user: UserNew = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> PMIDValidationResponse:
    """Validate one or more PubMed IDs

    Validates PMIDs against Europe PMC API and caches valid publications
    in the database for future use. Returns publication metadata for
    valid PMIDs.

    Args:
        request: PMIDValidationRequest with list of PMIDs (max 50)
        current_user: Current authenticated user
        db: Database session

    Returns:
        PMIDValidationResponse with validation results for each PMID

    Example request:
        ```json
        {
            "pmids": ["12345678", "23456789"]
        }
        ```

    Example response:
        ```json
        {
            "total_requested": 2,
            "valid_count": 2,
            "invalid_count": 0,
            "results": [
                {
                    "pmid": "12345678",
                    "is_valid": true,
                    "publication": {
                        "pmid": "12345678",
                        "title": "Example publication title",
                        "authors": ["Author A", "Author B"],
                        "journal": "Nature Genetics",
                        "year": 2023
                    }
                }
            ]
        }
        ```
    """
    logger.debug(
        "PMID validation requested",
        pmid_count=len(request.pmids),
        user_id=str(current_user.id),
    )

    service = PublicationService(db)
    try:
        result = await service.validate_pmids(
            request.pmids,
            user_id=str(current_user.id),
        )
        symbol = (request.gene_symbol or "").strip()  # "  " is no symbol
        if symbol:
            names = await gene_names(db, symbol)
            for r in result.results:
                r.mentions_gene = mentions(names, r.publication)

        logger.info(
            "PMID validation completed",
            requested=len(request.pmids),
            valid=result.valid_count,
            invalid=result.invalid_count,
            user_id=str(current_user.id),
        )

        return result
    finally:
        await service.close()


@router.get("/search", response_model=PublicationSearchResponse)
@api_endpoint()
def search_pubmed(
    *,
    query: SearchText = None,
    gene_symbol: SearchText = None,
    disease: SearchText = None,
    limit: int = Query(10, ge=1, le=25),
    current_user: UserNew = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PublicationSearchResponse:
    """Search PubMed literature (via Europe PMC) by free text, gene symbol and disease
    terms, all of which must match. Returns pmid, title, journal, year, publication type
    (case report or cohort) and an abstract snippet, best match first; get_publication
    returns the full abstract. Records are cached, so validate_pmids knows them."""
    if not any(p and p.strip() for p in (query, gene_symbol, disease)):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Send query, gene_symbol or disease",
        )
    term = search_term(query, gene_symbol, disease)
    try:
        total, found = search_publications(db, term, limit)
    except (httpx.HTTPError, TimeoutError) as e:
        logger.warning("PubMed search failed", error=str(e))
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Europe PMC is unavailable; retry later",
        ) from e
    return PublicationSearchResponse(
        query=term,
        total=total,
        results=[
            PublicationSearchHit(
                pmid=p.pmid,
                title=p.title,
                journal=p.journal,
                year=p.year,
                abstract_snippet=p.abstract[:300] if p.abstract else None,
                pub_type=p.pub_type,
            )
            for p in found
        ],
    )


@router.get(
    "/{pmid}",
    response_model=PublicationData,
    summary="Get publication by PMID",
)
@api_endpoint()
async def get_publication(
    *,
    pmid: str = Path(
        ...,
        description="PubMed ID",
        pattern=r"^\d+$",
    ),
    current_user: UserNew = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> PublicationData:
    """Get publication data by PMID

    Retrieves publication from cache or fetches from Europe PMC API.
    Valid publications are cached for future requests.
    To check PMIDs before citing them, use validate_pmids (up to 50 at once).

    Args:
        pmid: PubMed ID (numeric string)
        current_user: Current authenticated user
        db: Database session

    Returns:
        PublicationData with full publication metadata

    Raises:
        404: Publication not found
    """
    logger.debug(
        "Publication fetch requested",
        pmid=pmid,
        user_id=str(current_user.id),
    )

    service = PublicationService(db)
    try:
        publication = await service.get_publication(pmid)

        if publication is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Publication not found: {pmid}",
            )

        logger.info(
            "Publication returned",
            pmid=pmid,
            cached=True,  # If we got here, it's cached now
            user_id=str(current_user.id),
        )

        return publication
    finally:
        await service.close()


@router.get(
    "",
    response_model=list[PublicationData],
    summary="List cached publications",
)
@api_endpoint()
async def list_publications(
    *,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    search: SearchText = None,
    current_user: UserNew = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> list[PublicationData]:
    """List cached publications

    Returns publications from the local cache. Use this to browse
    previously validated publications. To check PMIDs, use validate_pmids.

    Args:
        skip: Pagination offset
        limit: Maximum number of results (1-100)
        search: Optional search term for title/authors
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of PublicationData objects
    """
    logger.debug(
        "Publications list requested",
        skip=skip,
        limit=limit,
        search=search,
        user_id=str(current_user.id),
    )

    stmt = select(Publication).order_by(Publication.created_at.desc())

    if search:
        search_term = f"%{escape_like(search)}%"
        stmt = stmt.where(
            (Publication.title.ilike(search_term, escape="\\"))
            | (Publication.author_string.ilike(search_term, escape="\\"))
            | (Publication.pmid.ilike(search_term, escape="\\"))
        )

    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    publications = result.scalars().all()

    logger.info(
        "Publications returned",
        count=len(publications),
        skip=skip,
        limit=limit,
        user_id=str(current_user.id),
    )

    return [
        PublicationData(
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
        for pub in publications
    ]


@router.get(
    "/stats/count",
    response_model=dict,
    summary="Get publication cache statistics",
)
@api_endpoint()
async def get_publication_stats(
    *,
    current_user: UserNew = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, int]:
    """Get statistics about cached publications

    Returns count of cached publications and other stats.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dictionary with cache statistics
    """
    # Count total publications
    count_stmt = select(func.count(Publication.id))
    count_result = await db.execute(count_stmt)
    total_count = count_result.scalar() or 0

    # Count open access
    oa_stmt = select(func.count(Publication.id)).where(
        Publication.is_open_access == True  # noqa: E712
    )
    oa_result = await db.execute(oa_stmt)
    oa_count = oa_result.scalar() or 0

    return {
        "total_cached": total_count,
        "open_access_count": oa_count,
    }
