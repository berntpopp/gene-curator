"""
CRUD operations for curations.
Extends CRUDBase with curation-specific operations.
Follows patterns from gene_assignment.py.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.logging import get_logger
from app.core.workflow_errors import transition_error
from app.crud.activation import same_entity
from app.crud.base import CRUDBase
from app.crud.curator_classification import curator_call
from app.crud.merge_patch import merge_patch
from app.crud.optimistic_lock import update_if_version
from app.crud.precuration_entity import refuse_entity_change, refuse_other_entity
from app.crud.workflow_engine import workflow_engine
from app.models import (
    ActiveCuration,
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
    EvidenceWarning,
    disease_fields,
    entity_allele,
    relationship_of_key,
)
from app.scoring.point_limits import scoring_configuration
from app.scoring.registry import engine_for
from app.services.evidence_ids import (
    check_ids,
    format_errors,
    score_scorable,
    shrunk_arrays,
)
from app.services.review_assignment import submit_reviewer
from app.services.review_guards import check_review_content, save_warnings
from app.services.row_provenance import stamped

logger = get_logger(__name__)
DELETED_REASON = "Curation deleted"  # pointer archive_reason of a soft delete


class OpenCurationExistsError(ValueError):
    """The gene already has an open (not active or archived) curation in the scope."""

    MESSAGE = "This disease entity already has an open curation in this scope"
    WHOLE_GENE = (
        "Open curation {id} has no disease entity, so it covers the whole gene in this "
        "scope; finish or archive it before curating another entity"
    )

    def __init__(self, curation_id: UUID, message: str = MESSAGE) -> None:
        super().__init__(message)
        self.curation_id = curation_id


def open_conflict_message(db: Session, curation_id: UUID) -> str:
    """Why an open curation blocks this entity; an unkeyed (legacy) one blocks them all."""
    if db.scalar(select(CurationNew.entity_key).where(CurationNew.id == curation_id)):
        return OpenCurationExistsError.MESSAGE
    return OpenCurationExistsError.WHOLE_GENE.format(id=curation_id)


class EntityRequiredError(ValueError):
    """The gene has several disease entities in the scope: say which (precuration_id)."""

    def __init__(self) -> None:
        super().__init__(
            "This gene has several disease entities in this scope; send the "
            "precuration_id of the one to curate"
        )


def open_curation_id(
    db: Session, gene_id: UUID, scope_id: UUID, entity_key: str
) -> UUID | None:
    """The entity's open (not active or archived) curation in the scope, if any; as in
    activation, '' (unlinked legacy or lumped) covers the whole gene."""
    return db.scalar(
        select(CurationNew.id).where(
            CurationNew.gene_id == gene_id,
            CurationNew.scope_id == scope_id,
            same_entity(CurationNew.entity_key, entity_key),
            CurationNew.status.notin_([CurationStatus.ACTIVE, CurationStatus.ARCHIVED]),
        )
    )


def entity_keys(db: Session, gene_id: UUID, scope_id: UUID) -> set[str]:
    """Disease entities of the gene in the scope: approved precurations, live curations."""
    pre = select(PrecurationNew.entity_key).where(
        PrecurationNew.gene_id == gene_id,
        PrecurationNew.scope_id == scope_id,
        PrecurationNew.status == CurationStatus.APPROVED,
    )
    cur = select(CurationNew.entity_key).where(
        CurationNew.gene_id == gene_id,
        CurationNew.scope_id == scope_id,
        CurationNew.status != CurationStatus.ARCHIVED,
    )
    return {k for k in [*db.scalars(pre), *db.scalars(cur)] if k}


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(UTC)


def section_total(scores: dict[str, Any], section: str) -> Any:
    """A section total: ClinGen `genetic_evidence_total`, else a custom point model's
    `genetic_total` (engine key = section key + _total)."""
    return scores.get(f"{section}_evidence_total", scores.get(f"{section}_total"))


def get_disease_fields(
    evidence: dict[str, Any] | None, precuration_evidence: dict[str, Any] | None
) -> dict[str, Any]:
    """Prefer curation disease fields, falling back to the linked precuration."""
    return disease_fields(evidence, precuration_evidence)


def _patched(
    item: Any, sent: dict[str, Any], merge: bool | None
) -> tuple[dict[str, Any], list[EvidenceWarning]]:
    """The evidence a save stores, and warnings for arrays a merge patch shortened."""
    if not merge:
        return sent, []
    merged = merge_patch(item.evidence_data, sent)
    return merged, shrunk_arrays(item.evidence_data, merged)


def _computed(
    db: Session,
    curation: CurationNew,
    evidence_data: dict[str, Any],
    ids: tuple[list[EvidenceWarning], set[str]] | None = None,
    lookup: bool = True,
) -> dict[str, Any]:
    """Score with the row's pinned version (latest on create), persisted with the evidence.
    Rows with a malformed or unknown PMID score nothing; ID warnings join the scoring
    ones as "path: message". ``lookup=False`` checks formats only (no network)."""
    if curation.clingen_adoption:  # #613: ClinGen's class, never points of ours
        return {
            "computed_scores": {},
            "computed_verdict": None,
            "computed_summary": None,
        }
    if ids is None:
        ids = (
            check_ids(db, evidence_data)
            if lookup
            else (format_errors(evidence_data), set())
        )
    config = scoring_configuration(
        db, curation.workflow_pair_id, curation.methodology_version_id
    )
    result = score_scorable(engine_for(config), config, evidence_data, ids[1])
    return {
        "computed_scores": {
            **result.scores,
            **result.evidence_breakdown,
            "warnings": [*result.warnings, *(f"{w.path}: {w.message}" for w in ids[0])],
        },
        "computed_verdict": result.verdict,
        "computed_summary": result.verdict_rationale,
    }


def _update_computed_scores(
    db: Session, curation: CurationNew, lookup: bool = True
) -> None:
    """Persist engine output in the same transaction as the evidence write."""
    for key, value in _computed(
        db, curation, curation.evidence_data, lookup=lookup
    ).items():
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

            evidence, pre = row.CurationNew.evidence_data, row.precuration_evidence
            disease = get_disease_fields(evidence, pre)
            key = row.CurationNew.entity_key

            summaries.append(
                CurationSummary(
                    id=row.CurationNew.id,
                    gene_id=row.CurationNew.gene_id,
                    gene_symbol=row.gene_symbol,
                    scope_id=row.CurationNew.scope_id,
                    scope_name=row.scope_name,
                    status=row.CurationNew.status,
                    workflow_stage=row.CurationNew.workflow_stage,
                    computed_verdict=row.CurationNew.computed_verdict,  # the key
                    curator_classification=row.CurationNew.curator_classification,
                    final_classification=row.CurationNew.final_classification,
                    clingen_adoption=row.CurationNew.clingen_adoption,
                    computed_scores={
                        "total_score": scores.get("total_score", 0.0),
                        "genetic_score": section_total(scores, "genetic") or 0.0,
                        "experimental_score": section_total(scores, "experimental")
                        or 0.0,
                    },
                    disease_name=disease["disease_name"],
                    relationship_type=relationship_of_key(key),
                    entity_key=key or "",
                    risk_allele=entity_allele(key, evidence, pre),
                    is_draft=row.CurationNew.is_draft,
                    created_at=row.CurationNew.created_at,
                    updated_at=row.CurationNew.updated_at,
                    curator_name=row.curator_name,
                    created_by=row.CurationNew.created_by,
                    lock_version=row.CurationNew.lock_version,
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

        precuration_id, entity_key, allowed = self._entity(db, obj_in)
        if not allowed:
            raise ValueError(
                "An approved precuration for this gene and scope is required"
            )
        pre = db.get(PrecurationNew, precuration_id) if precuration_id else None
        from app.crud.precuration import precuration_crud  # import cycle

        workflow_pair = precuration_crud.pair_for(db, pre, workflow_pair)  # MUI-03
        refuse_other_entity(
            db,
            entity_key,
            obj_in.evidence_data,
            pre.evidence_data if pre else None,
            {"precuration_id": pre.id} if pre else {},
        )
        # Create curation
        now = _utc_now()
        db_obj = CurationNew(
            gene_id=obj_in.gene_id,
            scope_id=obj_in.scope_id,
            workflow_pair_id=workflow_pair.id,
            precuration_id=precuration_id,
            entity_key=entity_key,
            evidence_data=obj_in.evidence_data,
            row_provenance=stamped(db, None, obj_in.evidence_data, None, user_id),
            status=CurationStatus.DRAFT,
            workflow_stage=WorkflowStage.CURATION,
            is_draft=True,
            lock_version=0,
            created_by=user_id,
            updated_by=user_id,
            created_at=now,
            updated_at=now,
        )
        # A re-curation keeps the source's call (422 for an unknown class)
        for key, value in curator_call(db, db_obj, obj_in).items():
            setattr(db_obj, key, value)
        # One open curation per entity (approval already created a draft, #398)
        open_id = open_curation_id(db, obj_in.gene_id, obj_in.scope_id, entity_key)
        if open_id:
            raise OpenCurationExistsError(open_id, open_conflict_message(db, open_id))
        _update_computed_scores(db, db_obj)
        db.add(db_obj)
        try:
            db.commit()
        except IntegrityError:
            # A concurrent create won the entity's open-curation index
            db.rollback()
            raced = open_curation_id(db, obj_in.gene_id, obj_in.scope_id, entity_key)
            if raced is None:
                raise
            raise OpenCurationExistsError(
                raced, open_conflict_message(db, raced)
            ) from None
        db.refresh(db_obj)

        logger.info(
            "Curation created",
            curation_id=str(db_obj.id),
            gene_id=str(obj_in.gene_id),
            scope_id=str(obj_in.scope_id),
            user_id=str(user_id),
        )

        return db_obj

    def _entity(
        self, db: Session, obj_in: CurationCreate
    ) -> tuple[UUID | None, str, bool]:
        """(precuration_id, entity_key, allowed) for a new curation. 4-eyes: it needs an
        approved precuration, unless it re-curates an active one, whose entity it inherits."""
        same = (
            CurationNew.gene_id == obj_in.gene_id,
            CurationNew.scope_id == obj_in.scope_id,
        )
        active = select(CurationNew).where(
            *same, CurationNew.status == CurationStatus.ACTIVE
        )
        if obj_in.precuration_id:
            pre = db.get(PrecurationNew, obj_in.precuration_id)
            if pre is None or (pre.gene_id, pre.scope_id) != (
                obj_in.gene_id,
                obj_in.scope_id,
            ):
                return None, "", False
            relinks_active = db.scalar(
                active.where(CurationNew.precuration_id == pre.id).limit(1)
            )
            ok = pre.status == CurationStatus.APPROVED or relinks_active is not None
            return pre.id, pre.entity_key, ok
        if len(entity_keys(db, obj_in.gene_id, obj_in.scope_id)) > 1:
            raise EntityRequiredError()
        source = db.scalars(active.limit(1)).first()
        if source:
            return source.precuration_id, source.entity_key, True
        approved = db.scalars(
            select(PrecurationNew)
            .where(
                PrecurationNew.gene_id == obj_in.gene_id,
                PrecurationNew.scope_id == obj_in.scope_id,
                PrecurationNew.status == CurationStatus.APPROVED,
            )
            .limit(1)
        ).first()
        # Unlinked as before: the detail view shows the approved one (no write on read)
        return (None, approved.entity_key, True) if approved else (None, "", False)

    def update_with_lock(
        self,
        db: Session,
        *,
        db_obj: CurationNew,
        obj_in: CurationUpdate,
        user_id: UUID,
        commit: bool = True,
    ) -> CurationNew | None:
        """
        Update curation with optimistic locking.
        Returns None if lock_version doesn't match (conflict). ``commit=False`` leaves
        the transaction open for the caller's further writes.
        """
        values: dict[str, Any] = {"updated_by": user_id, "updated_at": _utc_now()}
        if obj_in.evidence_data is not None:
            evidence, shrunk = _patched(db_obj, obj_in.evidence_data, obj_in.merge)
            refuse_entity_change(db, db_obj, evidence)
            warnings, unknown = check_ids(db, evidence)
            values["evidence_data"] = evidence
            values["row_provenance"] = stamped(
                db, db_obj.evidence_data, evidence, db_obj.row_provenance, user_id
            )
            values.update(_computed(db, db_obj, evidence, (shrunk + warnings, unknown)))
        values.update(curator_call(db, db_obj, obj_in))
        if not update_if_version(
            db, CurationNew, db_obj.id, obj_in.lock_version, values, commit=commit
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
    ) -> tuple[CurationNew, list[EvidenceWarning]] | None:
        """Save as draft with auto-save timestamp, whatever the content, plus warnings on
        its IDs (lookups precede the write). None if lock_version is stale."""
        evidence, shrunk = _patched(db_obj, draft_data.evidence_data, draft_data.merge)
        refuse_entity_change(db, db_obj, evidence)
        warnings, unknown = check_ids(db, evidence)
        warnings = shrunk + warnings
        values = {
            "evidence_data": evidence,
            "row_provenance": stamped(
                db, db_obj.evidence_data, evidence, db_obj.row_provenance, user_id
            ),
            **_computed(db, db_obj, evidence, (warnings, unknown)),
            "is_draft": True,
            "auto_saved_at": _utc_now(),
            "updated_by": user_id,
            **curator_call(db, db_obj, draft_data),
        }
        if not update_if_version(
            db, CurationNew, db_obj.id, draft_data.lock_version, values
        ):
            return None
        db.refresh(db_obj)
        return db_obj, save_warnings(db, db_obj, evidence, warnings)

    def submit_for_review(
        self,
        db: Session,
        *,
        db_obj: CurationNew,
        submit_data: CurationSubmit,
        user_id: UUID,
    ) -> CurationNew | None:
        """Submit curation for review via workflow engine."""
        check_review_content(db, db_obj)  # typed errors by path; the engine repeats it
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
            raise transition_error(validation)

        workflow_engine.execute_transition(
            db,
            db_obj.id,
            "curation",
            WorkflowStage.REVIEW,
            user_id,
            submit_data.notes,
            expected_version=submit_data.lock_version,
            reviewer_id=submit_reviewer(
                db, db_obj.scope_id, submit_data, db_obj.created_by
            ),
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
        _, unknown = check_ids(db, db_obj.evidence_data)
        result = score_scorable(
            scoring_engine or engine_for(config), config, db_obj.evidence_data, unknown
        )

        # Extract genetic and experimental scores from the scores dict
        genetic_score = section_total(result.scores, "genetic") or 0.0
        experimental_score = section_total(result.scores, "experimental") or 0.0

        return CurationScoreResponse(
            curation_id=db_obj.id,
            total_score=result.total_score,
            classification=result.verdict,
            genetic_score=genetic_score,
            experimental_score=experimental_score,
            breakdown=result.evidence_breakdown,
            warnings=result.warnings,
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
        # A deleted active curation must leave catalogue, views and export like a replaced one
        for pointer in db.query(ActiveCuration).filter(
            ActiveCuration.curation_id == db_obj.id,
            ActiveCuration.archived_at.is_(None),
        ):
            pointer.archived_at = _utc_now()
            pointer.archived_by = user_id
            pointer.archive_reason = DELETED_REASON

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
