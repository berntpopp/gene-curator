"""Move a schema's curations and precurations to its latest methodology version (#591).

A dry run writes nothing and reports per row: fields kept (same id), fields dropped (id
gone in the new version), new required fields now empty and old -> new score and class.
Apply does the same in one transaction: re-pin (078 allows only a later version of the
same schema), drop the gone fields, rescore as a save does and audit-log every row.
An active curation whose class changes, or that misses a new required field, is never
edited: an open copy on the new version goes to review (earlier reviewers are asked
again) or to draft, and replaces it only once a second person approves it (4-eyes);
until then the approved result stays active and exported. Unchanged ones are re-pinned
in place. Archived rows are history and stay as they are. Running it twice changes
nothing: rows already on the target, and active rows with an open copy, are not listed.
"""

from datetime import UTC, datetime
from typing import Any, Literal, cast
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.capabilities import INACTIVE_SCOPE
from app.core.logging import get_logger
from app.crud.curation import _computed
from app.crud.precuration_required import missing_required_fields
from app.crud.review_round import reassign_earlier_reviewers
from app.models import AuditLogNew, CurationSchema, NotificationNew, Scope
from app.models.methodology import MethodologyVersion
from app.models.model_enums import NotificationType
from app.models.models import (
    CurationNew,
    CurationStatus,
    Gene,
    PrecurationNew,
    WorkflowStage,
)

logger = get_logger(__name__)


class VersionMoveItem(BaseModel):
    """What the move does (or, on a dry run, would do) to one curation or precuration."""

    kind: Literal["curation", "precuration"]
    id: UUID
    gene: str | None = None
    status: str
    from_version: int
    to_version: int
    kept: list[str] = []
    dropped: list[str] = []
    missing_required: list[str] = []
    old_score: float | None = None
    new_score: float | None = None
    old_class: str | None = None
    new_class: str | None = None
    # an active curation stays active; an open copy goes to review or draft
    back_to: Literal["review", "draft"] | None = None
    copy_id: UUID | None = None  # the open copy, once applied
    skipped: str | None = None  # why the row is not moved (an inactive scope)


class VersionMoveResult(BaseModel):
    dry_run: bool
    schema_id: UUID
    to_version: int
    items: list[VersionMoveItem] = []


class VersionNotFoundError(LookupError):
    """No such schema, or no such published version of it."""


class StaleVersionError(ValueError):
    """The requested version is no longer the latest: plan the move again."""


Planned = tuple[CurationNew | PrecurationNew, VersionMoveItem, dict[str, Any], Any]


def _field_ids(defs: Any) -> set[str]:
    """Top-level field ids of flat definitions or ``sections[].fields[]``."""
    if not isinstance(defs, dict):
        return set()
    sections = [s for s in defs.get("sections") or [] if isinstance(s, dict)]
    return {k for k in defs if k != "sections"} | {
        f["id"]
        for s in sections
        for f in s.get("fields") or []
        if isinstance(f, dict) and f.get("id")
    }


