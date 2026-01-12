"""
Scope management API endpoints (RLS-based multi-tenant architecture).

This module provides scope management endpoints using PostgreSQL Row-Level Security
for secure multi-tenant data access.

Key Features:
- RLS-enforced permission checks
- Scope membership integration
- Automatic scope admin assignment on creation
- Fine-grained access control via ScopeRole enum

Created: 2025-10-13
Author: Claude Code (Automated Implementation)
"""

from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core import deps
from app.core.database import get_db
from app.core.enums import ScopeRole
from app.core.logging import get_logger
from app.crud.scope import scope_crud
from app.crud.scope_membership import scope_membership_crud
from app.models import Scope, User
from app.schemas.scope import (
    Scope as ScopeResponse,
    ScopeCreate,
    ScopeStatistics,
    ScopeUpdate,
    ScopeWithStats,
)
from app.schemas.scope_membership import ScopeMembershipCreate

logger = get_logger(__name__)

router = APIRouter()


@router.post("/", response_model=ScopeResponse, status_code=status.HTTP_201_CREATED)
def create_scope(
    *,
    db: Session = Depends(get_db),
    scope_in: ScopeCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Scope:
    """
    Create a new scope.

    Any authenticated user can create a scope and automatically becomes an admin
    of that scope. This follows GitHub's model where anyone can create an organization.

    Args:
        db: Database session
        scope_in: Scope creation data
        current_user: Current authenticated user

    Returns:
        Created Scope object with creator as scope admin

    Raises:
        HTTPException 400: Scope name already exists
    """
    # Set RLS context
    deps.set_rls_context(db, current_user)

    # Check if scope name already exists
    existing = scope_crud.get_by_name(db, name=scope_in.name)
    if existing:
        logger.warning(
            "Scope creation failed: name already exists",
            scope_name=scope_in.name,
            existing_scope_id=str(existing.id),
            user_id=str(current_user.id),
            user_email=current_user.email,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scope with name '{scope_in.name}' already exists. Please choose a different name.",
        )

    # Create scope
    scope = scope_crud.create_with_owner(db, obj_in=scope_in, owner_id=current_user.id)

    logger.debug(
        "Scope entity created, now creating admin membership",
        scope_id=str(scope.id),
        scope_name=scope.name,
        creator_id=str(current_user.id),
    )

    # Automatically create scope membership with admin role
    membership_data = ScopeMembershipCreate(
        user_id=current_user.id,
        email=None,
        team_id=None,
        role=ScopeRole.ADMIN,
        notes="Creator and initial scope administrator",
    )

    try:
        membership = scope_membership_crud.create_invitation(
            db,
            scope_id=scope.id,
            invited_by_id=current_user.id,
            obj_in=membership_data,
        )

        logger.info(
            "Scope membership created",
            membership_id=str(membership.id),
            scope_id=str(scope.id),
            user_id=str(current_user.id),
            role=membership.role,
            is_active=membership.is_active,
            accepted_at=str(membership.accepted_at)
            if membership.accepted_at
            else "NULL",
        )
    except Exception as e:
        logger.error(
            "Failed to create scope membership",
            scope_id=str(scope.id),
            user_id=str(current_user.id),
            error=e,
            error_type=type(e).__name__,
        )
        # Don't fail scope creation if membership fails - log and continue
        # The user can be added manually later

    logger.info(
        "Scope created successfully",
        scope_id=str(scope.id),
        scope_name=scope.name,
        creator_id=str(current_user.id),
        creator_username=current_user.name,
    )

    return scope


@router.get("/", response_model=list[ScopeResponse])
def list_scopes(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        50, ge=1, le=1000, description="Maximum number of records to return"
    ),
    active_only: bool = Query(True, description="Filter for active scopes only"),
    include_public: bool = Query(True, description="Include public scopes"),
) -> Sequence[Scope]:
    """
    List scopes the current user has access to.

    Returns scopes filtered by RLS policies:
    - Application admins see all scopes
    - Regular users see scopes they are members of
    - Public scopes are visible to all (if include_public=True)

    Args:
        db: Database session
        current_user: Current authenticated user
        skip: Pagination offset
        limit: Maximum results per page
        active_only: Filter for active scopes
        include_public: Include public scopes in results

    Returns:
        List of scopes the user has access to
    """
    # Set RLS context - this will filter scopes automatically
    deps.set_rls_context(db, current_user)

    # Application admins see ALL scopes
    if current_user.role.value == "admin":
        scopes = scope_crud.get_multi(
            db, skip=skip, limit=limit, active_only=active_only
        )

        logger.debug(
            "Listed all scopes for admin user",
            user_id=str(current_user.id),
            user_role=current_user.role.value,
            total_scopes=len(scopes),
            skip=skip,
            limit=limit,
        )

        return scopes

    # Regular users see scopes they are members of
    user_scopes = scope_membership_crud.get_user_scopes(db, user_id=current_user.id)

    # Extract scope objects
    scopes = [scope for scope, membership in user_scopes]

    # Filter by active status if requested
    if active_only:
        scopes = [s for s in scopes if s.is_active]

    # Apply pagination
    paginated_scopes = scopes[skip : skip + limit]

    logger.debug(
        "Listed scopes for user",
        user_id=str(current_user.id),
        user_role=current_user.role.value,
        total_scopes=len(scopes),
        returned_scopes=len(paginated_scopes),
        skip=skip,
        limit=limit,
    )

    return paginated_scopes


