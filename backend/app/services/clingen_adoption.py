"""Adopt ClinGen gene-disease validity classifications (#105).

An agent (or curator) sends the GeneFoundry `clingen_get_gene_validity` record per entity;
Gene Curator checks it against the entity and the schema, never fetches it. Each adopted
curation goes straight to review with an automatic comment; a different person approves
it through the normal workflow (4-eyes, D1). The ClinGen expert panel already did the
precuration, so adoption needs no precuration of ours.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.core.capabilities import EDIT, require, require_active_scope
from app.core.database import raise_if_rls_denied
from app.core.logging import get_logger
from app.crud.curation import _update_computed_scores, open_curation_id
from app.crud.curator_classification import allowed_classifications
from app.crud.precuration_entity import entity_key_of
from app.models import (
    CurationNew,
    CurationStatus,
    Gene,
    ReviewItemComment,
    Scope,
    UserNew,
    WorkflowPair,
    WorkflowStage,
)
from app.models.curation import _MOI_SYNONYMS
from app.schemas.clingen_adoption import (
    ClinGenAdoptionItem,
    ClinGenAdoptionResult,
    ClinGenAdoptionRow,
)
from app.schemas.curation import class_key
from app.scoring.point_limits import scoring_configuration

logger = get_logger(__name__)

ADOPTION_COMMENT = (
    "Curation details were taken from ClinGen as available there, the individual point "
    "values must be re-scored manually."
)

# VA-Spec 1.0 contribution roles (ClinGen SEPIO ContributoryRole value set, #593)
SEPIO_ROLES = {
    "curator": "SEPIO:0000156",
    "approver": "SEPIO:0000155",
    "interpreter": "SEPIO:0000331",
}


def _moi(value: str) -> str:
    """AD, 'Autosomal dominant inheritance' and HP:0000006 alike, as the entity key squashes."""
    squashed = "".join(c for c in value.lower() if c not in " _-").replace(
        "inheritance", ""
    )
    for abbr, synonyms in _MOI_SYNONYMS.items():
        if squashed == abbr or squashed in synonyms:
            return abbr.upper()
    return squashed.upper()


def _mondo(value: str) -> str:
    return value.strip().upper().replace("_", ":")


def _row_errors(db: Session, row: ClinGenAdoptionRow, gene: Gene | None) -> list[str]:
    record = row.clingen
    errors = []
    if gene is None:
        return ["gene_id: gene not found"]
    if gene.hgnc_id != record.hgnc_id:
        errors.append(f"clingen.hgnc_id: {record.hgnc_id} is not {gene.hgnc_id}")
    if _mondo(record.mondo) != _mondo(row.mondo_id):
        errors.append(
            f"clingen.mondo: {record.mondo} is not the entity's {row.mondo_id}"
        )
    if _moi(record.moi) != _moi(row.mode_of_inheritance):
        errors.append(
            f"clingen.moi: {record.moi} is not the entity's {row.mode_of_inheritance}"
        )
    if db.get(WorkflowPair, row.workflow_pair_id) is None:
        return [*errors, "workflow_pair_id: workflow pair not found"]
    allowed = allowed_classifications(scoring_configuration(db, row.workflow_pair_id))
    if class_key(record.classification) not in allowed:
        errors.append(
            f"clingen.classification: {record.classification} is not one of "
            f"{', '.join(allowed)}"
        )
    return errors


def _adopted_id(db: Session, row: ClinGenAdoptionRow, entity_key: str) -> UUID | None:
    """A live curation of the entity that adopted this ClinGen record already."""
    for curation in db.scalars(
        select(CurationNew).where(
            CurationNew.gene_id == row.gene_id,
            CurationNew.scope_id == row.scope_id,
            CurationNew.entity_key == entity_key,
            CurationNew.status != CurationStatus.ARCHIVED,
            CurationNew.clingen_adoption.isnot(None),
        )
    ):
        if (curation.clingen_adoption or {}).get("cggv_id") == row.clingen.cggv_id:
            return curation.id
    return None


def _evidence(row: ClinGenAdoptionRow) -> dict[str, Any]:
    entity = {"mondo_id": row.mondo_id, "mode_of_inheritance": row.mode_of_inheritance}
    if row.disease_name:
        entity["disease_name"] = row.disease_name
    return {"entity_definition": entity}


def adopt(
    db: Session, rows: list[ClinGenAdoptionRow], user: UserNew, *, dry_run: bool
) -> ClinGenAdoptionResult:
    """Check every row, then (unless dry_run or any row fails) create all curations in review
    in one transaction. 403 for a scope the user may not curate in."""
    errors: list[str] = []
    items: list[ClinGenAdoptionItem] = []
    plan: list[tuple[ClinGenAdoptionRow, str]] = []
    seen: set[tuple[UUID, UUID, str]] = set()
    for i, row in enumerate(rows):
        require(db, user, row.scope_id, EDIT)
        scope = db.get(Scope, row.scope_id)
        require_active_scope(scope)
        row_errors = _row_errors(db, row, db.get(Gene, row.gene_id))
        if scope is None:  # only platform admins pass require() for an unknown scope
            row_errors.insert(0, "scope_id: scope not found")
        key = entity_key_of(db, _evidence(row))
        if not row_errors and (adopted := _adopted_id(db, row, key)):
            items.append(
                ClinGenAdoptionItem(
                    row=i,
                    cggv_id=row.clingen.cggv_id,
                    action="unchanged",
                    curation_id=adopted,
                )
            )
            continue
        if not row_errors and (
            open_id := open_curation_id(db, row.gene_id, row.scope_id, key)
        ):
            row_errors.append(f"entity: already has open curation {open_id}")
        if (row.gene_id, row.scope_id, key) in seen:
            row_errors.append("entity: another row adopts it too")
        seen.add((row.gene_id, row.scope_id, key))
        errors.extend(f"rows[{i}].{e}" for e in row_errors)
        plan.append((row, key))
        items.append(
            ClinGenAdoptionItem(row=i, cggv_id=row.clingen.cggv_id, action="create")
        )
    result = ClinGenAdoptionResult(dry_run=dry_run, errors=errors, items=items)
    if errors or dry_run:
        return result
    created = _write(db, plan, user.id)
    ids = iter(c.id for c in created)
    for item in items:
        if item.action == "create":
            item.curation_id = next(ids)
    logger.info(
        "ClinGen classifications adopted", count=len(created), user_id=str(user.id)
    )
    return result


def _create(
    db: Session, row: ClinGenAdoptionRow, entity_key: str, user_id: UUID
) -> CurationNew:
    now = datetime.now(UTC)
    record = row.clingen
    curation = CurationNew(
        gene_id=row.gene_id,
        scope_id=row.scope_id,
        workflow_pair_id=row.workflow_pair_id,
        entity_key=entity_key,
        evidence_data=_evidence(row),
        status=CurationStatus.IN_REVIEW,
        workflow_stage=WorkflowStage.REVIEW,
        is_draft=False,
        lock_version=0,
        curator_classification=class_key(record.classification),
        curator_classification_rationale=record.citation,
        clingen_adoption=record.model_dump(mode="json"),
        created_by=user_id,
        updated_by=user_id,
        submitted_by=user_id,
        submitted_at=now,
        created_at=now,
        updated_at=now,
    )
    with db.no_autoflush:
        _update_computed_scores(db, curation, lookup=False)
    db.add(curation)
    db.flush()
    db.add(
        ReviewItemComment(
            curation_id=curation.id,
            author_id=user_id,
            item_path="clingen_adoption",
            body=ADOPTION_COMMENT,
        )
    )
    return curation


def _write(
    db: Session, plan: list[tuple[ClinGenAdoptionRow, str]], user_id: UUID
) -> list[CurationNew]:
    """All curations in one transaction; the flush of each can already hit the index."""
    try:
        created = [_create(db, row, key, user_id) for row, key in plan]
        db.commit()
        return created
    except IntegrityError as e:  # a concurrent curation of an entity won its open index
        db.rollback()
        raise HTTPException(
            409, "An entity got an open curation meanwhile; retry"
        ) from e
    except DBAPIError as e:
        db.rollback()
        raise_if_rls_denied(e, "Adopting here needs an accepted curator membership")
        raise


def _contribution(
    name: str | None, agent_type: str, role: str, date: Any
) -> dict[str, Any]:
    """No contributor id: the export is public and user ids are not (names already are)."""
    return {
        "contributor": {"name": name, "agentType": agent_type},
        "activityType": {
            "name": role,
            "primaryCoding": {"system": "SEPIO", "code": SEPIO_ROLES[role]},
        },
        "date": date.isoformat() if isinstance(date, datetime) else date,
    }


def adoption_statement(
    curation: CurationNew, curator_name: str | None, approver_name: str | None
) -> dict[str, Any] | None:
    """The adopted ClinGen record as a VA-Spec-style statement for the export; None if the
    curation adopted nothing."""
    record = curation.clingen_adoption
    if not record:
        return None
    contributions = [
        _contribution(
            record["expert_panel"],
            "organization",
            "interpreter",
            record["classified_date"],
        ),
        _contribution(curator_name, "person", "curator", curation.created_at),
    ]
    if curation.approved_by:
        contributions.append(
            _contribution(
                approver_name,
                "person",
                "approver",
                curation.approved_at,
            )
        )
    return {
        "type": "Statement",
        "id": record["cggv_id"],
        "classification": record["classification"],
        "moi": record["moi"],
        "mondo": record["mondo"],
        "reportedIn": [
            {
                "documentType": "ClinGen gene-disease validity curation",
                "title": record["citation"],
                "urls": [record["permalink"]],
            }
        ],
        "contributions": contributions,
        "extensions": [
            {"name": k, "value": record[k]} for k in ("retrieved_at", "record_sha256")
        ],
    }