def _missing(snapshot: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    return missing_required_fields(
        snapshot.get("field_definitions"), evidence, snapshot.get("validation_rules")
    )


def _open_twin(db: Session, row: CurationNew) -> UUID | None:
    """Another open curation of the entity: the re-curation that will replace it."""
    return db.scalar(
        select(CurationNew.id).where(
            CurationNew.gene_id == row.gene_id,
            CurationNew.scope_id == row.scope_id,
            CurationNew.entity_key == row.entity_key,
            CurationNew.status.notin_([CurationStatus.ACTIVE, CurationStatus.ARCHIVED]),
            CurationNew.id != row.id,
        )
    )


def _versions(
    db: Session, schema_id: UUID, version: int | None
) -> tuple[dict[UUID, MethodologyVersion], MethodologyVersion]:
    """The schema's published versions by id, and the latest (the move's target)."""
    if db.get(CurationSchema, schema_id) is None:
        raise VersionNotFoundError("Schema not found")
    versions = {
        v.id: v
        for v in db.scalars(
            select(MethodologyVersion).where(MethodologyVersion.schema_id == schema_id)
        )
    }
    if not versions or version not in {None, *(v.version for v in versions.values())}:
        raise VersionNotFoundError(f"Schema has no published version {version or ''}")
    target = max(versions.values(), key=lambda v: v.version)
    if version and version != target.version:  # new rows pin to the latest (042)
        raise StaleVersionError(
            f"Version {version} is no longer the latest ({target.version}); "
            "plan the move again"
        )
    return versions, target


Pinned = tuple[CurationNew | PrecurationNew, str | None, bool]


def _pinned_rows(db: Session, older: list[UUID], lock: bool) -> list[Pinned]:
    """(row, gene symbol, scope active) of curations, then precurations, pinned to an
    older version; archived ones excluded. ``lock`` first locks the writable ones (RLS
    hides an inactive scope's rows from FOR UPDATE, 054) until commit, so a concurrent
    save cannot be lost; the read after it sees every row as the dry run does."""
    out: list[Pinned] = []
    for model in (CurationNew, PrecurationNew):
        pinned = (
            model.methodology_version_id.in_(older),
            model.status != CurationStatus.ARCHIVED,
        )
        if lock:
            db.execute(
                select(model.id)
                .join(Scope, Scope.id == model.scope_id)
                .where(*pinned, Scope.is_active)
                .with_for_update(of=model)
            ).all()
        query = (
            select(model, Gene.approved_symbol, Scope.is_active)
            .join(Scope, Scope.id == model.scope_id)
            .outerjoin(Gene, Gene.id == model.gene_id)
            .where(*pinned)
            .order_by(model.created_at, model.id)
            .execution_options(populate_existing=True)  # the locked state
        )
        out += cast(list[Pinned], db.execute(query).all())
    return out


def _plan_curation(
    db: Session, row: CurationNew, item: VersionMoveItem, target: UUID, kept: Any
) -> dict[str, Any]:
    """Score as a save on the new version does; decide whether an active result reopens."""
    probe = CurationNew(workflow_pair_id=row.workflow_pair_id)  # never added
    probe.methodology_version_id = target
    computed = _computed(db, probe, kept, lookup=False)
    item.old_score = (row.computed_scores or {}).get("total_score")
    item.new_score = computed["computed_scores"].get("total_score")
    item.old_class, item.new_class = row.computed_verdict, computed["computed_verdict"]
    if row.status == CurationStatus.ACTIVE:
        if item.missing_required:
            item.back_to = "draft"
        elif item.old_class != item.new_class:
            item.back_to = "review"
    return computed


def _open_copy(
    db: Session, row: CurationNew, item: VersionMoveItem, values: dict[str, Any]
) -> CurationNew:
    """An open re-curation of the active row on the new version; the row stays active."""
    review = item.back_to == "review"
    copy = CurationNew(
        gene_id=row.gene_id,
        scope_id=row.scope_id,
        workflow_pair_id=row.workflow_pair_id,
        precuration_id=row.precuration_id,
        entity_key=row.entity_key,
        curator_classification=row.curator_classification,
        curator_classification_rationale=row.curator_classification_rationale,
        created_by=row.created_by,  # the curator's work: they may not approve it
        status=CurationStatus.IN_REVIEW if review else CurationStatus.DRAFT,
        workflow_stage=WorkflowStage.REVIEW if review else WorkflowStage.CURATION,
        is_draft=not review,
        submitted_at=datetime.now(UTC) if review else None,
        submitted_by=(row.submitted_by or row.created_by) if review else None,
        **values,
    )
    db.add(copy)
    db.flush()
    return copy


def _ask_earlier_reviewers(
    db: Session, copy: CurationNew, source: CurationNew, user_id: UUID, gene: str | None
) -> None:
    """The active row's reviewers get a pending review of the copy, as on resubmit."""
    for reviewer_id in reassign_earlier_reviewers(db, copy, user_id, source.id):
        db.add(
            NotificationNew(
                user_id=reviewer_id,
                type=NotificationType.REVIEW_ASSIGNED,
                title="New review assigned",
                message=f"New review assigned: {gene or 'Unknown'}",
                link=f"/scopes/{copy.scope_id}/curations/{copy.id}",
            )
        )


def _audit(
    db: Session,
    entity: CurationNew | PrecurationNew,
    item: VersionMoveItem,
    previous: str,
    extra: dict[str, Any],
    target: MethodologyVersion,
    user_id: UUID,
) -> None:
    db.add(
        AuditLogNew(
            entity_type=item.kind,
            entity_id=entity.id,
            scope_id=entity.scope_id,
            operation="CREATE" if item.copy_id else "UPDATE",
            change_type="version_move",  # D1: the mover may not review it (correctors)
            user_id=user_id,
            previous_status=previous,
            new_status=entity.status.value,
            schema_id=target.schema_id,
            changes={
                **item.model_dump(mode="json", exclude={"kind", "gene"}),
                "to_version_id": str(target.id),
                **extra,
            },
        )
    )
    db.flush()


def _apply(
    db: Session, planned: Planned, target: MethodologyVersion, user_id: UUID
) -> None:
    row, item, kept, computed = planned
    extra = {
        "from_version_id": str(row.methodology_version_id),
        # nothing is lost: the dropped values stay in the audit log
        "dropped_values": {k: (row.evidence_data or {})[k] for k in item.dropped},
    }
    if isinstance(row, CurationNew) and item.back_to:
        copy = _open_copy(
            db,
            row,
            item,
            # PostgreSQL pins a new row to the latest version itself (042): the target
            {
                "methodology_version_id": target.id,
                "evidence_data": kept,
                "updated_by": user_id,
                **computed,
            },
        )
        item.copy_id = copy.id
        _audit(db, copy, item, row.status.value, extra, target, user_id)
        if item.back_to == "review":
            _ask_earlier_reviewers(db, copy, row, user_id, item.gene)
        return
    previous = row.status.value
    row.methodology_version_id = target.id
    row.evidence_data = kept
    row.updated_by = user_id
    if isinstance(row, CurationNew):
        for key, value in computed.items():
            setattr(row, key, value)
        row.lock_version += 1  # PostgreSQL's 008 trigger sets the same value
    _audit(db, row, item, previous, extra, target, user_id)


def move_to_version(
    db: Session,
    schema_id: UUID,
    *,
    version: int | None,
    user_id: UUID,
    dry_run: bool,
) -> VersionMoveResult:
    """Plan and (unless dry_run) move every row of the schema to its latest version.
    ``version``, when given, must still be the latest (the version a dry run planned)."""
    versions, target = _versions(db, schema_id, version)
    older = [v.id for v in versions.values() if v.version < target.version]
    new = target.snapshot or {}
    new_ids = _field_ids(new.get("field_definitions"))
    out = VersionMoveResult(
        dry_run=dry_run, schema_id=schema_id, to_version=target.version
    )
    planned: list[Planned] = []
    for row, gene, scope_active in _pinned_rows(db, older, lock=not dry_run):
        active = isinstance(row, CurationNew) and row.status == CurationStatus.ACTIVE
        if active and _open_twin(db, cast(CurationNew, row)):
            continue  # its open re-curation is moved and replaces it
        assert row.methodology_version_id is not None  # selected by it
        pinned = versions[row.methodology_version_id]
        old = pinned.snapshot or {}
        gone = _field_ids(old.get("field_definitions")) - new_ids
        evidence = row.evidence_data or {}
        kept = {k: v for k, v in evidence.items() if k not in gone}
        item = VersionMoveItem(
            kind="curation" if isinstance(row, CurationNew) else "precuration",
            id=row.id,
            gene=gene,
            status=row.status.value,
            from_version=pinned.version,
            to_version=target.version,
            kept=sorted(k for k in kept if k in new_ids),
            dropped=sorted(k for k in evidence if k in gone),
            # only what the new version newly requires
            missing_required=[
                p for p in _missing(new, kept) if p not in _missing(old, evidence)
            ],
        )
        if not scope_active:  # RLS (054) refuses the write: dry run and apply alike
            item.skipped = INACTIVE_SCOPE
            out.items.append(item)
            continue
        computed = (
            _plan_curation(db, row, item, target.id, kept)
            if isinstance(row, CurationNew)
            else {}
        )
        out.items.append(item)
        planned.append((row, item, kept, computed))
    if dry_run:
        return out

    try:
        for plan in planned:
            _apply(db, plan, target, user_id)
        db.commit()
    except Exception:
        db.rollback()  # one transaction: nothing is moved
        raise
    logger.info(
        "Moved to methodology version",
        schema_id=str(schema_id),
        version=target.version,
        moved=len(planned),
        reopened=sum(1 for _, i, _, _ in planned if i.back_to),
    )
    return out
