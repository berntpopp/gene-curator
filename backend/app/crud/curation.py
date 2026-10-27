"""
CRUD operations for curations.
Extends CRUDBase with curation-specific operations.
Follows patterns from gene_assignment.py.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.logging import get_logger
from app.crud.base import CRUDBase
from app.crud.optimistic_lock import update_if_version
from app.crud.workflow_engine import workflow_engine
from app.models import (
    CurationNew,
    CurationStatus,
    Gene,
    PrecurationNew,
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
    disease_fields,
)
from app.scoring.base import ScoringEngine
from app.scoring.clingen import ENGINE_NAME, ClinGenEngine
from app.scoring.point_limits import scoring_configuration
from app.scoring.registry import scoring_registry

logger = get_logger(__name__)


class OpenCurationExistsError(ValueError):
    """The gene already has an open (not active or archived) curation in the scope."""

    def __init__(self, curation_id: UUID) -> None:
        super().__init__("This gene already has an open curation in this scope")
        self.curation_id = curation_id


def open_curation_id(db: Session, gene_id: UUID, scope_id: UUID) -> UUID | None:
    """The gene's open (not active or archived) curation in the scope, if any."""
    return db.scalar(
        select(CurationNew.id).where(
            CurationNew.gene_id == gene_id,
            CurationNew.scope_id == scope_id,
            CurationNew.status.notin_([CurationStatus.ACTIVE, CurationStatus.ARCHIVED]),
        )
    )


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(UTC)


def get_disease_fields(
    evidence: dict[str, Any] | None, precuration_evidence: dict[str, Any] | None
) -> dict[str, Any]:
    """Prefer curation disease fields, falling back to the linked precuration."""
    return disease_fields(evidence, precuration_evidence)


def _engine(config: dict[str, Any]) -> ScoringEngine:
    """The engine the schema's scoring_configuration names; ClinGen when it names none."""
    name = str(config.get("engine") or ENGINE_NAME)
    # schema_rules rejects unknown engine names at publish time
    return scoring_registry.get_engine(name) or ClinGenEngine()


def _computed(
    db: Session, curation: CurationNew, evidence_data: dict[str, Any]
) -> dict[str, Any]:
    """Score with the row's pinned version (latest on create), persisted with the evidence."""
    config = scoring_configuration(
        db, curation.workflow_pair_id, curation.methodology_version_id
    )
    result = _engine(config).calculate_scores(evidence_data, config)
    return {
        "computed_scores": {**result.scores, **result.evidence_breakdown},
        "computed_verdict": result.verdict,
        "computed_summary": result.verdict_rationale,
    }