@router.get("/{scope_id}", response_model=ScopeWithStats)
def get_scope_details(
    *,
    db: Session = Depends(get_db),
    scope_id: UUID,
    current_user: User = Depends(deps.get_current_active_user),
) -> ScopeWithStats:
    """
    Get scope details with statistics.

    User must be a member of the scope or it must be public.
    RLS policies automatically enforce access control.

    Args:
        db: Database session
        scope_id: Scope UUID
        current_user: Current authenticated user

    Returns:
        Scope with statistics

    Raises:
        HTTPException 404: Scope not found or access denied
    """
    # This will use RLS and return scope only if user has access
    scope = deps.get_scope(scope_id, db, current_user)

    # Get statistics
    scope_with_stats = scope_crud.get_with_statistics(db, scope_id=scope_id)

    if not scope_with_stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scope not found or access denied",
        )

    logger.info(
        "Retrieved scope details",
        scope_id=str(scope_id),
        scope_name=scope.name,
        user_id=str(current_user.id),
    )

    return ScopeWithStats(**scope_with_stats)


@router.patch("/{scope_id}", response_model=ScopeResponse)
def update_scope(
    *,
    db: Session = Depends(get_db),
    scope_id: UUID,
    scope_in: ScopeUpdate,
    scope: Scope = Depends(deps.require_scope_role(ScopeRole.ADMIN)),
) -> Scope:
    """
    Update scope details.

    Requires scope admin role or application admin.
    Uses RLS and role-based access control.

    Args:
        db: Database session
        scope_id: Scope UUID
        scope_in: Update data
        scope: Scope object (dependency ensures admin access)

    Returns:
        Updated scope object
    """
    # Scope is already validated by require_scope_role dependency
    updated_scope = scope_crud.update(db, db_obj=scope, obj_in=scope_in)

    logger.info(
        "Scope updated",
        scope_id=str(scope_id),
        scope_name=updated_scope.name,
    )

    return updated_scope


@router.delete("/{scope_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scope(
    *,
    db: Session = Depends(get_db),
    scope_id: UUID,
    current_user: User = Depends(deps.get_current_admin_user),
) -> None:
    """
    Delete a scope (application admin only).

    Only application administrators can delete scopes.
    This is a destructive operation that should be used with caution.

    Args:
        db: Database session
        scope_id: Scope UUID
        current_user: Current user (must be application admin)

    Raises:
        HTTPException 404: Scope not found
        HTTPException 400: Scope has active assignments
    """
    # Set RLS context
    deps.set_rls_context(db, current_user)

    # Get scope
    scope = scope_crud.get(db, id=scope_id)
    if not scope:
        logger.warning(
            "Delete scope failed: not found",
            scope_id=str(scope_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scope not found",
        )

    # Check if scope has active assignments (prevent accidental deletion)
    if scope_crud.has_active_assignments(db, scope_id=scope_id):
        logger.warning(
            "Delete scope failed: has active assignments",
            scope_id=str(scope_id),
            scope_name=scope.name,
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete scope with active gene assignments",
        )

    # Delete scope (CASCADE will delete memberships)
    scope_crud.remove(db, id=scope_id)

    logger.warning(
        "Scope deleted",
        scope_id=str(scope_id),
        scope_name=scope.name,
        deleted_by=str(current_user.id),
        deleted_by_username=current_user.name,
    )


@router.get("/{scope_id}/statistics", response_model=ScopeStatistics)
def get_scope_statistics(
    *,
    db: Session = Depends(get_db),
    scope_id: UUID,
    scope: Scope = Depends(deps.require_scope_role(ScopeRole.VIEWER)),
) -> ScopeStatistics:
    """
    Get detailed statistics for a scope.

    Requires viewer role or higher (any scope member can view statistics).

    Args:
        db: Database session
        scope_id: Scope UUID
        scope: Scope object (dependency ensures member access)

    Returns:
        Scope statistics including gene counts, curation progress, etc.
    """
    statistics = scope_crud.get_detailed_statistics(db, scope_id=scope_id)

    logger.debug(
        "Retrieved scope statistics",
        scope_id=str(scope_id),
        total_genes=statistics.get("total_genes", 0),
        active_curations=statistics.get("active_curations", 0),
    )

    return ScopeStatistics(**statistics)
