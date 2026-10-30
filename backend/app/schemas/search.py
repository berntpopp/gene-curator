"""Command-palette search response."""

from uuid import UUID

from pydantic import BaseModel


class GeneHit(BaseModel):
    id: UUID
    symbol: str
    hgnc_id: str
    classification: str | None = None


class CurationHit(BaseModel):
    id: UUID
    gene_symbol: str
    scope_id: UUID
    scope_name: str
    status: str
    disease_name: str | None = None
    mondo_id: str | None = None
    mode_of_inheritance: str | None = None


class ScopeHit(BaseModel):
    id: UUID
    name: str
    display_name: str


class SearchResponse(BaseModel):
    genes: list[GeneHit]
    curations: list[CurationHit]
    scopes: list[ScopeHit]
