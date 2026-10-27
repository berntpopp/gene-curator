"""
CRUD operations for schema repository management.
"""

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.crud.base import CRUDBase
from app.crud.schema_validators import validate_schema_structure
from app.models import (
    CurationNew,
    CurationSchema,
    CurationStatus,
    PrecurationNew,
    WorkflowPair,
)
from app.models.methodology import MethodologyVersion
from app.schemas.schema_repository import (
    CurationSchemaCreate,
    CurationSchemaUpdate,
    SchemaValidationResult,
    WorkflowPairCreate,
    WorkflowPairUpdate,
)
from app.scoring.base import ScoringResult
from app.scoring.registry import engine_for

logger = get_logger(__name__)


def _schema_content_hash(schema_data: dict[str, Any]) -> str:
    """SHA-256 checksum over the schema definition (stable key order)."""
    definition = {
        key: schema_data.get(key)
        for key in (
            "name",
            "version",
            "field_definitions",
            "validation_rules",
            "workflow_states",
            "ui_configuration",
            "scoring_configuration",
        )
    }
    return hashlib.sha256(
        json.dumps(definition, sort_keys=True, default=str).encode()
    ).hexdigest()


# Same keys as methodology_snapshot() in database/sql/042_methodology_versions.sql
SNAPSHOT_KEYS = (
    "field_definitions",
    "validation_rules",
    "scoring_configuration",
    "workflow_states",
    "ui_configuration",
)


def _score(evidence: Any, config: Any) -> ScoringResult:
    """Score like a curation save does (crud/curation.py `_computed`)."""
    config = config if isinstance(config, dict) else {}
    return engine_for(config).calculate_scores(
        evidence if isinstance(evidence, dict) else {}, config
    )


def publish_errors(definition: dict[str, Any]) -> list[str]:
    """Why `definition` cannot be published: static checks, then the version tests."""
    errors, _ = validate_schema_structure(definition)
    # tests only run on a valid definition; a malformed point model cannot score
    return errors or _test_failures(definition.get("scoring_configuration"))


def _test_failures(config: Any) -> list[str]:
    """`scoring_configuration.tests`: [{name, evidence_data, expect: {total?, class?}}]."""
    tests = config.get("tests", []) if isinstance(config, dict) else []
    if not isinstance(tests, list):
        return ["scoring_configuration.tests: must be a list"]
    out: list[str] = []
    for i, test in enumerate(tests):
        label = f"scoring_configuration.tests[{i}]"
        if not (
            isinstance(test, dict)
            and isinstance(test.get("evidence_data"), dict)
            and isinstance(test.get("expect"), dict)
        ):
            out.append(f"{label}: needs evidence_data and expect objects")
            continue
        label += f" ({test.get('name', '')})"
        try:
            result = _score(test["evidence_data"], config)
        except Exception as exc:  # user-written evidence must not turn into a 500
            out.append(f"{label}: scoring failed: {exc}")
            continue
        got = {"total": result.total_score, "class": result.verdict}
        out += [
            f"{label}: expected {key} {want!r}, got {got.get(key)!r}"
            for key, want in test["expect"].items()
            if got.get(key) != want
        ]
    return out


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
        # schema_hash is NOT NULL in the database and not supplied by clients
        if not obj_in_data.get("schema_hash"):
            obj_in_data["schema_hash"] = _schema_content_hash(obj_in_data)
        db_obj = CurationSchema(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def list_versions(
        self, db: Session, *, schema_id: UUID
    ) -> Sequence[MethodologyVersion]:
        """Methodology versions of a schema, newest first."""
        return db.scalars(
            select(MethodologyVersion)
            .where(MethodologyVersion.schema_id == schema_id)
            .order_by(MethodologyVersion.version.desc())
        ).all()

    def publish_version(
        self, db: Session, *, schema: CurationSchema, user_id: UUID
    ) -> MethodologyVersion:
        """Publish the schema's current content as its next, immutable version."""
        # Lock the schema row so concurrent publishes serialize on the next number
        db.execute(
            select(CurationSchema.id)
            .where(CurationSchema.id == schema.id)
            .with_for_update()
        )
        latest = db.scalar(
            select(func.max(MethodologyVersion.version)).where(
                MethodologyVersion.schema_id == schema.id
            )
        )
        version = MethodologyVersion(
            schema_id=schema.id,
            version=(latest or 0) + 1,
            snapshot={key: getattr(schema, key) for key in SNAPSHOT_KEYS},
            published_at=datetime.now(UTC),
            created_by=user_id,
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        return version

    def version_impact(
        self, db: Session, *, target: MethodologyVersion
    ) -> list[dict[str, Any]]:
        """Curations pinned to an older version of the schema whose total or class would
        change when re-scored with `target`. Read-only; RLS limits it to visible rows."""
        rows = db.execute(
            select(CurationNew, MethodologyVersion.version, MethodologyVersion.snapshot)
            .join(
                MethodologyVersion,
                CurationNew.methodology_version_id == MethodologyVersion.id,
            )
            .where(
                MethodologyVersion.schema_id == target.schema_id,
                MethodologyVersion.version < target.version,
                CurationNew.status != CurationStatus.ARCHIVED,
            )
            .order_by(CurationNew.created_at, CurationNew.id)
        ).all()
        new_config = target.snapshot.get("scoring_configuration")
        out = []
        for curation, version, snapshot in rows:
            try:
                old = _score(
                    curation.evidence_data, snapshot.get("scoring_configuration")
                )
                new = _score(curation.evidence_data, new_config)
            except Exception as exc:  # a pre-gate malformed pin must not fail the list
                logger.warning(
                    "Impact skipped curation",
                    curation_id=str(curation.id),
                    from_version=version,
                    error=str(exc),
                )
                continue
            if (old.total_score, old.verdict) != (new.total_score, new.verdict):
                out.append(
                    {
                        "curation_id": curation.id,
                        "gene_id": curation.gene_id,
                        "scope_id": curation.scope_id,
                        "from_version": version,
                        "old_total": old.total_score,
                        "old_class": old.verdict,
                        "new_total": new.total_score,
                        "new_class": new.verdict,
                    }
                )
        return out

    def derive(
        self,
        db: Session,
        *,
        source: MethodologyVersion,
        name: str,
        version: str,
        user_id: UUID,
    ) -> CurationSchema:
        """Copy a version's snapshot into a new inactive schema whose v1 points back at it."""
        parent = db.get(CurationSchema, source.schema_id)
        assert parent is not None  # versions cascade-delete with their schema
        data: dict[str, Any] = {
            **{key: source.snapshot.get(key) for key in SNAPSHOT_KEYS},
            "name": name,
            "version": version,
        }
        schema = CurationSchema(
            **data,
            schema_type=parent.schema_type,
            institution=parent.institution,
            description=parent.description,
            use_dynamic_form=parent.use_dynamic_form,
            is_active=False,
            created_by=user_id,
            schema_hash=_schema_content_hash(data),
        )
        if db.get_bind().dialect.name == "postgresql":
            # read by the 044 trigger that publishes v1; transaction-local
            db.execute(
                text("SELECT set_config('app.derived_from_version_id', :v, true)"),
                {"v": str(source.id)},
            )
            db.add(schema)
        else:  # SQLite has no trigger: publish v1 here
            db.add(schema)
            db.flush()
            db.add(
                MethodologyVersion(
                    schema_id=schema.id,
                    version=1,
                    snapshot=dict(source.snapshot),
                    published_at=datetime.now(UTC),
                    created_by=user_id,
                    derived_from_version_id=source.id,
                )
            )
        db.commit()
        db.refresh(schema)
        return schema

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
