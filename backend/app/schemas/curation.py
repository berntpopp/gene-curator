"""
Pydantic V2 schemas for curation API operations.
Follows existing patterns from gene_assignment.py (InDBBase pattern).
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import CurationStatus, WorkflowStage

# ========================================
# BASE SCHEMAS (DRY - shared fields)
# ========================================


class CurationBase(BaseModel):
    """Base schema with common curation fields."""

    gene_id: UUID = Field(..., description="Gene UUID")
    scope_id: UUID = Field(..., description="Scope UUID")
    workflow_pair_id: UUID = Field(..., description="Workflow pair UUID")
    precuration_id: UUID | None = Field(None, description="Parent precuration UUID")
    evidence_data: dict[str, Any] = Field(
        default_factory=dict, description="Schema-agnostic evidence"
    )


# ========================================
# REQUEST SCHEMAS
# ========================================


class CurationCreate(CurationBase):
    """Schema for creating a new curation."""

    pass


class CurationUpdate(BaseModel):
    """Schema for updating an existing curation."""

    evidence_data: dict[str, Any] | None = Field(
        None, description="Updated evidence data"
    )
    lock_version: int = Field(..., description="Optimistic locking version (required)")

    model_config = ConfigDict(extra="forbid")


class CurationDraftSave(BaseModel):
    """Schema for saving a curation as draft."""

    evidence_data: dict[str, Any] = Field(..., description="Draft evidence data")
    lock_version: int | None = Field(None, description="Optional lock version")


class CurationSubmit(BaseModel):
    """Schema for submitting a curation for review."""

    notes: str | None = Field(None, max_length=1000, description="Submission notes")
    lock_version: int = Field(..., description="Lock version for optimistic locking")


# ========================================
# DATABASE SCHEMAS (InDBBase pattern - matches gene_assignment.py)
# ========================================


class CurationInDBBase(CurationBase):
    """Base schema with database fields."""

    id: UUID
    status: CurationStatus
    workflow_stage: WorkflowStage
    is_draft: bool

    # Computed results
    computed_scores: dict[str, Any]
    computed_verdict: str | None
    computed_summary: str | None

    # Optimistic locking
    lock_version: int

    # Timestamps
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    approved_at: datetime | None
    auto_saved_at: datetime | None

    # User references
    created_by: UUID | None
    updated_by: UUID | None
    submitted_by: UUID | None
    approved_by: UUID | None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


# ========================================
# RESPONSE SCHEMAS
# ========================================


class Curation(CurationInDBBase):
    """Full curation response schema."""

    pass


class CurationSummary(BaseModel):
    """Lightweight curation summary for list views (no evidence_data)."""

    id: UUID
    gene_id: UUID
    gene_symbol: str
    scope_id: UUID
    scope_name: str
    status: CurationStatus
    workflow_stage: WorkflowStage
    computed_verdict: str | None
    is_draft: bool
    created_at: datetime
    updated_at: datetime
    curator_name: str | None

    model_config = ConfigDict(use_enum_values=True)


class CurationListResponse(BaseModel):
    """Paginated list response."""

    curations: list[CurationSummary]
    total: int
    skip: int
    limit: int


class CurationScoreResponse(BaseModel):
    """Score calculation response."""

    curation_id: UUID
    total_score: float
    classification: str
    genetic_score: float
    experimental_score: float
    breakdown: dict[str, Any]
    calculated_at: datetime


class CurationConflictResponse(BaseModel):
    """409 Conflict response for optimistic locking."""

    error: str = "Concurrent modification detected"
    current_lock_version: int
    current_state: dict[str, Any]
    your_lock_version: int
