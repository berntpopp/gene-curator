"""Export v1: reviewed curations for downstream publishers (#532). See docs/EXPORT.md."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.curation import RelationshipType


class ExportMethodology(BaseModel):
    schema_name: str | None = Field(None, description="Curation schema name")
    version: int | None = Field(
        None,
        description="Pinned methodology version; null when the caller may not read "
        "methodology versions (anonymous)",
    )
    version_id: UUID | None = Field(None, description="Pinned methodology version id")


class ExportCuration(BaseModel):
    curation_id: UUID
    entity_key: str = Field(
        ...,
        description="MONDO|MOI, plus |SUSCEPTIBILITY for susceptibility; '' when the "
        "curation has no MONDO id",
    )
    url: str = Field(..., description="Link back to the curation in Gene Curator")
    status: str = Field(..., description="Curation status: active or archived")
    scope_name: str
    hgnc_id: str
    approved_symbol: str
    disease_name: str | None = None
    mondo_id: str | None = None
    mode_of_inheritance: str | None = Field(None, description="As entered")
    moi_hpo_id: str | None = Field(None, description="HPO CURIE of the canonical MOI")
    relationship_type: RelationshipType = Field(
        "mendelian", description="mendelian or susceptibility (#539)"
    )
    computed_verdict: str | None = None
    final_classification: str | None = Field(
        None, description="Curator classification confirmed at approval, else computed"
    )
    curator_classification_rationale: str | None = Field(
        None, description="Why the curator's class differs from the computed one"
    )
    genetic_score: float | None = None
    experimental_score: float | None = None
    total_score: float | None = None
    methodology: ExportMethodology
    pmids: list[str] = Field(..., description="Cited PMIDs, deduplicated, sorted")
    curator_name: str | None = None
    reviewer_name: str | None = Field(None, description="Who approved the curation")
    approved_at: datetime | None = None
    activated_at: datetime
    archived_at: datetime | None = None
    archive_reason: str | None = Field(
        None,
        description="Why it was archived: 'Curation deleted' (retract it) or "
        "'Replaced by new active curation'",
    )
    updated_at: datetime = Field(..., description="Last change; the paging key")


class CurationExportPage(BaseModel):
    export_version: Literal["1"] = "1"
    items: list[ExportCuration]
    next_cursor: str | None = Field(
        None, description="Pass as cursor for the next page; null on the last page"
    )
