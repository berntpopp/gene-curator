"""Bind remote PMID results to an unchanged, freshly authorized curation before locking writes."""

from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.capabilities import EDIT, require
from app.core.workflow_errors import transition_error
from app.models import (
    CurationNew,
    CurationStatus,
    PrecurationNew,
    UserNew,
    WorkflowStage,
)
from app.scoring.point_limits import enforce_clingen_point_ranges
from app.services.evidence_ids import not_found, ontology_ids
from app.services.ontology_service import lookup_terms
from app.services.publication_service import evidence_pmids, unknown_pmids
from app.services.review_guards import check_review_content

if TYPE_CHECKING:
    from app.crud.workflow_engine import WorkflowEngine


@dataclass(frozen=True)
class ReviewEntry:
    item_id: UUID
    version: int
    state: tuple[Any, ...]
    pmids: frozenset[str]
    unknown: frozenset[str] = frozenset()
    terms: frozenset[str] = frozenset()  # MONDO, OMIM and HPO IDs
    unknown_terms: frozenset[str] = frozenset()


def _state(item: CurationNew) -> tuple[Any, ...]:
    return deepcopy(
        (
            item.scope_id,
            item.created_by,
            item.workflow_pair_id,
            item.methodology_version_id,
            item.workflow_stage,
            item.status,
            item.evidence_data,
        )
    )


def capture_review(db: Session, item: CurationNew) -> ReviewEntry:
    """Network-free validation and a detached copy of precisely what will be checked."""
    check_review_content(db, item)
    enforce_clingen_point_ranges(
        db, item.workflow_pair_id, item.evidence_data, item.methodology_version_id
    )
    return ReviewEntry(
        item.id,
        item.lock_version,
        _state(item),
        frozenset(evidence_pmids(item.evidence_data)),
        terms=frozenset(ontology_ids(item.evidence_data)),
    )


def lookup_reviews(db: Session, entries: list[ReviewEntry]) -> list[ReviewEntry]:
    """One deduplicated bounded batch for authorized snapshots, never parallel DB work."""
    pmids = set().union(*(entry.pmids for entry in entries))
    unknown = frozenset(unknown_pmids(db, pmids)) if pmids else frozenset()
    terms = set().union(*(entry.terms for entry in entries))
    unknown_terms = frozenset(lookup_terms(terms)[0]) if terms else frozenset()
    return [
        replace(
            entry,
            unknown=entry.pmids & unknown,
            unknown_terms=entry.terms & unknown_terms,
        )
        for entry in entries
    ]


def _conflict(item: CurationNew, expected: int) -> HTTPException:
    return HTTPException(
        409,
        detail={
            "error": "Concurrent modification detected",
            "current_lock_version": item.lock_version,
            "your_lock_version": expected,
            "current_state": item.evidence_data,
        },
    )


def _require_editor(
    db: Session, item: CurationNew, user_id: UUID, dedicated: bool
) -> None:
    user = db.get(UserNew, user_id)
    if user is None or not user.is_active:
        raise HTTPException(403, detail="User no longer active")
    require(db, user, item.scope_id, EDIT)
    if dedicated and user.role != "admin" and item.created_by != user_id:
        raise HTTPException(403, detail="Only the creator can submit for review")


def _authorize(
    engine: "WorkflowEngine",
    db: Session,
    item: CurationNew,
    user_id: UUID,
    dedicated: bool,
) -> None:
    _require_editor(db, item, user_id, dedicated)
    validation = engine.validate_transition(
        db, item.workflow_stage, WorkflowStage.REVIEW, user_id, item.id, "curation"
    )
    if not validation.is_valid:
        raise transition_error(validation)


def preflight_review(
    engine: "WorkflowEngine", db: Session, item: CurationNew, user_id: UUID
) -> ReviewEntry:
    with db.no_autoflush:
        _authorize(engine, db, item, user_id, False)
        return capture_review(db, item)


def prepare_review_entry(
    engine: "WorkflowEngine",
    db: Session,
    item: CurationNew,
    user_id: UUID,
    expected_version: int | None,
    entry: ReviewEntry | None = None,
) -> CurationNew:
    """Remote work precedes all mutations; FOR UPDATE then rechecks state and permissions."""
    with db.no_autoflush:
        _authorize(engine, db, item, user_id, expected_version is not None)
        if expected_version is not None and item.lock_version != expected_version:
            raise _conflict(item, expected_version)
        if entry is None:
            entry = lookup_reviews(db, [capture_review(db, item)])[0]
        item_id = item.id
        # Cached ORM values (including membership/user role) cannot authorize this write.
        db.expire_all()
        current = db.scalar(
            select(CurationNew)
            .where(CurationNew.id == item_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if current is None:
            raise HTTPException(403, detail="Curation no longer accessible")
        _require_editor(db, current, user_id, expected_version is not None)
        if (
            entry.item_id != current.id
            or entry.version != current.lock_version
            or entry.state != _state(current)
        ):
            raise _conflict(current, entry.version)
        _authorize(engine, db, current, user_id, expected_version is not None)
        capture_review(db, current)  # ranges and pinned content are local checks
        if entry.unknown:
            raise HTTPException(
                422,
                detail=f"PMID {', '.join(sorted(entry.unknown))} not found in Europe PMC; "
                "fix or remove before submitting",
            )
        if entry.unknown_terms:
            errors = not_found(current.evidence_data, set(entry.unknown_terms))
            raise HTTPException(
                422,
                detail={
                    "message": "Unknown ontology IDs; fix or remove before submitting",
                    "errors": [e.model_dump() for e in errors],
                },
            )
        return current


def transition_to_review(
    db: Session, item: CurationNew | PrecurationNew, user_id: UUID
) -> dict[str, Any]:
    """Apply one review-entry write, after the remote preflight and locked revalidation."""
    if isinstance(item, CurationNew):
        from app.crud.curation import _update_computed_scores

        # Queries used by scoring must not autoflush half of the submission metadata.
        with db.no_autoflush:
            _update_computed_scores(db, item, lookup=False)  # IDs were looked up
        item.submitted_at = datetime.now(UTC)
        item.submitted_by = user_id
    else:
        item.updated_by = user_id
        item.updated_at = datetime.now(UTC)
    item.workflow_stage = WorkflowStage.REVIEW
    item.status = (
        CurationStatus.IN_REVIEW
        if isinstance(item, CurationNew)
        else CurationStatus.SUBMITTED
    )
    item.is_draft = False
    # One ORM update also advances optimistic version on SQLite; PG's trigger matches it.
    if isinstance(item, CurationNew):
        item.lock_version += 1
    db.flush()
    return {"success": True, "message": "Transitioned to review"}
