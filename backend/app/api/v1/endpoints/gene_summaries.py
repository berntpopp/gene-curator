"""Gene summary endpoints

Provides access to gene summary aggregations across scopes.
Implements public/private data filtering based on authentication.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import (
    get_current_active_user,
    get_current_user_optional,
)
from app.core.logging import api_endpoint, get_logger
from app.crud.scope_visibility import member_scope_ids, visible_scope_ids
from app.models.models import CurationNew, Gene, Scope, UserNew
from app.schemas.gene_summary import GeneSummaryFull, GeneSummaryPublic
from app.services.gene_summary_service import GeneSummaryService

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/genes/{gene_id}/summary",
    response_model=GeneSummaryPublic | None,
)
@api_endpoint()
async def get_gene_public_summary(
    *,
    db: Session = Depends(get_db),
    gene_id: UUID,
) -> GeneSummaryPublic | None:
    """Get public gene summary (no authentication required)

    Returns aggregated statistics for gene across public scopes only.
    Private scope data is excluded from the response.

    Args:
        db: Database session
        gene_id: UUID of the gene

    Returns:
        Public gene summary with only public scope data; null when the gene has no
        public curation (an empty result, so the signed-out gene page logs no 404)

    Raises:
        HTTPException: 404 if the gene does not exist
    """
    service = GeneSummaryService(db)
    summary = service.get_public_summary(gene_id)

    if not summary:
        if db.get(Gene, gene_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Gene not found"
            )
        return None

    logger.debug(
        "Public gene summary retrieved",
        gene_id=str(gene_id),
        public_scopes=summary.public_scopes_count,
    )

    return summary


@router.get(
    "/genes/{gene_id}/summary/full",
    response_model=GeneSummaryFull,
)
@api_endpoint()
async def get_gene_full_summary(
    *,
    db: Session = Depends(get_db),
    gene_id: UUID,
    current_user: UserNew = Depends(get_current_active_user),
) -> GeneSummaryFull:
    """Get complete gene summary including private scopes (requires authentication)

    Returns aggregated statistics for gene across all scopes visible to the user.
    Filters scope summaries based on user's scope memberships.

    Args:
        db: Database session
        gene_id: UUID of the gene
        current_user: Current authenticated user

    Returns:
        Complete gene summary with public and accessible private scope data

    Raises:
        HTTPException: 404 if gene not found or has no curations
    """
    return GeneSummaryService(db).get_full_summary(gene_id, current_user)


@router.get(
    "/genes/{gene_id}/scopes",
    response_model=list[dict[str, Any]],
)
@api_endpoint()
async def get_gene_curating_scopes(
    *,
    db: Session = Depends(get_db),
    gene_id: UUID,
    current_user: UserNew | None = Depends(get_current_user_optional),
) -> list[dict[str, Any]]:
    """Get list of scopes curating this gene

    Public active scopes are visible to everyone, private ones to accepted members; platform
    admins get no bypass. Non-members count only active curations; members also see
    in-progress work (curation/review stage) in their own scopes.

    Args:
        db: Database session
        gene_id: UUID of the gene
        current_user: Current user (optional)

    Returns:
        List of scope information with curation counts
    """
    user_id = current_user.id if current_user else None
    rows = db.execute(
        select(CurationNew.scope_id, func.count())
        .where(
            CurationNew.gene_id == gene_id,
            CurationNew.scope_id.in_(visible_scope_ids(user_id)),
            or_(
                CurationNew.workflow_stage == "active",
                and_(
                    CurationNew.workflow_stage.in_(["curation", "review"]),
                    CurationNew.scope_id.in_(member_scope_ids(user_id)),
                ),
            ),
        )
        .group_by(CurationNew.scope_id)
    ).all()
    counts = dict(rows)
    scopes = (
        db.query(Scope)
        .filter(Scope.id.in_(list(counts)))
        .order_by(Scope.name, Scope.id)
        .all()
    )

    scope_list = [
        {
            "scope_id": str(scope.id),
            "scope_name": scope.name,
            "display_name": scope.display_name,
            "is_public": scope.is_public,
            "curation_count": counts[scope.id],
        }
        for scope in scopes
    ]

    logger.debug(
        "Listed gene curating scopes",
        gene_id=str(gene_id),
        scope_count=len(scope_list),
        user_id=str(current_user.id) if current_user else None,
    )

    return scope_list
