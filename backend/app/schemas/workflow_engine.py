"""
Pydantic schemas for workflow engine operations.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, validator

from app.models import ReviewStatus, WorkflowStage


# Workflow Transition Schemas
class WorkflowTransitionRequest(BaseModel):
    """Request to transition workflow stage."""

    target_stage: WorkflowStage = Field(..., description="Target workflow stage")
    notes: str | None = Field(None, max_length=1000, description="Transition notes")
    metadata: dict[str, Any] | None = Field(
        default_factory=dict, description="Additional metadata"
    )


class WorkflowTransition(BaseModel):
    """Workflow transition result."""

    item_id: UUID
    item_type: str
    from_stage: WorkflowStage
    to_stage: WorkflowStage
    executed_by: UUID
    executed_at: datetime
    notes: str | None
    metadata: dict[str, Any]
    success: bool = Field(default=True, description="Transition success status")
    message: str | None = Field(None, description="Transition result message")

    class Config:
        use_enum_values = True


# Workflow Validation Schemas
class WorkflowValidationResult(BaseModel):
    """Result of workflow transition validation."""

    is_valid: bool = Field(..., description="Whether transition is valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")
    requirements: list[str] = Field(
        default_factory=list, description="Content requirements"
    )


# Workflow State Information
class WorkflowStateInfo(BaseModel):
    """Current workflow state information."""

    item_id: UUID
    item_type: str
    current_stage: WorkflowStage
    available_transitions: list[WorkflowStage]
    workflow_history: list[dict[str, Any]]
    pending_reviews: list[dict[str, Any]]
    progress_metrics: dict[str, Any]
    last_updated: datetime
    last_updated_by: UUID | None

    class Config:
        use_enum_values = True


# Peer Review Schemas
class PeerReviewAssignmentRequest(BaseModel):
    """Request to assign peer reviewer."""

    reviewer_id: UUID = Field(..., description="Reviewer user ID")
    review_type: str = Field("peer_review", description="Type of review")
    notes: str | None = Field(None, max_length=500, description="Assignment notes")


class PeerReviewRequest(BaseModel):
    """Peer review assignment details."""

    review_id: UUID
    item_id: UUID
    item_type: str
    reviewer_id: UUID
    assigned_by: UUID
    review_type: str
    assigned_at: datetime
    status: ReviewStatus

    class Config:
        use_enum_values = True


class PeerReviewSubmission(BaseModel):
    """Peer review submission."""

    decision: str = Field(
        ..., description="Review decision (approve, request_changes, reject)"
    )
    comments: str | None = Field(None, max_length=2000, description="Review comments")
    suggested_changes: dict[str, Any] | None = Field(
        default_factory=dict, description="Suggested changes"
    )

    @validator("decision")
    def validate_decision(cls, v):
        valid_decisions = ["approve", "request_changes", "reject"]
        if v not in valid_decisions:
            raise ValueError(f"Decision must be one of: {valid_decisions}")
        return v


class PeerReviewResult(BaseModel):
    """Result of peer review submission."""

    review_id: UUID
    decision: str
    status: str
    auto_transitioned: bool = Field(
        default=False, description="Whether item was auto-transitioned"
    )
    next_stage: WorkflowStage | None = Field(
        None, description="Next workflow stage if transitioned"
    )

    class Config:
        use_enum_values = True


# Workflow Statistics
class WorkflowStatistics(BaseModel):
    """Workflow performance statistics."""

    scope_id: UUID | None = Field(None, description="Scope filter applied")
    time_period_days: int = Field(..., description="Time period for statistics")

    # Stage distribution
    stage_counts: dict[str, int] = Field(
        ..., description="Count of items in each stage"
    )
    total_transitions: int = Field(..., description="Total workflow transitions")
    completed_workflows: int = Field(
        ..., description="Workflows completed to active stage"
    )

    # Time metrics (in hours)
    avg_precuration_time_hours: float = Field(
        ..., description="Average time in precuration stage"
    )
    avg_curation_time_hours: float = Field(
        ..., description="Average time in curation stage"
    )
    avg_review_time_hours: float = Field(
        ..., description="Average time in review stage"
    )

    # Review metrics
    total_reviews: int = Field(..., description="Total peer reviews assigned")
    completed_reviews: int = Field(..., description="Completed peer reviews")
    pending_reviews: int = Field(..., description="Pending peer reviews")
    approval_rate: float = Field(..., description="Review approval rate (0.0-1.0)")

    # Performance insights
    bottleneck_stage: str | None = Field(None, description="Stage with most items")


# Workflow Dashboard
class WorkflowDashboard(BaseModel):
    """Comprehensive workflow dashboard data."""

    scope_id: UUID | None
    user_id: UUID

    # Personal workload
    my_assignments: dict[str, int] = Field(..., description="My items by stage")
    my_pending_reviews: int = Field(..., description="Reviews assigned to me")
    my_completed_reviews: int = Field(..., description="Reviews I've completed")

    # Team overview
    team_workload: dict[str, int] = Field(..., description="Team items by stage")
    team_pending_reviews: int = Field(..., description="Team pending reviews")

    # Recent activity
    recent_transitions: list[dict[str, Any]] = Field(
        ..., description="Recent workflow transitions"
    )
    recent_reviews: list[dict[str, Any]] = Field(
        ..., description="Recent review activity"
    )

    # Performance metrics
    avg_completion_time_days: float = Field(
        ..., description="Average workflow completion time"
    )
    quality_score: float = Field(
        ..., description="Quality score based on review outcomes"
    )


# Workflow Audit
class WorkflowAuditEntry(BaseModel):
    """Workflow audit trail entry."""

    id: UUID
    item_id: UUID
    item_type: str
    from_stage: WorkflowStage | None
    to_stage: WorkflowStage
    executed_by: UUID
    executed_at: datetime
    notes: str | None
    metadata: dict[str, Any]

    class Config:
        use_enum_values = True


class WorkflowAuditTrail(BaseModel):
    """Complete workflow audit trail."""

    item_id: UUID
    item_type: str
    entries: list[WorkflowAuditEntry]
    total_transitions: int
    total_time_hours: float | None
    created_at: datetime
    completed_at: datetime | None


# Bulk Workflow Operations
class BulkWorkflowTransitionRequest(BaseModel):
    """Request for bulk workflow transitions."""

    item_ids: list[UUID] = Field(..., min_length=1, max_length=50)
    item_type: str = Field(..., description="Type of items to transition")
    target_stage: WorkflowStage = Field(..., description="Target workflow stage")
    notes: str | None = Field(None, max_length=1000)
    metadata: dict[str, Any] | None = Field(default_factory=dict)


class BulkWorkflowTransitionResult(BaseModel):
    """Result of bulk workflow transitions."""

    successful_transitions: list[UUID]
    failed_transitions: list[dict[str, Any]]
    total_processed: int
    total_successful: int
    total_failed: int
    warnings: list[str]


# Workflow Configuration
class WorkflowConfiguration(BaseModel):
    """Workflow engine configuration."""

    scope_id: UUID

    # Stage requirements
    require_peer_review: bool = Field(
        True, description="Require peer review for transitions"
    )
    min_reviewers: int = Field(1, ge=1, le=5, description="Minimum number of reviewers")
    allow_self_review: bool = Field(
        False, description="Allow self-review (violates 4-eyes)"
    )

    # Auto-transition rules
    auto_transition_on_approval: bool = Field(
        True, description="Auto-transition when all reviews approved"
    )
    require_all_reviews_complete: bool = Field(
        True, description="Require all reviews before transition"
    )

    # Time limits (in hours)
    review_timeout_hours: int | None = Field(None, ge=1, description="Review timeout")
    stage_timeout_hours: int | None = Field(None, ge=1, description="Stage timeout")

    # Notification settings
    notify_on_assignment: bool = Field(True, description="Notify on review assignment")
    notify_on_transition: bool = Field(True, description="Notify on stage transition")
    escalation_enabled: bool = Field(
        False, description="Enable escalation for overdue items"
    )


# Workflow Analytics
class WorkflowAnalytics(BaseModel):
    """Advanced workflow analytics."""

    scope_id: UUID | None
    analysis_period_days: int

    # Throughput metrics
    items_entered: int
    items_completed: int
    completion_rate: float

    # Cycle time analysis
    avg_cycle_time_days: float
    median_cycle_time_days: float
    percentile_95_cycle_time_days: float

    # Stage analysis
    stage_throughput: dict[str, int]
    stage_efficiency: dict[str, float]  # Items completed / Items entered per stage

    # Quality metrics
    first_pass_yield: float  # Items that don't require rework
    review_effectiveness: float  # Quality issues caught in reviews

    # Resource utilization
    curator_utilization: dict[str, float]  # Work distribution among curators
    reviewer_utilization: dict[str, float]  # Review distribution among reviewers

    # Trend analysis
    weekly_trends: list[dict[str, Any]]
    bottleneck_analysis: dict[str, Any]


# Workflow Notifications
class WorkflowNotification(BaseModel):
    """Workflow-related notification."""

    id: UUID
    recipient_id: UUID
    notification_type: str
    item_id: UUID
    item_type: str
    stage: WorkflowStage
    message: str
    metadata: dict[str, Any]
    created_at: datetime
    read_at: datetime | None

    class Config:
        use_enum_values = True


class WorkflowNotificationPreferences(BaseModel):
    """User preferences for workflow notifications."""

    user_id: UUID

    # Notification channels
    email_enabled: bool = Field(True, description="Enable email notifications")
    in_app_enabled: bool = Field(True, description="Enable in-app notifications")

    # Notification types
    assignment_notifications: bool = Field(True, description="Notify on assignments")
    transition_notifications: bool = Field(True, description="Notify on transitions")
    review_notifications: bool = Field(True, description="Notify on review requests")
    completion_notifications: bool = Field(True, description="Notify on completions")

    # Frequency settings
    immediate_notifications: bool = Field(
        True, description="Send immediate notifications"
    )
    daily_digest: bool = Field(False, description="Send daily digest")
    weekly_summary: bool = Field(True, description="Send weekly summary")
