"""
Pydantic schemas for scope management.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, validator


# Base Scope Schema
class ScopeBase(BaseModel):
    """Base scope schema with common fields."""

    name: str = Field(
        ..., description="Unique scope identifier (e.g., 'kidney-genetics')"
    )
    display_name: str = Field(..., description="Human-readable scope name")
    description: str | None = Field(None, description="Scope description")
    institution: str | None = Field(None, description="Owning institution")
    scope_config: dict[str, Any] = Field(
        default_factory=dict, description="Scope-specific configuration"
    )

    @validator("name")
    def validate_name(cls, v):
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Scope name must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v.lower()


# Scope Creation Schema
class ScopeCreate(ScopeBase):
    """Schema for creating a new scope."""

    default_workflow_pair_id: UUID | None = Field(
        None, description="Default workflow pair for this scope"
    )


# Scope Update Schema
class ScopeUpdate(BaseModel):
    """Schema for updating an existing scope."""

    display_name: str | None = Field(None, description="Human-readable scope name")
    description: str | None = Field(None, description="Scope description")
    institution: str | None = Field(None, description="Owning institution")
    scope_config: dict[str, Any] | None = Field(
        None, description="Scope-specific configuration"
    )
    is_active: bool | None = Field(None, description="Scope active status")
    default_workflow_pair_id: UUID | None = Field(
        None, description="Default workflow pair for this scope"
    )


# Base Scope with Database Fields
class ScopeInDBBase(ScopeBase):
    """Base scope schema with database fields."""

    id: UUID
    is_active: bool
    default_workflow_pair_id: UUID | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None

    class Config:
        from_attributes = True


# Public Scope Schema
class Scope(ScopeInDBBase):
    """Public scope schema for API responses."""

    pass


# Scope with Statistics
class ScopeStatistics(BaseModel):
    """Detailed scope statistics."""

    total_genes_assigned: int = Field(
        ..., description="Total genes assigned to this scope"
    )
    genes_with_curator: int = Field(..., description="Genes with assigned curator")
    total_precurations: int = Field(..., description="Total precurations in this scope")
    total_curations: int = Field(..., description="Total curations in this scope")
    total_reviews: int = Field(..., description="Total reviews in this scope")
    active_curations: int = Field(..., description="Active curations in this scope")

    # Status breakdowns
    draft_curations: int = Field(..., description="Curations in draft state")
    submitted_curations: int = Field(..., description="Curations submitted for review")
    curations_in_review: int = Field(
        ..., description="Curations currently under review"
    )
    approved_curations: int = Field(..., description="Approved curations")
    rejected_curations: int = Field(..., description="Rejected curations")

    # Review metrics
    pending_reviews: int = Field(..., description="Reviews pending completion")
    approved_reviews: int = Field(..., description="Completed approved reviews")
    avg_review_time_days: float | None = Field(
        None, description="Average review time in days"
    )

    # Team metrics
    active_curators: int = Field(..., description="Active curators in this scope")
    active_reviewers: int = Field(..., description="Active reviewers in this scope")

    # Verdict distribution
    definitive_verdicts: int = Field(default=0, description="Definitive verdicts")
    strong_verdicts: int = Field(default=0, description="Strong verdicts")
    moderate_verdicts: int = Field(default=0, description="Moderate verdicts")
    limited_verdicts: int = Field(default=0, description="Limited verdicts")

    # Recent activity
    curations_last_30_days: int = Field(
        ..., description="Curations created in last 30 days"
    )
    activations_last_30_days: int = Field(
        ..., description="Curations activated in last 30 days"
    )

    class Config:
        from_attributes = True


class ScopeWithStats(Scope):
    """Scope with basic statistics included."""

    statistics: ScopeStatistics


# Scope User Assignment Schema
class ScopeUserAssignment(BaseModel):
    """Schema for scope-user assignments."""

    user_id: UUID
    user_name: str
    user_email: str
    user_role: str
    assigned_at: datetime

    class Config:
        from_attributes = True


# Workflow Pair Information for Scope
class ScopeWorkflowPair(BaseModel):
    """Workflow pair information for scope context."""

    id: UUID
    name: str
    version: str
    description: str | None
    precuration_schema_name: str
    curation_schema_name: str
    is_active: bool

    class Config:
        from_attributes = True


# Scope Configuration Schemas
class ScopeConfigUpdate(BaseModel):
    """Schema for updating scope configuration."""

    primary_inheritance_modes: list[str] | None = Field(
        None, description="Primary inheritance modes for this scope"
    )
    focus_areas: list[str] | None = Field(
        None, description="Focus areas for this scope"
    )
    custom_fields: dict[str, Any] | None = Field(
        None, description="Custom scope-specific fields"
    )
    quality_thresholds: dict[str, float] | None = Field(
        None, description="Quality thresholds for this scope"
    )


# Scope Activity Summary
class ScopeActivity(BaseModel):
    """Recent activity summary for a scope."""

    scope_id: UUID
    scope_name: str
    recent_curations: int = Field(..., description="Curations in last 7 days")
    recent_reviews: int = Field(..., description="Reviews completed in last 7 days")
    pending_work: int = Field(..., description="Total pending work items")
    overdue_reviews: int = Field(..., description="Overdue reviews")
    last_activity: datetime | None = Field(None, description="Last activity timestamp")

    class Config:
        from_attributes = True


# Scope Performance Metrics
class ScopePerformance(BaseModel):
    """Performance metrics for a scope."""

    scope_id: UUID
    scope_name: str

    # Throughput metrics
    avg_curation_time_days: float | None = Field(
        None, description="Average time from creation to submission"
    )
    avg_review_time_days: float | None = Field(
        None, description="Average review completion time"
    )

    # Quality metrics
    approval_rate: float | None = Field(
        None, description="Percentage of curations approved"
    )
    rejection_rate: float | None = Field(
        None, description="Percentage of curations rejected"
    )

    # Workload metrics
    curations_per_curator: float | None = Field(
        None, description="Average curations per curator"
    )
    reviews_per_reviewer: float | None = Field(
        None, description="Average reviews per reviewer"
    )

    # Trend metrics
    monthly_curation_trend: float | None = Field(
        None, description="Monthly curation growth rate"
    )
    monthly_activation_trend: float | None = Field(
        None, description="Monthly activation growth rate"
    )

    class Config:
        from_attributes = True


# Scope Comparison Schema
class ScopeComparison(BaseModel):
    """Schema for comparing multiple scopes."""

    scopes: list[ScopePerformance]
    comparison_period_days: int
    generated_at: datetime

    class Config:
        from_attributes = True
