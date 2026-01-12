"""
CRUD operations for curations.
Extends CRUDBase with curation-specific operations.
Follows patterns from gene_assignment.py.
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
    CurationStatus,
    Gene,
    Scope,
    UserNew,
    WorkflowPair,
    WorkflowStage,
)
from app.schemas.curation import (
    CurationCreate,
    CurationDraftSave,
    CurationScoreResponse,
    CurationSubmit,
    CurationSummary,
    CurationUpdate,
)

logger = get_logger(__name__)


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class CRUDCuration(CRUDBase[CurationNew, CurationCreate, CurationUpdate]):
    """
    CRUD operations for curations with workflow integration.

    Extends base CRUD with:
    - Scope-based filtering
    - Optimistic locking
    - Workflow state management
    - Score calculation (via dependency injection)
    """

    # ========================================
    # READ OPERATIONS
    # ========================================

    def get_with_relations(self, db: Session, id: UUID) -> CurationNew | None:
        """Get curation with eager-loaded relationships."""
        stmt = (
            select(CurationNew)
            .options(
                joinedload(CurationNew.gene),
                joinedload(CurationNew.scope),
                joinedload(CurationNew.creator),
            )
            .where(CurationNew.id == id)
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
    ) -> list[CurationNew]:
        """Get curations filtered by scope."""
        stmt = select(CurationNew).where(CurationNew.scope_id == scope_id)

        if status:
            stmt = stmt.where(CurationNew.status == status)
        if not include_drafts:
            stmt = stmt.where(CurationNew.is_draft == False)  # noqa: E712

        stmt = stmt.offset(skip).limit(limit).order_by(CurationNew.updated_at.desc())
        return list(db.execute(stmt).scalars().all())

    def get_by_gene_and_scope(
        self,
        db: Session,
        gene_id: UUID,
        scope_id: UUID,
    ) -> list[CurationNew]:
        """Get all curations for a gene within a scope."""
        stmt = (
            select(CurationNew)
            .where(
                CurationNew.gene_id == gene_id,
                CurationNew.scope_id == scope_id,
            )
            .order_by(CurationNew.created_at.desc())
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
        curator_id: UUID | None = None,
    ) -> tuple[list[CurationSummary], int]:
        """
        Get curation summaries with joined data for list views.
        Returns lightweight summaries (no evidence_data) for performance.
        """
        # Base query with joins
        stmt = (
            select(
                CurationNew,
                Gene.approved_symbol.label("gene_symbol"),
                Scope.name.label("scope_name"),
                UserNew.name.label("curator_name"),
            )
            .join(Gene, CurationNew.gene_id == Gene.id)
            .join(Scope, CurationNew.scope_id == Scope.id)
            .outerjoin(UserNew, CurationNew.created_by == UserNew.id)
        )

        # Apply filters
        if scope_id:
            stmt = stmt.where(CurationNew.scope_id == scope_id)
        if scope_ids:
            stmt = stmt.where(CurationNew.scope_id.in_(scope_ids))
        if gene_id:
            stmt = stmt.where(CurationNew.gene_id == gene_id)
        if status:
            stmt = stmt.where(CurationNew.status == status)
        if curator_id:
            stmt = stmt.where(CurationNew.created_by == curator_id)

        # Get total count (before pagination)
        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(CurationNew.id).subquery()
        )
        total = db.execute(count_stmt).scalar() or 0

        # Apply pagination and ordering
        stmt = stmt.offset(skip).limit(limit).order_by(CurationNew.updated_at.desc())

        results = db.execute(stmt).all()

        # Map to summary schema
        summaries = [
            CurationSummary(
                id=row.CurationNew.id,
                gene_id=row.CurationNew.gene_id,
                gene_symbol=row.gene_symbol,
                scope_id=row.CurationNew.scope_id,
                scope_name=row.scope_name,
                status=row.CurationNew.status,
                workflow_stage=row.CurationNew.workflow_stage,
                computed_verdict=row.CurationNew.computed_verdict,
                is_draft=row.CurationNew.is_draft,
                created_at=row.CurationNew.created_at,
                updated_at=row.CurationNew.updated_at,
                curator_name=row.curator_name,
            )
            for row in results
        ]

        return summaries, total

    # ========================================
    # WRITE OPERATIONS (with FK validation)
    # ========================================

    def create_curation(
        self,
        db: Session,
        *,
        obj_in: CurationCreate,
        user_id: UUID,
    ) -> CurationNew:
        """Create a new curation with proper initialization and FK validation."""
        # Validate foreign keys exist (prevents orphaned records)
        gene = db.get(Gene, obj_in.gene_id)
        if not gene:
            raise ValueError(f"Gene with id {obj_in.gene_id} not found")

        scope = db.get(Scope, obj_in.scope_id)
        if not scope:
            raise ValueError(f"Scope with id {obj_in.scope_id} not found")

        workflow_pair = db.get(WorkflowPair, obj_in.workflow_pair_id)
        if not workflow_pair:
            raise ValueError(
                f"WorkflowPair with id {obj_in.workflow_pair_id} not found"
            )

        # Create curation
        now = _utc_now()
        db_obj = CurationNew(
            gene_id=obj_in.gene_id,
            scope_id=obj_in.scope_id,
            workflow_pair_id=obj_in.workflow_pair_id,
            precuration_id=obj_in.precuration_id,
            evidence_data=obj_in.evidence_data,
            status=CurationStatus.DRAFT,
            workflow_stage=WorkflowStage.CURATION,
            is_draft=True,
            lock_version=0,
            created_by=user_id,
            updated_by=user_id,
            created_at=now,
            updated_at=now,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        logger.info(
            "Curation created",
            curation_id=str(db_obj.id),
            gene_id=str(obj_in.gene_id),
            scope_id=str(obj_in.scope_id),
            user_id=str(user_id),
        )

        return db_obj

    def update_with_lock(
        self,
        db: Session,
        *,
        db_obj: CurationNew,
        obj_in: CurationUpdate,
        user_id: UUID,
    ) -> CurationNew | None:
        """
        Update curation with optimistic locking.
        Returns None if lock_version doesn't match (conflict).
        """
        # Check lock version
        if db_obj.lock_version != obj_in.lock_version:
            logger.warning(
                "Optimistic lock conflict",
                curation_id=str(db_obj.id),
                current_version=db_obj.lock_version,
                requested_version=obj_in.lock_version,
            )
            return None

        # Update fields
        if obj_in.evidence_data is not None:
            db_obj.evidence_data = obj_in.evidence_data

        db_obj.lock_version += 1
        db_obj.updated_by = user_id
        db_obj.updated_at = _utc_now()

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def save_draft(
        self,
        db: Session,
        *,
        db_obj: CurationNew,
        draft_data: CurationDraftSave,
        user_id: UUID,
    ) -> CurationNew:
        """Save curation as draft with auto-save timestamp."""
        db_obj.evidence_data = draft_data.evidence_data
        db_obj.is_draft = True
        db_obj.auto_saved_at = _utc_now()
        db_obj.updated_by = user_id

        # Only increment lock_version if provided and matches
        if (
            draft_data.lock_version is not None
            and db_obj.lock_version == draft_data.lock_version
        ):
            db_obj.lock_version += 1

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def submit_for_review(
        self,
        db: Session,
        *,
        db_obj: CurationNew,
        submit_data: CurationSubmit,
        user_id: UUID,
    ) -> CurationNew | None:
        """Submit curation for review via workflow engine."""
        # Check lock version
        if db_obj.lock_version != submit_data.lock_version:
            return None

        # Validate transition
        validation = workflow_engine.validate_transition(
            db,
            db_obj.workflow_stage,
            WorkflowStage.REVIEW,
            user_id,
            db_obj.id,
            "curation",
        )

        if not validation.is_valid:
            raise ValueError(f"Invalid transition: {', '.join(validation.errors)}")

        # Execute transition
        workflow_engine.execute_transition(
            db,
            db_obj.id,
            "curation",
            WorkflowStage.REVIEW,
            user_id,
            submit_data.notes,
        )

        # Update curation status
        now = _utc_now()
        db_obj.status = CurationStatus.SUBMITTED
        db_obj.is_draft = False
        db_obj.submitted_at = now
        db_obj.submitted_by = user_id
        db_obj.lock_version += 1

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    # ========================================
    # SCORE CALCULATION (Dependency Injection)
    # ========================================

    def calculate_score(
        self,
        db: Session,
        db_obj: CurationNew,
        scoring_engine: Any = None,
    ) -> CurationScoreResponse:
        """
        Calculate score for curation.
        Accepts scoring engine via DI for testability.
        """
        # Lazy import to avoid circular dependency
        if scoring_engine is None:
            from app.scoring.clingen import ClinGenEngine

            scoring_engine = ClinGenEngine()

        # Calculate score
        result = scoring_engine.calculate_score(db_obj.evidence_data)

        # Update computed fields
        db_obj.computed_scores = result.get("breakdown", {})
        db_obj.computed_verdict = result.get("classification")
        db_obj.computed_summary = result.get("summary")

        db.add(db_obj)
        db.commit()

        return CurationScoreResponse(
            curation_id=db_obj.id,
            total_score=result.get("total_score", 0.0),
            classification=result.get("classification", "No Known"),
            genetic_score=result.get("genetic_total", 0.0),
            experimental_score=result.get("experimental_total", 0.0),
            breakdown=result.get("breakdown", {}),
            calculated_at=_utc_now(),
        )

    # ========================================
    # SOFT DELETE
    # ========================================

    def soft_delete(
        self,
        db: Session,
        *,
        db_obj: CurationNew,
        user_id: UUID,
    ) -> CurationNew:
        """Soft delete by setting status to archived."""
        db_obj.status = CurationStatus.ARCHIVED
        db_obj.updated_by = user_id
        db_obj.updated_at = _utc_now()

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        logger.info(
            "Curation archived",
            curation_id=str(db_obj.id),
            user_id=str(user_id),
        )

        return db_obj


# Singleton instance
curation_crud = CRUDCuration(CurationNew)
