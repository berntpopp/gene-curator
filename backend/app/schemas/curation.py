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


MERGE_DESCRIPTION = (
    "false or omitted: evidence_data replaces the stored evidence_data entirely. true: "
    "evidence_data is an RFC 7396 JSON merge patch on the stored evidence_data (objects "
    "merge, null deletes a key, arrays replace whole); a stale lock_version still 409s."
)


class CurationUpdate(BaseModel):
    """Schema for updating an existing curation."""

    evidence_data: dict[str, Any] | None = Field(
        None, description="Updated evidence data"
    )
    lock_version: int = Field(..., description="Optimistic locking version (required)")
    merge: bool | None = Field(None, description=MERGE_DESCRIPTION)

    model_config = ConfigDict(extra="forbid")


class CurationDraftSave(BaseModel):
    """Schema for saving a curation as draft."""

    evidence_data: dict[str, Any] = Field(..., description="Draft evidence data")
    lock_version: int = Field(..., description="Optimistic locking version (required)")
    merge: bool | None = Field(None, description=MERGE_DESCRIPTION)


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

    # Methodology version pinned at creation (None only without the 042 trigger, e.g. SQLite)
    methodology_version_id: UUID | None = None

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


class EvidenceWarning(BaseModel):
    """A value a draft keeps but that needs fixing before submit."""

    path: str = Field(..., description="Dotted field path in evidence_data")
    message: str


class CurationDraftResult(Curation):
    """Saved draft plus warnings: malformed or unknown PMIDs, MONDO, OMIM and HPO IDs."""

    warnings: list[EvidenceWarning] = []


_DISEASE_KEYS = ("disease_name", "mondo_id", "mode_of_inheritance")


def disease_fields(
    evidence: dict[str, Any] | None, precuration: dict[str, Any] | None
) -> dict[str, Any]:
    """Disease fields from the flat or nested (`entity_definition.*`) shape; evidence wins."""

    def pick(source: dict[str, Any] | None, key: str) -> Any:
        source = source or {}
        nested = source.get("entity_definition")
        return source.get(key) or (
            nested.get(key) if isinstance(nested, dict) else None
        )

    return {k: pick(evidence, k) or pick(precuration, k) for k in _DISEASE_KEYS}


class CurationDetail(CurationInDBBase):
    """Detailed curation response with expanded relations."""

    # Expanded from gene relationship
    gene_symbol: str | None = None
    hgnc_id: str | None = None

    # Expanded from scope relationship
    scope_name: str | None = None

    # Expanded from creator relationship
    curator_name: str | None = None
    curator_id: UUID | None = None

    # Extracted from evidence_data for convenience
    disease_name: str | None = None
    mondo_id: str | None = None
    mode_of_inheritance: str | None = None

    # User permissions for this curation (set by endpoint based on current user)
    can_edit: bool = False
    can_review: bool = False
    can_delete: bool = False
    # Open review round only: the user's approval is recorded / approvals still needed (#430)
    has_approved: bool = False
    approvals_remaining: int | None = None

    @classmethod
    def from_orm_with_relations(cls, curation: Any) -> "CurationDetail":
        """Create instance from ORM model with loaded relationships."""
        # Base data from model
        data = {
            "id": curation.id,
            "gene_id": curation.gene_id,
            "scope_id": curation.scope_id,
            "workflow_pair_id": curation.workflow_pair_id,
            "precuration_id": curation.precuration_id,
            "evidence_data": curation.evidence_data or {},
            "status": curation.status,
            "workflow_stage": curation.workflow_stage,
            "is_draft": curation.is_draft,
            "computed_scores": curation.computed_scores or {},
            "computed_verdict": curation.computed_verdict,
            "computed_summary": curation.computed_summary,
            "lock_version": curation.lock_version,
            "methodology_version_id": curation.methodology_version_id,
            "created_at": curation.created_at,
            "updated_at": curation.updated_at,
            "submitted_at": curation.submitted_at,
            "approved_at": curation.approved_at,
            "auto_saved_at": curation.auto_saved_at,
            "created_by": curation.created_by,
            "updated_by": curation.updated_by,
            "submitted_by": curation.submitted_by,
            "approved_by": curation.approved_by,
        }

        # Expand gene relationship
        if hasattr(curation, "gene") and curation.gene:
            data["gene_symbol"] = curation.gene.approved_symbol
            data["hgnc_id"] = curation.gene.hgnc_id

        # Expand scope relationship
        if hasattr(curation, "scope") and curation.scope:
            data["scope_name"] = curation.scope.name

        # Expand creator relationship
        if hasattr(curation, "creator") and curation.creator:
            data["curator_name"] = curation.creator.name or curation.creator.email
            data["curator_id"] = curation.creator.id

        # Extract from evidence_data OR precuration for convenience
        evidence: dict[str, Any] = curation.evidence_data or {}
        precuration_data: dict[str, Any] = {}
        if hasattr(curation, "precuration") and curation.precuration:
            precuration_data = curation.precuration.evidence_data or {}

        # Priority: evidence_data > precuration_data
        data.update(disease_fields(evidence, precuration_data))

        return cls(**data)


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
    computed_scores: dict[str, Any] | None = None
    disease_name: str | None = None
    is_draft: bool
    created_at: datetime
    updated_at: datetime
    curator_name: str | None
    created_by: UUID | None = None  # For 4-eyes filtering in review queue

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
    trace: dict[str, Any] | None = (
        None  # point model trace: sections > categories > types
    )
    calculated_at: datetime


class CurationConflictResponse(BaseModel):
    """409 Conflict response for optimistic locking."""

    error: str = "Concurrent modification detected"
    current_lock_version: int
    current_state: dict[str, Any]
    your_lock_version: int
