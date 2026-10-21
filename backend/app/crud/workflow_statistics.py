"""Workflow performance statistics (split out of workflow_engine.py)."""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models import (
    ActiveCuration,
    CurationNew,
    CurationStatus,
    PrecurationNew,
    Review,
    ReviewStatus,
)
from app.schemas.workflow_engine import WorkflowStatistics


def compute_workflow_statistics(
    db: Session,
    scope_id: UUID | None,
    days: int,
    average_stage_time: Callable[[Session, str, datetime, UUID | None], float],
) -> WorkflowStatistics:
    """Get workflow performance statistics."""
    from datetime import timedelta

    cutoff_date = datetime.now(UTC) - timedelta(days=days)

    # Base queries
    precuration_stmt = select(PrecurationNew).where(
        PrecurationNew.created_at >= cutoff_date
    )
    curation_stmt = select(CurationNew).where(CurationNew.created_at >= cutoff_date)
    review_stmt = select(Review).where(Review.assigned_at >= cutoff_date)
    active_stmt = select(ActiveCuration).where(
        ActiveCuration.activated_at >= cutoff_date
    )

    if scope_id:
        precuration_stmt = precuration_stmt.where(PrecurationNew.scope_id == scope_id)
        curation_stmt = curation_stmt.where(CurationNew.scope_id == scope_id)
        # Reviews and active curations would need JOIN to filter by scope

    # Stage counts
    from sqlalchemy import func as sqlalchemy_func

    stage_counts: dict[str, int] = {
        "entry": 0,  # Would need to be calculated based on unstarted assignments
        "precuration": db.execute(
            select(sqlalchemy_func.count()).select_from(
                precuration_stmt.where(
                    PrecurationNew.status == CurationStatus.DRAFT
                ).subquery()
            )
        ).scalar()
        or 0,
        "curation": db.execute(
            select(sqlalchemy_func.count()).select_from(
                curation_stmt.where(
                    CurationNew.status == CurationStatus.DRAFT
                ).subquery()
            )
        ).scalar()
        or 0,
        "review": db.execute(
            select(sqlalchemy_func.count()).select_from(
                review_stmt.where(Review.status == ReviewStatus.PENDING).subquery()
            )
        ).scalar()
        or 0,
        "active": db.execute(
            select(sqlalchemy_func.count()).select_from(active_stmt.subquery())
        ).scalar()
        or 0,
    }

    # Transition metrics
    total_transitions = sum(stage_counts.values())
    completed_workflows = (
        db.execute(
            select(sqlalchemy_func.count()).select_from(active_stmt.subquery())
        ).scalar()
        or 0
    )

    # Time-based metrics
    avg_precuration_time = average_stage_time(db, "precuration", cutoff_date, scope_id)
    avg_curation_time = average_stage_time(db, "curation", cutoff_date, scope_id)
    avg_review_time = average_stage_time(db, "review", cutoff_date, scope_id)

    # Review metrics
    total_reviews = (
        db.execute(
            select(sqlalchemy_func.count()).select_from(review_stmt.subquery())
        ).scalar()
        or 0
    )
    completed_reviews = (
        db.execute(
            select(sqlalchemy_func.count()).select_from(
                review_stmt.where(Review.status != ReviewStatus.PENDING).subquery()
            )
        ).scalar()
        or 0
    )
    pending_reviews = total_reviews - completed_reviews

    # Quality metrics
    approval_rate = 0.0
    if completed_reviews > 0:
        approved_reviews = (
            db.execute(
                select(sqlalchemy_func.count()).select_from(
                    review_stmt.where(
                        and_(
                            Review.status == ReviewStatus.APPROVED,
                            Review.recommendation == "approve",
                        )
                    ).subquery()
                )
            ).scalar()
            or 0
        )
        approval_rate = approved_reviews / completed_reviews

    return WorkflowStatistics(
        scope_id=scope_id,
        time_period_days=days,
        stage_counts=stage_counts,
        total_transitions=total_transitions,
        completed_workflows=completed_workflows,
        avg_precuration_time_hours=avg_precuration_time,
        avg_curation_time_hours=avg_curation_time,
        avg_review_time_hours=avg_review_time,
        total_reviews=total_reviews,
        completed_reviews=completed_reviews,
        pending_reviews=pending_reviews,
        approval_rate=approval_rate,
        bottleneck_stage=(
            max(stage_counts, key=lambda k: stage_counts[k]) if stage_counts else None
        ),
    )