def _update_computed_scores(db: Session, curation: CurationNew) -> None:
    """Persist engine output in the same transaction as the evidence write."""
    for key, value in _computed(db, curation, curation.evidence_data).items():
        setattr(curation, key, value)


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
                joinedload(CurationNew.precuration),
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
        include_archived: bool = False,
        exclude_creator_id: UUID | None = None,
    ) -> tuple[list[CurationSummary], int]:
        """
        Get curation summaries with joined data for list views.
        Returns lightweight summaries (no evidence_data) for performance.
        Excludes archived curations by default unless include_archived=True.
        Reads persisted scoring-engine results.
        Gets disease_name from linked precuration if not in curation.
        """
        # Base query with joins (including precuration for disease_name)
        stmt = (
            select(
                CurationNew,
                Gene.approved_symbol.label("gene_symbol"),
                Scope.name.label("scope_name"),
                UserNew.name.label("curator_name"),
                PrecurationNew.evidence_data.label("precuration_evidence"),
            )
            .join(Gene, CurationNew.gene_id == Gene.id)
            .join(Scope, CurationNew.scope_id == Scope.id)
            .outerjoin(UserNew, CurationNew.created_by == UserNew.id)
            .outerjoin(PrecurationNew, CurationNew.precuration_id == PrecurationNew.id)
        )

        # Exclude archived curations by default
        if not include_archived:
            stmt = stmt.where(CurationNew.status != CurationStatus.ARCHIVED)

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
        if exclude_creator_id:
            stmt = stmt.where(CurationNew.created_by != exclude_creator_id)

        # Get total count (before pagination)
        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(CurationNew.id).subquery()
        )
        total = db.execute(count_stmt).scalar() or 0

        # Apply pagination and ordering
        stmt = stmt.offset(skip).limit(limit).order_by(CurationNew.updated_at.desc())

        results = db.execute(stmt).all()

        # Map persisted engine scores to the list response.
        summaries = []
        for row in results:
            scores = row.CurationNew.computed_scores or {}
            verdict = row.CurationNew.computed_verdict

            disease = get_disease_fields(
                row.CurationNew.evidence_data, row.precuration_evidence
            )

            summaries.append(
                CurationSummary(
                    id=row.CurationNew.id,
                    gene_id=row.CurationNew.gene_id,
                    gene_symbol=row.gene_symbol,
                    scope_id=row.CurationNew.scope_id,
                    scope_name=row.scope_name,
                    status=row.CurationNew.status,
                    workflow_stage=row.CurationNew.workflow_stage,
                    computed_verdict=(
                        "No Known Disease Relationship"
                        if verdict == "no_known"
                        else verdict.title()
                        if verdict
                        else None
                    ),
                    computed_scores={
                        "total_score": scores.get("total_score", 0.0),
                        "genetic_score": scores.get("genetic_evidence_total", 0.0),
                        "experimental_score": scores.get(
                            "experimental_evidence_total", 0.0
                        ),
                    },
                    disease_name=disease["disease_name"],
                    is_draft=row.CurationNew.is_draft,
                    created_at=row.CurationNew.created_at,
                    updated_at=row.CurationNew.updated_at,
                    curator_name=row.curator_name,
                    created_by=row.CurationNew.created_by,
                )
            )

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

        # One open curation per gene and scope (approval already created a draft, #398)
        open_id = open_curation_id(db, obj_in.gene_id, obj_in.scope_id)
        if open_id:
            raise OpenCurationExistsError(open_id)

        # 4-eyes: curation needs an approved precuration, unless it re-curates an active one
        approved = select(PrecurationNew.id).where(
            PrecurationNew.gene_id == obj_in.gene_id,
            PrecurationNew.scope_id == obj_in.scope_id,
            PrecurationNew.status == CurationStatus.APPROVED,
        )
        if obj_in.precuration_id:
            allowed = db.scalar(
                approved.where(PrecurationNew.id == obj_in.precuration_id)
            )
        else:
            active = select(CurationNew.id).where(
                CurationNew.gene_id == obj_in.gene_id,
                CurationNew.scope_id == obj_in.scope_id,
                CurationNew.status == CurationStatus.ACTIVE,
            )
            allowed = db.scalar(approved.limit(1)) or db.scalar(active.limit(1))
        if not allowed:
            raise ValueError(
                "An approved precuration for this gene and scope is required"
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
        _update_computed_scores(db, db_obj)
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
        values: dict[str, Any] = {"updated_by": user_id, "updated_at": _utc_now()}
        if obj_in.evidence_data is not None:
            values["evidence_data"] = obj_in.evidence_data
            values.update(_computed(db, db_obj, obj_in.evidence_data))
        if not update_if_version(
            db, CurationNew, db_obj.id, obj_in.lock_version, values
        ):
            logger.warning(
                "Optimistic lock conflict",
                curation_id=str(db_obj.id),
                requested_version=obj_in.lock_version,
            )
            return None
        db.refresh(db_obj)
        return db_obj

    def save_draft(
        self,
        db: Session,
        *,
        db_obj: CurationNew,
        draft_data: CurationDraftSave,
        user_id: UUID,
    ) -> CurationNew | None:
        """Save curation as draft with auto-save timestamp. None if lock_version is stale."""
        values = {
            "evidence_data": draft_data.evidence_data,
            **_computed(db, db_obj, draft_data.evidence_data),
            "is_draft": True,
            "auto_saved_at": _utc_now(),
            "updated_by": user_id,
        }
        if not update_if_version(
            db, CurationNew, db_obj.id, draft_data.lock_version, values
        ):
            return None
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

        workflow_engine.execute_transition(
            db,
            db_obj.id,
            "curation",
            WorkflowStage.REVIEW,
            user_id,
            submit_data.notes,
            expected_version=submit_data.lock_version,
        )
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
        Preview the score without modifying the curation or committing the session.
        Accepts scoring engine via DI for testability.
        """
        config = scoring_configuration(
            db, db_obj.workflow_pair_id, db_obj.methodology_version_id
        )
        result = (scoring_engine or _engine(config)).calculate_scores(
            evidence_data=db_obj.evidence_data,
            schema_config=config,
            scope_context=None,
        )

        # Extract genetic and experimental scores from the scores dict
        genetic_score = result.scores.get("genetic_evidence_total", 0.0)
        experimental_score = result.scores.get("experimental_evidence_total", 0.0)

        return CurationScoreResponse(
            curation_id=db_obj.id,
            total_score=result.total_score,
            classification=result.verdict,
            genetic_score=genetic_score,
            experimental_score=experimental_score,
            breakdown=result.evidence_breakdown,
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
        db_obj.workflow_stage = WorkflowStage.ARCHIVED
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
