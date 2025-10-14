"""
Gene management API endpoints for schema-agnostic system.
Manages genes within the new scope-based architecture.
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core import deps
from app.core.database import get_db
from app.core.constants import (
    DEFAULT_GENE_SORT_FIELD,
    DEFAULT_SEARCH_LIMIT,
    DEFAULT_SKIP,
    DEFAULT_SORT_ORDER,
    GENES_DEFAULT_LIMIT,
    GENES_MAX_LIMIT,
    VALID_CHROMOSOMES,
)
from app.core.logging import api_endpoint
from app.crud.gene_new import gene_new_crud
from app.models import UserNew
from app.schemas.gene_new import (
    GeneAssignmentStatus,
    GeneBulkCreate,
    GeneBulkCreateResponse,
    GeneCurationProgress,
    GeneMergeRequest,
    GeneMergeResponse,
    GeneNew,
    GeneNewCreate,
    GeneNewListResponse,
    GeneNewStatistics,
    GeneNewSummary,
    GeneNewUpdate,
    GeneNewWithAssignments,
    GeneSearchQuery,
    GeneValidationResult,
    ScopeGeneListResponse,
)

router = APIRouter()


# ========================================
# CORE GENE ENDPOINTS
# ========================================


@router.get("/", response_model=GeneNewListResponse)
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
) -> GeneNewListResponse:
    """
    Retrieve genes with filtering and pagination.
    """
    # Check user permissions
    if current_user.role not in ["admin", "scope_admin", "curator", "viewer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    # Regular users can only see genes in their scopes
    if current_user.role not in ["admin"] and scope_id:
        user_scope_ids: list[UUID] = current_user.assigned_scopes or []
        if scope_id not in user_scope_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
            )

    if scope_id:
        genes = gene_new_crud.get_genes_for_scope(
            db, scope_id=scope_id, skip=skip, limit=limit, assigned_only=assigned_only
        )
    else:
        genes = gene_new_crud.get_multi(
            db, skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order
        )

    # Convert to summary format with assignment status
    gene_summaries = []
    for gene in genes:
        assignment_status = gene_new_crud.get_gene_assignment_status(
            db, gene_id=gene.id, scope_id=scope_id
        )
        progress = gene_new_crud.get_gene_curation_progress(
            db, gene_id=gene.id, scope_id=scope_id
        )

        summary = GeneNewSummary(
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

    return GeneNewListResponse(
        genes=gene_summaries,
        total=total,
        skip=skip,
        limit=limit,
        has_next=skip + limit < total,
        has_prev=skip > 0,
    )


@router.post("/", response_model=GeneNew)
@api_endpoint()
def create_gene(
    *,
    db: Session = Depends(get_db),
    gene_in: GeneNewCreate,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> GeneNew:
    """
    Create new gene. Requires curator or admin privileges.
    """
    if current_user.role not in ["curator", "admin", "scope_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    try:
        gene = gene_new_crud.create_with_owner(
            db, obj_in=gene_in, owner_id=current_user.id
        )
        return gene  # type: ignore[return-value]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.get("/search", response_model=list[GeneNewSummary])
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
) -> list[GeneNewSummary]:
    """
    Advanced gene search with multiple filters.
    """
    # Check scope permissions
    if current_user.role not in ["admin"] and scope_id:
        user_scope_ids: list[UUID] = current_user.assigned_scopes or []
        if scope_id not in user_scope_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
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

    genes = gene_new_crud.search(db, search_params=search_params)

    # Convert to summary format
    summaries = []
    for gene in genes:
        assignment_status = gene_new_crud.get_gene_assignment_status(
            db, gene_id=gene.id, scope_id=scope_id
        )
        progress = gene_new_crud.get_gene_curation_progress(
            db, gene_id=gene.id, scope_id=scope_id
        )

        summary = GeneNewSummary(
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


@router.get("/statistics", response_model=GeneNewStatistics)
def get_gene_statistics(
    *,
    db: Session = Depends(get_db),
    scope_id: UUID | None = Query(None, description="Filter by scope"),
    current_user: UserNew | None = Depends(deps.get_current_user_optional),
) -> GeneNewStatistics:
    """
    Get gene database statistics.
    Public endpoint with optional authentication for scope filtering.
    """
    # Check scope permissions (only if user is authenticated and scope is specified)
    if current_user and scope_id:
        if current_user.role not in ["admin"]:
            user_scope_ids: list[UUID] = current_user.assigned_scopes or []
            if scope_id not in user_scope_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions",
                )
    elif scope_id and not current_user:
        # If scope is specified but user is not authenticated, ignore scope filter
        scope_id = None

    statistics = gene_new_crud.get_statistics(db, scope_id=scope_id)
    return GeneNewStatistics(**statistics)


@router.get("/{gene_id}", response_model=GeneNewWithAssignments)
def get_gene(
    *,
    db: Session = Depends(get_db),
    gene_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> GeneNewWithAssignments:
    """
    Get gene by ID with assignment information.
    """
    gene = gene_new_crud.get(db, id=gene_id)
    if not gene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gene not found"
        )

    # Get assignment status
    assignment_status = gene_new_crud.get_gene_assignment_status(db, gene_id=gene_id)

    # Create enhanced response
    gene_with_assignments = GeneNewWithAssignments(
        **gene.__dict__,
        total_scope_assignments=assignment_status["total_scope_assignments"],
        scope_assignments=assignment_status["scope_assignments"],
        is_assigned_to_any_scope=assignment_status["is_assigned_to_any_scope"],
    )

    return gene_with_assignments


@router.put("/{gene_id}", response_model=GeneNew)
def update_gene(
    *,
    db: Session = Depends(get_db),
    gene_id: UUID,
    gene_in: GeneNewUpdate,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> GeneNew:
    """
    Update gene information. Requires curator or admin privileges.
    """
    gene = gene_new_crud.get(db, id=gene_id)
    if not gene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gene not found"
        )

    if current_user.role not in ["curator", "admin", "scope_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    try:
        gene = gene_new_crud.update_with_owner(
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
    gene = gene_new_crud.get(db, id=gene_id)
    if not gene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gene not found"
        )

    if current_user.role not in ["admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    # Check if gene has assignments or active work
    assignment_status = gene_new_crud.get_gene_assignment_status(db, gene_id=gene_id)
    if assignment_status["is_assigned_to_any_scope"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete gene with active assignments",
        )

    progress = gene_new_crud.get_gene_curation_progress(db, gene_id=gene_id)
    if progress["has_active_work"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete gene with active curation work",
        )

    gene_new_crud.remove(db, id=gene_id)
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
    gene = gene_new_crud.get(db, id=gene_id)
    if not gene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gene not found"
        )

    assignment_status = gene_new_crud.get_gene_assignment_status(db, gene_id=gene_id)
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
    gene = gene_new_crud.get(db, id=gene_id)
    if not gene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gene not found"
        )

    # Check scope permissions
    if current_user.role not in ["admin"] and scope_id:
        user_scope_ids: list[UUID] = current_user.assigned_scopes or []
        if scope_id not in user_scope_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
            )

    progress = gene_new_crud.get_gene_curation_progress(
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
    Bulk create genes. Requires curator or admin privileges.
    """
    if current_user.role not in ["curator", "admin", "scope_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    result = gene_new_crud.bulk_create(
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
    if current_user.role not in ["admin"] and scope_id not in (
        current_user.assigned_scopes or []
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    # Get scope information (would need proper scope lookup in real implementation)
    scope_name = "Unknown Scope"  # Would be populated from scope lookup

    genes = gene_new_crud.get_genes_for_scope(
        db, scope_id=scope_id, skip=skip, limit=limit, assigned_only=assigned_only
    )

    # Convert to summary format
    gene_summaries = []
    assigned_count = 0
    for gene in genes:
        assignment_status = gene_new_crud.get_gene_assignment_status(
            db, gene_id=gene.id, scope_id=scope_id
        )
        progress = gene_new_crud.get_gene_curation_progress(
            db, gene_id=gene.id, scope_id=scope_id
        )

        is_assigned = str(scope_id) in assignment_status["scope_assignments"]
        if is_assigned:
            assigned_count += 1

        summary = GeneNewSummary(
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
    gene = gene_new_crud.get(db, id=gene_id)
    if not gene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gene not found"
        )

    if current_user.role not in ["curator", "admin", "scope_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

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


@router.get("/hgnc/{hgnc_id}", response_model=GeneNew)
def get_gene_by_hgnc_id(
    *,
    db: Session = Depends(get_db),
    hgnc_id: str,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> GeneNew:
    """
    Get gene by HGNC ID.
    """
    gene = gene_new_crud.get_by_hgnc_id(db, hgnc_id=hgnc_id)
    if not gene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gene not found"
        )

    return gene  # type: ignore[return-value]


@router.get("/symbol/{symbol}", response_model=list[GeneNew])
def get_genes_by_symbol(
    *,
    db: Session = Depends(get_db),
    symbol: str,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> Sequence[GeneNew]:
    """
    Get genes by symbol (partial match).
    """
    # In a real implementation, this would do a more sophisticated search
    from app.core.constants import DEFAULT_SORT_ORDER

    genes = gene_new_crud.search(
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
    primary_gene = gene_new_crud.get(db, id=merge_request.primary_gene_id)
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
