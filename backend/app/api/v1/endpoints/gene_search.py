"""Gene search and lookup endpoints (split out of genes.py; same /genes prefix and paths).

Registered before genes.router in api.py: `/search` must not be read as `/{gene_id}`.
"""

from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core import deps
from app.core.constants import (
    DEFAULT_GENE_SORT_FIELD,
    DEFAULT_SEARCH_LIMIT,
    DEFAULT_SKIP,
    DEFAULT_SORT_ORDER,
    GENES_DEFAULT_LIMIT,
    GENES_MAX_LIMIT,
)
from app.core.database import get_db
from app.core.logging import api_endpoint
from app.core.search_text import SearchText
from app.crud.gene import gene_crud
from app.models import Gene as GeneModel, UserNew
from app.schemas.gene import Gene, GeneSearchQuery, GeneSummary
from app.services.scope_permissions import ScopePermissionService

router = APIRouter()


def summarize_genes(
    db: Session, genes: Sequence[GeneModel], scope_id: UUID | None
) -> list[GeneSummary]:
    """Gene rows with assignment status and active-work flag."""
    out = []
    for gene in genes:
        assigned = gene_crud.get_gene_assignment_status(
            db, gene_id=gene.id, scope_id=scope_id
        )
        progress = gene_crud.get_gene_curation_progress(
            db, gene_id=gene.id, scope_id=scope_id
        )
        out.append(
            GeneSummary(
                id=gene.id,
                hgnc_id=gene.hgnc_id,
                approved_symbol=gene.approved_symbol,
                chromosome=gene.chromosome,
                location=gene.location,
                is_assigned=assigned["is_assigned_to_any_scope"],
                has_active_work=progress["has_active_work"],
            )
        )
    return out


@router.get("/search/count", response_model=int)
@api_endpoint()
def count_search_genes(
    *,
    db: Session = Depends(get_db),
    query: SearchText = None,
    chromosome: str | None = Query(None, description="Filter by chromosome"),
    hgnc_id: str | None = Query(None, description="Filter by HGNC ID"),
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> int:
    """Total genes matching the `/search` filters, ignoring paging."""
    params = GeneSearchQuery(query=query, chromosome=chromosome, hgnc_id=hgnc_id)
    return gene_crud.count_search(db, search_params=params)


@router.get("/search", response_model=list[GeneSummary])
@api_endpoint()
def search_genes(
    *,
    db: Session = Depends(get_db),
    query: SearchText = None,
    chromosome: str | None = Query(None, description="Filter by chromosome"),
    hgnc_id: str | None = Query(None, description="Filter by HGNC ID"),
    scope_id: UUID | None = Query(None, description="Filter by scope"),
    assigned_only: bool = Query(False, description="Only assigned genes"),
    has_active_work: bool | None = Query(None, description="Filter by active work"),
    skip: int = Query(DEFAULT_SKIP, ge=0),
    limit: int = Query(GENES_DEFAULT_LIMIT, ge=1, le=GENES_MAX_LIMIT),
    sort_by: str = Query(DEFAULT_GENE_SORT_FIELD),
    sort_order: str = Query(DEFAULT_SORT_ORDER),
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> list[GeneSummary]:
    """
    Advanced gene search with multiple filters.
    """
    # Check scope permissions
    if scope_id and not ScopePermissionService.has_scope_access(
        db, current_user, scope_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this scope",
        )

    search_params = GeneSearchQuery(
        query=query,
        chromosome=chromosome,
        hgnc_id=hgnc_id,
        scope_id=scope_id,
        assigned_only=assigned_only,
        has_active_work=has_active_work,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    genes = gene_crud.search(db, search_params=search_params)

    return summarize_genes(db, genes, scope_id)


@router.get("/hgnc/{hgnc_id}", response_model=Gene)
def get_gene_by_hgnc_id(
    *,
    db: Session = Depends(get_db),
    hgnc_id: str,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> Gene:
    """
    Get gene by HGNC ID.
    """
    gene = gene_crud.get_by_hgnc_id(db, hgnc_id=hgnc_id)
    if not gene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gene not found"
        )

    return gene  # type: ignore[return-value]


@router.get("/symbol/{symbol}", response_model=list[Gene])
def get_genes_by_symbol(
    *,
    db: Session = Depends(get_db),
    symbol: str,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> Sequence[Gene]:
    """
    Get genes by symbol (partial match).
    """
    # In a real implementation, this would do a more sophisticated search
    from app.core.constants import DEFAULT_SORT_ORDER

    genes = gene_crud.search(
        db,
        search_params=GeneSearchQuery(
            query=symbol,
            limit=DEFAULT_SEARCH_LIMIT,
            sort_by="approved_symbol",
            sort_order=DEFAULT_SORT_ORDER,
        ),
    )
    return genes  # type: ignore[return-value]
