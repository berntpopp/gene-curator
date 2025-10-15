"""External validation endpoints

Provides validation of external identifiers (HGNC, PubMed, HPO) with caching.
Uses asynchronous validation services for optimal performance.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.logging import api_endpoint, get_logger
from app.models.models import UserNew
from app.schemas.validation import ValidationRequest, ValidationResult
from app.services.validation_service import ValidationService

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "/validate/batch",
    response_model=dict[str, ValidationResult],
)
@api_endpoint()
async def validate_batch(
    *,
    db: Session = Depends(get_db),
    request: ValidationRequest,
    current_user: UserNew = Depends(get_current_active_user),
) -> dict[str, ValidationResult]:
    """Batch validate values using specified validator

    Validates multiple values in a single request. Results are cached
    for improved performance on subsequent validations.

    Supported validators:
    - `hgnc`: Gene symbols
    - `pubmed`: PubMed IDs (PMIDs)
    - `hpo`: Human Phenotype Ontology terms

    Args:
        db: Database session
        request: Validation request with validator name and values
        current_user: Current authenticated user

    Returns:
        Dictionary mapping input values to validation results

    Example:
        ```
        {
            "validator_name": "hgnc",
            "values": ["BRCA1", "BRCA2", "INVALID"]
        }
        ```
    """
    service = ValidationService(db)

    logger.info(
        "Batch validation requested",
        validator=request.validator_name,
        value_count=len(request.values),
        user_id=str(current_user.id),
    )

    results = await service.validate_batch(
        request.validator_name,
        request.values,
    )

    # Calculate statistics
    valid_count = sum(1 for r in results.values() if r.is_valid)

    logger.info(
        "Batch validation completed",
        validator=request.validator_name,
        total=len(results),
        valid=valid_count,
        invalid=len(results) - valid_count,
        user_id=str(current_user.id),
    )

    return results


@router.post(
    "/validate/hgnc",
    response_model=ValidationResult,
)
@api_endpoint()
async def validate_hgnc(
    *,
    db: Session = Depends(get_db),
    gene_symbol: str = Query(..., description="Gene symbol to validate", min_length=1, max_length=50),
    skip_cache: bool = Query(False, description="Skip cache and force fresh validation"),
    current_user: UserNew = Depends(get_current_active_user),
) -> ValidationResult:
    """Validate gene symbol against HGNC

    Validates gene symbol using the HUGO Gene Nomenclature Committee (HGNC)
    REST API. Returns approved symbol, HGNC ID, and alternate symbols if valid.

    Caching: Results are cached for 30 days for performance.

    Args:
        db: Database session
        gene_symbol: Gene symbol to validate (e.g., "BRCA1")
        skip_cache: If true, bypass cache and query HGNC API directly
        current_user: Current authenticated user

    Returns:
        Validation result with gene data or error message

    Example response for valid gene:
        ```json
        {
            "is_valid": true,
            "status": "valid",
            "data": {
                "approved_symbol": "BRCA1",
                "hgnc_id": "HGNC:1100",
                "alias_symbols": ["BRCC1", "FANCS"],
                "status": "Approved"
            }
        }
        ```
    """
    service = ValidationService(db)

    logger.debug(
        "HGNC validation requested",
        gene_symbol=gene_symbol,
        skip_cache=skip_cache,
        user_id=str(current_user.id),
    )

    result = await service.validate("hgnc", gene_symbol, skip_cache=skip_cache)

    logger.info(
        "HGNC validation completed",
        gene_symbol=gene_symbol,
        is_valid=result.is_valid,
        status=result.status,
        user_id=str(current_user.id),
    )

    return result


@router.post(
    "/validate/pubmed",
    response_model=ValidationResult,
)
@api_endpoint()
async def validate_pubmed(
    *,
    db: Session = Depends(get_db),
    pmid: str = Query(..., description="PubMed ID to validate", pattern=r"^\d+$", min_length=1, max_length=10),
    skip_cache: bool = Query(False, description="Skip cache and force fresh validation"),
    current_user: UserNew = Depends(get_current_active_user),
) -> ValidationResult:
    """Validate PMID against PubMed

    Validates PubMed ID using NCBI E-utilities API. Returns publication
    metadata including title, authors, and journal if valid.

    Caching: Results are cached for 90 days (publications are immutable).

    Args:
        db: Database session
        pmid: PubMed ID to validate (numeric string, e.g., "31558469")
        skip_cache: If true, bypass cache and query PubMed API directly
        current_user: Current authenticated user

    Returns:
        Validation result with publication data or error message

    Example response for valid PMID:
        ```json
        {
            "is_valid": true,
            "status": "valid",
            "data": {
                "pmid": "31558469",
                "title": "Gene-disease validity curation...",
                "authors": ["Smith J", "Doe J"],
                "journal": "Nature Genetics",
                "pub_date": "2019/09/26"
            }
        }
        ```
    """
    service = ValidationService(db)

    logger.debug(
        "PubMed validation requested",
        pmid=pmid,
        skip_cache=skip_cache,
        user_id=str(current_user.id),
    )

    result = await service.validate("pubmed", pmid, skip_cache=skip_cache)

    logger.info(
        "PubMed validation completed",
        pmid=pmid,
        is_valid=result.is_valid,
        status=result.status,
        user_id=str(current_user.id),
    )

    return result


@router.post(
    "/validate/hpo",
    response_model=ValidationResult,
)
@api_endpoint()
async def validate_hpo(
    *,
    db: Session = Depends(get_db),
    hpo_term: str = Query(..., description="HPO term to validate", pattern=r"^HP:\d{7}$", min_length=10, max_length=10),
    skip_cache: bool = Query(False, description="Skip cache and force fresh validation"),
    current_user: UserNew = Depends(get_current_active_user),
) -> ValidationResult:
    """Validate HPO term against OLS

    Validates Human Phenotype Ontology term using EMBL-EBI Ontology
    Lookup Service (OLS) API. Returns term name, definition, and synonyms if valid.

    Caching: Results are cached for 14 days (ontologies update regularly).

    Args:
        db: Database session
        hpo_term: HPO term to validate (format: HP:NNNNNNN, e.g., "HP:0001250")
        skip_cache: If true, bypass cache and query OLS API directly
        current_user: Current authenticated user

    Returns:
        Validation result with term data or error message

    Example response for valid HPO term:
        ```json
        {
            "is_valid": true,
            "status": "valid",
            "data": {
                "term_id": "HP:0001250",
                "term_name": "Seizure",
                "definition": "A seizure is...",
                "synonyms": ["Epileptic seizure", "Fits"]
            }
        }
        ```
    """
    service = ValidationService(db)

    logger.debug(
        "HPO validation requested",
        hpo_term=hpo_term,
        skip_cache=skip_cache,
        user_id=str(current_user.id),
    )

    result = await service.validate("hpo", hpo_term, skip_cache=skip_cache)

    logger.info(
        "HPO validation completed",
        hpo_term=hpo_term,
        is_valid=result.is_valid,
        status=result.status,
        user_id=str(current_user.id),
    )

    return result


@router.get(
    "/cache/statistics",
    response_model=dict[str, int],
)
@api_endpoint()
async def get_cache_statistics(
    *,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> dict[str, int]:
    """Get validation cache statistics

    Returns statistics about the validation cache including total entries,
    active entries, and breakdown by validator type.

    Args:
        db: Database session
        current_user: Current authenticated user

    Returns:
        Cache statistics dictionary

    Example response:
        ```json
        {
            "total_entries": 1523,
            "active_entries": 1401,
            "expired_entries": 122,
            "hgnc": 856,
            "pubmed": 423,
            "hpo": 244
        }
        ```
    """
    service = ValidationService(db)
    stats = service.get_cache_statistics()

    logger.debug(
        "Cache statistics retrieved",
        total_entries=stats["total_entries"],
        user_id=str(current_user.id),
    )

    return stats
