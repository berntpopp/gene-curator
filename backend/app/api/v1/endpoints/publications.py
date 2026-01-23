"""Publication validation and retrieval endpoints

Provides PMID validation using Europe PMC API with database caching.
Publications are stored locally to reduce API calls and enable association
with curations and evidence items.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.deps import get_current_active_user
from app.core.logging import api_endpoint, get_logger
from app.models.models import Publication, UserNew
from app.schemas.validation import (
    PMIDValidationRequest,
    PMIDValidationResponse,
    PublicationData,
)
from app.services.publication_service import PublicationService

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
    search: str | None = Query(None, description="Search in title or authors"),
    current_user: UserNew = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> list[PublicationData]:
    """List cached publications

    Returns publications from the local cache. Use this to browse
    previously validated publications.

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
        search_term = f"%{search}%"
        stmt = stmt.where(
            (Publication.title.ilike(search_term))
            | (Publication.author_string.ilike(search_term))
            | (Publication.pmid.ilike(search_term))
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
