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


# HGNC Search schemas for gene autocomplete
class HGNCGeneSearchResult(BaseModel):
    """Single gene result from HGNC search"""

    hgnc_id: str = Field(..., description="HGNC ID (e.g., HGNC:1100)")
    symbol: str = Field(..., description="Approved gene symbol")
    name: str | None = Field(None, description="Approved gene name")
    alias_symbols: list[str] = Field(default=[], description="Alias gene symbols")
    previous_symbols: list[str] = Field(default=[], description="Previous gene symbols")
    chromosome: str | None = Field(None, description="Chromosome location")
    location: str | None = Field(
        None, description="Chromosomal location (e.g., 17q21.31)"
    )
    locus_type: str | None = Field(None, description="Locus type")
    status: str | None = Field(None, description="Gene status (e.g., Approved)")


class HGNCSearchRequest(BaseModel):
    """Request for HGNC gene search"""

    query: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Search query (gene symbol, HGNC ID, or partial name)",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results to return",
    )


class HGNCSearchResponse(BaseModel):
    """Response from HGNC gene search"""

    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Total matching results")
    results: list[HGNCGeneSearchResult] = Field(
        default=[], description="List of matching genes"
    )


# MONDO (Monarch Disease Ontology) schemas
class MONDOSearchResult(BaseModel):
    """Single disease result from MONDO search"""

    mondo_id: str = Field(..., description="MONDO ID (e.g., MONDO:0001071)")
    label: str = Field(..., description="Disease name/label")
    definition: str | None = Field(None, description="Disease definition")
    synonyms: list[str] = Field(default=[], description="Alternative names")
    xrefs: list[str] = Field(
        default=[], description="Cross-references (OMIM, DOID, etc.)"
    )
    iri: str | None = Field(None, description="Full IRI of the term")


class MONDOSearchRequest(BaseModel):
    """Request for MONDO disease search"""

    query: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Search query (disease name or MONDO ID)",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results to return",
    )


class MONDOSearchResponse(BaseModel):
    """Response from MONDO disease search"""

    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Total matching results")
    results: list[MONDOSearchResult] = Field(
        default=[], description="List of matching diseases"
    )


# OMIM (Online Mendelian Inheritance in Man) schemas
class OMIMPhenotype(BaseModel):
    """HPO phenotype associated with an OMIM disease"""

    hpo_id: str = Field(..., description="HPO term ID (e.g., HP:0001250)")
    name: str = Field(..., description="Phenotype name")
    category: str | None = Field(None, description="Phenotype category")
    frequency: str | None = Field(None, description="Frequency in patients")
    sources: list[str] = Field(default=[], description="Evidence sources (PMIDs)")


class OMIMGene(BaseModel):
    """Gene associated with an OMIM disease"""

    gene_id: str = Field(..., description="Gene ID (e.g., NCBIGene:8260)")
    symbol: str = Field(..., description="Gene symbol")


class OMIMDiseaseResult(BaseModel):
    """OMIM disease details from JAX Network API"""

    omim_id: str = Field(..., description="OMIM ID (e.g., OMIM:300855)")
    name: str = Field(..., description="Disease name")
    mondo_id: str | None = Field(None, description="Linked MONDO ID")
    description: str | None = Field(None, description="Disease description")
    phenotypes: dict[str, list[OMIMPhenotype]] = Field(
        default={}, description="Phenotypes grouped by category"
    )
    genes: list[OMIMGene] = Field(default=[], description="Associated genes")


class OMIMSearchResult(BaseModel):
    """Simplified OMIM result for search/autocomplete"""

    omim_id: str = Field(..., description="OMIM ID (e.g., OMIM:300855)")
    name: str = Field(..., description="Disease name")
    mondo_id: str | None = Field(None, description="Linked MONDO ID")
    gene_symbols: list[str] = Field(default=[], description="Associated gene symbols")


class OMIMSearchRequest(BaseModel):
    """Request for OMIM disease search"""

    query: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Search query (disease name or OMIM ID)",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results to return",
    )


