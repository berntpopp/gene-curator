"""Batch resolve pasted gene identifiers (paste-a-list gene intake)."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.capabilities import VIEW, require
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.models import GeneScopeAssignment, UserNew
from app.schemas.gene_resolve import GeneResolveRequest, GeneResolveResponse
from app.services.gene_resolver import resolve_genes

router = APIRouter()


@router.post("/resolve", response_model=GeneResolveResponse)
async def resolve(
    request: GeneResolveRequest,
    db: Session = Depends(get_db),
    user: UserNew = Depends(get_current_active_user),
) -> GeneResolveResponse:
    """Resolve symbols, previous symbols, aliases and HGNC IDs, preserving input order."""
    # scope_id (the intake dialog): flag candidates the scope already has, in one query
    if request.scope_id:
        require(db, user, request.scope_id, VIEW)
    result = await resolve_genes(db, request.symbols)
    if request.scope_id:
        candidates = [c for i in result.items for c in i.candidates if c.gene_id]
        curator_of = dict(
            db.execute(
                select(GeneScopeAssignment.gene_id, UserNew.name)
                .outerjoin(
                    UserNew, UserNew.id == GeneScopeAssignment.assigned_curator_id
                )
                .where(
                    GeneScopeAssignment.scope_id == request.scope_id,
                    GeneScopeAssignment.gene_id.in_({c.gene_id for c in candidates}),
                    GeneScopeAssignment.is_active,
                )
            ).all()
        )
        for c in candidates:
            c.in_scope = c.gene_id in curator_of
            c.in_scope_curator = curator_of.get(c.gene_id) if c.gene_id else None
    return result
