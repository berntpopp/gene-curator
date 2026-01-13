"""
Curation API endpoints.
Full CRUD with RLS integration and scope-based access control.
Follows patterns from gene_assignments.py, workflow.py, and genes.py.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.constants import (
    CURATIONS_DEFAULT_LIMIT,
    CURATIONS_MAX_LIMIT,
    DEFAULT_SKIP,
)
from app.core.database import get_db
from app.core.deps import get_current_active_user, set_rls_context
from app.core.logging import api_endpoint, get_logger
from app.crud.curation import curation_crud
from app.crud.precuration import precuration_crud
from app.models import CurationStatus, UserNew
from app.schemas.curation import (
    Curation,
    CurationConflictResponse,
    CurationCreate,
    CurationDetail,
    CurationDraftSave,
    CurationListResponse,
    CurationScoreResponse,
    CurationSubmit,
    CurationUpdate,
)

router = APIRouter()
logger = get_logger(__name__)


# ========================================
# HELPER FUNCTIONS
# ========================================


def _check_scope_access(
    current_user: UserNew,
    scope_id: UUID,
    action: str = "access",
) -> None:
    """
    Check if user has access to the specified scope.
    Raises HTTPException if access denied.
    Matches pattern from gene_assignments.py and workflow.py.
    """
    if current_user.role == "admin":
        return  # Admin bypasses scope checks

    user_scope_ids: list[UUID] = current_user.assigned_scopes or []
    if scope_id not in user_scope_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not authorized to {action} curations in this scope",
        )


# ========================================
# LIST & READ ENDPOINTS
# ========================================


@router.get("/", response_model=CurationListResponse)
@api_endpoint()
def list_curations(
    db: Session = Depends(get_db),
    skip: int = Query(DEFAULT_SKIP, ge=0, description="Records to skip"),
    limit: int = Query(
        CURATIONS_DEFAULT_LIMIT,
        ge=1,
        le=CURATIONS_MAX_LIMIT,
        description="Max records",
    ),
    scope_id: UUID | None = Query(None, description="Filter by scope"),
    gene_id: UUID | None = Query(None, description="Filter by gene"),
    curation_status: CurationStatus | None = Query(
        None, description="Filter by status"
    ),
    curator_id: UUID | None = Query(None, description="Filter by curator"),
    current_user: UserNew = Depends(get_current_active_user),
) -> CurationListResponse:
    """
    List curations with optional filters.
    RLS automatically filters to user's accessible scopes.
    """
    # Set RLS context for current user
    set_rls_context(db, current_user)

    # Determine scope filtering (matches workflow.py and genes.py pattern)
    scope_ids = None
    if current_user.role != "admin" and not scope_id:
        # Non-admin without specific scope: filter to their scopes
        scope_ids = current_user.assigned_scopes or []
        if not scope_ids:
            # User has no scopes assigned
            return CurationListResponse(curations=[], total=0, skip=skip, limit=limit)

    # If specific scope requested, verify access
    if scope_id and current_user.role != "admin":
        user_scope_ids: list[UUID] = current_user.assigned_scopes or []
        if scope_id not in user_scope_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )

    summaries, total = curation_crud.get_multi_filtered(
        db,
        skip=skip,
        limit=limit,
        scope_id=scope_id,
        scope_ids=scope_ids,
        gene_id=gene_id,
        status=curation_status,
        curator_id=curator_id,
    )

    return CurationListResponse(
        curations=summaries,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{curation_id}", response_model=CurationDetail)
@api_endpoint()
def get_curation(
    curation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> CurationDetail:
    """Get a single curation by ID with expanded relations."""
    # Set RLS context
    set_rls_context(db, current_user)

    curation = curation_crud.get_with_relations(db, curation_id)

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    # Verify scope access (matches gene_assignments.py pattern)
    if current_user.role != "admin":
        user_scope_ids: list[UUID] = current_user.assigned_scopes or []
        if curation.scope_id not in user_scope_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )

    # If no precuration linked, try to find approved one for this gene+scope
    if not curation.precuration:
        approved_precuration = precuration_crud.get_approved_for_gene_scope(
            db, curation.gene_id, curation.scope_id
        )
        if approved_precuration:
            # Temporarily attach for serialization
            curation.precuration = approved_precuration

    return CurationDetail.from_orm_with_relations(curation)


# ========================================
# CREATE ENDPOINT
# ========================================


@router.post("/", response_model=Curation, status_code=status.HTTP_201_CREATED)
@api_endpoint()
def create_curation(
    curation_in: CurationCreate,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Curation:
    """
    Create a new curation.
    Requires access to the target scope.
    """
    # Set RLS context
    set_rls_context(db, current_user)

    # Verify scope access (matches gene_assignments.py pattern)
    _check_scope_access(current_user, curation_in.scope_id, "create")

    try:
        curation = curation_crud.create_curation(
            db,
            obj_in=curation_in,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return Curation.model_validate(curation)


# ========================================
# UPDATE ENDPOINT (with optimistic locking)
# ========================================


@router.put(
    "/{curation_id}",
    response_model=Curation,
    responses={409: {"model": CurationConflictResponse}},
)
@api_endpoint()
def update_curation(
    curation_id: UUID,
    curation_in: CurationUpdate,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Curation:
    """
    Update a curation with optimistic locking.
    Returns 409 Conflict if lock_version doesn't match.
    """
    # Set RLS context
    set_rls_context(db, current_user)

    curation = curation_crud.get(db, curation_id)

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    # Verify scope access
    _check_scope_access(current_user, curation.scope_id, "update")

    # Check curation is editable
    if curation.status not in [CurationStatus.DRAFT, CurationStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft or rejected curations can be edited",
        )

    updated = curation_crud.update_with_lock(
        db,
        db_obj=curation,
        obj_in=curation_in,
        user_id=current_user.id,
    )

    if updated is None:
        # Return conflict response with current state
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "Concurrent modification detected",
                "current_lock_version": curation.lock_version,
                "your_lock_version": curation_in.lock_version,
                "current_state": curation.evidence_data,
            },
        )

    return Curation.model_validate(updated)


# ========================================
# DRAFT & SUBMIT ENDPOINTS
# ========================================


@router.patch("/{curation_id}/draft", response_model=Curation)
@api_endpoint()
def save_draft(
    curation_id: UUID,
    draft_in: CurationDraftSave,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Curation:
    """Save curation as draft (auto-save support)."""
    # Set RLS context
    set_rls_context(db, current_user)

    curation = curation_crud.get(db, curation_id)

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    # Only creator or admin can save drafts
    if current_user.role != "admin" and curation.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can save drafts",
        )

    updated = curation_crud.save_draft(
        db,
        db_obj=curation,
        draft_data=draft_in,
        user_id=current_user.id,
    )

    return Curation.model_validate(updated)


@router.post(
    "/{curation_id}/submit",
    response_model=Curation,
    responses={409: {"model": CurationConflictResponse}},
)
@api_endpoint()
def submit_curation(
    curation_id: UUID,
    submit_in: CurationSubmit,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Curation:
    """Submit curation for peer review."""
    # Set RLS context
    set_rls_context(db, current_user)

    curation = curation_crud.get(db, curation_id)

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    # Only creator or admin can submit
    if current_user.role != "admin" and curation.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can submit for review",
        )

    try:
        submitted = curation_crud.submit_for_review(
            db,
            db_obj=curation,
            submit_data=submit_in,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    if submitted is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Concurrent modification detected",
        )

    return Curation.model_validate(submitted)


# ========================================
# SCORE & DELETE ENDPOINTS
# ========================================


@router.get("/{curation_id}/score", response_model=CurationScoreResponse)
@api_endpoint()
def calculate_score(
    curation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> CurationScoreResponse:
    """Calculate ClinGen SOP v11 score for curation."""
    # Set RLS context
    set_rls_context(db, current_user)

    curation = curation_crud.get(db, curation_id)

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    # Verify scope access
    _check_scope_access(current_user, curation.scope_id, "calculate score for")

    return curation_crud.calculate_score(db, curation)


@router.delete("/{curation_id}", status_code=status.HTTP_204_NO_CONTENT)
@api_endpoint()
def delete_curation(
    curation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> None:
    """Soft delete a curation (archive)."""
    # Set RLS context
    set_rls_context(db, current_user)

    curation = curation_crud.get(db, curation_id)

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    # Verify scope access
    _check_scope_access(current_user, curation.scope_id, "delete")

    # Only allow deletion of drafts (or by admin)
    if curation.status != CurationStatus.DRAFT and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only draft curations can be deleted",
        )

    curation_crud.soft_delete(db, db_obj=curation, user_id=current_user.id)
