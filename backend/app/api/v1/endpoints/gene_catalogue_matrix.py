"""Catalogue genes x scopes matrix endpoint (read-only, public for public scopes)."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_optional
from app.core.logging import api_endpoint
from app.crud import gene_catalogue_matrix as matrix_crud
from app.models import UserNew
from app.schemas.gene_catalogue_matrix import MAX_MATRIX_SCOPES, MatrixResponse

router = APIRouter()


@router.get("/matrix", response_model=MatrixResponse)
@api_endpoint()
def get_catalogue_matrix(
    db: Session = Depends(get_db),
    current_user: UserNew | None = Depends(get_current_user_optional),
    scope_ids: list[UUID] = Query(
        ..., min_length=1, max_length=MAX_MATRIX_SCOPES, description="Scopes (columns)"
    ),
    search: str | None = Query(
        None,
        max_length=100,
        pattern=r"^[^\x00]*$",
        description="Gene symbol, HGNC ID or aliases (literal text)",
    ),
    agreement: Literal["agree", "disagree"] | None = Query(
        None, description="Only genes whose active classifications agree or disagree"
    ),
    classification: str | None = Query(
        None,
        max_length=100,
        description="Only genes with an active curation of this class in a shown scope",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sort_order: Literal["asc", "desc"] = Query("asc"),
) -> MatrixResponse:
    """Genes with a classification, stage and score per selected scope.

    Scopes the caller cannot see are dropped silently. In-progress curations appear only
    for scopes where the caller has an accepted membership; platform admins get no bypass.
    """
    return matrix_crud.get_matrix(
        db,
        scope_ids,
        current_user.id if current_user else None,
        search=search,
        agreement=agreement,
        classification=classification,
        skip=skip,
        limit=limit,
        descending=sort_order == "desc",
    )
