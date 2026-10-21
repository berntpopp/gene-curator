"""Batch resolve pasted gene identifiers (paste-a-list gene intake)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.models import UserNew
from app.schemas.gene_resolve import GeneResolveRequest, GeneResolveResponse
from app.services.gene_resolver import resolve_genes

router = APIRouter()


@router.post("/resolve", response_model=GeneResolveResponse)
async def resolve(
    request: GeneResolveRequest,
    db: Session = Depends(get_db),
    _user: UserNew = Depends(get_current_active_user),
) -> GeneResolveResponse:
    """Resolve symbols, previous symbols, aliases and HGNC IDs, preserving input order."""
    return await resolve_genes(db, request.symbols)
