"""
Gene management API endpoints for schema-agnostic system.
Manages genes within the scope-based architecture.
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
    VALID_CHROMOSOMES,
)
from app.core.database import get_db
from app.core.logging import api_endpoint
from app.crud.gene import gene_crud
from app.models import UserNew
from app.schemas.gene import (
    Gene,
    GeneAssignmentStatus,
    GeneBulkCreate,
    GeneBulkCreateResponse,
    GeneCreate,
    GeneCurationProgress,
    GeneListResponse,
    GeneMergeRequest,
    GeneMergeResponse,
    GeneSearchQuery,
    GeneStatistics,
    GeneSummary,
    GeneUpdate,
    GeneValidationResult,
    GeneWithAssignments,
    ScopeGeneListResponse,
)
from app.services.scope_permissions import ScopePermissionService

router = APIRouter()


# ========================================
# CORE GENE ENDPOINTS
# ========================================


@router.get("/", response_model=GeneListResponse)
@api_endpoint()
def get_genes(
    db: Session = Depends(get_db),
    skip: int = Query(DEFAULT_SKIP, ge=0, description="Number of records to skip"),
    limit: int = Query(
        GENES_DEFAULT_LIMIT,
        ge=1,
        le=GENES_MAX_LIMIT,
        description="Maximum number of records",
    ),
    scope_id: UUID | None = Query(None, description="Filter by scope"),
    assigned_only: bool = Query(False, description="Only show assigned genes"),
    has_active_work: bool | None = Query(
        None, description="Filter by active work status"
    ),
    sort_by: str = Query(DEFAULT_GENE_SORT_FIELD, description="Field to sort by"),
    sort_order: str = Query(DEFAULT_SORT_ORDER, description="Sort order"),
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> GeneListResponse:
    """
    Retrieve genes with filtering and pagination.
    """
    # All authenticated users can access genes (permission filtering happens at scope level)
    # No need for role check here - authentication is sufficient

    # Regular users can only see genes in their scopes
    if scope_id and not ScopePermissionService.has_scope_access(db, current_user, scope_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this scope",
        )

    if scope_id:
        genes = gene_crud.get_genes_for_scope(
            db, scope_id=scope_id, skip=skip, limit=limit, assigned_only=assigned_only
        )
    else:
        genes = gene_crud.get_multi(
            db, skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order
        )

    # Convert to summary format with assignment status
    gene_summaries = []
    for gene in genes:
        assignment_status = gene_crud.get_gene_assignment_status(
            db, gene_id=gene.id, scope_id=scope_id
        )
        progress = gene_crud.get_gene_curation_progress(
            db, gene_id=gene.id, scope_id=scope_id
        )

        summary = GeneSummary(
            id=gene.id,
            hgnc_id=gene.hgnc_id,
            approved_symbol=gene.approved_symbol,
            chromosome=gene.chromosome,
            location=gene.location,
            is_assigned=assignment_status["is_assigned_to_any_scope"],
            has_active_work=progress["has_active_work"],
        )
        gene_summaries.append(summary)

    total = len(genes)  # This would be a proper count query in real implementation

    return GeneListResponse(
        genes=gene_summaries,
        total=total,
        skip=skip,
        limit=limit,
        has_next=skip + limit < total,
        has_prev=skip > 0,
    )


@router.post("/", response_model=Gene)
@api_endpoint()
def create_gene(
    *,
    db: Session = Depends(get_db),
    gene_in: GeneCreate,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> Gene:
    """
    Create new gene. Available to all authenticated users.
    """
    # All authenticated users can create genes
    # RLS policies handle scope-based access control

    try:
        gene = gene_crud.create_with_owner(db, obj_in=gene_in, owner_id=current_user.id)
        return gene  # type: ignore[return-value]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.get("/search", response_model=list[GeneSummary])
@api_endpoint()
def search_genes(
    *,
    db: Session = Depends(get_db),
    query: str | None = Query(None, description="Search term"),
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
    if scope_id and not ScopePermissionService.has_scope_access(db, current_user, scope_id):
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

    # Convert to summary format
    summaries = []
    for gene in genes:
        assignment_status = gene_crud.get_gene_assignment_status(
            db, gene_id=gene.id, scope_id=scope_id
        )
        progress = gene_crud.get_gene_curation_progress(
            db, gene_id=gene.id, scope_id=scope_id
        )

        summary = GeneSummary(
            id=gene.id,
            hgnc_id=gene.hgnc_id,
            approved_symbol=gene.approved_symbol,
            chromosome=gene.chromosome,
            location=gene.location,
            is_assigned=assignment_status["is_assigned_to_any_scope"],
            has_active_work=progress["has_active_work"],
        )
        summaries.append(summary)

    return summaries


@router.get("/statistics", response_model=GeneStatistics)
def get_gene_statistics(
    *,
    db: Session = Depends(get_db),
    scope_id: UUID | None = Query(None, description="Filter by scope"),
    current_user: UserNew | None = Depends(deps.get_current_user_optional),
) -> GeneStatistics:
    """
    Get gene database statistics.
    Public endpoint with optional authentication for scope filtering.
    """
    # Check scope permissions (only if user is authenticated and scope is specified)
    if current_user and scope_id:
        if not ScopePermissionService.has_scope_access(db, current_user, scope_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this scope",
            )
    elif scope_id and not current_user:
        # If scope is specified but user is not authenticated, ignore scope filter
        scope_id = None

    statistics = gene_crud.get_statistics(db, scope_id=scope_id)
    return GeneStatistics(**statistics)


@router.get("/{gene_id}", response_model=GeneWithAssignments)
def get_gene(
    *,
    db: Session = Depends(get_db),
    gene_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> GeneWithAssignments:
    """
    Get gene by ID with assignment information.
    """
    gene = gene_crud.get(db, id=gene_id)
    if not gene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gene not found"
        )

    # Get assignment status
    assignment_status = gene_crud.get_gene_assignment_status(db, gene_id=gene_id)

    # Create enhanced response
    gene_with_assignments = GeneWithAssignments(
        **gene.__dict__,
        total_scope_assignments=assignment_status["total_scope_assignments"],
        scope_assignments=assignment_status["scope_assignments"],
        is_assigned_to_any_scope=assignment_status["is_assigned_to_any_scope"],
    )

    return gene_with_assignments


@router.put("/{gene_id}", response_model=Gene)
def update_gene(
    *,
    db: Session = Depends(get_db),
    gene_id: UUID,
    gene_in: GeneUpdate,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> Gene:
    """
    Update gene information. Available to all authenticated users.
    """
    gene = gene_crud.get(db, id=gene_id)
    if not gene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gene not found"
        )

    # All authenticated users can update genes
    # RLS policies handle scope-based access control

    try:
        gene = gene_crud.update_with_owner(
            db, db_obj=gene, obj_in=gene_in, owner_id=current_user.id
        )
        return gene  # type: ignore[return-value]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.delete("/{gene_id}")
def delete_gene(
    *,
    db: Session = Depends(get_db),
    gene_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict[str, str]:
    """
    Delete gene. Requires admin privileges.
    """
    gene = gene_crud.get(db, id=gene_id)
    if not gene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gene not found"
        )

    if current_user.role not in ["admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    # Check if gene has assignments or active work
    assignment_status = gene_crud.get_gene_assignment_status(db, gene_id=gene_id)
    if assignment_status["is_assigned_to_any_scope"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete gene with active assignments",
        )

    progress = gene_crud.get_gene_curation_progress(db, gene_id=gene_id)
    if progress["has_active_work"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete gene with active curation work",
        )

    gene_crud.remove(db, id=gene_id)
    return {"message": "Gene deleted successfully"}


# ========================================
# ASSIGNMENT AND PROGRESS ENDPOINTS
# ========================================


@router.get("/{gene_id}/assignments", response_model=GeneAssignmentStatus)
def get_gene_assignments(
    *,
    db: Session = Depends(get_db),
    gene_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> GeneAssignmentStatus:
    """
    Get assignment status for a gene across all scopes.
    """
    gene = gene_crud.get(db, id=gene_id)
    if not gene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gene not found"
        )

    assignment_status = gene_crud.get_gene_assignment_status(db, gene_id=gene_id)
    return GeneAssignmentStatus(**assignment_status)


@router.get("/{gene_id}/progress", response_model=GeneCurationProgress)
def get_gene_curation_progress(
    *,
    db: Session = Depends(get_db),
    gene_id: UUID,
    scope_id: UUID | None = Query(None, description="Filter by scope"),
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> GeneCurationProgress:
    """
    Get curation progress for a gene.
    """
    gene = gene_crud.get(db, id=gene_id)
    if not gene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gene not found"
        )

    # Check scope permissions
    if scope_id and not ScopePermissionService.has_scope_access(db, current_user, scope_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this scope",
        )

    progress = gene_crud.get_gene_curation_progress(
        db, gene_id=gene_id, scope_id=scope_id
    )
    return GeneCurationProgress(**progress)


# ========================================
# BULK OPERATIONS ENDPOINTS
# ========================================


@router.post("/bulk", response_model=GeneBulkCreateResponse)
@api_endpoint()
def bulk_create_genes(
    *,
    db: Session = Depends(get_db),
    bulk_request: GeneBulkCreate,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> GeneBulkCreateResponse:
    """
    Bulk create genes. Available to all authenticated users.
    """
    # All authenticated users can bulk create genes
    # RLS policies handle scope-based access control

    result = gene_crud.bulk_create(
        db,
        genes_data=bulk_request.genes,
        owner_id=current_user.id,
        skip_duplicates=bulk_request.skip_duplicates,
    )

    return GeneBulkCreateResponse(**result)


# ========================================
# SCOPE-SPECIFIC ENDPOINTS
# ========================================


@router.get("/scope/{scope_id}", response_model=ScopeGeneListResponse)
def get_scope_genes(
    *,
    db: Session = Depends(get_db),
    scope_id: UUID,
    skip: int = Query(DEFAULT_SKIP, ge=0),
    limit: int = Query(GENES_DEFAULT_LIMIT, ge=1, le=GENES_MAX_LIMIT),
    assigned_only: bool = Query(False, description="Only show assigned genes"),
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> ScopeGeneListResponse:
    """
    Get genes for a specific scope.
    """
    # Check scope access
    if not ScopePermissionService.has_scope_access(db, current_user, scope_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this scope",
        )

    # Get scope information (would need proper scope lookup in real implementation)
    scope_name = "Unknown Scope"  # Would be populated from scope lookup

    genes = gene_crud.get_genes_for_scope(
        db, scope_id=scope_id, skip=skip, limit=limit, assigned_only=assigned_only
    )

    # Convert to summary format
    gene_summaries = []
    assigned_count = 0
    for gene in genes:
        assignment_status = gene_crud.get_gene_assignment_status(
            db, gene_id=gene.id, scope_id=scope_id
        )
        progress = gene_crud.get_gene_curation_progress(
            db, gene_id=gene.id, scope_id=scope_id
        )

        is_assigned = str(scope_id) in assignment_status["scope_assignments"]
        if is_assigned:
            assigned_count += 1

        summary = GeneSummary(
            id=gene.id,
            hgnc_id=gene.hgnc_id,
            approved_symbol=gene.approved_symbol,
            chromosome=gene.chromosome,
            location=gene.location,
            is_assigned=is_assigned,
            has_active_work=progress["has_active_work"],
        )
        gene_summaries.append(summary)

    total = len(genes)
    unassigned_count = total - assigned_count

    return ScopeGeneListResponse(
        scope_id=scope_id,
        scope_name=scope_name,
        genes=gene_summaries,
        total=total,
        assigned=assigned_count,
        unassigned=unassigned_count,
        skip=skip,
        limit=limit,
        has_next=skip + limit < total,
        has_prev=skip > 0,
    )


# ========================================
# VALIDATION AND UTILITY ENDPOINTS
# ========================================


@router.post("/{gene_id}/validate", response_model=GeneValidationResult)
def validate_gene(
    *,
    db: Session = Depends(get_db),
    gene_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> GeneValidationResult:
    """
    Validate gene information against external sources.
    """
    gene = gene_crud.get(db, id=gene_id)
    if not gene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gene not found"
        )

    # All authenticated users can validate genes

    # Basic validation implementation
    # In a real system, this would validate against HGNC API
    warnings: list[str] = []
    errors: list[str] = []
    suggestions: list[str] = []

    # Basic format validation
    if not gene.hgnc_id.startswith("HGNC:"):
        errors.append("Invalid HGNC ID format")

    if not gene.approved_symbol:
        errors.append("Missing approved symbol")

    # Check for common issues
    if gene.chromosome and gene.chromosome not in VALID_CHROMOSOMES:
        warnings.append(f"Unusual chromosome designation: {gene.chromosome}")

    if not gene.location:
        suggestions.append("Consider adding chromosomal location information")

    return GeneValidationResult(
        is_valid=len(errors) == 0,
        hgnc_id=gene.hgnc_id,
        approved_symbol=gene.approved_symbol,
        warnings=warnings,
        errors=errors,
        suggestions=suggestions,
        external_data=None,
    )


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
            chromosome=None,
            hgnc_id=None,
            scope_id=None,
            assigned_only=False,
            has_active_work=None,
            skip=0,
            limit=DEFAULT_SEARCH_LIMIT,
            sort_by="approved_symbol",
            sort_order=DEFAULT_SORT_ORDER,
        ),
    )
    return genes  # type: ignore[return-value]


# ========================================
# ADVANCED OPERATIONS ENDPOINTS
# ========================================


@router.post("/merge", response_model=GeneMergeResponse)
def merge_genes(
    *,
    db: Session = Depends(get_db),
    merge_request: GeneMergeRequest,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> GeneMergeResponse:
    """
    Merge duplicate genes. Requires admin privileges.
    """
    if current_user.role not in ["admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    # Basic implementation - in a real system this would be much more sophisticated
    primary_gene = gene_crud.get(db, id=merge_request.primary_gene_id)
    if not primary_gene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Primary gene not found"
        )

    # This would need a comprehensive merge implementation
    warnings: list[str] = ["Gene merge functionality is not fully implemented"]
    errors: list[str] = []

    return GeneMergeResponse(
        merged_gene=primary_gene,  # type: ignore[arg-type]
        duplicate_genes_processed=len(merge_request.duplicate_gene_ids),
        assignments_transferred=0,
        precurations_transferred=0,
        curations_transferred=0,
        warnings=warnings,
        errors=errors,
    )
