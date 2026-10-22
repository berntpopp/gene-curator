"""
Schema repository API endpoints.
Manages curation methodology schemas and workflow pairs.
"""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import deps
from app.core.database import get_db
from app.crud.schema_repository import (
    SNAPSHOT_KEYS,
    publish_errors,
    schema_crud,
    workflow_pair_crud,
)
from app.models import UserNew
from app.models.methodology import MethodologyVersion as MethodologyVersionModel
from app.schemas.schema_repository import (
    CurationSchema,
    CurationSchemaCreate,
    CurationSchemaUpdate,
    MethodologyDerive,
    MethodologyVersion,
    MethodologyVersionImpact,
    SchemaValidationResult,
    WorkflowPair,
    WorkflowPairCreate,
    WorkflowPairUpdate,
)
from app.scoring.registry import scoring_registry

router = APIRouter()

DUPLICATE_SCHEMA = "Schema with this name and version already exists"


@contextmanager
def _unique_name_version(db: Session) -> Iterator[None]:
    """UNIQUE(name, version) decides a race the pre-check lost: same 400 as the check."""
    try:
        yield
    except IntegrityError as exc:
        diag = getattr(exc.orig, "diag", None)  # psycopg2 names the violated constraint
        clash = (
            diag.constraint_name == "curation_schemas_name_version_key"
            if diag
            else "UNIQUE constraint failed: curation_schemas.name, "
            "curation_schemas.version" in str(exc.orig)
        )
        if not clash:
            raise
        db.rollback()
        raise HTTPException(status_code=400, detail=DUPLICATE_SCHEMA) from exc


def _require_active_schemas(db: Session, *schema_ids: UUID | None) -> None:
    for schema_id in schema_ids:
        schema = schema_crud.get(db, id=schema_id) if schema_id else None
        if schema and not schema.is_active:
            raise HTTPException(
                status_code=400, detail=f"Schema '{schema.name}' is inactive"
            )


# ========================================
# CURATION SCHEMAS ENDPOINTS
# ========================================


