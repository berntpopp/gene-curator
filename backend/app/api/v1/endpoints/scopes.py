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

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import deps
from app.core.database import get_db
from app.core.enums import ScopeRole
from app.core.logging import get_logger
from app.crud.scope import scope_crud
from app.crud.scope_counts import get_counts_for_scopes
from app.crud.scope_membership import scope_membership_crud
from app.models import Scope, User, WorkflowPair
from app.schemas.scope import (
    Scope as ScopeResponse,
    ScopeCreate,
    ScopeListItem,
    ScopeListStats,
    ScopeStatistics,
    ScopeUpdate,
    ScopeWithStats,
)

logger = get_logger(__name__)

router = APIRouter()

_DETAIL_FIELDS = (
    "description",
    "institution",
    "is_public",
    "scope_config",
    "is_active",
    "created_at",
    "updated_at",
    "created_by",
)


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

    pair = db.get(WorkflowPair, scope_in.default_workflow_pair_id)
    if not pair or not pair.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow pair not found or inactive",
        )

    # Create scope
    scope = scope_crud.create_with_owner(db, obj_in=scope_in, owner_id=current_user.id)

    logger.debug(
        "Scope entity created, now creating admin membership",
        scope_id=str(scope.id),
        scope_name=scope.name,
        creator_id=str(current_user.id),
    )

    # Automatically create accepted scope membership with admin role.
    # On failure remove the scope again: an ownerless scope must not survive.
    try:
        membership = scope_membership_crud.create_owner_membership(
            db, scope_id=scope.id, owner_id=current_user.id
        )
    except Exception:
        db.rollback()
        db.delete(scope)
        db.commit()
        logger.error(
            "Failed to create owner membership; scope rolled back",
            scope_id=str(scope.id),
            user_id=str(current_user.id),
        )
        raise

    logger.info(
        "Scope membership created",
        membership_id=str(membership.id),
        scope_id=str(scope.id),
        user_id=str(current_user.id),
        role=membership.role,
    )

    logger.info(
        "Scope created successfully",
        scope_id=str(scope.id),
        scope_name=scope.name,
        creator_id=str(current_user.id),
        creator_username=current_user.name,
    )

    return scope


@router.get("/", response_model=list[ScopeListItem], response_model_exclude_unset=True)
def list_scopes(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        50, ge=1, le=1000, description="Maximum number of records to return"
    ),
    active_only: bool = Query(True, description="Filter for active scopes only"),
    name: str | None = Query(
        None, description="Case-insensitive part of the scope name or display name"
    ),
    detail: bool = Query(
        False, description="Full scope fields (config, description, timestamps)"
    ),
) -> list[ScopeListItem]:
    """
    List scopes the current user has access to with gene and member counts.

    Returns scopes filtered by RLS policies:
    - Application admins see all scopes
    - Regular users see scopes they are members of

    Args:
        db: Database session
        current_user: Current authenticated user
        skip: Pagination offset
        limit: Maximum results per page
        active_only: Filter for active scopes

    Returns:
        List of scopes the user has access to with counts
    """
    # Set RLS context - this will filter scopes automatically
    deps.set_rls_context(db, current_user)

    # Caller's accepted membership role per scope (admins may have none)
    user_scopes = scope_membership_crud.get_user_scopes(db, user_id=current_user.id)
    roles = {scope.id: getattr(m.role, "value", m.role) for scope, m in user_scopes}
    needle = name.lower() if name else None

    def matches(scope: Scope) -> bool:
        return (not active_only or scope.is_active) and (
            needle is None
            or needle in scope.name.lower()
            or needle in scope.display_name.lower()
        )

    if current_user.role.value == "admin":  # application admins see ALL scopes
        stmt = select(Scope).order_by(Scope.name, Scope.id)  # stable pages
        if active_only:
            stmt = stmt.where(Scope.is_active)
        if needle:
            pattern = f"%{needle}%"
            stmt = stmt.where(
                Scope.name.ilike(pattern) | Scope.display_name.ilike(pattern)
            )
        page = list(db.scalars(stmt.offset(skip).limit(limit)).all())
    else:
        scopes = [scope for scope, _ in user_scopes]
        # A non-member may open an active public scope (#484): list it too, with no role
        scopes += db.scalars(
            select(Scope)
            .where(Scope.is_public, Scope.is_active, Scope.id.notin_(list(roles)))
            .order_by(Scope.name)
        ).all()
        page = [s for s in scopes if matches(s)][skip : skip + limit]

    counts = get_counts_for_scopes(db, [sc.id for sc in page])
    result = []
    for scope in page:
        c = counts[scope.id]
        extra = {f: getattr(scope, f) for f in _DETAIL_FIELDS} if detail else {}
        result.append(
            ScopeListItem(
                id=scope.id,
                name=scope.name,
                display_name=scope.display_name,
                default_workflow_pair_id=scope.default_workflow_pair_id,
                stats=ScopeListStats(
                    total_genes=c["total"],
                    completed_genes=c["completed"],
                    member_count=c["members"],
                ),
                user_role=roles.get(scope.id),
                **extra,
            )
        )

    logger.debug(
        "Listed scopes for user",
        user_id=str(current_user.id),
        user_role=current_user.role.value,
        returned_scopes=len(result),
        skip=skip,
        limit=limit,
    )

    return result


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

    role = scope_membership_crud.get_user_role_in_scope(
        db, user_id=current_user.id, scope_id=scope_id
    )
    pair = scope.default_workflow_pair
    return ScopeWithStats(
        **scope_with_stats,
        user_role=role.value if role else None,
        curation_schema_id=pair.curation_schema_id if pair else None,
        precuration_schema_id=pair.precuration_schema_id if pair else None,
    )


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
    force: bool = Query(
        False,
        description="Force deletion even if scope has active gene assignments",
    ),
    current_user: User = Depends(deps.get_current_active_user),
) -> None:
    """
    Delete a scope (application admin or scope owner only).

    Application administrators and scope owners (creators) can delete scopes.
    This is a destructive operation that should be used with caution.

    Args:
        db: Database session
        scope_id: Scope UUID
        force: If True, delete even with active gene assignments (cascade delete)
        current_user: Current user (must be app admin or scope owner)

    Raises:
        HTTPException 404: Scope not found
        HTTPException 403: Not authorized to delete
        HTTPException 400: Scope has active assignments (unless force=True)
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

    # Check authorization: must be app admin or scope owner
    is_app_admin = current_user.role.value == "admin"
    is_scope_owner = scope.created_by == current_user.id

    if not is_app_admin and not is_scope_owner:
        logger.warning(
            "Delete scope failed: not authorized",
            scope_id=str(scope_id),
            scope_name=scope.name,
            user_id=str(current_user.id),
            is_app_admin=is_app_admin,
            is_scope_owner=is_scope_owner,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only application administrators or scope owners can delete scopes",
        )

    # Check if scope has active assignments (prevent accidental deletion)
    has_assignments = scope_crud.has_active_assignments(db, scope_id=scope_id)
    if has_assignments and not force:
        logger.warning(
            "Delete scope failed: has active assignments (use force=true to override)",
            scope_id=str(scope_id),
            scope_name=scope.name,
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete scope with active gene assignments. Use force=true to delete anyway.",
        )

    if has_assignments and force:
        logger.warning(
            "Force deleting scope with active assignments",
            scope_id=str(scope_id),
            scope_name=scope.name,
            user_id=str(current_user.id),
        )

    # Delete scope (CASCADE will delete memberships and assignments)
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
