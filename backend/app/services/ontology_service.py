"""Ontology search service for MONDO, OMIM, and HPO

This service provides search functionality for biomedical ontologies using:
- MONDO: EBI OLS4 API (https://www.ebi.ac.uk/ols4/api/v2/)
- OMIM: JAX Network API (https://ontology.jax.org/api/network/)
- HPO: JAX HPO API (https://ontology.jax.org/api/hp/)

Design Principles:
- Single Responsibility: Handles ontology search operations only
- DRY: Shared HTTP client configuration
- Graceful degradation: Returns empty results on API failures
"""

from typing import Any
from urllib.parse import quote

import httpx

from app.core.logging import get_logger, timed_operation
from app.schemas.validation import (
    HPOInheritancePattern,
    HPOInheritanceResponse,
    HPOSearchResponse,
    HPOSearchResult,
    MONDOSearchResponse,
    MONDOSearchResult,
    OMIMDiseaseResult,
    OMIMGene,
    OMIMPhenotype,
    OMIMSearchResponse,
    OMIMSearchResult,
)

logger = get_logger(__name__)

# API base URLs
MONDO_API_BASE = "https://www.ebi.ac.uk/ols4/api/v2"
OMIM_API_BASE = "https://ontology.jax.org/api/network"
HPO_API_BASE = "https://ontology.jax.org/api/hp"


