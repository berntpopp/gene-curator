"""
Pydantic schemas for the Gene model in schema-agnostic system.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Base Schema
class GeneBase(BaseModel):
    """Base schema for genes."""

    hgnc_id: str = Field(..., description="HGNC identifier (e.g., HGNC:1234)")
    approved_symbol: str = Field(
        ..., min_length=1, max_length=100, description="Official gene symbol"
    )
    previous_symbols: list[str] | None = Field(
        default_factory=list, description="Previously used gene symbols"
    )
    alias_symbols: list[str] | None = Field(
        default_factory=list, description="Alternative gene symbols"
    )
    chromosome: str | None = Field(
        None, max_length=10, description="Chromosome location"
    )
    location: str | None = Field(
        None, max_length=50, description="Chromosomal location (e.g., 17q21.31)"
    )
    details: dict[str, Any] | None = Field(
        default_factory=dict, description="Additional gene metadata"
    )

    @field_validator("hgnc_id")
    @classmethod
    def validate_hgnc_id(cls, v: str) -> str:
        """Validate HGNC ID format."""
        if not v.startswith("HGNC:") or not v[5:].isdigit():
            raise ValueError(
                "HGNC ID must be in format HGNC:#### where #### is a number"
            )
        return v


# Creation Schema
class GeneCreate(GeneBase):
    """Schema for creating a new gene."""

    pass


# Update Schema
class GeneUpdate(BaseModel):
    """Schema for updating gene information."""

    hgnc_id: str | None = Field(None, description="HGNC identifier")
    approved_symbol: str | None = Field(None, min_length=1, max_length=100)
    previous_symbols: list[str] | None = None
    alias_symbols: list[str] | None = None
    chromosome: str | None = Field(None, max_length=10)
    location: str | None = Field(None, max_length=50)
    details: dict[str, Any] | None = None

    @field_validator("hgnc_id")
    @classmethod
    def validate_hgnc_id(cls, v: str | None) -> str | None:
        """Validate HGNC ID format if provided."""
        if v is not None and (not v.startswith("HGNC:") or not v[5:].isdigit()):
            raise ValueError(
                "HGNC ID must be in format HGNC:#### where #### is a number"
            )
        return v


# Database Schema
class GeneInDBBase(GeneBase):
    """Base schema with database fields."""

    id: UUID
    record_hash: str
    previous_hash: str | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    model_config = ConfigDict(from_attributes=True)


# Public Response Schema
class Gene(GeneInDBBase):
    """Public schema for genes."""

    pass


# Gene with Assignment Information
class GeneWithAssignments(Gene):
    """Gene with assignment information."""

    total_scope_assignments: int = Field(
        default=0, description="Total scope assignments"
    )
    scope_assignments: dict[str, Any] = Field(
        default_factory=dict, description="Assignment details by scope"
    )
    is_assigned_to_any_scope: bool = Field(
        default=False, description="Has any scope assignments"
    )

    model_config = ConfigDict(from_attributes=True)


# Gene with Curation Progress
class GeneWithProgress(Gene):
    """Gene with curation progress information."""

    total_precurations: int = Field(default=0, description="Total precurations")
    total_curations: int = Field(default=0, description="Total curations")
    precuration_status_counts: dict[str, int] = Field(
        default_factory=dict, description="Precuration counts by status"
    )
    curation_status_counts: dict[str, int] = Field(
        default_factory=dict, description="Curation counts by status"
    )
    has_active_work: bool = Field(default=False, description="Has active work")

    model_config = ConfigDict(from_attributes=True)


# Gene Summary for Lists
class GeneSummary(BaseModel):
    """Minimal gene information for lists and dropdowns."""

    id: UUID
    hgnc_id: str
    approved_symbol: str
    chromosome: str | None
    location: str | None
    is_assigned: bool = Field(default=False, description="Has scope assignments")
    has_active_work: bool = Field(default=False, description="Has active curation work")

    model_config = ConfigDict(from_attributes=True)


# Search Query Schema
class GeneSearchQuery(BaseModel):
    """Schema for gene search queries."""

    query: str | None = Field(
        None, description="Search term for gene symbol, name, or HGNC ID"
    )
    chromosome: str | None = Field(None, description="Filter by chromosome")
    hgnc_id: str | None = Field(None, description="Filter by specific HGNC ID")
    scope_id: UUID | None = Field(None, description="Filter by scope assignment")
    assigned_only: bool = Field(False, description="Only show assigned genes")
    has_active_work: bool | None = Field(
        None, description="Filter by active work status"
    )
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(
        50, ge=1, le=500, description="Maximum number of records to return"
    )
    sort_by: str = Field("approved_symbol", description="Field to sort by")
    sort_order: str = Field("asc", pattern="^(asc|desc)$", description="Sort order")


# List Response Schema
class GeneListResponse(BaseModel):
    """Response for paginated gene lists."""

    genes: list[GeneSummary]
    total: int
    skip: int
    limit: int
    has_next: bool
    has_prev: bool


# Statistics Schema
class GeneStatistics(BaseModel):
    """Gene database statistics with curation-focused metrics."""

    scope_id: UUID | None = Field(None, description="Scope filter applied")

    # Curation-focused statistics (primary)
    curated_genes: int = Field(0, description="Genes with active curations")
    active_curations: int = Field(0, description="Total active curation count")
    scopes_with_curations: int = Field(0, description="Scopes that have curations")
    total_scopes: int = Field(0, description="Total scope count")
    recent_curations: int = Field(0, description="Curations activated in last 30 days")
    pending_review: int = Field(0, description="Curations awaiting approval")

    # Gene database statistics (secondary, for admin)
    total_genes: int = Field(0, description="Total genes in database")
    genes_with_details: int = Field(0, description="Genes with detailed metadata")

    # Assignment statistics (when no scope filter)
    total_assignments: int | None = Field(None, description="Total scope assignments")
    assigned_genes: int | None = Field(None, description="Genes with assignments")
    unassigned_genes: int | None = Field(None, description="Genes without assignments")


# Bulk Operations
class GeneBulkCreate(BaseModel):
    """Schema for bulk gene creation."""

    genes: list[GeneCreate] = Field(..., min_length=1, max_length=100)
    validate_hgnc: bool = Field(
        True, description="Whether to validate HGNC IDs against external API"
    )
    skip_duplicates: bool = Field(
        True, description="Whether to skip genes with existing HGNC IDs"
    )


class GeneBulkCreateResponse(BaseModel):
    """Response for bulk gene creation."""

    created_genes: list[Gene]
    skipped_genes: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    total_processed: int
    total_created: int
    total_skipped: int
    total_errors: int


# Gene Assignment Status
class GeneAssignmentStatus(BaseModel):
    """Assignment status for a gene."""

    gene_id: UUID
    total_scope_assignments: int
    scope_assignments: dict[str, Any]
    is_assigned_to_any_scope: bool

    model_config = ConfigDict(from_attributes=True)


# Gene Curation Progress
class GeneCurationProgress(BaseModel):
    """Curation progress for a gene."""

    gene_id: UUID
    scope_id: UUID | None
    total_precurations: int
    total_curations: int
    precuration_status_counts: dict[str, int]
    curation_status_counts: dict[str, int]
    has_active_work: bool

    model_config = ConfigDict(from_attributes=True)


# Scope-specific Gene List
class ScopeGeneListResponse(BaseModel):
    """Response for scope-specific gene lists."""

    scope_id: UUID
    scope_name: str
    genes: list[GeneSummary]
    total: int
    assigned: int
    unassigned: int
    skip: int
    limit: int
    has_next: bool
    has_prev: bool


# Gene Import/Export
class GeneImportRequest(BaseModel):
    """Request for gene import."""

    source: str = Field(..., description="Import source (hgnc, manual, file)")
    data: dict[str, Any] = Field(..., description="Import data")
    options: dict[str, Any] = Field(default_factory=dict, description="Import options")


class GeneImportResponse(BaseModel):
    """Response for gene import."""

    import_id: UUID
    source: str
    status: str
    total_genes: int
    processed_genes: int
    successful_imports: int
    failed_imports: int
    warnings: list[str]
    errors: list[str]
    started_at: datetime
    completed_at: datetime | None


# Gene Validation
class GeneValidationResult(BaseModel):
    """Result of gene validation."""

    is_valid: bool
    hgnc_id: str
    approved_symbol: str
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    external_data: dict[str, Any] | None = Field(
        None, description="External validation data"
    )


# Gene Merge Request
class GeneMergeRequest(BaseModel):
    """Request to merge duplicate genes."""

    primary_gene_id: UUID = Field(..., description="Gene to keep")
    duplicate_gene_ids: list[UUID] = Field(
        ..., min_length=1, description="Genes to merge into primary"
    )
    merge_strategy: str = Field(
        "prefer_primary", description="How to handle conflicting data"
    )
    preserve_history: bool = Field(True, description="Preserve audit history")


class GeneMergeResponse(BaseModel):
    """Response for gene merge operation."""

    merged_gene: Gene
    duplicate_genes_processed: int
    assignments_transferred: int
    precurations_transferred: int
    curations_transferred: int
    warnings: list[str]
    errors: list[str]
