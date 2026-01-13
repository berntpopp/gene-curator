"""
Precuration API endpoints.
Full CRUD with RLS integration and scope-based access control.
Follows patterns from curations.py.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.constants import (
    DEFAULT_SKIP,
    PRECURATIONS_DEFAULT_LIMIT,
    PRECURATIONS_MAX_LIMIT,
)
from app.core.database import get_db
from app.core.deps import get_current_active_user, set_rls_context
from app.core.logging import api_endpoint, get_logger
from app.crud.precuration import precuration_crud
from app.models import CurationStatus, UserNew
from app.schemas.precuration import (
    Precuration,
    PrecurationApprovalResult,
    PrecurationCreate,
    PrecurationListResponse,
    PrecurationSubmit,
    PrecurationUpdate,
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
    """
    if current_user.role == "admin":
        return  # Admin bypasses scope checks

    user_scope_ids: list[UUID] = current_user.assigned_scopes or []
    if scope_id not in user_scope_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not authorized to {action} precurations in this scope",
        )


# ========================================
# LIST & READ ENDPOINTS
# ========================================


@router.get("/", response_model=PrecurationListResponse)
@api_endpoint()
def list_precurations(
    db: Session = Depends(get_db),
    skip: int = Query(DEFAULT_SKIP, ge=0, description="Records to skip"),
    limit: int = Query(
        PRECURATIONS_DEFAULT_LIMIT,
        ge=1,
        le=PRECURATIONS_MAX_LIMIT,
        description="Max records",
    ),
    scope_id: UUID | None = Query(None, description="Filter by scope"),
    gene_id: UUID | None = Query(None, description="Filter by gene"),
    precuration_status: CurationStatus | None = Query(
        None, description="Filter by status"
    ),
    current_user: UserNew = Depends(get_current_active_user),
) -> PrecurationListResponse:
    """
    List precurations with optional filters.
    RLS automatically filters to user's accessible scopes.
    """
    # CRITICAL: Set RLS context for current user
    set_rls_context(db, current_user)

    # Determine scope filtering
    scope_ids = None
    if current_user.role != "admin" and not scope_id:
        scope_ids = current_user.assigned_scopes or []
        if not scope_ids:
            return PrecurationListResponse(
                precurations=[], total=0, skip=skip, limit=limit
            )

    # If specific scope requested, verify access
    if scope_id and current_user.role != "admin":
        user_scope_ids: list[UUID] = current_user.assigned_scopes or []
        if scope_id not in user_scope_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )

    summaries, total = precuration_crud.get_multi_filtered(
        db,
        skip=skip,
        limit=limit,
        scope_id=scope_id,
        scope_ids=scope_ids,
        gene_id=gene_id,
        status=precuration_status,
    )

    return PrecurationListResponse(
        precurations=summaries,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{precuration_id}", response_model=Precuration)
@api_endpoint()
def get_precuration(
    precuration_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Precuration:
    """Get a single precuration by ID."""
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    precuration = precuration_crud.get_with_relations(db, precuration_id)

    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )

    # Verify scope access
    _check_scope_access(current_user, precuration.scope_id, "view")

    return Precuration.model_validate(precuration)


# ========================================
# CREATE ENDPOINT
# ========================================


@router.post("/", response_model=Precuration, status_code=status.HTTP_201_CREATED)
@api_endpoint()
def create_precuration(
    precuration_in: PrecurationCreate,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Precuration:
    """
    Create a new precuration.
    Requires access to the target scope.
    """
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    # Verify scope access
    _check_scope_access(current_user, precuration_in.scope_id, "create")

    try:
        precuration = precuration_crud.create_precuration(
            db,
            obj_in=precuration_in,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return Precuration.model_validate(precuration)


# ========================================
# UPDATE ENDPOINT
# ========================================


@router.put("/{precuration_id}", response_model=Precuration)
@api_endpoint()
def update_precuration(
    precuration_id: UUID,
    precuration_in: PrecurationUpdate,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Precuration:
    """Update a precuration's evidence data."""
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    precuration = precuration_crud.get(db, precuration_id)

    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )

    # Verify scope access
    _check_scope_access(current_user, precuration.scope_id, "update")

    # Check precuration is editable
    if precuration.status not in [CurationStatus.DRAFT, CurationStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft or rejected precurations can be edited",
        )

    # Update evidence_data
    if precuration_in.evidence_data is not None:
        precuration.evidence_data = precuration_in.evidence_data
        precuration.updated_by = current_user.id

    db.add(precuration)
    db.commit()
    db.refresh(precuration)

    return Precuration.model_validate(precuration)


# ========================================
# DRAFT & SUBMIT ENDPOINTS
# ========================================


@router.patch("/{precuration_id}/draft", response_model=Precuration)
@api_endpoint()
def save_draft(
    precuration_id: UUID,
    draft_data: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Precuration:
    """Save precuration as draft (auto-save support)."""
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    precuration = precuration_crud.get(db, precuration_id)

    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )

    # Only creator or admin can save drafts
    if current_user.role != "admin" and precuration.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can save drafts",
        )

    updated = precuration_crud.save_draft(
        db,
        db_obj=precuration,
        evidence_data=draft_data.get("evidence_data", {}),
        user_id=current_user.id,
    )

    return Precuration.model_validate(updated)


@router.post("/{precuration_id}/submit", response_model=Precuration)
@api_endpoint()
def submit_precuration(
    precuration_id: UUID,
    submit_in: PrecurationSubmit,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Precuration:
    """Submit precuration for peer review."""
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    precuration = precuration_crud.get(db, precuration_id)

    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )

    # Only creator or admin can submit
    if current_user.role != "admin" and precuration.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can submit for review",
        )

    try:
        submitted = precuration_crud.submit_for_review(
            db,
            db_obj=precuration,
            submit_data=submit_in,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return Precuration.model_validate(submitted)


# ========================================
# APPROVAL & REJECTION ENDPOINTS
# ========================================


@router.post("/{precuration_id}/approve", response_model=PrecurationApprovalResult)
@api_endpoint()
def approve_precuration(
    precuration_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> PrecurationApprovalResult:
    """
    Approve precuration and optionally create linked curation.
    Requires reviewer role in scope.
    """
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    precuration = precuration_crud.get(db, precuration_id)

    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )

    # Verify scope access with reviewer role
    _check_scope_access(current_user, precuration.scope_id, "approve")

    # 4-eyes principle: creator cannot approve their own precuration
    if precuration.created_by == current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot approve your own precuration (4-eyes principle)",
        )

    try:
        result = precuration_crud.approve_and_create_curation(
            db,
            db_obj=precuration,
            approver_id=current_user.id,
            create_curation=True,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return result


@router.post("/{precuration_id}/reject", response_model=Precuration)
@api_endpoint()
def reject_precuration(
    precuration_id: UUID,
    rejection_data: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Precuration:
    """Reject precuration with reason."""
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    precuration = precuration_crud.get(db, precuration_id)

    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )

    # Verify scope access
    _check_scope_access(current_user, precuration.scope_id, "reject")

    reason = rejection_data.get("reason", "No reason provided")

    rejected = precuration_crud.reject(
        db,
        db_obj=precuration,
        user_id=current_user.id,
        reason=reason,
    )

    return Precuration.model_validate(rejected)


# ========================================
# DELETE ENDPOINT
# ========================================


@router.delete("/{precuration_id}", status_code=status.HTTP_204_NO_CONTENT)
@api_endpoint()
def delete_precuration(
    precuration_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> None:
    """Soft delete a precuration (archive)."""
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    precuration = precuration_crud.get(db, precuration_id)

    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )

    # Verify scope access
    _check_scope_access(current_user, precuration.scope_id, "delete")

    # Only allow deletion of drafts (or by admin)
    if precuration.status != CurationStatus.DRAFT and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only draft precurations can be deleted",
        )

    precuration_crud.soft_delete(db, db_obj=precuration, user_id=current_user.id)
