"""Validation Pydantic schemas for external validators (HGNC, PubMed, HPO)"""

from typing import Any

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """Result of external validation"""

    is_valid: bool = Field(..., description="Whether validation passed")
    status: str = Field(
        ...,
        description="Validation status: valid, invalid, not_found, error",
    )
    data: dict[str, Any] | None = Field(
        None, description="Validated data from external API"
    )
    suggestions: dict[str, list[str]] | None = Field(
        None, description="Suggestions for invalid inputs (e.g., did_you_mean)"
    )
    error_message: str | None = Field(
        None, description="Error message if validation failed"
    )
    error_code: str | None = Field(None, description="Error code if applicable")


class ValidationRequest(BaseModel):
    """Request for batch validation"""

    validator_name: str = Field(..., description="Validator to use: hgnc, pubmed, hpo")
    values: list[str] = Field(..., description="Values to validate")


class HGNCValidationData(BaseModel):
    """HGNC-specific validation data"""

    approved_symbol: str = Field(..., description="HGNC approved gene symbol")
    hgnc_id: str = Field(..., description="HGNC ID (e.g., HGNC:1100)")
    alias_symbols: list[str] = Field(default=[], description="Alias gene symbols")
    previous_symbols: list[str] = Field(default=[], description="Previous gene symbols")
    status: str = Field(..., description="Gene status (e.g., Approved)")
    locus_type: str | None = Field(None, description="Locus type")


class PubMedValidationData(BaseModel):
    """PubMed-specific validation data"""

    pmid: str = Field(..., description="PubMed ID")
    title: str = Field(..., description="Publication title")
    authors: list[str] = Field(..., description="Author names")
    journal: str = Field(..., description="Journal name")
    pub_date: str = Field(..., description="Publication date")
    doi: str | None = Field(None, description="DOI if available")


class HPOValidationData(BaseModel):
    """HPO-specific validation data"""

    term_id: str = Field(..., description="HPO term ID (e.g., HP:0001250)")
    term_name: str = Field(..., description="HPO term name")
    definition: str = Field(..., description="Term definition")
    synonyms: list[str] = Field(default=[], description="Term synonyms")


class CacheStatistics(BaseModel):
    """Validation cache statistics"""

    total_entries: int = Field(..., description="Total cache entries")
    hgnc_entries: int = Field(..., description="HGNC cache entries")
    pubmed_entries: int = Field(..., description="PubMed cache entries")
    hpo_entries: int = Field(..., description="HPO cache entries")
    total_hits: int = Field(..., description="Total cache hits")
    hit_rate: float = Field(..., description="Cache hit rate (0.0-1.0)")
    expired_entries: int = Field(..., description="Expired entries pending cleanup")
