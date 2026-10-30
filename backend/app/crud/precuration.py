"""
CRUD operations for precurations.
Extends CRUDBase with precuration-specific operations.
Follows patterns from curation.py.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.logging import get_logger
from app.crud.base import CRUDBase
from app.crud.curation import OpenCurationExistsError, _patched, open_curation_id
from app.crud.optimistic_lock import claim_version
from app.crud.precuration_entity import conflict, entity_key_of, open_draft, write_draft
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
from app.schemas.curation import EvidenceWarning, disease_fields
from app.schemas.precuration import (
    PrecurationApprovalResult,
    PrecurationCreate,
    PrecurationSubmit,
    PrecurationSummary,
    PrecurationUpdate,
)
from app.services.evidence_ids import check_ids
from app.services.review_assignment import submit_reviewer
from app.services.review_guards import check_review_content

logger = get_logger(__name__)


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(UTC)


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

    def get_approved_for_gene_scope(
        self,
        db: Session,
        gene_id: UUID,
        scope_id: UUID,
    ) -> PrecurationNew | None:
        """Get the approved precuration for a gene within a scope."""
        stmt = (
            select(PrecurationNew)
            .where(
                PrecurationNew.gene_id == gene_id,
                PrecurationNew.scope_id == scope_id,
                PrecurationNew.status == "approved",
            )
            .order_by(PrecurationNew.updated_at.desc())
        )
        return db.execute(stmt).scalars().first()

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
        exclude_creator_id: UUID | None = None,
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
        if exclude_creator_id:
            stmt = stmt.where(PrecurationNew.created_by != exclude_creator_id)

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
                **disease_fields(row.PrecurationNew.evidence_data, None),
                is_draft=row.PrecurationNew.is_draft,
                created_at=row.PrecurationNew.created_at,
                updated_at=row.PrecurationNew.updated_at,
                curator_name=row.curator_name,
                created_by=row.PrecurationNew.created_by,
                lock_version=row.PrecurationNew.lock_version,
            )
            for row in results
        ]

        return summaries, total

    # ========================================
    # WRITE OPERATIONS (with FK validation)
    # ========================================

    def get_open_draft(
        self,
        db: Session,
        *,
        gene_id: UUID,
        scope_id: UUID,
        user_id: UUID,
        entity_key: str = "",
    ) -> PrecurationNew | None:
        """The creator's draft for this gene, scope and disease entity ('' = none yet)."""
        return open_draft(db, gene_id, scope_id, user_id, entity_key)

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
            scope_id=scope.id,
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
        key = entity_key_of(db, obj_in.evidence_data)  # before add: no autoflush
        db.add(db_obj)
        try:
            db.commit()
        except IntegrityError:
            # The author already has a draft for this entity (or a concurrent create won).
            db.rollback()
            existing = self.get_open_draft(
                db,
                gene_id=obj_in.gene_id,
                scope_id=scope.id,
                user_id=user_id,
                entity_key=key,
            )
            if existing is None:
                raise
            return existing
        db.refresh(db_obj)

        logger.info(
            "Precuration created",
            precuration_id=str(db_obj.id),
            gene_id=str(obj_in.gene_id),
            scope_id=str(obj_in.scope_id),
            user_id=str(user_id),
        )

        return db_obj

    def update_with_lock(
        self,
        db: Session,
        *,
        db_obj: PrecurationNew,
        evidence_data: dict[str, Any] | None,
        lock_version: int,
        user_id: UUID,
        merge: bool = False,
    ) -> tuple[PrecurationNew, list[EvidenceWarning]] | None:
        """Update evidence with optimistic locking, plus warnings on its IDs and on arrays a
        merge shortened. None if lock_version is stale."""
        values: dict[str, Any] = {"updated_by": user_id}
        warnings: list[EvidenceWarning] = []
        if evidence_data is not None:
            evidence_data, warnings = _patched(db_obj, evidence_data, merge)
            warnings += check_ids(db, evidence_data)[0]
            values["evidence_data"] = evidence_data
        if not write_draft(db, db_obj, lock_version, values):
            return None
        db.refresh(db_obj)
        return db_obj, warnings

    def save_draft(
        self,
        db: Session,
        *,
        db_obj: PrecurationNew,
        evidence_data: dict[str, Any],
        lock_version: int,
        user_id: UUID,
        merge: bool = False,
    ) -> tuple[PrecurationNew, list[EvidenceWarning]] | None:
        """Save as draft with auto-save timestamp, whatever the content, plus warnings on
        its IDs (lookups precede the write). None if lock_version is stale."""
        evidence_data, shrunk = _patched(db_obj, evidence_data, merge)
        warnings, _ = check_ids(db, evidence_data)
        warnings = shrunk + warnings
        values = {
            "evidence_data": evidence_data,
            "is_draft": True,
            "auto_saved_at": _utc_now(),
            "updated_by": user_id,
        }
        if not write_draft(db, db_obj, lock_version, values):
            return None
        db.refresh(db_obj)
        return db_obj, warnings

    def _check_submittable(
        self, db: Session, db_obj: PrecurationNew, user_id: UUID
    ) -> None:
        """Raise unless the precuration may enter review (required fields, L/S, transition)."""
        check_review_content(db, db_obj)

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

    def submit_for_review(
        self,
        db: Session,
        *,
        db_obj: PrecurationNew,
        submit_data: PrecurationSubmit,
        user_id: UUID,
    ) -> PrecurationNew | None:
        """Submit precuration for review via workflow engine. None if lock_version is stale."""
        reviewer_id = submit_reviewer(db, db_obj.scope_id, submit_data)
        # Compare-and-bump in one UPDATE first: a stale submit matches no row and changes nothing
        if not claim_version(db, PrecurationNew, db_obj.id, submit_data.lock_version):
            return None
        try:
            self._check_submittable(db, db_obj, user_id)
        except Exception:
            db.rollback()  # undo the claim: a refused submit must not bump the version
            raise

        # Execute transition
        workflow_engine.execute_transition(
            db,
            db_obj.id,
            "precuration",
            WorkflowStage.REVIEW,
            user_id,
            submit_data.notes,
            reviewer_id=reviewer_id,
        )

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
        allowed = workflow_engine.transitions_for(db, db_obj)
        if WorkflowStage.CURATION not in allowed.get(db_obj.workflow_stage, []):
            raise ValueError(
                f"Invalid transition from {db_obj.workflow_stage.value} to curation"
            )

        curation = None
        key = db_obj.entity_key
        # One open curation per entity: an open one (e.g. a re-curation) stays the only one
        workflow_pair = (
            self._get_workflow_pair_for_precuration(db, db_obj)
            if create_curation
            and not open_curation_id(
                db, db_obj.gene_id, db_obj.scope_id, db_obj.entity_key
            )
            else None
        )

        # Update precuration status (after pair selection, which may refuse)
        db_obj.status = CurationStatus.APPROVED
        db_obj.workflow_stage = WorkflowStage.CURATION
        db_obj.updated_by = approver_id
        db_obj.updated_at = _utc_now()

        if workflow_pair:
            # Create curation with prefilled data
            curation = CurationNew(
                gene_id=db_obj.gene_id,
                scope_id=db_obj.scope_id,
                workflow_pair_id=workflow_pair.id,
                precuration_id=db_obj.id,  # Link to precuration
                entity_key=db_obj.entity_key,
                status=CurationStatus.DRAFT,
                workflow_stage=WorkflowStage.CURATION,
                is_draft=True,
                evidence_data=self._prefill_curation_data(
                    db_obj.evidence_data, workflow_pair.data_mapping or {}
                ),
                lock_version=0,
                # The precuration author authors the curation, so 4-eyes review
                # excludes them and not the approver.
                created_by=db_obj.created_by,
                updated_by=approver_id,
                created_at=_utc_now(),
                updated_at=_utc_now(),
            )
            db.add(curation)

        db.add(db_obj)
        try:
            db.commit()
        except IntegrityError:
            # A concurrent curation of this entity won its open-curation index
            db.rollback()
            raced = open_curation_id(db, db_obj.gene_id, db_obj.scope_id, key)
            if raced is None:
                raise
            raise conflict(OpenCurationExistsError.MESSAGE, curation_id=raced) from None
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
        """Archive only precurations without linked curations, including archived ones."""
        curation_count = self.has_associated_curations(db, db_obj.id)
        if curation_count > 0:
            raise ValueError(
                f"Cannot delete precuration: {curation_count} linked "
                f"curation(s) exist. Remove or reassign them first."
            )

        db_obj.status = CurationStatus.ARCHIVED
        db_obj.workflow_stage = WorkflowStage.ARCHIVED
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

    def has_associated_curations(self, db: Session, precuration_id: UUID) -> int:
        """Count curations linked to this precuration."""
        stmt = (
            select(func.count())
            .select_from(CurationNew)
            .where(CurationNew.precuration_id == precuration_id)
        )
        return db.execute(stmt).scalar() or 0

    # ========================================
    # HELPER METHODS
    # ========================================

    def _get_workflow_pair_for_precuration(
        self, db: Session, precuration: PrecurationNew
    ) -> WorkflowPair | None:
        """Active pair for this precuration's schema: the scope default if it applies,
        else the only match; several matches without an applicable default refuse."""
        stmt = select(WorkflowPair).where(
            WorkflowPair.precuration_schema_id == precuration.precuration_schema_id,
            WorkflowPair.is_active == True,  # noqa: E712
        )
        pairs = list(db.execute(stmt).scalars())
        scope = db.get(Scope, precuration.scope_id)
        default_id = scope.default_workflow_pair_id if scope else None
        for pair in pairs:
            if pair.id == default_id:
                return pair
        if len(pairs) > 1:
            raise ValueError(
                "Several active workflow pairs use this precuration schema and the "
                "scope's default workflow pair is not one of them; a scope admin must "
                "set the scope's default workflow pair before approval"
            )
        return pairs[0] if pairs else None

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
