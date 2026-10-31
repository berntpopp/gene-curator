"""Gene summary Pydantic schemas for cross-scope aggregation"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.curation import RelationshipType


class ScopeSummary(BaseModel):
    """Summary of curation for a single scope"""

    scope_id: UUID = Field(..., description="Scope UUID")
    scope_name: str = Field(
        ..., description="Scope slug (e.g., kidney-genetics), as tools take it"
    )
    scope_display_name: str = Field(..., description="Scope name to show people")
    is_public: bool = Field(..., description="Whether scope is public")
    classification: str | None = Field(
        None,
        description="Classification key of the schema (ClinGen: definitive, strong, moderate, limited, no_known, disputed, refuted)",
    )
    curation_id: UUID | None = Field(None, description="Curation this row links to")
    synopsis: str | None = Field(
        None,
        description="Synopsis of the active curation (schema synopsis_field); members, "
        "or anyone when the scope exports evidence publicly",
    )
    disease_name: str | None = Field(None, description="Disease of the curation")
    mondo_id: str | None = Field(None, description="MONDO id of the disease")
    mode_of_inheritance: str | None = Field(None, description="Mode of inheritance")
    relationship_type: RelationshipType = Field(
        "mendelian", description="mendelian or susceptibility (#539)"
    )
    stage: str | None = Field(None, description="Workflow stage of the curation")
    in_progress: bool = Field(
        False, description="True for a member's not-yet-active curation"
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
    conflict_summary: dict[str, int] = Field(
        default_factory=dict,
        description="classification_summary of the disease entities in conflict only",
    )
    scope_summaries: list[ScopeSummary] = Field(
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
