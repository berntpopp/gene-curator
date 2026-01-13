"""Gene Catalogue API endpoints.

The Gene Catalogue is a read-only aggregation layer that provides a unified view
of genes with finished curations across all scopes. It exists independently from
scope-level data and never modifies source data.

Key principles:
- Read-only: No write operations
- Scope-independent: Does not affect scope workflows
- Derived data only: All content computed from active curations
- Aggregation by gene: Same gene across scopes consolidated
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import api_endpoint
from app.crud import gene_catalogue as catalogue_crud
from app.schemas.gene_catalogue import (
    GeneCatalogueFilters,
    GeneCatalogueResponse,
)

router = APIRouter()


@router.get("/", response_model=GeneCatalogueResponse)
@api_endpoint()
def get_gene_catalogue(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return"),
    search: str | None = Query(
        None, description="Search gene symbol, HGNC ID, or aliases"
    ),
    classification: str | None = Query(
        None, description="Filter by classification (definitive, strong, etc.)"
    ),
    disease: str | None = Query(None, description="Search/filter by disease name"),
    scope_id: UUID | None = Query(None, description="Filter by specific scope"),
    chromosome: str | None = Query(None, description="Filter by chromosome"),
    sort_by: str = Query(
        "approved_symbol",
        description="Sort field: approved_symbol, total_curations, chromosome",
    ),
    sort_order: str = Query("asc", description="Sort order: asc or desc"),
) -> GeneCatalogueResponse:
    """
    Get the Gene Catalogue.

    Returns genes with at least one active (finished) curation across all scopes.
    This is a read-only, public endpoint that aggregates curation data.

    The catalogue shows:
    - Gene identification (symbol, HGNC ID, location)
    - Total curations and scope count per gene
    - Classification distribution across scopes
    - Unique diseases associated with the gene
    - Per-scope curation details (disease, classification, scores)

    Supports filtering by:
    - Gene search (symbol, HGNC ID, aliases)
    - Classification (definitive, strong, moderate, etc.)
    - Disease name (partial match)
    - Specific scope
    - Chromosome

    No authentication required - this is a public reporting endpoint.
    """
    filters = GeneCatalogueFilters(
        search=search,
        classification=classification,
        disease=disease,
        scope_id=scope_id,
        chromosome=chromosome,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return catalogue_crud.get_gene_catalogue(db, filters)


@router.get("/filters/classifications", response_model=list[str])
@api_endpoint()
def get_available_classifications(
    db: Session = Depends(get_db),
) -> list[str]:
    """
    Get available classifications for filtering.

    Returns list of classification values that have at least one
    active curation in the catalogue.

    Public endpoint - no authentication required.
    """
    return catalogue_crud.get_available_classifications(db)


@router.get("/filters/diseases", response_model=list[str])
@api_endpoint()
def get_available_diseases(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Maximum diseases to return"),
) -> list[str]:
    """
    Get available diseases for filtering.

    Returns list of unique disease names from active curations.

    Public endpoint - no authentication required.
    """
    return catalogue_crud.get_available_diseases(db, limit=limit)


@router.get("/filters/scopes", response_model=list[dict[str, str | bool]])
@api_endpoint()
def get_available_scopes(
    db: Session = Depends(get_db),
) -> list[dict[str, str | bool]]:
    """
    Get scopes available for filtering.

    Returns scopes that have at least one active curation.

    Public endpoint - no authentication required.
    """
    return catalogue_crud.get_available_scopes_for_catalogue(db)
