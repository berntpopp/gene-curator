"""Export v1 of reviewed curations (#532): active and archived pointers, keyset-paged."""

from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, or_, select
from sqlalchemy.orm import Session, aliased, joinedload

from app.core.config import settings
from app.core.synopsis import synopsis_of
from app.crud.curation import get_disease_fields, section_total
from app.crud.scope_visibility import member_scope_ids, visible_scope_ids
from app.models import (
    ActiveCuration,
    CurationNew,
    CurationSchema,
    CurationStatus,
    Gene,
    Review,
    ReviewStatus,
    Scope,
    UserNew,
    WorkflowPair,
)
from app.models.curation import _MOI_SYNONYMS
from app.models.methodology import MethodologyVersion
from app.schemas.curation import entity_allele, relationship_of_key
from app.schemas.curation_export import (
    CurationExportPage,
    ExportCuration,
    ExportMethodology,
)
from app.services.clingen_adoption import adoption_agent, adoption_statement
from app.services.export_provenance import curation_contributions, evidence_lines
from app.services.publication_service import evidence_pmids

_MOI_HPO = {abbr.upper(): hpo.upper() for abbr, (_, hpo) in _MOI_SYNONYMS.items()}

# The pointer or the curation, whichever changed last (re-curation, archive, delete)
_changed_at = case(
    (CurationNew.updated_at > ActiveCuration.updated_at, CurationNew.updated_at),
    else_=ActiveCuration.updated_at,
)


def encode_cursor(at: datetime, row_id: UUID) -> str:
    """Opaque, URL-safe page cursor (base64url): "+00:00" in a raw query string is a space."""
    return urlsafe_b64encode(f"{at.isoformat()}|{row_id}".encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    """Inverse of encode_cursor; ValueError for anything else."""
    raw = urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
    at, _, row_id = raw.partition("|")
    return datetime.fromisoformat(at), UUID(row_id)


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
            CurationSchema.id,
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
        # outer: legacy rows pin no version (085 lets every caller read versions)
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
    members = set(db.scalars(member_scope_ids(user_id))) if user_id else set()
    # Fetched apart: .unique() cannot hash a JSON column
    schema_ids = {row[-2] for row in rows if row[-2]}
    uis: dict[UUID | None, dict[str, Any] | None] = dict(
        db.execute(
            select(CurationSchema.id, CurationSchema.ui_configuration).where(
                CurationSchema.id.in_(schema_ids)
            )
        )
        .tuples()
        .all()
    )
    # Approving reviewers (VA-Spec assessors), oldest first; RLS may hide reviews
    assessors: dict[UUID, list[tuple[str | None, datetime | None]]] = {}
    for cid, name, at in db.execute(
        select(Review.curation_id, UserNew.name, Review.reviewed_at)
        .join(UserNew, Review.reviewer_id == UserNew.id)
        .where(
            Review.curation_id.in_({row[1].id for row in rows}),
            Review.status == ReviewStatus.APPROVED,
        )
        .order_by(Review.reviewed_at)
    ):
        assessors.setdefault(cid, []).append((name or None, at))
    items = [_item(members, uis, assessors, *row) for row in rows[:limit]]
    last = rows[limit - 1] if len(rows) > limit else None
    return CurationExportPage(
        items=items,
        next_cursor=encode_cursor(last[-1], last[0].id) if last else None,
    )


def _item(
    members: set[UUID],
    uis: dict[UUID | None, dict[str, Any] | None],
    assessors: dict[UUID, list[tuple[str | None, datetime | None]]],
    ac: ActiveCuration,
    c: CurationNew,
    gene: Gene,
    scope: Scope,
    curator_name: str | None,
    reviewer_name: str | None,
    schema_name: str | None,
    version: int | None,
    schema_id: UUID | None,
    updated_at: datetime,
) -> ExportCuration:
    # #613: an adoption has no points of ours, also one scored before the fix
    scores: dict[str, Any] = {} if c.clingen_adoption else (c.computed_scores or {})
    # #558: members always; others only when the public scope opted in
    detail = scope.id in members or (scope.is_public and scope.export_evidence_public)
    parts = ac.entity_key.split("|")  # MONDO|MOI[|SUSCEPTIBILITY[|ALLELE]]
    moi = parts[1] if len(parts) > 1 else ""
    pre = c.precuration.evidence_data if c.precuration else None
    lines = evidence_lines(c.evidence_data, c.row_provenance) if detail else None
    made = curation_contributions(
        curator_name,
        c.created_at,
        reviewer_name,
        c.approved_at,
        lines or [],
        assessors.get(c.id),
    )
    made[1:1] = adoption_agent(c, curator_name)  # after the curator, as row agents are
    return ExportCuration(
        curation_id=c.id,
        entity_key=ac.entity_key,
        url=f"{settings.GENE_CURATOR_FRONTEND_URL}/scopes/{scope.id}/curations/{c.id}",
        status=c.status.value,
        scope_name=scope.name,
        hgnc_id=gene.hgnc_id,
        approved_symbol=gene.approved_symbol,
        **get_disease_fields(c.evidence_data, pre),
        moi_hpo_id=_MOI_HPO.get(moi),
        relationship_type=relationship_of_key(ac.entity_key),
        risk_allele=entity_allele(ac.entity_key, c.evidence_data, pre),
        computed_verdict=None if c.clingen_adoption else c.computed_verdict,
        final_classification=c.final_classification,
        curator_classification_rationale=c.curator_classification_rationale,
        genetic_score=section_total(scores, "genetic"),
        experimental_score=section_total(scores, "experimental"),
        association_score=section_total(scores, "association"),
        total_score=scores.get("total_score"),
        methodology=ExportMethodology(
            schema_name=schema_name,
            version=version,
            version_id=c.methodology_version_id,
        ),
        pmids=sorted(evidence_pmids(c.evidence_data), key=int),
        evidence=c.evidence_data if detail else None,
        scores=c.computed_scores if detail and not c.clingen_adoption else None,
        summary=c.computed_summary if detail else None,
        curator_name=curator_name,
        reviewer_name=reviewer_name,
        approved_at=c.approved_at,
        activated_at=ac.activated_at,
        archived_at=ac.archived_at,
        archive_reason=ac.archive_reason,
        updated_at=updated_at,
        adoption=adoption_statement(c, curator_name, reviewer_name),
        contributions=made,
        evidence_lines=lines,
        synopsis=synopsis_of(c.evidence_data, uis.get(schema_id)) if detail else None,
    )
