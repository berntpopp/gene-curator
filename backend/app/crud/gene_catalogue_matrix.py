"""Genes x scopes matrix for the catalogue.

Visibility is explicit, not left to RLS: a scope is visible when it is public or the caller
has an accepted, active membership. Platform admins get no bypass. Only members see
in-progress curations (non-active, non-archived). Query count is constant in the page size.
"""

from collections import defaultdict
from typing import Literal
from uuid import UUID

from sqlalchemy import String, func, or_, select
from sqlalchemy.orm import Session

from app.core.search_text import escape_like
from app.models import ActiveCuration, CurationNew, Gene, Scope, ScopeMembership
from app.models.models import CurationStatus
from app.schemas.gene_catalogue_matrix import (
    Agreement,
    MatrixCell,
    MatrixResponse,
    MatrixRow,
    MatrixScope,
)

_DONE = (CurationStatus.ACTIVE, CurationStatus.ARCHIVED)


def _agreement(cells: list[MatrixCell]) -> Agreement:
    verdicts = {
        c.classification.lower()
        for c in cells
        if c.classification and not c.in_progress
    }
    if not verdicts:
        return "none"
    if sum(1 for c in cells if c.classification and not c.in_progress) == 1:
        return "single"
    return "agree" if len(verdicts) == 1 else "disagree"


def get_matrix(
    db: Session,
    scope_ids: list[UUID],
    user_id: UUID | None,
    *,
    search: str | None = None,
    agreement: Literal["agree", "disagree"] | None = None,
    skip: int = 0,
    limit: int = 20,
    descending: bool = False,
) -> MatrixResponse:
    member_ids: set[UUID] = set()
    if user_id:
        member_ids = set(
            db.execute(
                select(ScopeMembership.scope_id).where(
                    ScopeMembership.user_id == user_id,
                    ScopeMembership.is_active.is_(True),
                    ScopeMembership.accepted_at.is_not(None),
                )
            )
            .scalars()
            .all()
        )

    found = (
        db.execute(
            select(Scope).where(
                Scope.id.in_(scope_ids),
                Scope.is_active.is_(True),
                or_(Scope.is_public.is_(True), Scope.id.in_(member_ids)),
            )
        )
        .scalars()
        .all()
    )
    by_id = {s.id: s for s in found}
    scopes = [by_id[i] for i in dict.fromkeys(scope_ids) if i in by_id]
    visible = list(by_id)
    mine = [i for i in visible if i in member_ids]

    active_genes = select(ActiveCuration.gene_id).where(
        ActiveCuration.archived_at.is_(None), ActiveCuration.scope_id.in_(visible)
    )
    gene_filter = [Gene.id.in_(active_genes)]
    if mine:
        gene_filter.append(
            Gene.id.in_(
                select(CurationNew.gene_id).where(
                    CurationNew.scope_id.in_(mine), CurationNew.status.not_in(_DONE)
                )
            )
        )
    query = select(Gene).where(or_(*gene_filter))

    if search:
        term = f"%{escape_like(search)}%"
        query = query.where(
            or_(
                Gene.approved_symbol.ilike(term, escape="\\"),
                Gene.hgnc_id.ilike(term, escape="\\"),
                Gene.previous_symbols.cast(String).ilike(term, escape="\\"),
                Gene.alias_symbols.cast(String).ilike(term, escape="\\"),
            )
        )
    if agreement:
        verdict = func.lower(CurationNew.computed_verdict)
        distinct = func.count(func.distinct(verdict))
        having = (
            [distinct > 1]
            if agreement == "disagree"
            else [distinct == 1, func.count() > 1]
        )
        classified = (
            select(ActiveCuration.gene_id)
            .join(CurationNew, CurationNew.id == ActiveCuration.curation_id)
            .where(
                ActiveCuration.archived_at.is_(None),
                ActiveCuration.scope_id.in_(visible),
                CurationNew.computed_verdict.is_not(None),
            )
            .group_by(ActiveCuration.gene_id)
            .having(*having)
        )
        query = query.where(Gene.id.in_(classified))

    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    # Gene.id breaks symbol ties so pages never repeat or skip rows.
    order = (
        (Gene.approved_symbol.desc(), Gene.id.desc())
        if descending
        else (Gene.approved_symbol.asc(), Gene.id.asc())
    )
    genes = db.execute(query.order_by(*order).offset(skip).limit(limit)).scalars().all()

    cells: dict[UUID, dict[UUID, MatrixCell]] = defaultdict(dict)
    gene_ids = [g.id for g in genes]
    if gene_ids and visible:
        in_progress = (
            db.execute(
                select(CurationNew)
                .where(
                    CurationNew.gene_id.in_(gene_ids),
                    CurationNew.scope_id.in_(mine),
                    CurationNew.status.not_in(_DONE),
                )
                .order_by(CurationNew.updated_at)
            )
            .scalars()
            .all()
            if mine
            else []
        )
        for c in in_progress:  # oldest first, so the latest revision overwrites
            cells[c.gene_id][c.scope_id] = _cell(c, in_progress=True)
        active = db.execute(
            select(CurationNew)
            .join(ActiveCuration, ActiveCuration.curation_id == CurationNew.id)
            .where(
                ActiveCuration.gene_id.in_(gene_ids),
                ActiveCuration.scope_id.in_(visible),
                ActiveCuration.archived_at.is_(None),
            )
        ).scalars()
        for c in active:  # an active curation outranks an in-progress revision
            cells[c.gene_id][c.scope_id] = _cell(c, in_progress=False)

    order_of = {s.id: n for n, s in enumerate(scopes)}
    rows = []
    for gene in genes:
        row_cells = sorted(cells[gene.id].values(), key=lambda c: order_of[c.scope_id])
        rows.append(
            MatrixRow(
                gene_id=gene.id,
                hgnc_id=gene.hgnc_id,
                approved_symbol=gene.approved_symbol,
                chromosome=gene.chromosome,
                location=gene.location,
                agreement=_agreement(row_cells),
                cells=row_cells,
            )
        )
    return MatrixResponse(
        scopes=[MatrixScope.model_validate(s, from_attributes=True) for s in scopes],
        rows=rows,
        total=total,
        skip=skip,
        limit=limit,
        has_next=skip + limit < total,
        has_prev=skip > 0,
    )


def _cell(c: CurationNew, *, in_progress: bool) -> MatrixCell:
    return MatrixCell(
        scope_id=c.scope_id,
        curation_id=c.id,
        classification=c.computed_verdict,
        stage=c.workflow_stage.value,
        status=c.status.value,
        total_score=(c.computed_scores or {}).get("total_score"),
        in_progress=in_progress,
    )
