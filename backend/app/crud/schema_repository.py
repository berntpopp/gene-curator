"""
CRUD operations for schema repository management.
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.crud.schema_validators import validate_schema_structure
from app.models import (
    CurationNew,
    CurationSchema,
    PrecurationNew,
    WorkflowPair,
)
from app.schemas.schema_repository import (
    CurationSchemaCreate,
    CurationSchemaUpdate,
    SchemaValidationResult,
    WorkflowPairCreate,
    WorkflowPairUpdate,
)


class CRUDCurationSchema(
    CRUDBase[CurationSchema, CurationSchemaCreate, CurationSchemaUpdate]
):
    """CRUD operations for curation schemas."""

    def get_by_name_and_version(
        self, db: Session, *, name: str, version: str
    ) -> CurationSchema | None:
        """Get schema by name and version."""
        return (
            db.execute(
                select(CurationSchema).where(
                    and_(CurationSchema.name == name, CurationSchema.version == version)
                )
            )
            .scalars()
            .first()
        )

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        schema_type: str | None = None,
        institution: str | None = None,
        active_only: bool = True,
    ) -> Sequence[CurationSchema]:
        """Get multiple schemas with filtering."""
        stmt = select(CurationSchema)

        if active_only:
            stmt = stmt.where(CurationSchema.is_active)  # Fixed: use == instead of is

        if schema_type:
            stmt = stmt.where(CurationSchema.schema_type == schema_type)

        if institution:
            stmt = stmt.where(CurationSchema.institution == institution)

        return (
            db.execute(
                stmt.order_by(CurationSchema.name, CurationSchema.version.desc())
                .offset(skip)
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def create_with_owner(
        self, db: Session, *, obj_in: CurationSchemaCreate, owner_id: UUID
    ) -> CurationSchema:
        """Create schema with owner."""
        obj_in_data = obj_in.model_dump()
        obj_in_data["created_by"] = owner_id
        db_obj = CurationSchema(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def is_schema_in_use(self, db: Session, *, schema_id: UUID) -> bool:
        """Check if schema is currently in use by workflow pairs or curations."""
        # Check workflow pairs
        workflow_pair_count = db.execute(
            select(func.count(WorkflowPair.id)).where(
                or_(
                    WorkflowPair.precuration_schema_id == schema_id,
                    WorkflowPair.curation_schema_id == schema_id,
                )
            )
        ).scalar()

        # Check direct usage in precurations (precurations use precuration_schema_id)
        precuration_count = db.execute(
            select(func.count(PrecurationNew.id)).where(
                PrecurationNew.precuration_schema_id == schema_id
            )
        ).scalar()

        # Curations don't have a direct schema_id, they use workflow_pair_id
        # So we check if any workflow pair using this schema is referenced by curations
        curation_count = db.execute(
            select(func.count(CurationNew.id))
            .join(WorkflowPair, CurationNew.workflow_pair_id == WorkflowPair.id)
            .where(
                or_(
                    WorkflowPair.precuration_schema_id == schema_id,
                    WorkflowPair.curation_schema_id == schema_id,
                )
            )
        ).scalar()

        return (
            (workflow_pair_count or 0) > 0
            or (precuration_count or 0) > 0
            or (curation_count or 0) > 0
        )

    def validate_schema_structure(
        self, schema_data: dict[str, Any]
    ) -> SchemaValidationResult:
        """
        Validate schema structure and configuration.

        Delegates to SchemaValidatorChain for complexity management.
        Complexity: 2 (delegation + result construction)

        Args:
            schema_data: The schema dictionary to validate

        Returns:
            SchemaValidationResult with validation outcome
        """
        # Delegate validation to schema_validators module
        errors, warnings = validate_schema_structure(schema_data)

        return SchemaValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            field_count=len(schema_data.get("field_definitions", {})),
            has_scoring=bool(schema_data.get("scoring_configuration")),
            has_validation=bool(schema_data.get("validation_rules")),
        )


class CRUDWorkflowPair(CRUDBase[WorkflowPair, WorkflowPairCreate, WorkflowPairUpdate]):
    """CRUD operations for workflow pairs."""

    def get_by_name_and_version(
        self, db: Session, *, name: str, version: str
    ) -> WorkflowPair | None:
        """Get workflow pair by name and version."""
        return (
            db.execute(
                select(WorkflowPair).where(
                    and_(WorkflowPair.name == name, WorkflowPair.version == version)
                )
            )
            .scalars()
            .first()
        )

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, active_only: bool = True
    ) -> Sequence[WorkflowPair]:
        """Get multiple workflow pairs with filtering."""
        stmt = select(WorkflowPair)

        if active_only:
            stmt = stmt.where(WorkflowPair.is_active)  # Fixed: use == instead of is

        return (
            db.execute(
                stmt.order_by(WorkflowPair.name, WorkflowPair.version.desc())
                .offset(skip)
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def create_with_owner(
        self, db: Session, *, obj_in: WorkflowPairCreate, owner_id: UUID
    ) -> WorkflowPair:
        """Create workflow pair with owner."""
        obj_in_data = obj_in.model_dump()
        obj_in_data["created_by"] = owner_id
        db_obj = WorkflowPair(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def is_workflow_pair_in_use(self, db: Session, *, workflow_pair_id: UUID) -> bool:
        """Check if workflow pair is currently in use."""
        # Check if any scopes are using this as default workflow pair
        from app.models import Scope

        scope_count = db.execute(
            select(func.count(Scope.id)).where(
                Scope.default_workflow_pair_id == workflow_pair_id
            )
        ).scalar()

        # Check if any precurations/curations are using schemas from this workflow pair
        workflow_pair = self.get(db, id=workflow_pair_id)
        if not workflow_pair:
            return False

        # Check precurations using the precuration_schema
        precuration_count = db.execute(
            select(func.count(PrecurationNew.id)).where(
                PrecurationNew.precuration_schema_id
                == workflow_pair.precuration_schema_id
            )
        ).scalar()

        # Check curations using this workflow_pair
        curation_count = db.execute(
            select(func.count(CurationNew.id)).where(
                CurationNew.workflow_pair_id == workflow_pair_id
            )
        ).scalar()

        return (
            (scope_count or 0) > 0
            or (precuration_count or 0) > 0
            or (curation_count or 0) > 0
        )

    def get_workflow_pairs_for_scope(
        self, db: Session, *, scope_id: UUID
    ) -> Sequence[WorkflowPair]:
        """Get workflow pairs available for a specific scope."""
        # For now, return all active workflow pairs
        # In the future, this could be filtered based on scope-specific criteria
        return self.get_multi(db, active_only=True)

    def get_usage_statistics(
        self, db: Session, *, workflow_pair_id: UUID
    ) -> dict[str, Any]:
        """Get usage statistics for a workflow pair."""
        workflow_pair = self.get(db, id=workflow_pair_id)
        if not workflow_pair:
            return {}

        # Count scopes using this as default
        from app.models import Scope

        scope_count = db.execute(
            select(func.count(Scope.id)).where(
                Scope.default_workflow_pair_id == workflow_pair_id
            )
        ).scalar()

        # Count active precurations and curations using the schemas
        precuration_count = db.execute(
            select(func.count(PrecurationNew.id)).where(
                PrecurationNew.precuration_schema_id
                == workflow_pair.precuration_schema_id
            )
        ).scalar()

        curation_count = db.execute(
            select(func.count(CurationNew.id)).where(
                CurationNew.workflow_pair_id == workflow_pair_id
            )
        ).scalar()

        return {
            "workflow_pair_id": workflow_pair_id,
            "scopes_using_as_default": scope_count or 0,
            "active_precurations": precuration_count or 0,
            "active_curations": curation_count or 0,
            "total_usage": (scope_count or 0)
            + (precuration_count or 0)
            + (curation_count or 0),
        }


# Create instances
schema_crud = CRUDCurationSchema(CurationSchema)
workflow_pair_crud = CRUDWorkflowPair(WorkflowPair)
