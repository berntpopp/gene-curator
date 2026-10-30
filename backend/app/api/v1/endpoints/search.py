"""GET /search: grouped hits for the command palette.

Visibility mirrors the list endpoints: genes are global; scopes and curations come from
the caller's accepted, active memberships (platform admins see all active scopes, as in
list_scopes / list_curations). Three queries, whatever the limit.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.logging import api_endpoint
from app.core.search_text import MAX_SEARCH, escape_like
from app.crud.gene_catalogue_matrix import VERDICT_ORDER
from app.crud.scope_visibility import visible_scope_ids
from app.models.models import (
    ActiveCuration,
    CurationNew,
    CurationStatus,
    Gene,
    PrecurationNew,
    Scope,
    UserNew,
)
from app.schemas.curation import disease_fields
from app.schemas.search import CurationHit, GeneHit, ScopeHit, SearchResponse

router = APIRouter()

MIN_Q, MAX_Q = 2, MAX_SEARCH
# a gene split into disease entities (#530) has one curation per entity and scope
# ponytail: a fixed cap; page or group by gene if a query ever matches more
CURATION_HITS = 20


def _like(q: str) -> tuple[str, str]:
    """Escape LIKE wildcards; returns (contains, prefix) patterns."""
    esc = escape_like(q)
    return f"%{esc}%", f"{esc}%"


def _rank(column: Any, q: str, prefix: str) -> Any:
    """Exact match first, then prefix, then the rest."""
    return case(
        (func.lower(column) == q.lower(), 0),
        (column.ilike(prefix, escape="\\"), 1),
        else_=2,
    )


def _visible(stmt: Any, user: UserNew, scope_id_col: Any) -> Any:
    """Shared rule (crud/scope_visibility): public, or accepted membership; no admin bypass."""
    return stmt.where(scope_id_col.in_(visible_scope_ids(user.id)))


@router.get("", response_model=SearchResponse)
@api_endpoint()
def search(
    q: str = Query(..., description="Search text"),
    limit: int = Query(
        5, ge=1, le=10, description="Max gene and scope hits; curations: up to 20"
    ),
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> SearchResponse:
    q = q.strip()
    if not MIN_Q <= len(q) <= MAX_Q or "\x00" in q:
        raise HTTPException(
            status_code=422, detail=f"q must be {MIN_Q}-{MAX_Q} characters"
        )
    contains, prefix = _like(q)

    # Highest active classification in a scope the caller can see (#273); a gene split
    # into several disease entities (#530) shows its strongest, newest first on ties
    rank = case(
        {v: n for n, v in enumerate(VERDICT_ORDER)},
        value=func.lower(CurationNew.computed_verdict),
        else_=len(VERDICT_ORDER),
    )
    classification = (
        select(CurationNew.computed_verdict)
        .join(ActiveCuration, ActiveCuration.curation_id == CurationNew.id)
        .where(
            ActiveCuration.gene_id == Gene.id,
            ActiveCuration.archived_at.is_(None),
            ActiveCuration.scope_id.in_(visible_scope_ids(current_user.id)),
        )
        .order_by(rank, ActiveCuration.activated_at.desc())
        .limit(1)
        .correlate(Gene)
        .scalar_subquery()
    )
    genes = db.execute(
        select(Gene.id, Gene.approved_symbol, Gene.hgnc_id, classification)
        .where(
            Gene.approved_symbol.ilike(contains, escape="\\")
            | Gene.hgnc_id.ilike(prefix, escape="\\")
        )
        .order_by(_rank(Gene.approved_symbol, q, prefix), Gene.approved_symbol, Gene.id)
        .limit(limit)
    ).all()

    scopes = db.execute(
        _visible(
            select(Scope.id, Scope.name, Scope.display_name).where(
                Scope.is_active == True,  # noqa: E712
                Scope.name.ilike(contains, escape="\\")
                | Scope.display_name.ilike(contains, escape="\\"),
            ),
            current_user,
            Scope.id,
        )
        .order_by(_rank(Scope.name, q, prefix), Scope.name, Scope.id)
        .limit(limit)
    ).all()

    curations = db.execute(
        _visible(
            select(
                CurationNew.id,
                Gene.approved_symbol,
                CurationNew.scope_id,
                Scope.name,
                CurationNew.status,
                CurationNew.evidence_data,
                PrecurationNew.evidence_data,
            )
            .join(Gene, CurationNew.gene_id == Gene.id)
            .join(Scope, CurationNew.scope_id == Scope.id)
            .outerjoin(PrecurationNew, CurationNew.precuration_id == PrecurationNew.id)
            .where(
                CurationNew.status != CurationStatus.ARCHIVED,
                Gene.approved_symbol.ilike(contains, escape="\\"),
            ),
            current_user,
            CurationNew.scope_id,
        )
        .order_by(
            _rank(Gene.approved_symbol, q, prefix),
            Gene.approved_symbol,
            CurationNew.updated_at.desc(),
            CurationNew.id,
        )
        .limit(CURATION_HITS)
    ).all()

    return SearchResponse(
        genes=[
            GeneHit(id=r[0], symbol=r[1], hgnc_id=r[2], classification=r[3])
            for r in genes
        ],
        curations=[
            CurationHit(
                id=r[0],
                gene_symbol=r[1],
                scope_id=r[2],
                scope_name=r[3],
                status=getattr(r[4], "value", r[4]),
                **disease_fields(r[5], r[6]),
            )
            for r in curations
        ],
        scopes=[ScopeHit(id=r[0], name=r[1], display_name=r[2]) for r in scopes],
    )
