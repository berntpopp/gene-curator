"""
Schema repository API endpoints.
Manages curation methodology schemas and workflow pairs.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core import deps
from app.crud.schema_repository import schema_crud, workflow_pair_crud
from app.models import UserNew
from app.schemas.schema_repository import (
    CurationSchema,
    CurationSchemaCreate,
    CurationSchemaUpdate,
    SchemaValidationResult,
    WorkflowPair,
    WorkflowPairCreate,
    WorkflowPairUpdate,
)
from app.scoring.registry import scoring_registry

router = APIRouter()


# ========================================
# CURATION SCHEMAS ENDPOINTS
# ========================================


@router.get("/curation-schemas", response_model=list[CurationSchema])
def get_curation_schemas(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    schema_type: str | None = Query(None, description="Filter by schema type"),
    institution: str | None = Query(None, description="Filter by institution"),
    active_only: bool = Query(True, description="Filter for active schemas only"),
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> list[CurationSchema]:
    """
    Retrieve curation schemas with optional filtering.
    """
    schemas = schema_crud.get_multi(
        db,
        skip=skip,
        limit=limit,
        schema_type=schema_type,
        institution=institution,
        active_only=active_only,
    )
    return schemas


@router.post("/curation-schemas", response_model=CurationSchema)
def create_curation_schema(
    *,
    db: Session = Depends(deps.get_db),
    schema_in: CurationSchemaCreate,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> CurationSchema:
    """
    Create new curation schema. Requires curator or admin privileges.
    """
    if current_user.role not in ["curator", "admin", "scope_admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Check if schema name/version already exists
    existing_schema = schema_crud.get_by_name_and_version(
        db, name=schema_in.name, version=schema_in.version
    )
    if existing_schema:
        raise HTTPException(
            status_code=400, detail="Schema with this name and version already exists"
        )

    # Validate schema structure
    validation_result = schema_crud.validate_schema_structure(schema_in.dict())
    if not validation_result.is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid schema structure: {', '.join(validation_result.errors)}",
        )

    schema = schema_crud.create_with_owner(
        db, obj_in=schema_in, owner_id=current_user.id
    )
    return schema


@router.get("/curation-schemas/{schema_id}", response_model=CurationSchema)
def get_curation_schema(
    *,
    db: Session = Depends(deps.get_db),
    schema_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> CurationSchema:
    """
    Get curation schema by ID.
    """
    schema = schema_crud.get(db, id=schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    return schema


@router.put("/curation-schemas/{schema_id}", response_model=CurationSchema)
def update_curation_schema(
    *,
    db: Session = Depends(deps.get_db),
    schema_id: UUID,
    schema_in: CurationSchemaUpdate,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> CurationSchema:
    """
    Update curation schema. Requires curator or admin privileges.
    """
    schema = schema_crud.get(db, id=schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    if current_user.role not in ["curator", "admin", "scope_admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Only creator or admin can update
    if schema.created_by != current_user.id and current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Can only update own schemas")

    schema = schema_crud.update(db, db_obj=schema, obj_in=schema_in)
    return schema


@router.delete("/curation-schemas/{schema_id}")
def delete_curation_schema(
    *,
    db: Session = Depends(deps.get_db),
    schema_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict:
    """
    Delete curation schema. Requires admin privileges.
    """
    schema = schema_crud.get(db, id=schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Check if schema is in use
    if schema_crud.is_schema_in_use(db, schema_id=schema_id):
        raise HTTPException(
            status_code=400, detail="Cannot delete schema that is currently in use"
        )

    schema_crud.remove(db, id=schema_id)
    return {"message": "Schema deleted successfully"}


@router.post(
    "/curation-schemas/{schema_id}/validate", response_model=SchemaValidationResult
)
def validate_curation_schema(
    *,
    db: Session = Depends(deps.get_db),
    schema_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> SchemaValidationResult:
    """
    Validate a curation schema structure and compatibility.
    """
    schema = schema_crud.get(db, id=schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    # Validate schema structure
    validation_result = schema_crud.validate_schema_structure(
        {
            "field_definitions": schema.field_definitions,
            "validation_rules": schema.validation_rules,
            "scoring_configuration": schema.scoring_configuration,
            "workflow_states": schema.workflow_states,
            "ui_configuration": schema.ui_configuration,
        }
    )

    return validation_result


@router.get(
    "/curation-schemas/{schema_id}/compatible-engines", response_model=list[str]
)
def get_compatible_scoring_engines(
    *,
    db: Session = Depends(deps.get_db),
    schema_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> list[str]:
    """
    Get scoring engines compatible with a schema.
    """
    schema = schema_crud.get(db, id=schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    compatible_engines = scoring_registry.find_engines_for_schema(
        schema.name, schema.version
    )

    return compatible_engines


# ========================================
# WORKFLOW PAIRS ENDPOINTS
# ========================================


@router.get("/workflow-pairs", response_model=list[WorkflowPair])
def get_workflow_pairs(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    active_only: bool = Query(
        True, description="Filter for active workflow pairs only"
    ),
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> list[WorkflowPair]:
    """
    Retrieve workflow pairs with optional filtering.
    """
    workflow_pairs = workflow_pair_crud.get_multi(
        db, skip=skip, limit=limit, active_only=active_only
    )
    return workflow_pairs


@router.post("/workflow-pairs", response_model=WorkflowPair)
def create_workflow_pair(
    *,
    db: Session = Depends(deps.get_db),
    workflow_pair_in: WorkflowPairCreate,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> WorkflowPair:
    """
    Create new workflow pair. Requires curator or admin privileges.
    """
    if current_user.role not in ["curator", "admin", "scope_admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

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

    workflow_pair = workflow_pair_crud.create_with_owner(
        db, obj_in=workflow_pair_in, owner_id=current_user.id
    )
    return workflow_pair


@router.get("/workflow-pairs/{workflow_pair_id}", response_model=WorkflowPair)
def get_workflow_pair(
    *,
    db: Session = Depends(deps.get_db),
    workflow_pair_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> WorkflowPair:
    """
    Get workflow pair by ID.
    """
    workflow_pair = workflow_pair_crud.get(db, id=workflow_pair_id)
    if not workflow_pair:
        raise HTTPException(status_code=404, detail="Workflow pair not found")

    return workflow_pair


@router.put("/workflow-pairs/{workflow_pair_id}", response_model=WorkflowPair)
def update_workflow_pair(
    *,
    db: Session = Depends(deps.get_db),
    workflow_pair_id: UUID,
    workflow_pair_in: WorkflowPairUpdate,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> WorkflowPair:
    """
    Update workflow pair. Requires curator or admin privileges.
    """
    workflow_pair = workflow_pair_crud.get(db, id=workflow_pair_id)
    if not workflow_pair:
        raise HTTPException(status_code=404, detail="Workflow pair not found")

    if current_user.role not in ["curator", "admin", "scope_admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Only creator or admin can update
    if workflow_pair.created_by != current_user.id and current_user.role not in [
        "admin"
    ]:
        raise HTTPException(
            status_code=403, detail="Can only update own workflow pairs"
        )

    workflow_pair = workflow_pair_crud.update(
        db, db_obj=workflow_pair, obj_in=workflow_pair_in
    )
    return workflow_pair


@router.delete("/workflow-pairs/{workflow_pair_id}")
def delete_workflow_pair(
    *,
    db: Session = Depends(deps.get_db),
    workflow_pair_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict:
    """
    Delete workflow pair. Requires admin privileges.
    """
    workflow_pair = workflow_pair_crud.get(db, id=workflow_pair_id)
    if not workflow_pair:
        raise HTTPException(status_code=404, detail="Workflow pair not found")

    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Check if workflow pair is in use
    if workflow_pair_crud.is_workflow_pair_in_use(
        db, workflow_pair_id=workflow_pair_id
    ):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete workflow pair that is currently in use",
        )

    workflow_pair_crud.remove(db, id=workflow_pair_id)
    return {"message": "Workflow pair deleted successfully"}


# ========================================
# SCORING ENGINES ENDPOINTS
# ========================================


@router.get("/scoring-engines", response_model=list[dict])
def get_scoring_engines(
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> list[dict]:
    """
    Get list of available scoring engines.
    """
    engines = scoring_registry.list_engines()
    return engines


@router.get("/scoring-engines/{engine_name}", response_model=dict)
def get_scoring_engine_info(
    *,
    engine_name: str,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict:
    """
    Get detailed information about a specific scoring engine.
    """
    engine_info = scoring_registry.get_engine_info(engine_name)
    if not engine_info:
        raise HTTPException(status_code=404, detail="Scoring engine not found")

    return engine_info


@router.post("/scoring-engines/{engine_name}/validate")
def validate_evidence_with_engine(
    *,
    engine_name: str,
    evidence_data: dict,
    schema_config: dict,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict:
    """
    Validate evidence data using a specific scoring engine.
    """
    errors = scoring_registry.validate_evidence(
        engine_name, evidence_data, schema_config
    )

    return {"engine_name": engine_name, "is_valid": len(errors) == 0, "errors": errors}


@router.post("/scoring-engines/{engine_name}/calculate")
def calculate_scores_with_engine(
    *,
    engine_name: str,
    evidence_data: dict,
    schema_config: dict,
    scope_context: dict | None = None,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict:
    """
    Calculate scores using a specific scoring engine.
    """
    result = scoring_registry.calculate_scores(
        engine_name, evidence_data, schema_config, scope_context
    )

    if not result:
        raise HTTPException(status_code=404, detail="Scoring engine not found")

    return {"engine_name": engine_name, "result": result.dict()}
