"""
Pydantic schemas for gene-scope assignments.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, validator


# Base Schema
class GeneScopeAssignmentBase(BaseModel):
    """Base schema for gene-scope assignments."""

    gene_id: UUID = Field(..., description="Gene identifier")
    scope_id: UUID = Field(..., description="Scope identifier")
    assigned_curator_id: UUID | None = Field(None, description="Assigned curator ID")
    priority_level: str = Field("medium", description="Assignment priority level")
    assignment_notes: str | None = Field(None, description="Notes about the assignment")

    @validator("priority_level")
    def validate_priority_level(cls, v):
        valid_priorities = ["high", "medium", "low"]
        if v not in valid_priorities:
            raise ValueError(f"Priority level must be one of: {valid_priorities}")
        return v


# Creation Schema
class GeneScopeAssignmentCreate(GeneScopeAssignmentBase):
    """Schema for creating a new gene-scope assignment."""

    pass


# Update Schema
class GeneScopeAssignmentUpdate(BaseModel):
    """Schema for updating a gene-scope assignment."""

    assigned_curator_id: UUID | None = Field(None, description="Assigned curator ID")
    priority_level: str | None = Field(None, description="Assignment priority level")
    assignment_notes: str | None = Field(None, description="Notes about the assignment")

    @validator("priority_level")
    def validate_priority_level(cls, v):
        if v is not None:
            valid_priorities = ["high", "medium", "low"]
            if v not in valid_priorities:
                raise ValueError(f"Priority level must be one of: {valid_priorities}")
        return v


# Database Schema
class GeneScopeAssignmentInDBBase(GeneScopeAssignmentBase):
    """Base schema with database fields."""

    id: UUID
    is_active: bool
    assigned_at: datetime
    assigned_by: UUID
    curator_assigned_at: datetime | None
    curator_assigned_by: UUID | None
    deactivated_at: datetime | None
    deactivated_by: UUID | None
    deactivation_reason: str | None
    created_at: datetime
    updated_at: datetime
    last_updated_by: UUID | None

    class Config:
        from_attributes = True


# Public Response Schema
class GeneScopeAssignment(GeneScopeAssignmentInDBBase):
    """Public schema for gene-scope assignments."""

    pass


# Enhanced Assignment with Gene and Scope Details
class GeneScopeAssignmentWithDetails(GeneScopeAssignment):
    """Gene-scope assignment with related entity details."""

    gene_symbol: str | None = Field(None, description="Gene approved symbol")
    gene_hgnc_id: str | None = Field(None, description="Gene HGNC ID")
    gene_chromosome: str | None = Field(None, description="Gene chromosome")
    scope_name: str | None = Field(None, description="Scope name")
    scope_display_name: str | None = Field(None, description="Scope display name")
    curator_name: str | None = Field(None, description="Assigned curator name")
    curator_email: str | None = Field(None, description="Assigned curator email")

    class Config:
        from_attributes = True


# Assignment Statistics
class GeneScopeAssignmentStatistics(BaseModel):
    """Statistics for a gene-scope assignment."""

    assignment_id: UUID
    gene_id: UUID
    scope_id: UUID
    assigned_curator_id: UUID | None
    is_active: bool
    assigned_at: datetime
    curator_assigned_at: datetime | None

    # Work progress
    total_precurations: int = Field(default=0, description="Total precurations")
    draft_precurations: int = Field(default=0, description="Draft precurations")
    submitted_precurations: int = Field(default=0, description="Submitted precurations")
    approved_precurations: int = Field(default=0, description="Approved precurations")

    total_curations: int = Field(default=0, description="Total curations")
    draft_curations: int = Field(default=0, description="Draft curations")
    submitted_curations: int = Field(default=0, description="Submitted curations")
    in_review_curations: int = Field(default=0, description="Curations in review")
    approved_curations: int = Field(default=0, description="Approved curations")

    has_active_work: bool = Field(
        default=False, description="Has active work in progress"
    )

    class Config:
        from_attributes = True


# Curator Workload Schema
class CuratorWorkload(BaseModel):
    """Workload statistics for a curator."""

    curator_id: UUID
    scope_id: UUID | None
    total_assignments: int = Field(..., description="Total gene assignments")
    assignments_with_active_work: int = Field(
        ..., description="Assignments with active work"
    )

    # Priority breakdown
    priority_breakdown: dict[str, int] = Field(
        ..., description="Assignments by priority level"
    )
    high_priority_assignments: int = Field(
        default=0, description="High priority assignments"
    )
    medium_priority_assignments: int = Field(
        default=0, description="Medium priority assignments"
    )
    low_priority_assignments: int = Field(
        default=0, description="Low priority assignments"
    )

    class Config:
        from_attributes = True


# Gene Assignment Summary for Lists
class GeneScopeAssignmentSummary(BaseModel):
    """Minimal assignment information for lists."""

    id: UUID
    gene_id: UUID
    gene_symbol: str
    gene_hgnc_id: str
    scope_id: UUID
    scope_name: str
    assigned_curator_id: UUID | None
    curator_name: str | None
    priority_level: str
    is_active: bool
    assigned_at: datetime
    has_active_work: bool = Field(default=False, description="Has active work")

    class Config:
        from_attributes = True


# Bulk Assignment Request
class BulkGeneScopeAssignmentCreate(BaseModel):
    """Schema for bulk gene-scope assignments."""

    gene_ids: list[UUID] = Field(
        ..., min_length=1, max_length=100, description="List of gene IDs"
    )
    scope_id: UUID = Field(..., description="Target scope ID")
    assigned_curator_id: UUID | None = Field(
        None, description="Optional curator to assign"
    )
    priority_level: str = Field(
        "medium", description="Priority level for all assignments"
    )
    assignment_notes: str | None = Field(None, description="Notes for all assignments")

    @validator("priority_level")
    def validate_priority_level(cls, v):
        valid_priorities = ["high", "medium", "low"]
        if v not in valid_priorities:
            raise ValueError(f"Priority level must be one of: {valid_priorities}")
        return v


# Bulk Assignment Response
class BulkGeneScopeAssignmentResponse(BaseModel):
    """Response for bulk gene-scope assignments."""

    created_assignments: list[GeneScopeAssignment]
    skipped_assignments: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    total_processed: int
    total_created: int
    total_skipped: int
    total_errors: int


# Available Gene for Assignment
class AvailableGene(BaseModel):
    """Gene available for assignment to a scope."""

    gene_id: UUID
    hgnc_id: str
    approved_symbol: str
    chromosome: str | None
    location: str | None

    class Config:
        from_attributes = True


# Curator Assignment Request
class CuratorAssignmentRequest(BaseModel):
    """Request to assign a curator to a gene-scope assignment."""

    curator_id: UUID = Field(..., description="Curator to assign")


# Assignment Filter Parameters
class AssignmentFilters(BaseModel):
    """Filtering parameters for assignments."""

    scope_id: UUID | None = Field(None, description="Filter by scope")
    curator_id: UUID | None = Field(None, description="Filter by curator")
    gene_id: UUID | None = Field(None, description="Filter by gene")
    priority_level: str | None = Field(None, description="Filter by priority level")
    is_active: bool | None = Field(True, description="Filter by active status")
    has_curator: bool | None = Field(None, description="Filter by curator assignment")
    has_active_work: bool | None = Field(
        None, description="Filter by active work status"
    )
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(100, ge=1, le=500, description="Maximum number of records")

    @validator("priority_level")
    def validate_priority_level(cls, v):
        if v is not None:
            valid_priorities = ["high", "medium", "low"]
            if v not in valid_priorities:
                raise ValueError(f"Priority level must be one of: {valid_priorities}")
        return v


# Assignment List Response
class GeneScopeAssignmentListResponse(BaseModel):
    """Response for paginated assignment lists."""

    assignments: list[GeneScopeAssignmentSummary]
    total: int
    skip: int
    limit: int
    has_next: bool
    has_prev: bool


# Deactivation Request
class DeactivateAssignmentRequest(BaseModel):
    """Request to deactivate an assignment."""

    reason: str | None = Field(
        None, max_length=500, description="Reason for deactivation"
    )


# Assignment Activity Summary
class AssignmentActivity(BaseModel):
    """Recent activity summary for assignments."""

    scope_id: UUID
    scope_name: str
    recent_assignments: int = Field(..., description="New assignments in last 7 days")
    recent_curator_assignments: int = Field(
        ..., description="Curator assignments in last 7 days"
    )
    pending_curator_assignments: int = Field(
        ..., description="Assignments without curator"
    )
    overdue_assignments: int = Field(
        ..., description="High priority assignments over 30 days old"
    )
    last_activity: datetime | None = Field(None, description="Last assignment activity")

    class Config:
        from_attributes = True


# Scope Assignment Overview
class ScopeAssignmentOverview(BaseModel):
    """Overview of assignments within a scope."""

    scope_id: UUID
    scope_name: str
    scope_display_name: str

    total_assignments: int = Field(..., description="Total active assignments")
    assigned_genes: int = Field(..., description="Genes assigned to curators")
    unassigned_genes: int = Field(..., description="Genes not assigned to curators")

    # Priority distribution
    high_priority: int = Field(default=0, description="High priority assignments")
    medium_priority: int = Field(default=0, description="Medium priority assignments")
    low_priority: int = Field(default=0, description="Low priority assignments")

    # Work status
    assignments_with_work: int = Field(
        default=0, description="Assignments with active work"
    )
    assignments_pending_start: int = Field(
        default=0, description="Assignments not yet started"
    )

    # Team metrics
    active_curators: int = Field(default=0, description="Curators with assignments")
    avg_assignments_per_curator: float | None = Field(
        None, description="Average assignments per curator"
    )

    class Config:
        from_attributes = True
