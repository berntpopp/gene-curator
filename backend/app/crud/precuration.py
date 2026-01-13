"""
CRUD operations for precurations.
Extends CRUDBase with precuration-specific operations.
Follows patterns from curation.py.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.logging import get_logger
from app.crud.base import CRUDBase
from app.crud.workflow_engine import workflow_engine
from app.models import (
    CurationNew,
    CurationSchema,
    CurationStatus,
    Gene,
    PrecurationNew,
    Scope,
    UserNew,
    WorkflowPair,
    WorkflowStage,
)
from app.schemas.precuration import (
    PrecurationApprovalResult,
    PrecurationCreate,
    PrecurationSubmit,
    PrecurationSummary,
    PrecurationUpdate,
)

logger = get_logger(__name__)


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class CRUDPrecuration(CRUDBase[PrecurationNew, PrecurationCreate, PrecurationUpdate]):
    """
    CRUD operations for precurations with workflow integration.

    Extends base CRUD with:
    - ClinGen SOP v11 validation
    - Scope-based filtering
    - Workflow state management
    - Precuration-to-curation data mapping
    """

    # ========================================
    # READ OPERATIONS
    # ========================================

    def get_with_relations(self, db: Session, id: UUID) -> PrecurationNew | None:
        """Get precuration with eager-loaded relationships."""
        stmt = (
            select(PrecurationNew)
            .options(
                joinedload(PrecurationNew.gene),
                joinedload(PrecurationNew.scope),
                joinedload(PrecurationNew.creator),
                joinedload(PrecurationNew.precuration_schema),
            )
            .where(PrecurationNew.id == id)
        )
        return db.execute(stmt).scalars().first()

    def get_by_scope(
        self,
        db: Session,
        scope_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
        status: CurationStatus | None = None,
        include_drafts: bool = True,
    ) -> list[PrecurationNew]:
        """Get precurations filtered by scope."""
        stmt = select(PrecurationNew).where(PrecurationNew.scope_id == scope_id)

        if status:
            stmt = stmt.where(PrecurationNew.status == status)
        if not include_drafts:
            stmt = stmt.where(PrecurationNew.is_draft == False)  # noqa: E712

        stmt = stmt.offset(skip).limit(limit).order_by(PrecurationNew.updated_at.desc())
        return list(db.execute(stmt).scalars().all())

    def get_by_gene_and_scope(
        self,
        db: Session,
        gene_id: UUID,
        scope_id: UUID,
    ) -> list[PrecurationNew]:
        """Get all precurations for a gene within a scope."""
        stmt = (
            select(PrecurationNew)
            .where(
                PrecurationNew.gene_id == gene_id,
                PrecurationNew.scope_id == scope_id,
            )
            .order_by(PrecurationNew.created_at.desc())
        )
        return list(db.execute(stmt).scalars().all())

    def get_multi_filtered(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        scope_id: UUID | None = None,
        scope_ids: list[UUID] | None = None,
        gene_id: UUID | None = None,
        status: CurationStatus | None = None,
    ) -> tuple[list[PrecurationSummary], int]:
        """
        Get precuration summaries with joined data for list views.
        Returns lightweight summaries (no evidence_data) for performance.
        """
        # Base query with joins
        stmt = (
            select(
                PrecurationNew,
                Gene.approved_symbol.label("gene_symbol"),
                Scope.name.label("scope_name"),
                UserNew.name.label("curator_name"),
            )
            .join(Gene, PrecurationNew.gene_id == Gene.id)
            .join(Scope, PrecurationNew.scope_id == Scope.id)
            .outerjoin(UserNew, PrecurationNew.created_by == UserNew.id)
        )

        # Apply filters
        if scope_id:
            stmt = stmt.where(PrecurationNew.scope_id == scope_id)
        if scope_ids:
            stmt = stmt.where(PrecurationNew.scope_id.in_(scope_ids))
        if gene_id:
            stmt = stmt.where(PrecurationNew.gene_id == gene_id)
        if status:
            stmt = stmt.where(PrecurationNew.status == status)

        # Get total count (before pagination)
        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(PrecurationNew.id).subquery()
        )
        total = db.execute(count_stmt).scalar() or 0

        # Apply pagination and ordering
        stmt = stmt.offset(skip).limit(limit).order_by(PrecurationNew.updated_at.desc())

        results = db.execute(stmt).all()

        # Map to summary schema - extract Mondo ID and MOI from evidence_data
        summaries = [
            PrecurationSummary(
                id=row.PrecurationNew.id,
                gene_id=row.PrecurationNew.gene_id,
                gene_symbol=row.gene_symbol,
                scope_id=row.PrecurationNew.scope_id,
                scope_name=row.scope_name,
                status=row.PrecurationNew.status,
                workflow_stage=row.PrecurationNew.workflow_stage,
                mondo_id=row.PrecurationNew.evidence_data.get("mondo_id"),
                disease_name=row.PrecurationNew.evidence_data.get("disease_name"),
                mode_of_inheritance=row.PrecurationNew.evidence_data.get(
                    "mode_of_inheritance"
                ),
                is_draft=row.PrecurationNew.is_draft,
                created_at=row.PrecurationNew.created_at,
                updated_at=row.PrecurationNew.updated_at,
                curator_name=row.curator_name,
            )
            for row in results
        ]

        return summaries, total

    # ========================================
    # WRITE OPERATIONS (with FK validation)
    # ========================================

    def create_precuration(
        self,
        db: Session,
        *,
        obj_in: PrecurationCreate,
        user_id: UUID,
    ) -> PrecurationNew:
        """Create a new precuration with proper initialization and FK validation."""
        # Validate foreign keys exist
        gene = db.get(Gene, obj_in.gene_id)
        if not gene:
            raise ValueError(f"Gene with id {obj_in.gene_id} not found")

        scope = db.get(Scope, obj_in.scope_id)
        if not scope:
            raise ValueError(f"Scope with id {obj_in.scope_id} not found")

        precuration_schema = db.get(CurationSchema, obj_in.precuration_schema_id)
        if not precuration_schema:
            raise ValueError(
                f"CurationSchema with id {obj_in.precuration_schema_id} not found"
            )

        # Create precuration
        now = _utc_now()
        db_obj = PrecurationNew(
            gene_id=obj_in.gene_id,
            scope_id=obj_in.scope_id,
            precuration_schema_id=obj_in.precuration_schema_id,
            evidence_data=obj_in.evidence_data,
            status=CurationStatus.DRAFT,
            workflow_stage=WorkflowStage.PRECURATION,
            is_draft=True,
            created_by=user_id,
            updated_by=user_id,
            created_at=now,
            updated_at=now,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        logger.info(
            "Precuration created",
            precuration_id=str(db_obj.id),
            gene_id=str(obj_in.gene_id),
            scope_id=str(obj_in.scope_id),
            user_id=str(user_id),
        )

        return db_obj

    def save_draft(
        self,
        db: Session,
        *,
        db_obj: PrecurationNew,
        evidence_data: dict[str, Any],
        user_id: UUID,
    ) -> PrecurationNew:
        """Save precuration as draft with auto-save timestamp."""
        db_obj.evidence_data = evidence_data
        db_obj.is_draft = True
        db_obj.auto_saved_at = _utc_now()
        db_obj.updated_by = user_id

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def submit_for_review(
        self,
        db: Session,
        *,
        db_obj: PrecurationNew,
        submit_data: PrecurationSubmit,
        user_id: UUID,
    ) -> PrecurationNew:
        """Submit precuration for review via workflow engine."""
        # Validate transition
        validation = workflow_engine.validate_transition(
            db,
            db_obj.workflow_stage,
            WorkflowStage.REVIEW,
            user_id,
            db_obj.id,
            "precuration",
        )

        if not validation.is_valid:
            raise ValueError(f"Invalid transition: {', '.join(validation.errors)}")

        # Execute transition
        workflow_engine.execute_transition(
            db,
            db_obj.id,
            "precuration",
            WorkflowStage.REVIEW,
            user_id,
            submit_data.notes,
        )

        # Update precuration status
        db_obj.status = CurationStatus.SUBMITTED
        db_obj.workflow_stage = WorkflowStage.REVIEW
        db_obj.is_draft = False
        db_obj.updated_by = user_id
        db_obj.updated_at = _utc_now()

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def approve_and_create_curation(
        self,
        db: Session,
        *,
        db_obj: PrecurationNew,
        approver_id: UUID,
        create_curation: bool = True,
    ) -> PrecurationApprovalResult:
        """
        Approve a precuration and optionally create a linked curation.

        Implements ClinGen SOP v11 workflow:
        1. Precuration approved after review
        2. New curation auto-created with prefilled data
        3. Curation linked to precuration via precuration_id
        """
        # Validate can be approved
        if db_obj.status not in [CurationStatus.SUBMITTED, CurationStatus.IN_REVIEW]:
            raise ValueError("Precuration must be submitted or in review to approve")

        # Update precuration status
        db_obj.status = CurationStatus.APPROVED
        db_obj.workflow_stage = WorkflowStage.CURATION
        db_obj.updated_by = approver_id
        db_obj.updated_at = _utc_now()

        curation = None
        if create_curation:
            # Get workflow pair for data mapping
            workflow_pair = self._get_workflow_pair_for_precuration(db, db_obj)

            if workflow_pair:
                # Create curation with prefilled data
                curation = CurationNew(
                    gene_id=db_obj.gene_id,
                    scope_id=db_obj.scope_id,
                    workflow_pair_id=workflow_pair.id,
                    precuration_id=db_obj.id,  # Link to precuration
                    status=CurationStatus.DRAFT,
                    workflow_stage=WorkflowStage.CURATION,
                    is_draft=True,
                    evidence_data=self._prefill_curation_data(
                        db_obj.evidence_data, workflow_pair.data_mapping or {}
                    ),
                    lock_version=0,
                    created_by=approver_id,
                    updated_by=approver_id,
                    created_at=_utc_now(),
                    updated_at=_utc_now(),
                )
                db.add(curation)

        db.add(db_obj)
        db.commit()
        if curation:
            db.refresh(curation)
        db.refresh(db_obj)

        logger.info(
            "Precuration approved",
            precuration_id=str(db_obj.id),
            curation_created=curation is not None,
            curation_id=str(curation.id) if curation else None,
            approver_id=str(approver_id),
        )

        return PrecurationApprovalResult(
            precuration_id=db_obj.id,
            approved=True,
            curation_created=curation is not None,
            curation_id=curation.id if curation else None,
            message="Precuration approved"
            + (f" and curation {curation.id} created" if curation else ""),
        )

    def reject(
        self,
        db: Session,
        *,
        db_obj: PrecurationNew,
        user_id: UUID,
        reason: str,
    ) -> PrecurationNew:
        """Reject precuration with reason."""
        db_obj.status = CurationStatus.REJECTED
        db_obj.workflow_stage = WorkflowStage.PRECURATION
        db_obj.updated_by = user_id
        db_obj.updated_at = _utc_now()
        # Store rejection reason in computed_fields
        db_obj.computed_fields = {
            **(db_obj.computed_fields or {}),
            "rejection_reason": reason,
            "rejected_at": _utc_now().isoformat(),
            "rejected_by": str(user_id),
        }

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        logger.info(
            "Precuration rejected",
            precuration_id=str(db_obj.id),
            user_id=str(user_id),
            reason=reason,
        )

        return db_obj

    def soft_delete(
        self,
        db: Session,
        *,
        db_obj: PrecurationNew,
        user_id: UUID,
    ) -> PrecurationNew:
        """Soft delete by setting status to archived."""
        db_obj.status = CurationStatus.ARCHIVED
        db_obj.updated_by = user_id
        db_obj.updated_at = _utc_now()

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        logger.info(
            "Precuration archived",
            precuration_id=str(db_obj.id),
            user_id=str(user_id),
        )

        return db_obj

    # ========================================
    # HELPER METHODS
    # ========================================

    def _get_workflow_pair_for_precuration(
        self, db: Session, precuration: PrecurationNew
    ) -> WorkflowPair | None:
        """Get workflow pair that uses this precuration's schema."""
        stmt = select(WorkflowPair).where(
            WorkflowPair.precuration_schema_id == precuration.precuration_schema_id,
            WorkflowPair.is_active == True,  # noqa: E712
        )
        return db.execute(stmt).scalars().first()

    def _prefill_curation_data(
        self,
        precuration_data: dict[str, Any],
        data_mapping: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply data mapping to prefill curation evidence from precuration."""
        curation_data: dict[str, Any] = {}
        mapping = data_mapping.get("precuration_to_curation", {})

        for source_field, target_path in mapping.items():
            if source_field in precuration_data:
                # Handle nested target paths (e.g., "entity_definition.mondo_id")
                parts = target_path.split(".")
                current = curation_data
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = precuration_data[source_field]

        return curation_data


# Singleton instance
precuration_crud = CRUDPrecuration(PrecurationNew)
