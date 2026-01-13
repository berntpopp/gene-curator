"""
Pydantic V2 schemas for precuration API operations.
Follows ClinGen SOP v11 requirements for gene-disease-MOI establishment.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import CurationStatus, WorkflowStage

# ========================================
# PRECURATION EVIDENCE DATA SCHEMA
# ========================================


class PrecurationEvidenceData(BaseModel):
    """
    ClinGen SOP v11 precuration evidence structure.
    These fields are stored in the evidence_data JSONB column.
    """

    # Disease Entity (required for ClinGen)
    mondo_id: str = Field(..., description="Mondo Disease Ontology ID")
    disease_name: str = Field(..., description="Disease name (dyadic naming)")

    # Mode of Inheritance (required)
    mode_of_inheritance: str = Field(..., description="MOI code (AD, AR, XLD, etc.)")
    hp_moi_term: str | None = Field(None, description="HPO term for MOI")

    # Lumping & Splitting (conditional)
    lumping_splitting_applicable: bool = Field(False, description="Whether L&S applies")
    lumping_splitting_decision: str | None = Field(
        None, description="LUMP, SPLIT, or NOT_APPLICABLE"
    )
    lumping_splitting_notes: str | None = Field(None, description="L&S rationale")

    # Affiliation
    affiliation: str | None = Field(None, description="Curation group/affiliation")

    # Additional notes
    curator_notes: str | None = Field(None, description="Curator notes")


# ========================================
# REQUEST SCHEMAS
# ========================================


class PrecurationCreate(BaseModel):
    """Schema for creating a new precuration."""

    gene_id: UUID = Field(..., description="Gene UUID")
    scope_id: UUID = Field(..., description="Scope UUID")
    precuration_schema_id: UUID = Field(..., description="Precuration schema UUID")
    evidence_data: dict[str, Any] = Field(
        default_factory=dict, description="Precuration evidence data"
    )


class PrecurationUpdate(BaseModel):
    """Schema for updating an existing precuration."""

    evidence_data: dict[str, Any] | None = Field(
        None, description="Updated evidence data"
    )

    model_config = ConfigDict(extra="forbid")


class PrecurationSubmit(BaseModel):
    """Schema for submitting a precuration for review."""

    notes: str | None = Field(None, max_length=1000, description="Submission notes")


# ========================================
# DATABASE SCHEMAS (InDBBase pattern)
# ========================================


class PrecurationInDBBase(BaseModel):
    """Base schema with database fields."""

    id: UUID
    gene_id: UUID
    scope_id: UUID
    precuration_schema_id: UUID

    status: CurationStatus
    workflow_stage: WorkflowStage
    is_draft: bool

    evidence_data: dict[str, Any]
    computed_scores: dict[str, Any]
    computed_fields: dict[str, Any]

    created_at: datetime
    updated_at: datetime
    auto_saved_at: datetime | None

    created_by: UUID | None
    updated_by: UUID | None

    version_number: int

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


# ========================================
# RESPONSE SCHEMAS
# ========================================


class Precuration(PrecurationInDBBase):
    """Full precuration response schema."""

    pass


class PrecurationSummary(BaseModel):
    """Lightweight precuration summary for list views."""

    id: UUID
    gene_id: UUID
    gene_symbol: str
    scope_id: UUID
    scope_name: str
    status: CurationStatus
    workflow_stage: WorkflowStage
    mondo_id: str | None
    disease_name: str | None
    mode_of_inheritance: str | None
    is_draft: bool
    created_at: datetime
    updated_at: datetime
    curator_name: str | None

    model_config = ConfigDict(use_enum_values=True)


class PrecurationListResponse(BaseModel):
    """Paginated list response."""

    precurations: list[PrecurationSummary]
    total: int
    skip: int
    limit: int


class PrecurationApprovalResult(BaseModel):
    """Result of precuration approval."""

    precuration_id: UUID
    approved: bool
    curation_created: bool
    curation_id: UUID | None
    message: str