class OntologyService:
    """Search service for biomedical ontologies (MONDO, OMIM, HPO)

    Provides autocomplete-friendly search for disease and phenotype ontologies
    used in gene curation workflows.
    """

    def __init__(self) -> None:
        """Initialize HTTP clients for each API"""
        self._mondo_client = httpx.AsyncClient(
            base_url=MONDO_API_BASE,
            headers={"Accept": "application/json"},
            timeout=15.0,
        )
        self._omim_client = httpx.AsyncClient(
            base_url=OMIM_API_BASE,
            headers={"Accept": "application/json"},
            timeout=15.0,
        )
        self._hpo_client = httpx.AsyncClient(
            base_url=HPO_API_BASE,
            headers={"Accept": "application/json"},
            timeout=15.0,
        )

    async def close(self) -> None:
        """Close all HTTP clients"""
        await self._mondo_client.aclose()
        await self._omim_client.aclose()
        await self._hpo_client.aclose()

    @staticmethod
    def _extract_ols4_label(element: dict[str, Any]) -> str:
        """Extract label from OLS4 element (can be list or string)"""
        label = element.get("label", [])
        if isinstance(label, list):
            return label[0] if label else ""
        return label or ""

    @staticmethod
    def _extract_ols4_definition(element: dict[str, Any]) -> str | None:
        """Extract definition from OLS4 element"""
        def_list = element.get("definition", [])
        if not def_list or not isinstance(def_list, list):
            return None
        first_def = def_list[0]
        if isinstance(first_def, dict):
            value = first_def.get("value", "")
            return str(value) if value else ""
        return first_def if isinstance(first_def, str) else None

    @staticmethod
    def _extract_ols4_synonyms(element: dict[str, Any]) -> list[str]:
        """Extract synonyms from OLS4 element"""
        synonyms: list[str] = []
        synonym_data = element.get("synonym", [])
        if not isinstance(synonym_data, list):
            return synonyms
        for syn in synonym_data:
            if isinstance(syn, dict) and syn.get("value"):
                synonyms.append(syn["value"])
            elif isinstance(syn, str):
                synonyms.append(syn)
        return synonyms[:5]

    @staticmethod
    def _extract_ols4_xrefs(element: dict[str, Any]) -> list[str]:
        """Extract cross-references from OLS4 linked entities"""
        xrefs = []
        prefixes = ("OMIM:", "DOID:", "Orphanet:", "MESH:")
        linked = element.get("linkedEntities", {})
        for key in linked:
            if any(prefix in key for prefix in prefixes):
                xrefs.append(key)
        return xrefs[:10]

    def _parse_mondo_element(self, element: dict[str, Any]) -> MONDOSearchResult | None:
        """Parse a single MONDO element from OLS4 response"""
        mondo_id = element.get("curie", "")
        if not mondo_id.startswith("MONDO:"):
            return None

        return MONDOSearchResult(
            mondo_id=mondo_id,
            label=self._extract_ols4_label(element),
            definition=self._extract_ols4_definition(element),
            synonyms=self._extract_ols4_synonyms(element),
            xrefs=self._extract_ols4_xrefs(element),
            iri=element.get("iri"),
        )

    @timed_operation("mondo_search", warning_threshold_ms=3000)
    async def search_mondo(self, query: str, limit: int = 10) -> MONDOSearchResponse:
        """Search MONDO ontology for diseases

        Uses EBI OLS4 API to search the Monarch Disease Ontology.

        Args:
            query: Search query (disease name or MONDO ID)
            limit: Maximum results to return

        Returns:
            MONDOSearchResponse with matching diseases
        """
        try:
            response = await self._mondo_client.get(
                "/entities",
                params={
                    "search": query,
                    "size": limit,
                    "lang": "en",
                    "exactMatch": "false",
                    "includeObsoleteEntities": "false",
                    "ontologyId": "mondo",
                },
            )

            if response.status_code != 200:
                logger.error(
                    "MONDO API error",
                    status_code=response.status_code,
                    query=query,
                )
                return MONDOSearchResponse(query=query, total_results=0, results=[])

            data = response.json()
            results = [
                r
                for element in data.get("elements", [])
                if (r := self._parse_mondo_element(element)) is not None
            ]

            total_results = data.get("totalElements", len(results))

            logger.info(
                "MONDO search completed",
                query=query,
                results_count=len(results),
                total_available=total_results,
            )

            return MONDOSearchResponse(
                query=query,
                total_results=total_results,
                results=results,
            )

        except httpx.TimeoutException:
            logger.error("MONDO API timeout", query=query)
            return MONDOSearchResponse(query=query, total_results=0, results=[])
        except Exception as e:
            logger.error("MONDO search error", query=query, error=e)
            return MONDOSearchResponse(query=query, total_results=0, results=[])

    @timed_operation("omim_fetch", warning_threshold_ms=3000)
    async def get_omim_disease(self, omim_id: str) -> OMIMDiseaseResult | None:
        """Fetch OMIM disease details from JAX Network API

        Args:
            omim_id: OMIM ID (with or without "OMIM:" prefix)

        Returns:
            OMIMDiseaseResult with disease details, or None if not found
        """
        try:
            # Normalize OMIM ID
            if not omim_id.upper().startswith("OMIM:"):
                omim_id = f"OMIM:{omim_id}"
            omim_id = omim_id.upper()

            # URL encode the OMIM ID
            encoded_id = quote(omim_id, safe="")

            response = await self._omim_client.get(f"/annotation/{encoded_id}")

            if response.status_code == 404:
                logger.info("OMIM disease not found", omim_id=omim_id)
                return None

            if response.status_code != 200:
                logger.error(
                    "OMIM API error",
                    status_code=response.status_code,
                    omim_id=omim_id,
                )
                return None

            data = response.json()

            # Extract disease info
            disease = data.get("disease", {})
            categories = data.get("categories", {})
            gene_data = data.get("genes", [])

            # Build phenotypes by category
            phenotypes: dict[str, list[OMIMPhenotype]] = {}
            for category_name, phenotype_list in categories.items():
                if not isinstance(phenotype_list, list):
                    continue
                category_phenotypes = []
                for pheno in phenotype_list:
                    metadata = pheno.get("metadata", {})
                    category_phenotypes.append(
                        OMIMPhenotype(
                            hpo_id=pheno.get("id", ""),
                            name=pheno.get("name", ""),
                            category=category_name,
                            frequency=metadata.get("frequency"),
                            sources=metadata.get("sources", []),
                        )
                    )
                if category_phenotypes:
                    phenotypes[category_name] = category_phenotypes

            # Build genes list
            genes = [
                OMIMGene(
                    gene_id=g.get("id", ""),
                    symbol=g.get("name", ""),
                )
                for g in gene_data
            ]

            result = OMIMDiseaseResult(
                omim_id=disease.get("id", omim_id),
                name=disease.get("name", ""),
                mondo_id=disease.get("mondoId"),
                description=disease.get("description"),
                phenotypes=phenotypes,
                genes=genes,
            )

            logger.info(
                "OMIM disease fetched",
                omim_id=omim_id,
                name=result.name,
                phenotype_categories=len(phenotypes),
                genes_count=len(genes),
            )

            return result

        except httpx.TimeoutException:
            logger.error("OMIM API timeout", omim_id=omim_id)
            return None
        except Exception as e:
            logger.error("OMIM fetch error", omim_id=omim_id, error=e)
            return None

    @timed_operation("omim_search", warning_threshold_ms=3000)
    async def search_omim(self, query: str, limit: int = 10) -> OMIMSearchResponse:
        """Search OMIM diseases via MONDO (OMIM doesn't have direct search)

        Uses MONDO search with OMIM xref filtering to find OMIM diseases.

        Args:
            query: Search query (disease name or OMIM ID)
            limit: Maximum results to return

        Returns:
            OMIMSearchResponse with matching diseases
        """
        try:
            # If query looks like an OMIM ID, try direct fetch
            clean_query = query.strip().upper()
            if clean_query.startswith("OMIM:") or clean_query.isdigit():
                omim_id = clean_query if ":" in clean_query else f"OMIM:{clean_query}"
                disease = await self.get_omim_disease(omim_id)
                if disease:
                    return OMIMSearchResponse(
                        query=query,
                        total_results=1,
                        results=[
                            OMIMSearchResult(
                                omim_id=disease.omim_id,
                                name=disease.name,
                                mondo_id=disease.mondo_id,
                                gene_symbols=[g.symbol for g in disease.genes],
                            )
                        ],
                    )
                return OMIMSearchResponse(query=query, total_results=0, results=[])

            # Search MONDO and filter for entries with OMIM xrefs
            mondo_response = await self.search_mondo(query, limit=limit * 2)

            results = []
            for mondo_result in mondo_response.results:
                # Find OMIM xrefs
                omim_xrefs = [
                    xref for xref in mondo_result.xrefs if xref.startswith("OMIM:")
                ]
                for omim_id in omim_xrefs[:1]:  # Take first OMIM xref
                    results.append(
                        OMIMSearchResult(
                            omim_id=omim_id,
                            name=mondo_result.label,
                            mondo_id=mondo_result.mondo_id,
                            gene_symbols=[],
                        )
                    )
                    if len(results) >= limit:
                        break
                if len(results) >= limit:
                    break

            logger.info(
                "OMIM search completed",
                query=query,
                results_count=len(results),
            )

            return OMIMSearchResponse(
                query=query,
                total_results=len(results),
                results=results,
            )

        except Exception as e:
            logger.error("OMIM search error", query=query, error=e)
            return OMIMSearchResponse(query=query, total_results=0, results=[])

    @timed_operation("hpo_search", warning_threshold_ms=3000)
    async def search_hpo(self, query: str, limit: int = 10) -> HPOSearchResponse:
        """Search HPO ontology for phenotypes

        Uses JAX HPO API for reliable phenotype search.

        Args:
            query: Search query (phenotype name or HPO ID)
            limit: Maximum results to return

        Returns:
            HPOSearchResponse with matching phenotypes
        """
        try:
            response = await self._hpo_client.get(
                "/search",
                params={
                    "q": query,
                    "max": limit,
                },
            )

            if response.status_code != 200:
                logger.error(
                    "HPO API error",
                    status_code=response.status_code,
                    query=query,
                )
                return HPOSearchResponse(query=query, total_results=0, results=[])

            data = response.json()
            terms = data.get("terms", [])

            results = [
                HPOSearchResult(
                    hpo_id=term.get("id", ""),
                    name=term.get("name", ""),
                    definition=term.get("definition"),
                    synonyms=term.get("synonyms", [])[:5],
                    descendant_count=term.get("descendantCount", 0),
                )
                for term in terms
            ]

            total_results = data.get("totalCount", len(results))

            logger.info(
                "HPO search completed",
                query=query,
                results_count=len(results),
                total_available=total_results,
            )

            return HPOSearchResponse(
                query=query,
                total_results=total_results,
                results=results,
            )

        except httpx.TimeoutException:
            logger.error("HPO API timeout", query=query)
            return HPOSearchResponse(query=query, total_results=0, results=[])
        except Exception as e:
            logger.error("HPO search error", query=query, error=e)
            return HPOSearchResponse(query=query, total_results=0, results=[])

    # In-memory cache for inheritance patterns (rarely change)
    _inheritance_cache: HPOInheritanceResponse | None = None

    @timed_operation("hpo_inheritance", warning_threshold_ms=5000)
    async def get_inheritance_patterns(self) -> HPOInheritanceResponse:
        """Get all HPO inheritance pattern terms

        Fetches inheritance patterns from two branches:
        - HP:0034345 (Mendelian inheritance): AD, AR, X-linked, Mitochondrial, etc.
        - HP:0001426 (Non-Mendelian inheritance): Digenic, Oligogenic, Polygenic

        Results are cached in memory since inheritance patterns rarely change.

        Returns:
            HPOInheritanceResponse with categorized inheritance patterns
        """
        # Return cached result if available
        if OntologyService._inheritance_cache is not None:
            logger.debug("Returning cached inheritance patterns")
            cached = OntologyService._inheritance_cache
            return HPOInheritanceResponse(
                total_patterns=cached.total_patterns,
                mendelian=cached.mendelian,
                non_mendelian=cached.non_mendelian,
                cached=True,
            )

        mendelian_patterns: list[HPOInheritancePattern] = []
        non_mendelian_patterns: list[HPOInheritancePattern] = []

        try:
            # Fetch Mendelian inheritance patterns (HP:0034345 descendants)
            mendelian_response = await self._hpo_client.get(
                "/terms/HP:0034345/descendants"
            )
            if mendelian_response.status_code == 200:
                # API returns array directly, not {terms: [...]}
                terms = mendelian_response.json()
                if isinstance(terms, list):
                    for term in terms:
                        mendelian_patterns.append(
                            HPOInheritancePattern(
                                hpo_id=term.get("id", ""),
                                name=term.get("name", ""),
                                definition=term.get("definition"),
                                category="mendelian",
                            )
                        )

            # Fetch Non-Mendelian inheritance patterns (HP:0001426 descendants)
            non_mendelian_response = await self._hpo_client.get(
                "/terms/HP:0001426/descendants"
            )
            if non_mendelian_response.status_code == 200:
                # API returns array directly, not {terms: [...]}
                terms = non_mendelian_response.json()
                if isinstance(terms, list):
                    for term in terms:
                        non_mendelian_patterns.append(
                            HPOInheritancePattern(
                                hpo_id=term.get("id", ""),
                                name=term.get("name", ""),
                                definition=term.get("definition"),
                                category="non_mendelian",
                            )
                        )

            total = len(mendelian_patterns) + len(non_mendelian_patterns)

            result = HPOInheritanceResponse(
                total_patterns=total,
                mendelian=mendelian_patterns,
                non_mendelian=non_mendelian_patterns,
                cached=False,
            )

            # Cache the result
            OntologyService._inheritance_cache = result

            logger.info(
                "HPO inheritance patterns fetched",
                mendelian_count=len(mendelian_patterns),
                non_mendelian_count=len(non_mendelian_patterns),
                total=total,
            )

            return result

        except httpx.TimeoutException:
            logger.error("HPO API timeout fetching inheritance patterns")
            return HPOInheritanceResponse(
                total_patterns=0, mendelian=[], non_mendelian=[], cached=False
            )
        except Exception as e:
            logger.error("HPO inheritance fetch error", error=e)
            return HPOInheritanceResponse(
                total_patterns=0, mendelian=[], non_mendelian=[], cached=False
            )
