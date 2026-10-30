"""
Pydantic schemas for scope management.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCOPE_NAME = "Scope name or display name, instead of scope_id"


# Base Scope Schema
class ScopeBase(BaseModel):
    """Base scope schema with common fields."""

    name: str = Field(
        ...,
        max_length=255,
        description="Unique scope identifier (e.g., 'kidney-genetics')",
    )
    display_name: str = Field(
        ..., max_length=255, description="Human-readable scope name"
    )
    description: str | None = Field(None, description="Scope description")
    institution: str | None = Field(
        None, max_length=255, description="Owning institution"
    )
    is_public: bool = Field(False, description="Whether scope is publicly visible")
    scope_config: dict[str, Any] = Field(
        default_factory=dict, description="Scope-specific configuration"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        # Match database constraint: only alphanumeric and hyphens (no underscores)
        if not v.replace("-", "").isalnum():
            raise ValueError(
                "Scope name must contain only alphanumeric characters and hyphens"
            )
        return v.lower()


# Scope Creation Schema
class ScopeCreate(ScopeBase):
    """Schema for creating a new scope."""

    default_workflow_pair_id: UUID | None = Field(
        None,
        description="Workflow pair (methodology) for this scope; omitted, the pair "
        "with is_default=true from get_workflow_pairs is used",
    )


# Scope Update Schema
class ScopeUpdate(BaseModel):
    """Schema for updating an existing scope."""

    display_name: str | None = Field(
        None, max_length=255, description="Human-readable scope name"
    )
    description: str | None = Field(None, description="Scope description")
    institution: str | None = Field(
        None, max_length=255, description="Owning institution"
    )
    is_public: bool | None = Field(None, description="Public scope visibility")
    approvals_require_session: bool | None = None
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
    # approvals only from a signed-in person, not a token or MCP call (#560)
    approvals_require_session: bool = False
    default_workflow_pair_id: UUID | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None

    model_config = ConfigDict(from_attributes=True)


# Public Scope Schema
class Scope(ScopeInDBBase):
    """Public scope schema for API responses."""

    pass


# Scope List Stats (embedded in ScopeListItem)
class ScopeListStats(BaseModel):
    """Basic statistics for scope list views."""

    total_genes: int = Field(
        default=0, description="Total genes assigned to this scope"
    )
    completed_genes: int = Field(
        default=0, description="Genes with an active curation (never above total_genes)"
    )
    member_count: int = Field(
        default=0, description="Number of active members in this scope"
    )


# Scope List Item with basic counts
class ScopeListItem(BaseModel):
    """Compact scope row with counts; detail=true adds the remaining scope fields."""

    id: UUID
    name: str
    display_name: str
    default_workflow_pair_id: UUID | None
    stats: ScopeListStats | None = Field(
        default=None, description="Basic scope statistics"
    )
    user_role: str | None = Field(
        default=None,
        description="Caller's role from an accepted membership in this scope, if any",
    )
    # Only with detail=true (unset fields are left out of the response)
    description: str | None = None
    institution: str | None = None
    is_public: bool | None = None
    scope_config: dict[str, Any] | None = None
    is_active: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: UUID | None = None


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
    completed_genes: int = Field(
        default=0, description="Genes with an active curation (never above total genes)"
    )
    pending_invitations: int = Field(
        default=0, description="Members invited but not yet accepted"
    )

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
    member_count: int = Field(..., description="Total active members in this scope")

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

    model_config = ConfigDict(from_attributes=True)


class ScopeWithStats(Scope):
    """Scope with basic statistics included."""

    statistics: ScopeStatistics
    user_role: str | None = Field(
        default=None,
        description="Caller's role from an accepted membership in this scope, if any",
    )
    curation_schema_id: UUID | None = Field(
        default=None, description="Curation schema of the default workflow pair"
    )
    precuration_schema_id: UUID | None = Field(
        default=None, description="Precuration schema of the default workflow pair"
    )


# Scope User Assignment Schema


# Workflow Pair Information for Scope


# Scope Configuration Schemas


# Scope Activity Summary


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

    model_config = ConfigDict(from_attributes=True)


# Scope Comparison Schema
