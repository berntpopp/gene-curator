"""Ontology search endpoints for MONDO, OMIM, and HPO

Provides search functionality for biomedical ontologies used in gene curation.
These endpoints support autocomplete and term lookup for disease and phenotype
terminology standardization.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.core.deps import get_current_active_user
from app.core.logging import api_endpoint, get_logger
from app.models.models import UserNew
from app.schemas.validation import (
    HPOInheritanceResponse,
    HPOSearchRequest,
    HPOSearchResponse,
    MONDOSearchRequest,
    MONDOSearchResponse,
    OMIMDiseaseResult,
    OMIMSearchRequest,
    OMIMSearchResponse,
)
from app.services.ontology_service import OntologyService

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "/mondo/search",
    response_model=MONDOSearchResponse,
    summary="Search MONDO diseases",
)
@api_endpoint()
async def search_mondo_diseases(
    *,
    request: MONDOSearchRequest,
    current_user: UserNew = Depends(get_current_active_user),
) -> MONDOSearchResponse:
    """Search the Monarch Disease Ontology (MONDO) for diseases

    Searches MONDO via EBI OLS4 API for disease terms matching the query.
    Supports searching by disease name, synonym, or MONDO ID.

    Use this endpoint for disease autocomplete in precuration forms.

    Args:
        request: Search request with query and limit
        current_user: Current authenticated user

    Returns:
        MONDOSearchResponse with matching diseases

    Example request:
        ```json
        {
            "query": "intellectual disability",
            "limit": 10
        }
        ```

    Example response:
        ```json
        {
            "query": "intellectual disability",
            "total_results": 100,
            "results": [
                {
                    "mondo_id": "MONDO:0001071",
                    "label": "intellectual disability",
                    "definition": "A broad category of disorders...",
                    "synonyms": ["mental retardation"],
                    "xrefs": ["OMIM:612745", "DOID:1059"]
                }
            ]
        }
        ```
    """
    logger.debug(
        "MONDO search requested",
        query=request.query,
        limit=request.limit,
        user_id=str(current_user.id),
    )

    service = OntologyService()
    try:
        result = await service.search_mondo(request.query, request.limit)

        logger.info(
            "MONDO search completed",
            query=request.query,
            results_count=result.total_results,
            user_id=str(current_user.id),
        )

        return result
    finally:
        await service.close()


@router.post(
    "/omim/search",
    response_model=OMIMSearchResponse,
    summary="Search OMIM diseases",
)
@api_endpoint()
async def search_omim_diseases(
    *,
    request: OMIMSearchRequest,
    current_user: UserNew = Depends(get_current_active_user),
) -> OMIMSearchResponse:
    """Search OMIM (Online Mendelian Inheritance in Man) diseases

    Searches for OMIM disease entries. For text queries, searches via MONDO
    and filters for entries with OMIM cross-references. For OMIM IDs, fetches
    directly from JAX Network API.

    Use this endpoint for OMIM disease autocomplete in precuration forms.

    Args:
        request: Search request with query and limit
        current_user: Current authenticated user

    Returns:
        OMIMSearchResponse with matching diseases

    Example request:
        ```json
        {
            "query": "300855",
            "limit": 10
        }
        ```
    """
    logger.debug(
        "OMIM search requested",
        query=request.query,
        limit=request.limit,
        user_id=str(current_user.id),
    )

    service = OntologyService()
    try:
        result = await service.search_omim(request.query, request.limit)

        logger.info(
            "OMIM search completed",
            query=request.query,
            results_count=result.total_results,
            user_id=str(current_user.id),
        )

        return result
    finally:
        await service.close()


@router.get(
    "/omim/{omim_id}",
    response_model=OMIMDiseaseResult,
    summary="Get OMIM disease details",
)
@api_endpoint()
async def get_omim_disease(
    *,
    omim_id: str = Path(
        ...,
        description="OMIM ID (e.g., 'OMIM:300855' or '300855')",
        examples=["OMIM:300855", "300855"],
    ),
    current_user: UserNew = Depends(get_current_active_user),
) -> OMIMDiseaseResult:
    """Get detailed OMIM disease information

    Fetches complete disease details from JAX Network API including:
    - Disease name and description
    - Linked MONDO ID
    - Associated phenotypes (HPO terms) grouped by category
    - Associated genes

    This endpoint is useful for populating precuration forms after
    selecting an OMIM disease from search results.

    Args:
        omim_id: OMIM identifier
        current_user: Current authenticated user

    Returns:
        OMIMDiseaseResult with full disease details

    Raises:
        404: OMIM disease not found

    Example response:
        ```json
        {
            "omim_id": "OMIM:300855",
            "name": "Ogden syndrome",
            "mondo_id": "MONDO:0010457",
            "description": "Ogden syndrome is a rare...",
            "phenotypes": {
                "Nervous System": [
                    {
                        "hpo_id": "HP:0001263",
                        "name": "Global developmental delay",
                        "category": "Nervous System",
                        "frequency": "1/1"
                    }
                ]
            },
            "genes": [
                {"gene_id": "NCBIGene:8260", "symbol": "NAA10"}
            ]
        }
        ```
    """
    logger.debug(
        "OMIM fetch requested",
        omim_id=omim_id,
        user_id=str(current_user.id),
    )

    service = OntologyService()
    try:
        result = await service.get_omim_disease(omim_id)

        if result is None:
            logger.warning(
                "OMIM disease not found",
                omim_id=omim_id,
                user_id=str(current_user.id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OMIM disease not found: {omim_id}",
            )

        logger.info(
            "OMIM disease fetched",
            omim_id=omim_id,
            name=result.name,
            user_id=str(current_user.id),
        )

        return result
    finally:
        await service.close()


@router.post(
    "/hpo/search",
    response_model=HPOSearchResponse,
    summary="Search HPO phenotypes",
)
@api_endpoint()
async def search_hpo_terms(
    *,
    request: HPOSearchRequest,
    current_user: UserNew = Depends(get_current_active_user),
) -> HPOSearchResponse:
    """Search Human Phenotype Ontology (HPO) for phenotypes

    Searches HPO via JAX API for phenotype terms matching the query.
    Supports searching by phenotype name, synonym, or HPO ID.

    Use this endpoint for phenotype autocomplete in evidence forms.

    Args:
        request: Search request with query and limit
        current_user: Current authenticated user

    Returns:
        HPOSearchResponse with matching phenotypes

    Example request:
        ```json
        {
            "query": "seizure",
            "limit": 10
        }
        ```

    Example response:
        ```json
        {
            "query": "seizure",
            "total_results": 100,
            "results": [
                {
                    "hpo_id": "HP:0001250",
                    "name": "Seizure",
                    "definition": "A seizure is an intermittent...",
                    "synonyms": ["Epileptic seizure", "Seizures"],
                    "descendant_count": 346
                }
            ]
        }
        ```
    """
    logger.debug(
        "HPO search requested",
        query=request.query,
        limit=request.limit,
        user_id=str(current_user.id),
    )

    service = OntologyService()
    try:
        result = await service.search_hpo(request.query, request.limit)

        logger.info(
            "HPO search completed",
            query=request.query,
            results_count=result.total_results,
            user_id=str(current_user.id),
        )

        return result
    finally:
        await service.close()


@router.get(
    "/hpo/{hpo_id}/validate",
    response_model=HPOSearchResponse,
    summary="Validate HPO term",
)
@api_endpoint()
async def validate_hpo_term(
    *,
    hpo_id: str = Path(
        ...,
        description="HPO term ID (e.g., 'HP:0001250')",
        pattern=r"^HP:\d{7}$",
    ),
    current_user: UserNew = Depends(get_current_active_user),
) -> HPOSearchResponse:
    """Validate and fetch HPO term details

    Validates an HPO term ID and returns its details if found.
    Use this endpoint to verify HPO terms entered by users.

    Args:
        hpo_id: HPO term ID in format HP:NNNNNNN
        current_user: Current authenticated user

    Returns:
        HPOSearchResponse with single result if valid
    """
    logger.debug(
        "HPO validation requested",
        hpo_id=hpo_id,
        user_id=str(current_user.id),
    )

    service = OntologyService()
    try:
        result = await service.search_hpo(hpo_id, limit=1)

        logger.info(
            "HPO validation completed",
            hpo_id=hpo_id,
            found=result.total_results > 0,
            user_id=str(current_user.id),
        )

        return result
    finally:
        await service.close()


@router.get(
    "/hpo/inheritance",
    response_model=HPOInheritanceResponse,
    summary="Get HPO inheritance patterns",
)
@api_endpoint()
async def get_inheritance_patterns(
    *,
    current_user: UserNew = Depends(get_current_active_user),
) -> HPOInheritanceResponse:
    """Get all HPO inheritance pattern terms

    Returns all valid HPO inheritance patterns, categorized as:
    - Mendelian: Autosomal dominant, Autosomal recessive, X-linked, etc.
    - Non-Mendelian: Digenic, Oligogenic, Polygenic

    Results are cached server-side since inheritance patterns rarely change.
    Use this endpoint to populate inheritance pattern dropdowns in forms.

    Args:
        current_user: Current authenticated user

    Returns:
        HPOInheritanceResponse with categorized inheritance patterns

    Example response:
        ```json
        {
            "total_patterns": 14,
            "mendelian": [
                {
                    "hpo_id": "HP:0000006",
                    "name": "Autosomal dominant inheritance",
                    "definition": "A mode of inheritance...",
                    "category": "mendelian"
                }
            ],
            "non_mendelian": [
                {
                    "hpo_id": "HP:0010984",
                    "name": "Digenic inheritance",
                    "definition": "A type of inheritance...",
                    "category": "non_mendelian"
                }
            ],
            "cached": false
        }
        ```
    """
    logger.debug(
        "HPO inheritance patterns requested",
        user_id=str(current_user.id),
    )

    service = OntologyService()
    try:
        result = await service.get_inheritance_patterns()

        logger.info(
            "HPO inheritance patterns returned",
            total_patterns=result.total_patterns,
            cached=result.cached,
            user_id=str(current_user.id),
        )

        return result
    finally:
        await service.close()
