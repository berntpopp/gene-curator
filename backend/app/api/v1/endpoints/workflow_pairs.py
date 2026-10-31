"""Workflow pair endpoints (split from schemas.py): global pairs by platform admins,
scope-owned pairs by that scope's admins (workflow.create, #284)."""

from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core import deps
from app.core.capabilities import WORKFLOW_CREATE, audit, require
from app.core.database import get_db
from app.crud.schema_repository import schema_crud, workflow_pair_crud
from app.models import UserNew
from app.schemas.schema_repository import (
    WorkflowPair,
    WorkflowPairCreate,
    WorkflowPairUpdate,
)

router = APIRouter()


def _require_active_schemas(
    db: Session, owner: UUID | None, *schema_ids: UUID | None
) -> None:
    """Active schemas, global or owned by the pair's scope (never another scope's)."""
    for schema_id in schema_ids:
        schema = schema_crud.get(db, id=schema_id) if schema_id else None
        if schema and not schema.is_active:
            raise HTTPException(
                status_code=400, detail=f"Schema '{schema.name}' is inactive"
            )
        if schema and schema.owner_scope_id not in (None, owner):
            raise HTTPException(
                status_code=403,
                detail=f"Schema '{schema.name}' belongs to another scope",
            )


# ========================================
# WORKFLOW PAIRS ENDPOINTS
# ========================================


@router.get("/workflow-pairs", response_model=list[WorkflowPair])
def get_workflow_pairs(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    active_only: bool = Query(
        True, description="Filter for active workflow pairs only"
    ),
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> Sequence[WorkflowPair]:
    """
    List workflow pairs (methodologies). Each pairs a precuration schema with a
    curation schema; they differ in those schemas and their scoring. The pair with
    is_default=true is what create_scope uses when no default_workflow_pair_id is given.
    """
    workflow_pairs = workflow_pair_crud.get_multi(
        db, skip=skip, limit=limit, active_only=active_only
    )
    return workflow_pairs  # type: ignore[return-value]


@router.post("/workflow-pairs", response_model=WorkflowPair)
def create_workflow_pair(
    *,
    db: Session = Depends(get_db),
    workflow_pair_in: WorkflowPairCreate,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> WorkflowPair:
    """
    Create new workflow pair: global by platform admins, or owned by owner_scope_id by
    that scope's admins (workflow.create) from global or the same scope's schemas.
    """
    owner = workflow_pair_in.owner_scope_id
    require(db, current_user, owner, WORKFLOW_CREATE)
    # Check if workflow pair name/version already exists
    existing_pair = workflow_pair_crud.get_by_name_and_version(
        db, name=workflow_pair_in.name, version=workflow_pair_in.version
    )
    if existing_pair:
        raise HTTPException(
            status_code=400,
            detail="Workflow pair with this name and version already exists",
        )

    # Validate that referenced schemas exist
    precuration_schema = schema_crud.get(db, id=workflow_pair_in.precuration_schema_id)
    curation_schema = schema_crud.get(db, id=workflow_pair_in.curation_schema_id)

    if not precuration_schema:
        raise HTTPException(status_code=400, detail="Precuration schema not found")
    if not curation_schema:
        raise HTTPException(status_code=400, detail="Curation schema not found")

    # Validate schema compatibility
    if precuration_schema.schema_type not in ["precuration", "combined"]:
        raise HTTPException(
            status_code=400,
            detail="Precuration schema must be of type 'precuration' or 'combined'",
        )

    if curation_schema.schema_type not in ["curation", "combined"]:
        raise HTTPException(
            status_code=400,
            detail="Curation schema must be of type 'curation' or 'combined'",
        )

    _require_active_schemas(db, owner, precuration_schema.id, curation_schema.id)

    workflow_pair = workflow_pair_crud.create_with_owner(
        db, obj_in=workflow_pair_in, owner_id=current_user.id, commit=False
    )
    audit(db, current_user, WORKFLOW_CREATE, owner, ("workflow_pair", workflow_pair.id))
    db.commit()
    db.refresh(workflow_pair)
    return workflow_pair  # type: ignore[return-value]


@router.get("/workflow-pairs/{workflow_pair_id}", response_model=WorkflowPair)
def get_workflow_pair(
    *,
    db: Session = Depends(get_db),
    workflow_pair_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> WorkflowPair:
    """
    Get workflow pair by ID.
    """
    workflow_pair = workflow_pair_crud.get(db, id=workflow_pair_id)
    if not workflow_pair:
        raise HTTPException(status_code=404, detail="Workflow pair not found")

    return workflow_pair  # type: ignore[return-value]


@router.put("/workflow-pairs/{workflow_pair_id}", response_model=WorkflowPair)
def update_workflow_pair(
    *,
    db: Session = Depends(get_db),
    workflow_pair_id: UUID,
    workflow_pair_in: WorkflowPairUpdate,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> WorkflowPair:
    """
    Update workflow pair: platform admins, or the owner scope's admins (workflow.create).
    """
    workflow_pair = workflow_pair_crud.get(db, id=workflow_pair_id)
    if not workflow_pair:
        raise HTTPException(status_code=404, detail="Workflow pair not found")
    owner = workflow_pair.owner_scope_id
    require(db, current_user, owner, WORKFLOW_CREATE)

    _require_active_schemas(
        db,
        owner,
        workflow_pair_in.precuration_schema_id,
        workflow_pair_in.curation_schema_id,
    )
    audit(db, current_user, WORKFLOW_CREATE, owner, ("workflow_pair", workflow_pair.id))
    workflow_pair = workflow_pair_crud.update(  # its commit writes the audit row too
        db, db_obj=workflow_pair, obj_in=workflow_pair_in
    )
    return workflow_pair  # type: ignore[return-value]


@router.delete("/workflow-pairs/{workflow_pair_id}")
def delete_workflow_pair(
    *,
    db: Session = Depends(get_db),
    workflow_pair_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict[str, str]:
    """
    Delete workflow pair: platform admins, or the owner scope's admins (workflow.create).
    """
    workflow_pair = workflow_pair_crud.get(db, id=workflow_pair_id)
    if not workflow_pair:
        raise HTTPException(status_code=404, detail="Workflow pair not found")
    owner = workflow_pair.owner_scope_id
    require(db, current_user, owner, WORKFLOW_CREATE)

    # Check if workflow pair is in use
    if workflow_pair_crud.is_workflow_pair_in_use(
        db, workflow_pair_id=workflow_pair_id
    ):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete workflow pair that is currently in use",
        )

    audit(db, current_user, WORKFLOW_CREATE, owner, ("workflow_pair", workflow_pair_id))
    workflow_pair_crud.remove(db, id=workflow_pair_id)  # its commit writes the audit
    return {"message": "Workflow pair deleted successfully"}
