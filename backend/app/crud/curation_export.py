"""Export v1 of reviewed curations (#532): active and archived pointers, keyset-paged."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, or_, select
from sqlalchemy.orm import Session, aliased, joinedload

from app.core.config import settings
from app.crud.curation import get_disease_fields
from app.crud.scope_visibility import member_scope_ids, visible_scope_ids
from app.models import (
    ActiveCuration,
    CurationNew,
    CurationSchema,
    CurationStatus,
    Gene,
    Scope,
    UserNew,
    WorkflowPair,
)
from app.models.curation import _MOI_SYNONYMS
from app.models.methodology import MethodologyVersion
from app.schemas.curation_export import (
    CurationExportPage,
    ExportCuration,
    ExportMethodology,
)
from app.services.publication_service import evidence_pmids

_MOI_HPO = {abbr.upper(): hpo.upper() for abbr, (_, hpo) in _MOI_SYNONYMS.items()}

# The pointer or the curation, whichever changed last (re-curation, archive, delete)
_changed_at = case(
    (CurationNew.updated_at > ActiveCuration.updated_at, CurationNew.updated_at),
    else_=ActiveCuration.updated_at,
)


def export_curations(
    db: Session,
    user_id: UUID | None,
    scope_id: UUID | None,
    updated_since: datetime | None,
    after: tuple[datetime, UUID] | None,
    limit: int,
) -> CurationExportPage:
    curator, reviewer = aliased(UserNew), aliased(UserNew)
    query = (
        select(
            ActiveCuration,
            CurationNew,
            Gene,
            Scope,
            curator.name,
            reviewer.name,
            CurationSchema.name,
            MethodologyVersion.version,
            _changed_at,
        )
        .options(joinedload(CurationNew.precuration))
        .join(CurationNew, ActiveCuration.curation_id == CurationNew.id)
        .join(Gene, ActiveCuration.gene_id == Gene.id)
        .join(Scope, ActiveCuration.scope_id == Scope.id)
        .outerjoin(curator, CurationNew.created_by == curator.id)
        .outerjoin(reviewer, CurationNew.approved_by == reviewer.id)
        .outerjoin(WorkflowPair, CurationNew.workflow_pair_id == WorkflowPair.id)
        .outerjoin(CurationSchema, WorkflowPair.curation_schema_id == CurationSchema.id)
        # RLS hides methodology versions from anonymous callers: version is then null
        .outerjoin(
            MethodologyVersion,
            CurationNew.methodology_version_id == MethodologyVersion.id,
        )
        .where(
            ActiveCuration.scope_id.in_(visible_scope_ids(user_id)),
            # Same rule as curation RLS (050): non-members see active curations only
            or_(
                CurationNew.status == CurationStatus.ACTIVE,
                ActiveCuration.scope_id.in_(member_scope_ids(user_id)),
            ),
        )
        .order_by(_changed_at, ActiveCuration.id)
        .limit(limit + 1)
    )
    if scope_id:
        query = query.where(ActiveCuration.scope_id == scope_id)
    if updated_since:
        query = query.where(_changed_at >= updated_since)
    if after:
        query = query.where(
            or_(
                _changed_at > after[0],
                and_(_changed_at == after[0], ActiveCuration.id > after[1]),
            )
        )
    rows = db.execute(query).unique().all()
    items = [_item(*row) for row in rows[:limit]]
    last = rows[limit - 1] if len(rows) > limit else None
    return CurationExportPage(
        items=items,
        next_cursor=f"{last[-1].isoformat()}|{last[0].id}" if last else None,
    )


def _item(
    ac: ActiveCuration,
    c: CurationNew,
    gene: Gene,
    scope: Scope,
    curator_name: str | None,
    reviewer_name: str | None,
    schema_name: str | None,
    version: int | None,
    updated_at: datetime,
) -> ExportCuration:
    scores: dict[str, Any] = c.computed_scores or {}
    _, _, moi = ac.entity_key.partition("|")
    return ExportCuration(
        curation_id=c.id,
        entity_key=ac.entity_key,
        url=f"{settings.GENE_CURATOR_FRONTEND_URL}/scopes/{scope.id}/curations/{c.id}",
        status=c.status.value,
        scope_name=scope.name,
        hgnc_id=gene.hgnc_id,
        approved_symbol=gene.approved_symbol,
        **get_disease_fields(
            c.evidence_data, c.precuration.evidence_data if c.precuration else None
        ),
        moi_hpo_id=_MOI_HPO.get(moi),
        computed_verdict=c.computed_verdict,
        genetic_score=scores.get("genetic_evidence_total"),
        experimental_score=scores.get("experimental_evidence_total"),
        total_score=scores.get("total_score"),
        methodology=ExportMethodology(
            schema_name=schema_name,
            version=version,
            version_id=c.methodology_version_id,
        ),
        pmids=sorted(evidence_pmids(c.evidence_data), key=int),
        curator_name=curator_name,
        reviewer_name=reviewer_name,
        approved_at=c.approved_at,
        activated_at=ac.activated_at,
        archived_at=ac.archived_at,
        archive_reason=ac.archive_reason,
        updated_at=updated_at,
    )