class OMIMSearchResponse(BaseModel):
    """Response from OMIM disease search"""

    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Total matching results")
    results: list[OMIMSearchResult] = Field(
        default=[], description="List of matching diseases"
    )


# HPO Search schemas (enhanced for search functionality)
class HPOSearchResult(BaseModel):
    """Single HPO term result from search"""

    hpo_id: str = Field(..., description="HPO term ID (e.g., HP:0001250)")
    name: str = Field(..., description="Term name")
    definition: str | None = Field(None, description="Term definition")
    synonyms: list[str] = Field(default=[], description="Term synonyms")
    descendant_count: int = Field(default=0, description="Number of child terms")


class HPOSearchRequest(BaseModel):
    """Request for HPO term search"""

    query: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Search query (phenotype name or HPO ID)",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results to return",
    )


class HPOSearchResponse(BaseModel):
    """Response from HPO term search"""

    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Total matching results")
    results: list[HPOSearchResult] = Field(
        default=[], description="List of matching HPO terms"
    )


# HPO Inheritance Pattern schemas
class HPOInheritancePattern(BaseModel):
    """Single HPO inheritance pattern term"""

    hpo_id: str = Field(..., description="HPO term ID (e.g., HP:0000006)")
    name: str = Field(..., description="Inheritance pattern name")
    definition: str | None = Field(None, description="Term definition")
    category: str = Field(
        ..., description="Category: mendelian, non_mendelian, or qualifier"
    )


class HPOInheritanceResponse(BaseModel):
    """Response containing all inheritance pattern options"""

    total_patterns: int = Field(..., description="Total inheritance patterns")
    mendelian: list[HPOInheritancePattern] = Field(
        default=[], description="Mendelian inheritance patterns"
    )
    non_mendelian: list[HPOInheritancePattern] = Field(
        default=[], description="Non-Mendelian inheritance patterns"
    )
    cached: bool = Field(default=False, description="Whether result was from cache")


# Publication/PMID validation schemas
class PublicationAuthor(BaseModel):
    """Publication author information"""

    name: str = Field(..., description="Author name")
    affiliation: str | None = Field(None, description="Author affiliation")


class PublicationData(BaseModel):
    """Validated publication data from PubMed/Europe PMC"""

    pmid: str = Field(..., description="PubMed ID")
    title: str = Field(..., description="Publication title")
    authors: list[str] = Field(default=[], description="Author names")
    author_string: str | None = Field(None, description="Formatted author string")
    journal: str = Field(..., description="Journal name")
    journal_abbrev: str | None = Field(None, description="Journal abbreviation")
    year: int | None = Field(None, description="Publication year")
    volume: str | None = Field(None, description="Journal volume")
    issue: str | None = Field(None, description="Journal issue")
    pages: str | None = Field(None, description="Page numbers")
    doi: str | None = Field(None, description="DOI")
    pmcid: str | None = Field(None, description="PubMed Central ID")
    abstract: str | None = Field(None, description="Publication abstract")
    pub_type: str | None = Field(None, description="Publication type")
    is_open_access: bool = Field(default=False, description="Open access status")
    cited_by_count: int | None = Field(None, description="Citation count")
    publication_date: str | None = Field(None, description="Full publication date")


class PMIDValidationRequest(BaseModel):
    """Request to validate one or more PMIDs"""

    pmids: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of PubMed IDs to validate (max 50)",
    )


class PMIDValidationResult(BaseModel):
    """Result of single PMID validation"""

    pmid: str = Field(..., description="PubMed ID")
    is_valid: bool = Field(..., description="Whether PMID exists")
    publication: PublicationData | None = Field(
        None, description="Publication data if valid"
    )
    error: str | None = Field(None, description="Error message if invalid")


class PMIDValidationResponse(BaseModel):
    """Response from PMID validation"""

    total_requested: int = Field(..., description="Number of PMIDs requested")
    valid_count: int = Field(..., description="Number of valid PMIDs")
    invalid_count: int = Field(..., description="Number of invalid PMIDs")
    results: list[PMIDValidationResult] = Field(
        default=[], description="Validation results"
    )
