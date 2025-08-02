"""
Gene-scope assignment API endpoints.
Manages the assignment of genes to clinical specialties and curators.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core import deps
from app.crud.gene_assignment import gene_assignment_crud
from app.models import UserNew
from app.schemas.gene_assignment import (
    AvailableGene,
    BulkGeneScopeAssignmentCreate,
    BulkGeneScopeAssignmentResponse,
    CuratorAssignmentRequest,
    CuratorWorkload,
    DeactivateAssignmentRequest,
    GeneScopeAssignment,
    GeneScopeAssignmentCreate,
    GeneScopeAssignmentListResponse,
    GeneScopeAssignmentStatistics,
    GeneScopeAssignmentSummary,
    GeneScopeAssignmentUpdate,
    GeneScopeAssignmentWithDetails,
    ScopeAssignmentOverview,
)

router = APIRouter()


# ========================================
# GENE-SCOPE ASSIGNMENTS ENDPOINTS
# ========================================


@router.get("/", response_model=GeneScopeAssignmentListResponse)
def get_gene_assignments(
    db: Session = Depends(deps.get_db),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records"),
    scope_id: UUID | None = Query(None, description="Filter by scope"),
    curator_id: UUID | None = Query(None, description="Filter by curator"),
    gene_id: UUID | None = Query(None, description="Filter by gene"),
    priority_level: str | None = Query(None, description="Filter by priority level"),
    is_active: bool = Query(True, description="Filter by active status"),
    has_curator: bool | None = Query(None, description="Filter by curator assignment"),
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> GeneScopeAssignmentListResponse:
    """
    Retrieve gene-scope assignments with filtering.
    """
    # Check user permissions
    if current_user.role not in ["admin", "scope_admin", "curator"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Regular users can only see assignments in their scopes
    if current_user.role not in ["admin"] and scope_id:
        user_scope_ids = current_user.assigned_scopes or []
        if scope_id not in user_scope_ids:
            raise HTTPException(status_code=403, detail="Not enough permissions")

    # Get assignments with filtering
    if is_active:
        assignments = gene_assignment_crud.get_active_assignments(
            db,
            skip=skip,
            limit=limit,
            scope_id=scope_id,
            curator_id=curator_id,
            gene_id=gene_id,
        )
    else:
        # Implementation would need to be added to CRUD for inactive assignments
        assignments = gene_assignment_crud.get_multi(db, skip=skip, limit=limit)

    # Convert to summary format (would need to join with related data)
    assignment_summaries = []
    for assignment in assignments:
        # This would need proper JOIN queries in a real implementation
        summary = GeneScopeAssignmentSummary(
            id=assignment.id,
            gene_id=assignment.gene_id,
            gene_symbol="",  # Would be populated from JOIN
            gene_hgnc_id="",  # Would be populated from JOIN
            scope_id=assignment.scope_id,
            scope_name="",  # Would be populated from JOIN
            assigned_curator_id=assignment.assigned_curator_id,
            curator_name="",  # Would be populated from JOIN
            priority_level=assignment.priority_level,
            is_active=assignment.is_active,
            assigned_at=assignment.assigned_at,
            has_active_work=gene_assignment_crud.has_active_work(
                db, assignment_id=assignment.id
            ),
        )
        assignment_summaries.append(summary)

    total = len(
        assignments
    )  # This would be a proper count query in real implementation

    return GeneScopeAssignmentListResponse(
        assignments=assignment_summaries,
        total=total,
        skip=skip,
        limit=limit,
        has_next=skip + limit < total,
        has_prev=skip > 0,
    )


@router.post("/", response_model=GeneScopeAssignment)
def create_gene_assignment(
    *,
    db: Session = Depends(deps.get_db),
    assignment_in: GeneScopeAssignmentCreate,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> GeneScopeAssignment:
    """
    Create new gene-scope assignment. Requires curator or admin privileges.
    """
    if current_user.role not in ["curator", "admin", "scope_admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Check if user has access to the target scope
    if current_user.role not in ["admin"]:
        user_scope_ids = current_user.assigned_scopes or []
        if assignment_in.scope_id not in user_scope_ids:
            raise HTTPException(
                status_code=403, detail="Not enough permissions for this scope"
            )

    try:
        assignment = gene_assignment_crud.create_assignment(
            db, obj_in=assignment_in, assigned_by=current_user.id
        )
        return assignment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{assignment_id}", response_model=GeneScopeAssignmentWithDetails)
def get_gene_assignment(
    *,
    db: Session = Depends(deps.get_db),
    assignment_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> GeneScopeAssignmentWithDetails:
    """
    Get gene-scope assignment by ID with detailed information.
    """
    assignment = gene_assignment_crud.get(db, id=assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Check user permissions
    if current_user.role not in ["admin"] and assignment.scope_id not in (
        current_user.assigned_scopes or []
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Convert to detailed format (would need JOIN queries in real implementation)
    detailed_assignment = GeneScopeAssignmentWithDetails(
        **assignment.__dict__,
        gene_symbol="",  # Would be populated from JOIN
        gene_hgnc_id="",  # Would be populated from JOIN
        gene_chromosome="",  # Would be populated from JOIN
        scope_name="",  # Would be populated from JOIN
        scope_display_name="",  # Would be populated from JOIN
        curator_name="",  # Would be populated from JOIN
        curator_email="",  # Would be populated from JOIN
    )

    return detailed_assignment


@router.put("/{assignment_id}", response_model=GeneScopeAssignment)
def update_gene_assignment(
    *,
    db: Session = Depends(deps.get_db),
    assignment_id: UUID,
    assignment_in: GeneScopeAssignmentUpdate,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> GeneScopeAssignment:
    """
    Update gene-scope assignment. Requires curator or admin privileges.
    """
    assignment = gene_assignment_crud.get(db, id=assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if current_user.role not in ["curator", "admin", "scope_admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Check scope access
    if current_user.role not in ["admin"] and assignment.scope_id not in (
        current_user.assigned_scopes or []
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    assignment = gene_assignment_crud.update(
        db, db_obj=assignment, obj_in=assignment_in
    )
    return assignment


@router.delete("/{assignment_id}")
def deactivate_gene_assignment(
    *,
    db: Session = Depends(deps.get_db),
    assignment_id: UUID,
    deactivation_request: DeactivateAssignmentRequest,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict:
    """
    Deactivate gene-scope assignment. Requires admin privileges.
    """
    assignment = gene_assignment_crud.get(db, id=assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if current_user.role not in ["admin", "scope_admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        gene_assignment_crud.deactivate_assignment(
            db,
            assignment_id=assignment_id,
            deactivated_by=current_user.id,
            reason=deactivation_request.reason,
        )
        return {"message": "Assignment deactivated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{assignment_id}/reactivate")
def reactivate_gene_assignment(
    *,
    db: Session = Depends(deps.get_db),
    assignment_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict:
    """
    Reactivate gene-scope assignment. Requires admin privileges.
    """
    assignment = gene_assignment_crud.get(db, id=assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if current_user.role not in ["admin", "scope_admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    gene_assignment_crud.reactivate_assignment(
        db, assignment_id=assignment_id, reactivated_by=current_user.id
    )
    return {"message": "Assignment reactivated successfully"}


@router.get("/{assignment_id}/statistics", response_model=GeneScopeAssignmentStatistics)
def get_assignment_statistics(
    *,
    db: Session = Depends(deps.get_db),
    assignment_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> GeneScopeAssignmentStatistics:
    """
    Get detailed statistics for a gene-scope assignment.
    """
    assignment = gene_assignment_crud.get(db, id=assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Check permissions
    if current_user.role not in ["admin"] and assignment.scope_id not in (
        current_user.assigned_scopes or []
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    statistics = gene_assignment_crud.get_assignment_statistics(
        db, assignment_id=assignment_id
    )
    return GeneScopeAssignmentStatistics(**statistics)


# ========================================
# BULK OPERATIONS ENDPOINTS
# ========================================


@router.post("/bulk", response_model=BulkGeneScopeAssignmentResponse)
def bulk_create_gene_assignments(
    *,
    db: Session = Depends(deps.get_db),
    bulk_request: BulkGeneScopeAssignmentCreate,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> BulkGeneScopeAssignmentResponse:
    """
    Bulk create gene-scope assignments. Requires curator or admin privileges.
    """
    if current_user.role not in ["curator", "admin", "scope_admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Check scope access
    if current_user.role not in ["admin"]:
        user_scope_ids = current_user.assigned_scopes or []
        if bulk_request.scope_id not in user_scope_ids:
            raise HTTPException(
                status_code=403, detail="Not enough permissions for this scope"
            )

    result = gene_assignment_crud.bulk_assign_genes(
        db,
        gene_ids=bulk_request.gene_ids,
        scope_id=bulk_request.scope_id,
        curator_id=bulk_request.assigned_curator_id,
        assigned_by=current_user.id,
    )

    return BulkGeneScopeAssignmentResponse(**result)


# ========================================
# CURATOR MANAGEMENT ENDPOINTS
# ========================================


@router.post("/{assignment_id}/assign-curator")
def assign_curator_to_gene(
    *,
    db: Session = Depends(deps.get_db),
    assignment_id: UUID,
    curator_request: CuratorAssignmentRequest,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict:
    """
    Assign a curator to a gene-scope assignment.
    """
    assignment = gene_assignment_crud.get(db, id=assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if current_user.role not in ["curator", "admin", "scope_admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Check scope access
    if current_user.role not in ["admin"] and assignment.scope_id not in (
        current_user.assigned_scopes or []
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        gene_assignment_crud.assign_curator(
            db,
            assignment_id=assignment_id,
            curator_id=curator_request.curator_id,
            assigned_by=current_user.id,
        )
        return {"message": "Curator assigned successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{assignment_id}/unassign-curator")
def unassign_curator_from_gene(
    *,
    db: Session = Depends(deps.get_db),
    assignment_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict:
    """
    Remove curator from a gene-scope assignment.
    """
    assignment = gene_assignment_crud.get(db, id=assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if current_user.role not in ["curator", "admin", "scope_admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Check scope access
    if current_user.role not in ["admin"] and assignment.scope_id not in (
        current_user.assigned_scopes or []
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    gene_assignment_crud.unassign_curator(
        db, assignment_id=assignment_id, unassigned_by=current_user.id
    )
    return {"message": "Curator unassigned successfully"}


@router.get("/curator/{curator_id}/workload", response_model=CuratorWorkload)
def get_curator_workload(
    *,
    db: Session = Depends(deps.get_db),
    curator_id: UUID,
    scope_id: UUID | None = Query(None, description="Filter by specific scope"),
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> CuratorWorkload:
    """
    Get workload statistics for a curator.
    """
    # Check permissions
    if (
        current_user.role not in ["admin", "scope_admin"]
        and current_user.id != curator_id
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    workload = gene_assignment_crud.get_curator_workload(
        db, curator_id=curator_id, scope_id=scope_id
    )
    return CuratorWorkload(**workload)


@router.get(
    "/curator/{curator_id}/assignments", response_model=list[GeneScopeAssignmentSummary]
)
def get_curator_assignments(
    *,
    db: Session = Depends(deps.get_db),
    curator_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    scope_id: UUID | None = Query(None, description="Filter by specific scope"),
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> list[GeneScopeAssignmentSummary]:
    """
    Get assignments for a specific curator.
    """
    # Check permissions
    if (
        current_user.role not in ["admin", "scope_admin"]
        and current_user.id != curator_id
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    assignments = gene_assignment_crud.get_curator_assignments(
        db, curator_id=curator_id, skip=skip, limit=limit, scope_id=scope_id
    )

    # Convert to summary format (would need JOIN queries in real implementation)
    summaries = []
    for assignment in assignments:
        summary = GeneScopeAssignmentSummary(
            id=assignment.id,
            gene_id=assignment.gene_id,
            gene_symbol="",  # Would be populated from JOIN
            gene_hgnc_id="",  # Would be populated from JOIN
            scope_id=assignment.scope_id,
            scope_name="",  # Would be populated from JOIN
            assigned_curator_id=assignment.assigned_curator_id,
            curator_name="",  # Would be populated from JOIN
            priority_level=assignment.priority_level,
            is_active=assignment.is_active,
            assigned_at=assignment.assigned_at,
            has_active_work=gene_assignment_crud.has_active_work(
                db, assignment_id=assignment.id
            ),
        )
        summaries.append(summary)

    return summaries


# ========================================
# SCOPE-SPECIFIC ENDPOINTS
# ========================================


@router.get("/scope/{scope_id}", response_model=list[GeneScopeAssignmentSummary])
def get_scope_assignments(
    *,
    db: Session = Depends(deps.get_db),
    scope_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    include_inactive: bool = Query(False, description="Include inactive assignments"),
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> list[GeneScopeAssignmentSummary]:
    """
    Get all assignments for a specific scope.
    """
    # Check scope access
    if current_user.role not in ["admin"] and scope_id not in (
        current_user.assigned_scopes or []
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    assignments = gene_assignment_crud.get_scope_assignments(
        db, scope_id=scope_id, skip=skip, limit=limit, include_inactive=include_inactive
    )

    # Convert to summary format (would need JOIN queries in real implementation)
    summaries = []
    for assignment in assignments:
        summary = GeneScopeAssignmentSummary(
            id=assignment.id,
            gene_id=assignment.gene_id,
            gene_symbol="",  # Would be populated from JOIN
            gene_hgnc_id="",  # Would be populated from JOIN
            scope_id=assignment.scope_id,
            scope_name="",  # Would be populated from JOIN
            assigned_curator_id=assignment.assigned_curator_id,
            curator_name="",  # Would be populated from JOIN
            priority_level=assignment.priority_level,
            is_active=assignment.is_active,
            assigned_at=assignment.assigned_at,
            has_active_work=gene_assignment_crud.has_active_work(
                db, assignment_id=assignment.id
            ),
        )
        summaries.append(summary)

    return summaries


@router.get("/scope/{scope_id}/available-genes", response_model=list[AvailableGene])
def get_available_genes_for_scope(
    *,
    db: Session = Depends(deps.get_db),
    scope_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> list[AvailableGene]:
    """
    Get genes available for assignment to a scope.
    """
    # Check scope access
    if current_user.role not in ["admin"] and scope_id not in (
        current_user.assigned_scopes or []
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    available_genes_data = gene_assignment_crud.get_unassigned_genes(
        db, scope_id=scope_id, skip=skip, limit=limit
    )

    available_genes = []
    for gene_data in available_genes_data:
        available_gene = AvailableGene(
            gene_id=gene_data["gene_id"],
            hgnc_id=gene_data["hgnc_id"],
            approved_symbol=gene_data["approved_symbol"],
            chromosome=gene_data["chromosome"],
            location=gene_data["location"],
        )
        available_genes.append(available_gene)

    return available_genes


@router.get("/scope/{scope_id}/overview", response_model=ScopeAssignmentOverview)
def get_scope_assignment_overview(
    *,
    db: Session = Depends(deps.get_db),
    scope_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> ScopeAssignmentOverview:
    """
    Get assignment overview for a scope.
    """
    # Check scope access
    if current_user.role not in ["admin"] and scope_id not in (
        current_user.assigned_scopes or []
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    assignments = gene_assignment_crud.get_scope_assignments(
        db, scope_id=scope_id, skip=0, limit=10000, include_inactive=False
    )

    # Calculate overview statistics
    total_assignments = len(assignments)
    assigned_genes = sum(1 for a in assignments if a.assigned_curator_id is not None)
    unassigned_genes = total_assignments - assigned_genes

    # Priority distribution
    priority_counts = {"high": 0, "medium": 0, "low": 0}
    for assignment in assignments:
        priority = assignment.priority_level or "medium"
        priority_counts[priority] = priority_counts.get(priority, 0) + 1

    # Work status
    assignments_with_work = 0
    for assignment in assignments:
        if gene_assignment_crud.has_active_work(db, assignment_id=assignment.id):
            assignments_with_work += 1

    assignments_pending_start = total_assignments - assignments_with_work

    # Team metrics
    unique_curators = set()
    for assignment in assignments:
        if assignment.assigned_curator_id:
            unique_curators.add(assignment.assigned_curator_id)

    active_curators = len(unique_curators)
    avg_assignments_per_curator = (
        assigned_genes / active_curators if active_curators > 0 else None
    )

    # This would need proper scope name lookup in real implementation
    overview = ScopeAssignmentOverview(
        scope_id=scope_id,
        scope_name="",  # Would be populated from scope lookup
        scope_display_name="",  # Would be populated from scope lookup
        total_assignments=total_assignments,
        assigned_genes=assigned_genes,
        unassigned_genes=unassigned_genes,
        high_priority=priority_counts["high"],
        medium_priority=priority_counts["medium"],
        low_priority=priority_counts["low"],
        assignments_with_work=assignments_with_work,
        assignments_pending_start=assignments_pending_start,
        active_curators=active_curators,
        avg_assignments_per_curator=avg_assignments_per_curator,
    )

    return overview
