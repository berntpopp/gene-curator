"""
Scope management API endpoints.
Handles clinical specialty scopes and their configurations.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core import deps
from app.crud.scope import scope_crud
from app.models import User
from app.schemas.scope import (
    Scope,
    ScopeCreate,
    ScopeStatistics,
    ScopeUpdate,
    ScopeWithStats,
)

router = APIRouter()


@router.get("/", response_model=list[Scope])
def get_scopes(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    active_only: bool = Query(True, description="Filter for active scopes only"),
    institution: str | None = Query(None, description="Filter by institution"),
    current_user: User = Depends(deps.get_current_active_user),
) -> list[Scope]:
    """
    Retrieve scopes with optional filtering.
    """
    # Check if user has admin access or is assigned to view scopes
    if current_user.role.value not in ["admin", "scope_admin"]:
        # Regular users can only see scopes they're assigned to
        user_scope_ids = []  # TODO: Implement scope assignments for regular users
        scopes = scope_crud.get_user_scopes(
            db, user_scope_ids=user_scope_ids, active_only=active_only
        )
        return scopes[skip : skip + limit]

    # Admin users can see all scopes
    scopes = scope_crud.get_multi(
        db, skip=skip, limit=limit, active_only=active_only, institution=institution
    )
    return scopes


@router.post("/", response_model=Scope)
def create_scope(
    *,
    db: Session = Depends(deps.get_db),
    scope_in: ScopeCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Scope:
    """
    Create new scope. Requires admin privileges.
    """
    if current_user.role.value not in ["admin", "scope_admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Check if scope name already exists
    if scope_crud.get_by_name(db, name=scope_in.name):
        raise HTTPException(
            status_code=400, detail="Scope with this name already exists"
        )

    scope = scope_crud.create_with_owner(db, obj_in=scope_in, owner_id=current_user.id)
    return scope


@router.get("/{scope_id}", response_model=ScopeWithStats)
def get_scope(
    *,
    db: Session = Depends(deps.get_db),
    scope_id: UUID,
    current_user: User = Depends(deps.get_current_active_user),
) -> ScopeWithStats:
    """
    Get scope by ID with statistics.
    """
    scope = scope_crud.get(db, id=scope_id)
    if not scope:
        raise HTTPException(status_code=404, detail="Scope not found")

    # Check if user has access to this scope
    if current_user.role.value not in ["admin", "scope_admin"] and scope_id not in (
        current_user.assigned_scopes or []
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    scope_with_stats = scope_crud.get_with_statistics(db, scope_id=scope_id)
    return scope_with_stats


@router.put("/{scope_id}", response_model=Scope)
def update_scope(
    *,
    db: Session = Depends(deps.get_db),
    scope_id: UUID,
    scope_in: ScopeUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Scope:
    """
    Update scope. Requires admin privileges.
    """
    scope = scope_crud.get(db, id=scope_id)
    if not scope:
        raise HTTPException(status_code=404, detail="Scope not found")

    if current_user.role.value not in ["admin", "scope_admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    scope = scope_crud.update(db, db_obj=scope, obj_in=scope_in)
    return scope


@router.delete("/{scope_id}")
def delete_scope(
    *,
    db: Session = Depends(deps.get_db),
    scope_id: UUID,
    current_user: User = Depends(deps.get_current_active_user),
) -> dict:
    """
    Delete scope. Requires admin privileges.
    """
    scope = scope_crud.get(db, id=scope_id)
    if not scope:
        raise HTTPException(status_code=404, detail="Scope not found")

    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Check if scope has active assignments
    if scope_crud.has_active_assignments(db, scope_id=scope_id):
        raise HTTPException(
            status_code=400, detail="Cannot delete scope with active gene assignments"
        )

    scope_crud.remove(db, id=scope_id)
    return {"message": "Scope deleted successfully"}


@router.get("/{scope_id}/statistics", response_model=ScopeStatistics)
def get_scope_statistics(
    *,
    db: Session = Depends(deps.get_db),
    scope_id: UUID,
    current_user: User = Depends(deps.get_current_active_user),
) -> ScopeStatistics:
    """
    Get detailed statistics for a scope.
    """
    scope = scope_crud.get(db, id=scope_id)
    if not scope:
        raise HTTPException(status_code=404, detail="Scope not found")

    # Check if user has access to this scope
    if current_user.role.value not in ["admin", "scope_admin"] and scope_id not in (
        current_user.assigned_scopes or []
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    statistics = scope_crud.get_detailed_statistics(db, scope_id=scope_id)
    return statistics


@router.get("/{scope_id}/workflow-pairs", response_model=list[dict])
def get_scope_workflow_pairs(
    *,
    db: Session = Depends(deps.get_db),
    scope_id: UUID,
    current_user: User = Depends(deps.get_current_active_user),
) -> list[dict]:
    """
    Get available workflow pairs for a scope.
    """
    scope = scope_crud.get(db, id=scope_id)
    if not scope:
        raise HTTPException(status_code=404, detail="Scope not found")

    # Check if user has access to this scope
    if current_user.role.value not in ["admin", "scope_admin"] and scope_id not in (
        current_user.assigned_scopes or []
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    workflow_pairs = scope_crud.get_available_workflow_pairs(db, scope_id=scope_id)
    return workflow_pairs


@router.post("/{scope_id}/assign-users")
def assign_users_to_scope(
    *,
    db: Session = Depends(deps.get_db),
    scope_id: UUID,
    user_ids: list[UUID],
    current_user: User = Depends(deps.get_current_active_user),
) -> dict:
    """
    Assign users to a scope. Requires admin privileges.
    """
    scope = scope_crud.get(db, id=scope_id)
    if not scope:
        raise HTTPException(status_code=404, detail="Scope not found")

    if current_user.role.value not in ["admin", "scope_admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Assign users to scope
    assigned_count = scope_crud.assign_users(db, scope_id=scope_id, user_ids=user_ids)

    return {
        "message": f"Successfully assigned {assigned_count} users to scope",
        "scope_id": scope_id,
        "assigned_users": assigned_count,
    }


@router.post("/{scope_id}/remove-users")
def remove_users_from_scope(
    *,
    db: Session = Depends(deps.get_db),
    scope_id: UUID,
    user_ids: list[UUID],
    current_user: User = Depends(deps.get_current_active_user),
) -> dict:
    """
    Remove users from a scope. Requires admin privileges.
    """
    scope = scope_crud.get(db, id=scope_id)
    if not scope:
        raise HTTPException(status_code=404, detail="Scope not found")

    if current_user.role.value not in ["admin", "scope_admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Remove users from scope
    removed_count = scope_crud.remove_users(db, scope_id=scope_id, user_ids=user_ids)

    return {
        "message": f"Successfully removed {removed_count} users from scope",
        "scope_id": scope_id,
        "removed_users": removed_count,
    }


@router.get("/{scope_id}/users", response_model=list[dict])
def get_scope_users(
    *,
    db: Session = Depends(deps.get_db),
    scope_id: UUID,
    current_user: User = Depends(deps.get_current_active_user),
) -> list[dict]:
    """
    Get users assigned to a scope.
    """
    scope = scope_crud.get(db, id=scope_id)
    if not scope:
        raise HTTPException(status_code=404, detail="Scope not found")

    # Check if user has access to this scope
    if current_user.role.value not in ["admin", "scope_admin"] and scope_id not in (
        current_user.assigned_scopes or []
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    users = scope_crud.get_scope_users(db, scope_id=scope_id)
    return users


@router.put("/{scope_id}/default-workflow-pair")
def set_default_workflow_pair(
    *,
    db: Session = Depends(deps.get_db),
    scope_id: UUID,
    workflow_pair_id: UUID,
    current_user: User = Depends(deps.get_current_active_user),
) -> dict:
    """
    Set default workflow pair for a scope. Requires admin privileges.
    """
    scope = scope_crud.get(db, id=scope_id)
    if not scope:
        raise HTTPException(status_code=404, detail="Scope not found")

    if current_user.role.value not in ["admin", "scope_admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Update default workflow pair
    scope = scope_crud.set_default_workflow_pair(
        db, scope_id=scope_id, workflow_pair_id=workflow_pair_id
    )

    return {
        "message": "Default workflow pair updated successfully",
        "scope_id": scope_id,
        "default_workflow_pair_id": workflow_pair_id,
    }
