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

from app.core.capabilities import (
    EDIT,
    allowed_pair_ids,
    require,
    require_active_scope,
)
from app.core.database import raise_if_rls_denied
from app.core.logging import get_logger
from app.crud.curation import _patched, _update_computed_scores, open_curation_id
from app.crud.curator_classification import allowed_classifications
from app.crud.precuration_entity import entity_key_of
from app.crud.review_round import reassign_earlier_reviewers
from app.mcp.audit import request_agent
from app.models import (
    AuditLogNew,
    CurationNew,
    CurationStatus,
    Gene,
    NotificationNew,
    ReviewItemComment,
    Scope,
    UserNew,
    WorkflowPair,
    WorkflowStage,
)
from app.models.model_enums import NotificationType
from app.schemas.clingen_adoption import (
    ClinGenAdoptionItem,
    ClinGenAdoptionResult,
    ClinGenAdoptionRow,
    entity_errors,
)
from app.schemas.curation import CLASSIFICATION_KEYS, CurationUpdate, class_key
from app.schemas.provenance import Agent, Contribution, contribution
from app.scoring.point_limits import scoring_configuration
from app.services.evidence_diff import NEW_REVIEW_ROUND
from app.services.export_provenance import _software

logger = get_logger(__name__)

ADOPTION_COMMENT = (
    "Classification adopted from ClinGen, which holds its evidence and points; none are "
    "scored here. Diagnostics can still be added while it is in review."
)


def _row_errors(db: Session, row: ClinGenAdoptionRow, gene: Gene | None) -> list[str]:
    record = row.clingen
    if gene is None:
        return ["gene_id: gene not found"]
    errors = entity_errors(
        record, gene.hgnc_id, row.mondo_id, row.mode_of_inheritance, "clingen"
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
        elif (
            allowed := allowed_pair_ids(scope)
        ) and row.workflow_pair_id not in allowed:
            row_errors.append("workflow_pair_id: not allowed in this scope (#284)")
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
            ClinGenAdoptionItem(
                row=i,
                cggv_id=row.clingen.cggv_id,
                action="refused" if row_errors else "create",
            )
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
        clingen_adoption=record.model_dump(mode="json")
        | ({"adopted_by_agent": agent} if (agent := request_agent.get()) else {}),
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


def adopted_edit_allowed(curation: CurationNew, update: CurationUpdate) -> bool:
    """#613: an adoption in review still takes evidence (diagnostics: ClinGen has none,
    and nothing of it is scored); 409 for a new entity or classification, which are
    ClinGen's. False for anything else, which the draft-only rule refuses."""
    if not (curation.clingen_adoption and curation.status == CurationStatus.IN_REVIEW):
        return False
    entity = (curation.evidence_data or {}).get("entity_definition")
    after = (
        _patched(curation, update.evidence_data, update.merge)[0]
        if update.evidence_data is not None
        else curation.evidence_data or {}
    )
    if (
        CLASSIFICATION_KEYS & update.model_fields_set
        or after.get("entity_definition") != entity
    ):
        raise HTTPException(
            409, "An adopted curation keeps ClinGen's entity and classification"
        )
    return True


def restart_review_round(db: Session, curation: CurationNew, user_id: UUID) -> None:
    """After an edit in review, as on resubmit: approvals of the old content no longer
    count and each earlier reviewer is asked again (a round starts at submitted_at)."""
    curation.submitted_at = datetime.now(UTC)
    db.add(  # the new round is a submission: diff baseline=previous_submission (KGDB e2e)
        AuditLogNew(
            entity_type="curations",
            entity_id=curation.id,
            scope_id=curation.scope_id,
            operation="UPDATE",
            change_type=NEW_REVIEW_ROUND,
            user_id=user_id,
            previous_status=curation.status.value,
            new_status=curation.status.value,
            changes={"evidence_data": curation.evidence_data},
        )
    )
    db.flush()
    gene = db.get(Gene, curation.gene_id)
    for reviewer_id in reassign_earlier_reviewers(db, curation, user_id):
        db.add(  # as a resubmit notifies (workflow_engine)
            NotificationNew(
                user_id=reviewer_id,
                type=NotificationType.REVIEW_ASSIGNED,
                title="New review assigned",
                message=f"New review assigned: {gene.approved_symbol if gene else 'Unknown'}",
                link=f"/scopes/{curation.scope_id}/curations/{curation.id}",
            )
        )
    db.commit()
    db.refresh(curation)


def adoption_agent(
    curation: CurationNew, curator_name: str | None
) -> list[Contribution]:
    """The AI agent that adopted it over MCP, as a software curator on the curator's
    behalf (the adoption has no evidence rows to carry it)."""
    agent = (curation.clingen_adoption or {}).get("adopted_by_agent")
    if not isinstance(agent, dict):
        return []
    return [
        contribution(
            "curator",
            _software(agent),
            curation.created_at,
            actedOnBehalfOf=Agent(name=curator_name, agentType="person"),
        )
    ]


def adoption_statement(
    curation: CurationNew, curator_name: str | None, approver_name: str | None
) -> dict[str, Any] | None:
    """The adopted ClinGen record as a VA-Spec-style statement for the export; None if the
    curation adopted nothing."""
    record = curation.clingen_adoption
    if not record:
        return None
    # No contributor id: the export is public and user ids are not (names already are)
    made = [
        contribution(
            "curator", Agent(name=curator_name, agentType="person"), curation.created_at
        ),
    ]
    if curation.approved_by:
        made.append(
            contribution(
                "approver",
                Agent(name=approver_name, agentType="person"),
                curation.approved_at,
            )
        )
    return clingen_statement(record, made)


def clingen_statement(
    record: dict[str, Any] | None, ours: list[Contribution] | None = None
) -> dict[str, Any] | None:
    """A stored ClinGen record as a VA-Spec-style statement: the GCEP as interpreter, then
    `ours` (who adopted and approved it); None without a record. Also the export's
    clingen_reference, which KGDB parses with the adoption."""
    if not record:
        return None
    made = [
        contribution(
            "interpreter",
            Agent(name=record["expert_panel"], agentType="organization"),
            record["classified_date"],
        ),
        *(ours or []),
    ]
    contributions = [c.model_dump(mode="json", exclude_none=True) for c in made]
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
