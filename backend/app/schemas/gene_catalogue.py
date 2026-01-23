"""Gene Catalogue Pydantic schemas for read-only aggregation view.

The Gene Catalogue is a read-only aggregation layer that provides a unified view
of genes with finished curations across all scopes. It never modifies source data.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScopeCurationSummary(BaseModel):
    """Summary of an active curation within a single scope."""

    scope_id: UUID = Field(..., description="Scope UUID")
    scope_name: str = Field(..., description="Scope slug (e.g., kidney-genetics)")
    scope_display_name: str = Field(..., description="Human-readable scope name")
    is_public: bool = Field(
        default=False, description="Whether scope is publicly visible"
    )

    # Disease information from evidence_data
    disease_name: str | None = Field(None, description="Disease name from curation")
    mondo_id: str | None = Field(None, description="MONDO ontology ID")
    mode_of_inheritance: str | None = Field(
        None, description="Mode of inheritance (AD, AR, XLD, etc.)"
    )

    # Classification and scoring from computed fields
    classification: str | None = Field(
        None,
        description="Classification verdict: definitive, strong, moderate, limited, no_known, disputed, refuted",
    )
    genetic_score: float | None = Field(None, description="Genetic evidence score")
    experimental_score: float | None = Field(
        None, description="Experimental evidence score"
    )
    total_score: float | None = Field(None, description="Combined total score")

    # Metadata
    activated_at: datetime = Field(..., description="When curation became active")
    curator_name: str | None = Field(None, description="Primary curator name")

    model_config = ConfigDict(from_attributes=True)


class GeneCatalogueEntry(BaseModel):
    """Single gene entry in the catalogue with aggregated curation information."""

    # Gene identification
    gene_id: UUID = Field(..., description="Gene UUID")
    hgnc_id: str = Field(..., description="HGNC identifier (e.g., HGNC:1100)")
    approved_symbol: str = Field(..., description="Official gene symbol")
    chromosome: str | None = Field(None, description="Chromosome (e.g., 17)")
    location: str | None = Field(
        None, description="Chromosomal location (e.g., 17q21.31)"
    )

    # Aggregated counts
    total_curations: int = Field(
        ..., description="Total number of active curations for this gene"
    )
    scope_count: int = Field(..., description="Number of scopes with active curations")

    # Classification distribution
    classifications: dict[str, int] = Field(
        default_factory=dict,
        description="Count by classification (e.g., {'definitive': 2, 'strong': 1})",
    )

    # Unique diseases across all curations
    diseases: list[str] = Field(
        default_factory=list, description="List of unique disease names"
    )

    # Per-scope curation details
    scope_curations: list[ScopeCurationSummary] = Field(
        default_factory=list, description="Detailed curation info per scope"
    )

    model_config = ConfigDict(from_attributes=True)


class GeneCatalogueSummaryStats(BaseModel):
    """Summary statistics for the entire catalogue."""

    total_genes_curated: int = Field(
        ..., description="Total number of genes with at least one active curation"
    )
    total_curations: int = Field(
        ..., description="Total number of active curations across all genes"
    )
    total_scopes: int = Field(..., description="Number of scopes with active curations")
    classification_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Overall classification distribution across all curations",
    )

    model_config = ConfigDict(from_attributes=True)


class GeneCatalogueResponse(BaseModel):
    """Paginated response for Gene Catalogue queries."""

    entries: list[GeneCatalogueEntry] = Field(
        default_factory=list, description="List of gene catalogue entries"
    )

    # Pagination
    total: int = Field(..., description="Total number of matching entries")
    skip: int = Field(default=0, description="Number of records skipped")
    limit: int = Field(default=20, description="Maximum records per page")
    has_next: bool = Field(default=False, description="More results available")
    has_prev: bool = Field(default=False, description="Previous results available")

    # Summary statistics
    summary: GeneCatalogueSummaryStats = Field(
        ..., description="Aggregate statistics for the catalogue"
    )

    model_config = ConfigDict(from_attributes=True)


class GeneCatalogueFilters(BaseModel):
    """Query filters for Gene Catalogue."""

    search: str | None = Field(
        None, description="Search gene symbol, HGNC ID, or aliases"
    )
    classification: str | None = Field(
        None,
        description="Filter by classification (definitive, strong, moderate, etc.)",
    )
    disease: str | None = Field(None, description="Search/filter by disease name")
    scope_id: UUID | None = Field(None, description="Filter by specific scope")
    chromosome: str | None = Field(None, description="Filter by chromosome")

    # Pagination and sorting
    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(
        default=20, ge=1, le=100, description="Maximum records to return"
    )
    sort_by: str = Field(
        default="approved_symbol",
        description="Sort field: approved_symbol, total_curations, chromosome",
    )
    sort_order: str = Field(default="asc", description="Sort order: asc or desc")

    model_config = ConfigDict(from_attributes=True)


class ScopeFilterOption(BaseModel):
    """Scope option for catalogue filter dropdowns."""

    id: str = Field(..., description="Scope UUID as string")
    name: str = Field(..., description="Scope slug (e.g., kidney-genetics)")
    display_name: str = Field(..., description="Human-readable scope name")
    is_active: bool = Field(default=True, description="Whether scope is active")

    model_config = ConfigDict(from_attributes=True)