@router.get("/curation-schemas", response_model=list[CurationSchema])
def get_curation_schemas(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    schema_type: str | None = Query(None, description="Filter by schema type"),
    institution: str | None = Query(None, description="Filter by institution"),
    active_only: bool = Query(True, description="Filter for active schemas only"),
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> Sequence[CurationSchema]:
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
    return schemas  # type: ignore[return-value]


@router.post("/curation-schemas", response_model=CurationSchema)
def create_curation_schema(
    *,
    db: Session = Depends(get_db),
    schema_in: CurationSchemaCreate,
    current_user: UserNew = Depends(deps.get_current_admin_user),
) -> CurationSchema:
    """
    Create new curation schema. Requires platform admin.
    """
    # Check if schema name/version already exists
    existing_schema = schema_crud.get_by_name_and_version(
        db, name=schema_in.name, version=schema_in.version
    )
    if existing_schema:
        raise HTTPException(status_code=400, detail=DUPLICATE_SCHEMA)

    # Same gate as publish: on PostgreSQL the insert publishes v1 (042 trigger)
    errors = publish_errors(schema_in.model_dump())
    if errors:
        raise HTTPException(
            status_code=400, detail=f"Invalid schema structure: {', '.join(errors)}"
        )

    with _unique_name_version(db):
        schema = schema_crud.create_with_owner(
            db, obj_in=schema_in, owner_id=current_user.id
        )
    return schema  # type: ignore[return-value]


@router.get("/curation-schemas/{schema_id}", response_model=CurationSchema)
def get_curation_schema(
    *,
    db: Session = Depends(get_db),
    schema_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> CurationSchema:
    """
    Get curation schema by ID.
    """
    schema = schema_crud.get(db, id=schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    return schema  # type: ignore[return-value]


@router.get(
    "/curation-schemas/{schema_id}/versions", response_model=list[MethodologyVersion]
)
def list_methodology_versions(
    *,
    db: Session = Depends(get_db),
    schema_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> Sequence[MethodologyVersion]:
    """List a schema's methodology versions, newest first."""
    if not schema_crud.get(db, id=schema_id):
        raise HTTPException(status_code=404, detail="Schema not found")
    return schema_crud.list_versions(db, schema_id=schema_id)  # type: ignore[return-value]


@router.post(
    "/curation-schemas/{schema_id}/versions",
    response_model=MethodologyVersion,
    status_code=201,
)
def publish_methodology_version(
    *,
    db: Session = Depends(get_db),
    schema_id: UUID,
    current_user: UserNew = Depends(deps.get_current_admin_user),
) -> MethodologyVersion:
    """Publish the schema's current content as a new immutable version. Requires platform admin.

    Existing curations keep the version they were created with; new ones get this one.
    A definition that fails the static checks or one of its tests is refused (422).
    """
    schema = schema_crud.get(db, id=schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
    errors = publish_errors({key: getattr(schema, key) for key in SNAPSHOT_KEYS})
    if errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "Methodology version not published", "errors": errors},
        )
    return schema_crud.publish_version(  # type: ignore[return-value]
        db, schema=schema, user_id=current_user.id
    )


@router.get(
    "/curation-schemas/{schema_id}/versions/{version_id}/impact",
    response_model=list[MethodologyVersionImpact],
)
def methodology_version_impact(
    *,
    db: Session = Depends(get_db),
    schema_id: UUID,
    version_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> list[dict[str, Any]]:
    """Preview an upgrade: visible curations pinned to an older version whose total or
    class would change when re-scored with this one. Changes nothing."""
    target = db.get(MethodologyVersionModel, version_id)
    if not target or target.schema_id != schema_id:
        raise HTTPException(status_code=404, detail="Methodology version not found")
    return schema_crud.version_impact(db, target=target)


@router.post(
    "/curation-schemas/{schema_id}/versions/{version_id}/derive",
    response_model=CurationSchema,
    status_code=201,
)
def derive_methodology(
    *,
    db: Session = Depends(get_db),
    schema_id: UUID,
    version_id: UUID,
    derive_in: MethodologyDerive,
    current_user: UserNew = Depends(deps.get_current_admin_user),
) -> CurationSchema:
    """Create an inactive schema from a published version. Requires platform admin.

    The new schema's v1 records the version it was derived from.
    """
    source = db.get(MethodologyVersionModel, version_id)
    if not source or source.schema_id != schema_id:
        raise HTTPException(status_code=404, detail="Methodology version not found")
    if schema_crud.get_by_name_and_version(
        db, name=derive_in.name, version=derive_in.version
    ):
        raise HTTPException(status_code=400, detail=DUPLICATE_SCHEMA)
    with _unique_name_version(db):
        return schema_crud.derive(  # type: ignore[return-value]
            db,
            source=source,
            name=derive_in.name,
            version=derive_in.version,
            user_id=current_user.id,
        )


@router.put("/curation-schemas/{schema_id}", response_model=CurationSchema)
def update_curation_schema(
    *,
    db: Session = Depends(get_db),
    schema_id: UUID,
    schema_in: CurationSchemaUpdate,
    current_user: UserNew = Depends(deps.get_current_admin_user),
) -> CurationSchema:
    """
    Update curation schema. Requires platform admin.
    """
    schema = schema_crud.get(db, id=schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    with _unique_name_version(db):
        schema = schema_crud.update(db, db_obj=schema, obj_in=schema_in)
    return schema  # type: ignore[return-value]


@router.delete("/curation-schemas/{schema_id}")
def delete_curation_schema(
    *,
    db: Session = Depends(get_db),
    schema_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict[str, str]:
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
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
    schema_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> Sequence[str]:
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


@router.get("/methodology-versions/{version_id}", response_model=MethodologyVersion)
def get_methodology_version(
    *,
    db: Session = Depends(get_db),
    version_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> MethodologyVersion:
    """Get one methodology version (forms render the version a curation is pinned to)."""
    version = db.get(MethodologyVersionModel, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Methodology version not found")
    return version  # type: ignore[return-value]


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
    Retrieve workflow pairs with optional filtering.
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
    current_user: UserNew = Depends(deps.get_current_admin_user),
) -> WorkflowPair:
    """
    Create new workflow pair. Requires platform admin.
    """
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

    _require_active_schemas(db, precuration_schema.id, curation_schema.id)

    workflow_pair = workflow_pair_crud.create_with_owner(
        db, obj_in=workflow_pair_in, owner_id=current_user.id
    )
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
    current_user: UserNew = Depends(deps.get_current_admin_user),
) -> WorkflowPair:
    """
    Update workflow pair. Requires platform admin.
    """
    workflow_pair = workflow_pair_crud.get(db, id=workflow_pair_id)
    if not workflow_pair:
        raise HTTPException(status_code=404, detail="Workflow pair not found")

    _require_active_schemas(
        db,
        workflow_pair_in.precuration_schema_id,
        workflow_pair_in.curation_schema_id,
    )
    workflow_pair = workflow_pair_crud.update(
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


@router.get("/scoring-engines")
def get_scoring_engines(
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> Sequence[dict[str, Any]]:
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
) -> dict[str, Any]:
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
    evidence_data: dict[str, Any],
    schema_config: dict[str, Any],
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict[str, Any]:
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
    evidence_data: dict[str, Any],
    schema_config: dict[str, Any],
    scope_context: dict[str, Any] | None = None,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict[str, Any]:
    """
    Calculate scores using a specific scoring engine.
    """
    result = scoring_registry.calculate_scores(
        engine_name, evidence_data, schema_config, scope_context
    )

    if not result:
        raise HTTPException(status_code=404, detail="Scoring engine not found")

    return {"engine_name": engine_name, "result": result.model_dump()}
