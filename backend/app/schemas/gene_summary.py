"""Gene summary Pydantic schemas for cross-scope aggregation"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScopeSummary(BaseModel):
    """Summary of curation for a single scope"""

    scope_id: UUID = Field(..., description="Scope UUID")
    scope_name: str = Field(..., description="Scope name (e.g., kidney-genetics)")
    is_public: bool = Field(..., description="Whether scope is public")
    classification: str | None = Field(
        None,
        description="Classification: definitive, strong, moderate, limited, no_known, disputed, refuted",
    )
    genetic_score: float = Field(..., description="Total genetic evidence score")
    experimental_score: float = Field(
        ..., description="Total experimental evidence score"
    )
    total_score: float = Field(..., description="Combined total score")
    last_updated: datetime = Field(..., description="Last curation update timestamp")
    curator_count: int = Field(..., description="Number of curators involved")
    evidence_count: int = Field(..., description="Total evidence items")


class GeneSummaryPublic(BaseModel):
    """Public gene summary (only public scopes)"""

    gene_id: UUID = Field(..., description="Gene UUID")
    public_scopes_count: int = Field(
        ..., description="Number of public scopes curating this gene"
    )
    classification_summary: dict[str, int] = Field(
        ...,
        description="Count of curations by classification (e.g., {'definitive': 2, 'strong': 1})",
    )
    consensus_classification: str | None = Field(
        None, description="Consensus classification (if applicable)"
    )
    has_conflicts: bool = Field(
        ..., description="Whether different scopes have conflicting classifications"
    )
    scope_summaries: list[dict[str, Any]] = Field(
        ..., description="Per-scope summary details"
    )
    last_updated: datetime = Field(..., description="Last computation timestamp")

    model_config = ConfigDict(from_attributes=True)


class GeneSummaryFull(GeneSummaryPublic):
    """Full gene summary including private scopes (authenticated users)"""

    total_scopes_curated: int = Field(
        ..., description="Total number of scopes (public + private)"
    )
    private_scopes_count: int = Field(..., description="Number of private scopes")
    consensus_confidence: float | None = Field(
        None, description="Consensus confidence score (0.0-1.0)"
    )
    computation_version: int = Field(..., description="Computation algorithm version")
    is_stale: bool = Field(..., description="Whether summary needs recomputation")

    model_config = ConfigDict(from_attributes=True)


class GeneSummaryResponse(BaseModel):
    """API response wrapper for gene summaries"""

    gene_id: UUID
    gene_symbol: str | None = None
    hgnc_id: str | None = None
    summary: GeneSummaryPublic

    model_config = ConfigDict(from_attributes=True)
