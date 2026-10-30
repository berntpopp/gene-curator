"""Genes x scopes matrix for the catalogue.

Visibility is explicit, not left to RLS: a scope is visible when it is public or the caller
has an accepted, active membership. Platform admins get no bypass. Only members see
in-progress curations (non-active, non-archived). Query count is constant in the page size.
"""

from collections import defaultdict
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import String, func, or_, select
from sqlalchemy.orm import Session

from app.core.search_text import escape_like
from app.crud.curator_classification import class_key_sql
from app.models import ActiveCuration, CurationNew, Gene, Scope, ScopeMembership
from app.models.models import CurationStatus
from app.schemas.curation import class_key
from app.schemas.gene_catalogue_matrix import (
    Agreement,
    MatrixCell,
    MatrixResponse,
    MatrixRow,
    MatrixScope,
)

_DONE = (CurationStatus.ACTIVE, CurationStatus.ARCHIVED)


# Highest first: a scope with several active entities shows its strongest verdict.
VERDICT_ORDER = ("definitive", "strong", "moderate", "limited", "disputed", "refuted")


def verdict_rank(verdict: str | None) -> int:
    v = class_key(verdict or "")
    return VERDICT_ORDER.index(v) if v in VERDICT_ORDER else len(VERDICT_ORDER)


def _agreement(active: list[CurationNew]) -> Agreement:
    """Per gene-disease-MOI entity (#530): scopes agree or disagree on the same entity."""
    by_entity: dict[str, list[str]] = defaultdict(list)
    for c in active:
        if c.final_classification:
            by_entity[c.entity_key].append(class_key(c.final_classification))
    if any(len(set(v)) > 1 for v in by_entity.values()):
        return "disagree"
    if any(len(v) > 1 for v in by_entity.values()):
        return "agree"
    return "single" if by_entity else "none"


def _with_class(query: Any, visible: list[UUID], classification: str | None) -> Any:
    """Only genes with a visible active curation of this class (any case), #539."""
    if not classification:
        return query
    return query.where(
        Gene.id.in_(
            select(ActiveCuration.gene_id)
            .join(CurationNew, CurationNew.id == ActiveCuration.curation_id)
            .where(
                ActiveCuration.archived_at.is_(None),
                ActiveCuration.scope_id.in_(visible),
                class_key_sql(CurationNew.final_classification)
                == class_key(classification),
            )
        )
    )


def get_matrix(
    db: Session,
    scope_ids: list[UUID],
    user_id: UUID | None,
    *,
    search: str | None = None,
    agreement: Literal["agree", "disagree"] | None = None,
    classification: str | None = None,
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
        distinct = func.count(
            func.distinct(class_key_sql(CurationNew.final_classification))
        )

        def entities(*having: Any) -> Any:
            """Genes with an entity whose visible active verdicts match `having`."""
            return (
                select(ActiveCuration.gene_id)
                .join(CurationNew, CurationNew.id == ActiveCuration.curation_id)
                .where(
                    ActiveCuration.archived_at.is_(None),
                    ActiveCuration.scope_id.in_(visible),
                    CurationNew.final_classification.is_not(None),
                )
                .group_by(ActiveCuration.gene_id, ActiveCuration.entity_key)
                .having(*having)
            )

        disagreeing = entities(distinct > 1)
        query = query.where(
            Gene.id.in_(disagreeing)
            if agreement == "disagree"
            else Gene.id.in_(entities(distinct == 1, func.count() > 1))
            & Gene.id.not_in(disagreeing)
        )

    query = _with_class(query, visible, classification)

    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    # Gene.id breaks symbol ties so pages never repeat or skip rows.
    order = (
        (Gene.approved_symbol.desc(), Gene.id.desc())
        if descending
        else (Gene.approved_symbol.asc(), Gene.id.asc())
    )
    genes = db.execute(query.order_by(*order).offset(skip).limit(limit)).scalars().all()

    cells: dict[UUID, dict[UUID, MatrixCell]] = defaultdict(dict)
    actives: dict[UUID, list[CurationNew]] = defaultdict(list)
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
        # An active curation outranks an in-progress revision; several active entities
        # in one scope show the highest verdict (last write wins; stable on id).
        for c in sorted(
            active, key=lambda c: (-verdict_rank(c.final_classification), str(c.id))
        ):
            actives[c.gene_id].append(c)
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
                agreement=_agreement(actives[gene.id]),
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
        classification=c.final_classification,
        stage=c.workflow_stage.value,
        status=c.status.value,
        total_score=(c.computed_scores or {}).get("total_score"),
        in_progress=in_progress,
    )
