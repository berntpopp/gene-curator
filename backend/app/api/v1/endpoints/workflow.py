"""
Multi-stage workflow management API endpoints.
Handles workflow transitions, peer reviews, and workflow monitoring.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.crud.workflow_engine import workflow_engine
from app.models import UserNew
from app.schemas.workflow_engine import (
    BulkWorkflowTransitionRequest,
    BulkWorkflowTransitionResult,
    PeerReviewAssignmentRequest,
    PeerReviewRequest,
    PeerReviewResult,
    PeerReviewSubmission,
    WorkflowAnalytics,
    WorkflowAuditTrail,
    WorkflowConfiguration,
    WorkflowDashboard,
    WorkflowStateInfo,
    WorkflowStatistics,
    WorkflowTransition,
    WorkflowTransitionRequest,
    WorkflowValidationResult,
)

router = APIRouter()


# ========================================
# WORKFLOW TRANSITION ENDPOINTS
# ========================================


@router.get("/{item_type}/{item_id}/state", response_model=WorkflowStateInfo)
def get_workflow_state(
    *,
    db: Session = Depends(get_db),
    item_type: str,
    item_id: UUID,
    current_user: UserNew = Depends(get_current_active_user),
) -> WorkflowStateInfo:
    """
    Get current workflow state and available transitions for an item.
    """
    # All authenticated users can view workflow states
    # RLS policies handle scope-based access

    try:
        state_info = workflow_engine.get_workflow_state(db, item_id, item_type)
        return state_info
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post(
    "/{item_type}/{item_id}/validate-transition",
    response_model=WorkflowValidationResult,
)
def validate_workflow_transition(
    *,
    db: Session = Depends(get_db),
    item_type: str,
    item_id: UUID,
    transition_request: WorkflowTransitionRequest,
    current_user: UserNew = Depends(get_current_active_user),
) -> WorkflowValidationResult:
    """
    Validate a proposed workflow transition without executing it.
    """
    # All authenticated users can validate transitions
    # RLS policies handle scope-based access

    try:
        # Get current stage first
        current_stage, _ = workflow_engine._get_current_stage_and_item(
            db, item_id, item_type
        )
        if current_stage is None:
            raise HTTPException(status_code=404, detail="Item not found")

        validation = workflow_engine.validate_transition(
            db,
            current_stage,
            transition_request.target_stage,
            current_user.id,
            item_id,
            item_type,
        )
        return validation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{item_type}/{item_id}/transition", response_model=WorkflowTransition)
def execute_workflow_transition(
    *,
    db: Session = Depends(get_db),
    item_type: str,
    item_id: UUID,
    transition_request: WorkflowTransitionRequest,
    current_user: UserNew = Depends(get_current_active_user),
) -> WorkflowTransition:
    """
    Execute a workflow state transition.
    """
    # All authenticated users can execute transitions
    # RLS policies + workflow engine handle scope-based access

    try:
        transition = workflow_engine.execute_transition(
            db,
            item_id,
            item_type,
            transition_request.target_stage,
            current_user.id,
            transition_request.notes,
            transition_request.metadata,
        )
        return transition
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ========================================
# PEER REVIEW ENDPOINTS
# ========================================


@router.post("/{item_type}/{item_id}/assign-reviewer", response_model=PeerReviewRequest)
def assign_peer_reviewer(
    *,
    db: Session = Depends(get_db),
    item_type: str,
    item_id: UUID,
    assignment_request: PeerReviewAssignmentRequest,
    current_user: UserNew = Depends(get_current_active_user),
) -> PeerReviewRequest:
    """
    Assign a peer reviewer to an item in review stage.
    """
    # All authenticated users can assign reviewers in their scopes
    # Workflow engine enforces 4-eyes principle and scope access

    try:
        review_request = workflow_engine.assign_peer_reviewer(
            db,
            item_id,
            item_type,
            assignment_request.reviewer_id,
            current_user.id,
            assignment_request.review_type,
        )
        return review_request
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/reviews/{review_id}/submit", response_model=PeerReviewResult)
def submit_peer_review(
    *,
    db: Session = Depends(get_db),
    review_id: UUID,
    review_submission: PeerReviewSubmission,
    current_user: UserNew = Depends(get_current_active_user),
) -> PeerReviewResult:
    """
    Submit a peer review decision.
    """
    # All authenticated users can submit reviews they're assigned to
    # Workflow engine validates reviewer assignment

    try:
        result = workflow_engine.submit_peer_review(
            db,
            review_id,
            current_user.id,
            review_submission.decision,
            review_submission.comments,
            review_submission.suggested_changes,
        )
        return PeerReviewResult(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/reviews/my-assignments", response_model=list[PeerReviewRequest])
def get_my_review_assignments(
    *,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None, description="Filter by review status"),
    current_user: UserNew = Depends(get_current_active_user),
) -> Sequence[PeerReviewRequest]:
    """
    Get peer review assignments for the current user.
    """
    from app.models import Review, ReviewStatus

    query = select(Review).where(Review.reviewer_id == current_user.id)

    if status:
        try:
            status_enum = ReviewStatus(status)
            query = query.where(Review.status == status_enum)
        except ValueError as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid status: {status}"
            ) from e

    reviews = (
        db.execute(query.order_by(Review.assigned_at.desc()).offset(skip).limit(limit))
        .scalars()
        .all()
    )

    # Convert Review model to PeerReviewRequest schema
    result: list[PeerReviewRequest] = []
    for review in reviews:
        # Map curation_id to item_id, use "curation" as item_type
        result.append(
            PeerReviewRequest(
                review_id=review.id,
                item_id=review.curation_id,
                item_type="curation",
                reviewer_id=review.reviewer_id,
                assigned_by=review.assigned_by or current_user.id,  # Fallback if None
                review_type="peer_review",  # Default value
                assigned_at=review.assigned_at,
                status=review.status,
            )
        )
    return result


# ========================================
# WORKFLOW MONITORING ENDPOINTS
# ========================================


@router.get("/statistics", response_model=WorkflowStatistics)
def get_workflow_statistics(
    *,
    db: Session = Depends(get_db),
    scope_id: UUID | None = Query(None, description="Filter by scope"),
    days: int = Query(30, ge=1, le=365, description="Time period in days"),
    current_user: UserNew = Depends(get_current_active_user),
) -> WorkflowStatistics:
    """
    Get workflow performance statistics.
    """
    # All authenticated users can view workflow statistics
    # Check scope access
    if current_user.role not in ["admin"] and scope_id:
        user_scope_ids: list[UUID] = current_user.assigned_scopes or []
        if scope_id not in user_scope_ids:
            raise HTTPException(status_code=403, detail="Not enough permissions")

    statistics = workflow_engine.get_workflow_statistics(db, scope_id, days)
    return statistics


@router.get("/dashboard", response_model=WorkflowDashboard)
def get_workflow_dashboard(
    *,
    db: Session = Depends(get_db),
    scope_id: UUID | None = Query(None, description="Filter by scope"),
    current_user: UserNew = Depends(get_current_active_user),
) -> WorkflowDashboard:
    """
    Get comprehensive workflow dashboard data for the current user.
    """
    # All authenticated users can view their workflow dashboard
    # Check scope access
    if current_user.role not in ["admin"] and scope_id:
        user_scope_ids: list[UUID] = current_user.assigned_scopes or []
        if scope_id not in user_scope_ids:
            raise HTTPException(status_code=403, detail="Not enough permissions")

    # Build dashboard data (simplified implementation)
    from app.models import (
        GeneScopeAssignment,
        Review,
        ReviewStatus,
    )

    # Personal workload
    my_assignments_query = select(GeneScopeAssignment).where(
        GeneScopeAssignment.assigned_curator_id == current_user.id
    )
    if scope_id:
        my_assignments_query = my_assignments_query.where(
            GeneScopeAssignment.scope_id == scope_id
        )

    my_assignments_count = db.execute(
        select(func.count(GeneScopeAssignment.id)).select_from(
            my_assignments_query.subquery()
        )
    ).scalar()

    # My pending reviews
    my_pending_reviews = db.execute(
        select(func.count(Review.id)).where(
            Review.reviewer_id == current_user.id,
            Review.status == ReviewStatus.PENDING,
        )
    ).scalar()

    # My completed reviews
    my_completed_reviews = db.execute(
        select(func.count(Review.id)).where(
            Review.reviewer_id == current_user.id,
            Review.status == ReviewStatus.APPROVED,
        )
    ).scalar()

    # Basic dashboard structure
    dashboard = WorkflowDashboard(
        scope_id=scope_id,
        user_id=current_user.id,
        my_assignments={"total": my_assignments_count or 0},
        my_pending_reviews=my_pending_reviews or 0,
        my_completed_reviews=my_completed_reviews or 0,
        team_workload={"total": 0},  # Would need more complex query
        team_pending_reviews=0,  # Would need more complex query
        recent_transitions=[],  # Would query audit log
        recent_reviews=[],  # Would query recent review activity
        avg_completion_time_days=0.0,  # Would calculate from historical data
        quality_score=0.0,  # Would calculate from review outcomes
    )

    return dashboard


@router.get("/{item_type}/{item_id}/audit-trail", response_model=WorkflowAuditTrail)
def get_workflow_audit_trail(
    *,
    db: Session = Depends(get_db),
    item_type: str,
    item_id: UUID,
    current_user: UserNew = Depends(get_current_active_user),
) -> WorkflowAuditTrail:
    """
    Get complete workflow audit trail for an item.
    """
    # All authenticated users can view audit trails for items in their scopes
    # RLS policies handle scope-based access

    # Basic audit trail structure (would need full implementation)
    audit_trail = WorkflowAuditTrail(
        item_id=item_id,
        item_type=item_type,
        entries=[],  # Would query audit log
        total_transitions=0,
        total_time_hours=None,
        created_at=datetime.utcnow(),
        completed_at=None,
    )

    return audit_trail


# ========================================
# BULK OPERATIONS ENDPOINTS
# ========================================


@router.post("/bulk-transition", response_model=BulkWorkflowTransitionResult)
def bulk_workflow_transition(
    *,
    db: Session = Depends(get_db),
    bulk_request: BulkWorkflowTransitionRequest,
    current_user: UserNew = Depends(get_current_active_user),
) -> BulkWorkflowTransitionResult:
    """
    Execute bulk workflow transitions. Requires admin privileges.
    """
    # Only admins can execute bulk transitions
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    successful_transitions: list[UUID] = []
    failed_transitions: list[dict[str, Any]] = []
    warnings: list[str] = []

    for item_id in bulk_request.item_ids:
        try:
            workflow_engine.execute_transition(
                db,
                item_id,
                bulk_request.item_type,
                bulk_request.target_stage,
                current_user.id,
                bulk_request.notes,
                bulk_request.metadata,
            )
            successful_transitions.append(item_id)
        except Exception as e:
            failed_transitions.append({"item_id": item_id, "error": str(e)})

    return BulkWorkflowTransitionResult(
        successful_transitions=successful_transitions,
        failed_transitions=failed_transitions,
        total_processed=len(bulk_request.item_ids),
        total_successful=len(successful_transitions),
        total_failed=len(failed_transitions),
        warnings=warnings,
    )


# ========================================
# WORKFLOW CONFIGURATION ENDPOINTS
# ========================================


@router.get("/configuration/{scope_id}", response_model=WorkflowConfiguration)
def get_workflow_configuration(
    *,
    db: Session = Depends(get_db),
    scope_id: UUID,
    current_user: UserNew = Depends(get_current_active_user),
) -> WorkflowConfiguration:
    """
    Get workflow configuration for a scope.
    """
    # All authenticated users can view workflow configuration for their scopes
    # Check scope access
    if current_user.role != "admin":
        user_scope_ids: list[UUID] = current_user.assigned_scopes or []
        if scope_id not in user_scope_ids:
            raise HTTPException(status_code=403, detail="Not enough permissions")

    # Return default configuration (would be stored in database in real implementation)
    return WorkflowConfiguration(
        scope_id=scope_id,
        require_peer_review=True,
        min_reviewers=1,
        allow_self_review=False,
        auto_transition_on_approval=True,
        require_all_reviews_complete=True,
        review_timeout_hours=None,
        stage_timeout_hours=None,
        notify_on_assignment=True,
        notify_on_transition=True,
        escalation_enabled=False,
    )


@router.put("/configuration/{scope_id}", response_model=WorkflowConfiguration)
def update_workflow_configuration(
    *,
    db: Session = Depends(get_db),
    scope_id: UUID,
    config_update: WorkflowConfiguration,
    current_user: UserNew = Depends(get_current_active_user),
) -> WorkflowConfiguration:
    """
    Update workflow configuration for a scope. Requires admin privileges.
    """
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # In real implementation, this would update the configuration in database
    config_update.scope_id = scope_id
    return config_update


# ========================================
# ADVANCED ANALYTICS ENDPOINTS
# ========================================


@router.get("/analytics", response_model=WorkflowAnalytics)
def get_workflow_analytics(
    *,
    db: Session = Depends(get_db),
    scope_id: UUID | None = Query(None, description="Filter by scope"),
    days: int = Query(90, ge=7, le=365, description="Analysis period in days"),
    current_user: UserNew = Depends(get_current_active_user),
) -> WorkflowAnalytics:
    """
    Get advanced workflow analytics and performance insights.
    """
    # All authenticated users can view analytics for their scopes
    # Check scope access
    if current_user.role != "admin" and scope_id:
        user_scope_ids: list[UUID] = current_user.assigned_scopes or []
        if scope_id not in user_scope_ids:
            raise HTTPException(status_code=403, detail="Not enough permissions")

    # Return basic analytics structure (would need full implementation)
    return WorkflowAnalytics(
        scope_id=scope_id,
        analysis_period_days=days,
        items_entered=0,
        items_completed=0,
        completion_rate=0.0,
        avg_cycle_time_days=0.0,
        median_cycle_time_days=0.0,
        percentile_95_cycle_time_days=0.0,
        stage_throughput={},
        stage_efficiency={},
        first_pass_yield=0.0,
        review_effectiveness=0.0,
        curator_utilization={},
        reviewer_utilization={},
        weekly_trends=[],
        bottleneck_analysis={},
    )
