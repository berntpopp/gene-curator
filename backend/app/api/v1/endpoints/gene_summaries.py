"""Gene summary endpoints

Provides access to gene summary aggregations across scopes.
Implements public/private data filtering based on authentication.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import (
    get_current_active_user,
    get_current_admin_user,
    get_current_user_optional,
)
from app.core.logging import api_endpoint, get_logger
from app.models.models import CurationNew, Scope, UserNew
from app.schemas.gene_summary import GeneSummaryFull, GeneSummaryPublic
from app.services.gene_summary_service import GeneSummaryService
from app.services.scope_permissions import ScopePermissionService

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/genes/{gene_id}/summary",
    response_model=GeneSummaryPublic,
)
@api_endpoint()
async def get_gene_public_summary(
    *,
    db: Session = Depends(get_db),
    gene_id: UUID,
) -> GeneSummaryPublic:
    """Get public gene summary (no authentication required)

    Returns aggregated statistics for gene across public scopes only.
    Private scope data is excluded from the response.

    Args:
        db: Database session
        gene_id: UUID of the gene

    Returns:
        Public gene summary with only public scope data

    Raises:
        HTTPException: 404 if no public curations found for gene
    """
    service = GeneSummaryService(db)
    summary = service.get_public_summary(gene_id)

    if not summary:
        logger.info(
            "No public gene summary available",
            gene_id=str(gene_id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No public curations found for this gene",
        )

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
    service = GeneSummaryService(db)

    # Always recompute for authenticated users to ensure freshness
    summary = service.compute_summary(gene_id)

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gene not found or has no curations",
        )

    # Filter scope summaries based on user permissions
    visible_scope_ids = {
        str(s.id) for s in ScopePermissionService.get_visible_scopes(db, current_user)
    }

    filtered_scope_summaries = [
        s for s in summary.scope_summaries if s.get("scope_id") in visible_scope_ids
    ]

    # Recalculate counts based on filtered summaries
    public_count = sum(1 for s in filtered_scope_summaries if s.get("is_public"))
    private_count = sum(1 for s in filtered_scope_summaries if not s.get("is_public"))

    logger.debug(
        "Full gene summary retrieved",
        gene_id=str(gene_id),
        total_scopes=len(filtered_scope_summaries),
        public_scopes=public_count,
        private_scopes=private_count,
        user_id=str(current_user.id),
    )

    return GeneSummaryFull(
        gene_id=summary.gene_id,
        total_scopes_curated=len(filtered_scope_summaries),
        public_scopes_count=public_count,
        private_scopes_count=private_count,
        classification_summary=summary.classification_summary,
        consensus_classification=summary.consensus_classification,
        consensus_confidence=summary.consensus_confidence,
        has_conflicts=summary.has_conflicts,
        scope_summaries=filtered_scope_summaries,
        last_updated=summary.last_computed_at,
        computation_version=1,  # SOP v11 version
        is_stale=summary.is_stale,
    )


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

    Returns scopes with active curations for the gene, filtered by user permissions.
    Public scopes are always visible; private scopes only if user is a member.

    Args:
        db: Database session
        gene_id: UUID of the gene
        current_user: Current user (optional, for filtering private scopes)

    Returns:
        List of scope information with curation counts
    """
    # Get all active curations for gene
    query = db.query(CurationNew).filter(
        CurationNew.gene_id == gene_id,
        CurationNew.workflow_stage.in_(["curation", "review", "active"]),
    )

    # Apply visibility filter based on user permissions
    query = ScopePermissionService.filter_visible_curations(db, query, current_user)

    curations = query.all()

    # Get unique scopes
    scope_ids = list({c.scope_id for c in curations})
    scopes = db.query(Scope).filter(Scope.id.in_(scope_ids)).all()

    scope_list = [
        {
            "scope_id": str(scope.id),
            "scope_name": scope.name,
            "display_name": scope.display_name,
            "is_public": scope.is_public,
            "curation_count": sum(1 for c in curations if c.scope_id == scope.id),
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


@router.post(
    "/genes/{gene_id}/summary/recompute",
    status_code=status.HTTP_202_ACCEPTED,
)
@api_endpoint()
async def recompute_gene_summary(
    *,
    db: Session = Depends(get_db),
    gene_id: UUID,
    current_user: UserNew = Depends(get_current_admin_user),
) -> dict[str, str]:
    """Manually trigger gene summary recomputation (admin only)

    Forces immediate recomputation of gene summary aggregations.
    Normally summaries are computed on-demand or via background jobs.

    Args:
        db: Database session
        gene_id: UUID of the gene
        current_user: Current admin user

    Returns:
        Success message with recomputation status
    """
    service = GeneSummaryService(db)
    summary = service.compute_summary(gene_id)

    logger.info(
        "Gene summary manually recomputed",
        gene_id=str(gene_id),
        total_scopes=summary.total_scopes_curated,
        user_id=str(current_user.id),
    )

    return {
        "message": "Gene summary recomputed successfully",
        "gene_id": str(gene_id),
        "total_scopes": str(summary.total_scopes_curated),
    }
