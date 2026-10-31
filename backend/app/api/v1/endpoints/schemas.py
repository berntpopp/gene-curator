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
from app.core.capabilities import (
    METHODOLOGY_DERIVE,
    METHODOLOGY_EDIT,
    METHODOLOGY_PUBLISH,
    audit,
    require,
)
from app.core.database import get_db
from app.core.enum_options import flatten_sections
from app.core.schema_compact import compact_field, ranges_for, rules_for, subtree
from app.crud.optimistic_lock import claim_version
from app.crud.schema_repository import (
    SNAPSHOT_KEYS,
    publish_errors,
    schema_crud,
)
from app.models import CurationSchema as CurationSchemaModel, UserNew
from app.models.methodology import MethodologyVersion as MethodologyVersionModel
from app.schemas.schema_repository import (
    CurationSchema,
    CurationSchemaCreate,
    CurationSchemaSubtree,
    CurationSchemaSummary,
    CurationSchemaUpdate,
    MethodologyDerive,
    MethodologyVersion,
    MethodologyVersionImpact,
    SchemaValidationResult,
)
from app.scoring.point_model import point_model
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


# ========================================
# CURATION SCHEMAS ENDPOINTS
# ========================================


@router.get(
    "/curation-schemas",
    response_model=list[CurationSchema] | list[CurationSchemaSummary],
)
def get_curation_schemas(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    schema_type: str | None = Query(None, description="Filter by schema type"),
    institution: str | None = Query(None, description="Filter by institution"),
    active_only: bool = Query(True, description="Filter for active schemas only"),
    detail: bool = Query(
        False, description="Full schemas (fields, scoring, UI) instead of summary rows"
    ),
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> Sequence[CurationSchema] | list[CurationSchemaSummary]:
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
    if not detail:
        return [CurationSchemaSummary.model_validate(x) for x in schemas]
    return schemas  # type: ignore[return-value]


@router.post("/curation-schemas", response_model=CurationSchema)
def create_curation_schema(
    *,
    db: Session = Depends(get_db),
    schema_in: CurationSchemaCreate,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> CurationSchema:
    """
    Create new curation schema: global (owner_scope_id null) by platform admins, or owned
    by a scope by its admins (methodology.derive).
    """
    require(db, current_user, schema_in.owner_scope_id, METHODOLOGY_DERIVE)
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
            db, obj_in=schema_in, owner_id=current_user.id, commit=False
        )
        audit(
            db,
            current_user,
            METHODOLOGY_DERIVE,
            schema.owner_scope_id,
            ("curation_schema", schema.id),
        )
        db.commit()
    db.refresh(schema)
    return schema  # type: ignore[return-value]


@router.get(
    "/curation-schemas/{schema_id}",
    response_model=CurationSchema | CurationSchemaSubtree,
)
def get_curation_schema(
    *,
    db: Session = Depends(get_db),
    schema_id: UUID,
    compact: bool = Query(
        False,
        description="Fields flattened by id without display keys (label, help, "
        "order...); option values only; ui_configuration is {} and "
        "scoring_configuration is null",
    ),
    path: str | None = Query(
        None,
        max_length=300,
        description="Dotted evidence path, e.g. genetic_evidence.case_level."
        "autosomal_recessive.predicted_or_proven_null: only that field, its "
        "validation rules and point ranges, without the schema envelope",
    ),
    scoring: bool = Query(
        False,
        description="Only the scoring_configuration",
    ),
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> CurationSchema | CurationSchemaSubtree:
    """
    Get curation schema by ID. Pass compact=true to read only the field contract and
    path= to read one evidence field (one table's row fields) instead of all.
    """
    schema = schema_crud.get(db, id=schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
    if scoring:  # the whole schema is too large for an MCP result (#612)
        return CurationSchema.model_validate(schema).model_copy(
            update={"field_definitions": {}, "ui_configuration": {}}
        )
    if not compact and not path:
        return schema  # type: ignore[return-value]

    fields = flatten_sections(schema.field_definitions or {})
    if compact:
        fields = {k: compact_field(v) for k, v in fields.items()}
    if path:  # only that subtree, its rules and point ranges (rounds 4 and 5)
        try:
            field = subtree(fields, path)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=exc.args[0]) from exc
        model = point_model(schema.scoring_configuration)
        return CurationSchemaSubtree(
            schema_id=schema.id,
            path=path,
            field=field,
            validation_rules=rules_for(schema.validation_rules or {}, path, field),
            point_ranges=ranges_for(model, path) if model else [],
        )
    return CurationSchema.model_validate(schema).model_copy(
        update={
            "field_definitions": fields,
            "ui_configuration": {},
            "scoring_configuration": None,
        }
    )


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
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> MethodologyVersion:
    """Publish the schema's current content as a new immutable version: platform admins, or
    the owner scope's admins (methodology.publish).

    Existing curations keep the version they were created with; new ones get this one.
    A definition that fails the static checks or one of its tests is refused (422).
    """
    schema = schema_crud.get(db, id=schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
    require(db, current_user, schema.owner_scope_id, METHODOLOGY_PUBLISH)
    errors = publish_errors({key: getattr(schema, key) for key in SNAPSHOT_KEYS})
    if errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "Methodology version not published", "errors": errors},
        )
    version = schema_crud.publish_version(
        db, schema=schema, user_id=current_user.id, commit=False
    )
    audit(
        db,
        current_user,
        METHODOLOGY_PUBLISH,
        schema.owner_scope_id,
        ("methodology_version", version.id),
        {"schema_id": schema.id, "version": version.version},
    )
    db.commit()
    db.refresh(version)
    return version  # type: ignore[return-value]


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
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> CurationSchema:
    """Create an inactive schema from a published version: global by platform admins, or
    owned by owner_scope_id by that scope's admins (methodology.derive).

    The new schema's v1 records the version it was derived from. The source must be
    global or the same scope's.
    """
    require(db, current_user, derive_in.owner_scope_id, METHODOLOGY_DERIVE)
    source = db.get(MethodologyVersionModel, version_id)
    if not source or source.schema_id != schema_id:
        raise HTTPException(status_code=404, detail="Methodology version not found")
    parent = schema_crud.get(db, id=schema_id)
    if parent and parent.owner_scope_id not in (None, derive_in.owner_scope_id):
        raise HTTPException(status_code=403, detail="Schema belongs to another scope")
    if schema_crud.get_by_name_and_version(
        db, name=derive_in.name, version=derive_in.version
    ):
        raise HTTPException(status_code=400, detail=DUPLICATE_SCHEMA)
    with _unique_name_version(db):
        schema = schema_crud.derive(
            db,
            source=source,
            name=derive_in.name,
            version=derive_in.version,
            user_id=current_user.id,
            owner_scope_id=derive_in.owner_scope_id,
            commit=False,
        )
        audit(
            db,
            current_user,
            METHODOLOGY_DERIVE,
            schema.owner_scope_id,
            ("curation_schema", schema.id),
            {"derived_from_version_id": source.id},
        )
        db.commit()
    db.refresh(schema)
    return schema  # type: ignore[return-value]


@router.put("/curation-schemas/{schema_id}", response_model=CurationSchema)
def update_curation_schema(
    *,
    db: Session = Depends(get_db),
    schema_id: UUID,
    schema_in: CurationSchemaUpdate,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> CurationSchema:
    """
    Update curation schema: platform admins, or the owner scope's admins (methodology.edit).
    """
    schema = schema_crud.get(db, id=schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
    require(db, current_user, schema.owner_scope_id, METHODOLOGY_EDIT)

    with _unique_name_version(db):
        if not claim_version(
            db, CurationSchemaModel, schema_id, schema_in.lock_version
        ):
            raise HTTPException(
                status_code=409,
                detail="This schema was saved by someone else since you opened it. "
                "Reload it and apply your changes again.",
            )
        values = schema_in.model_dump(exclude_unset=True, exclude={"lock_version"})
        audit(  # before update(), whose commit writes it with the change
            db,
            current_user,
            METHODOLOGY_EDIT,
            schema.owner_scope_id,
            ("curation_schema", schema.id),
            {"fields": sorted(values)},
        )
        schema = schema_crud.update(db, db_obj=schema, obj_in=values)
    return schema  # type: ignore[return-value]


@router.delete("/curation-schemas/{schema_id}")
def delete_curation_schema(
    *,
    db: Session = Depends(get_db),
    schema_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict[str, str]:
    """
    Delete curation schema: platform admins, or the owner scope's admins (methodology.edit).
    """
    schema = schema_crud.get(db, id=schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
    require(db, current_user, schema.owner_scope_id, METHODOLOGY_EDIT)

    # Check if schema is in use
    if schema_crud.is_schema_in_use(db, schema_id=schema_id):
        raise HTTPException(
            status_code=400, detail="Cannot delete schema that is currently in use"
        )

    owner = schema.owner_scope_id
    audit(db, current_user, METHODOLOGY_EDIT, owner, ("curation_schema", schema_id))
    schema_crud.remove(db, id=schema_id)  # its commit writes the audit row too
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
    schema_id: UUID | None = Query(
        None, description="List the verdicts this schema's scoring config emits"
    ),
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict[str, Any]:
    """
    Get detailed information about a specific scoring engine.
    """
    schema = schema_crud.get(db, id=schema_id) if schema_id else None
    if schema_id and not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
    config = schema.scoring_configuration if schema else None
    engine_info = scoring_registry.get_engine_info(engine_name, config)
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
