"""Schemas for batch resolution of pasted gene identifiers."""

import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

MAX_RESOLVE_INPUTS = 1000
MAX_TOKEN_LENGTH = 50
# Payload cap per entry: longer entries are rejected outright, shorter invalid ones are reported per item.
MAX_ENTRY_LENGTH = 256
# Symbols, HGNC IDs and families like "HOXA@": no whitespace, quotes or separators.
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@\-]*$")

MatchType = Literal["symbol", "previous_symbol", "alias", "hgnc_id"]
ResolveReason = Literal["lookup_cap", "lookup_timeout", "invalid_identifier"]


def is_gene_token(value: str) -> bool:
    """True for something that can be a symbol or HGNC ID (anything else is never looked up)."""
    return len(value) <= MAX_TOKEN_LENGTH and _TOKEN.match(value) is not None


class GeneResolveRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=1, max_length=MAX_RESOLVE_INPUTS)
    scope_id: UUID | None = Field(
        None, description="Flag candidates already in this scope (caller must see it)"
    )

    @field_validator("symbols")
    @classmethod
    def _clean(cls, values: list[str]) -> list[str]:
        cleaned = [v.strip() for v in values]
        for index, value in enumerate(cleaned):
            if len(value) > MAX_ENTRY_LENGTH:
                raise ValueError(
                    f"entry {index} is longer than {MAX_ENTRY_LENGTH} characters"
                )
        return cleaned


class GeneCandidate(BaseModel):
    hgnc_id: str
    symbol: str
    name: str | None = None
    gene_id: UUID | None = Field(
        None, description="Local gene row, null if only in HGNC"
    )
    in_scope: bool | None = Field(None, description="Already in the request's scope_id")
    in_scope_curator: str | None = Field(
        None, description="Its assigned curator there, if any (kept on add)"
    )


class GeneResolveItem(BaseModel):
    input: str
    index: int
    status: Literal["resolved", "ambiguous", "not_found"]
    match_type: MatchType | None = None
    source: Literal["local", "hgnc"] | None = None
    candidates: list[GeneCandidate] = Field(default_factory=list)
    reason: ResolveReason | None = Field(
        None, description="Why an input was not looked up at HGNC (not_found only)"
    )
    duplicate_of: int | None = Field(
        None, description="Index of the first input that resolved to the same gene"
    )


class GeneResolveCounts(BaseModel):
    resolved: int
    ambiguous: int
    not_found: int


class GeneResolveResponse(BaseModel):
    items: list[GeneResolveItem]
    counts: GeneResolveCounts
