"""Schemas for the catalogue genes x scopes matrix (read-only)."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

MAX_MATRIX_SCOPES = 50

Agreement = Literal["agree", "disagree", "single", "none"]


class MatrixScope(BaseModel):
    id: UUID
    name: str
    display_name: str
    is_public: bool


class MatrixCell(BaseModel):
    """One gene in one scope: the active curation, else the member's in-progress one."""

    scope_id: UUID
    curation_id: UUID
    classification: str | None = None
    stage: str = Field(..., description="Workflow stage of the curation")
    status: str = Field(..., description="Curation status")
    total_score: float | None = None
    in_progress: bool = Field(
        ..., description="True when not yet active; only visible to scope members"
    )


class MatrixRow(BaseModel):
    gene_id: UUID
    hgnc_id: str
    approved_symbol: str
    chromosome: str | None = None
    location: str | None = None
    agreement: Agreement = Field(
        ...,
        description="Across active classifications: agree, disagree, "
        "single (only one classified scope) or none",
    )
    cells: list[MatrixCell] = Field(default_factory=list)


class MatrixResponse(BaseModel):
    scopes: list[MatrixScope] = Field(
        ..., description="Requested scopes the caller may see, in request order"
    )
    rows: list[MatrixRow]
    total: int
    skip: int
    limit: int
    has_next: bool
    has_prev: bool
