"""Command-palette search response."""

from uuid import UUID

from pydantic import BaseModel


class GeneHit(BaseModel):
    id: UUID
    symbol: str
    hgnc_id: str


class CurationHit(BaseModel):
    id: UUID
    gene_symbol: str
    scope_id: UUID
    scope_name: str
    status: str


class ScopeHit(BaseModel):
    id: UUID
    name: str
    display_name: str


class SearchResponse(BaseModel):
    genes: list[GeneHit]
    curations: list[CurationHit]
    scopes: list[ScopeHit]
