"""HGNC gene symbol validator with caching and search functionality"""

from typing import Any

import httpx

from app.core.logging import get_logger
from app.schemas.validation import (
    HGNCGeneSearchResult,
    HGNCSearchResponse,
    HGNCValidationData,
    ValidationResult,
)
from app.services.validators.base import ExternalValidator

logger = get_logger(__name__)

# HGNC REST API endpoint
HGNC_API_BASE = "https://rest.genenames.org"


class HGNCValidator(ExternalValidator):
    """Validates gene symbols against HGNC database"""

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(
            base_url=HGNC_API_BASE,
            headers={"Accept": "application/json"},
            timeout=10.0,
        )

    async def validate(self, gene_symbol: str) -> ValidationResult:
        """Validate gene symbol against HGNC API

        Args:
            gene_symbol: Gene symbol to validate (e.g., 'BRCA1')

        Returns:
            ValidationResult with HGNC data if valid
        """
        try:
            # Search by symbol
            response = await self.client.get(f"/fetch/symbol/{gene_symbol.upper()}")

            if response.status_code == 404:
                # Try searching for suggestions
                search_response = await self.client.get(
                    "/search",
                    params={"query": gene_symbol, "rows": 5},
                )
                suggestions = []
                if search_response.status_code == 200:
                    search_data = search_response.json()
                    if "response" in search_data and "docs" in search_data["response"]:
                        suggestions = [
                            doc.get("symbol", "")
                            for doc in search_data["response"]["docs"][:5]
                        ]

                return ValidationResult(
                    is_valid=False,
                    status="not_found",
                    suggestions={"did_you_mean": suggestions} if suggestions else None,
                    error_message=f"Gene symbol '{gene_symbol}' not found in HGNC database",
                )

            if response.status_code != 200:
                logger.error(
                    "HGNC API error",
                    status_code=response.status_code,
                    gene_symbol=gene_symbol,
                )
                return ValidationResult(
                    is_valid=False,
                    status="error",
                    error_message="HGNC API request failed",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()

            # Extract HGNC data
            if "response" not in data or "docs" not in data["response"]:
                return ValidationResult(
                    is_valid=False,
                    status="error",
                    error_message="Unexpected HGNC API response format",
                )

            docs = data["response"]["docs"]
            if not docs:
                return ValidationResult(
                    is_valid=False,
                    status="not_found",
                    error_message=f"Gene symbol '{gene_symbol}' not found",
                )

            hgnc_doc = docs[0]

            # Build validation data
            validation_data = HGNCValidationData(
                approved_symbol=hgnc_doc.get("symbol", ""),
                hgnc_id=hgnc_doc.get("hgnc_id", ""),
                alias_symbols=hgnc_doc.get("alias_symbol", []),
                previous_symbols=hgnc_doc.get("prev_symbol", []),
                status=hgnc_doc.get("status", ""),
                locus_type=hgnc_doc.get("locus_type"),
            )

            logger.info(
                "HGNC validation successful",
                gene_symbol=gene_symbol,
                approved_symbol=validation_data.approved_symbol,
                hgnc_id=validation_data.hgnc_id,
            )

            return ValidationResult(
                is_valid=True,
                status="valid",
                data=validation_data.model_dump(),
            )

        except httpx.TimeoutException:
            logger.error("HGNC API timeout", gene_symbol=gene_symbol)
            return ValidationResult(
                is_valid=False,
                status="error",
                error_message="HGNC API request timed out",
                error_code="TIMEOUT",
            )
        except Exception as e:
            logger.error(
                "HGNC validation error",
                gene_symbol=gene_symbol,
                error=e,
            )
            return ValidationResult(
                is_valid=False,
                status="error",
                error_message=f"Validation error: {e!s}",
                error_code="EXCEPTION",
            )

    async def batch_validate(
        self, gene_symbols: list[str]
    ) -> dict[str, ValidationResult]:
        """Validate multiple gene symbols

        Args:
            gene_symbols: List of gene symbols to validate

        Returns:
            Dictionary mapping gene symbols to ValidationResults
        """
        results = {}
        for symbol in gene_symbols:
            results[symbol] = await self.validate(symbol)

        logger.info(
            "HGNC batch validation completed",
            total=len(gene_symbols),
            valid=sum(1 for r in results.values() if r.is_valid),
        )

        return results

    async def search(self, query: str, limit: int = 10) -> HGNCSearchResponse:
        """Search HGNC database for genes matching query

        Supports searching by:
        - Gene symbol (exact or partial with wildcard)
        - HGNC ID (e.g., HGNC:1100 or just 1100)
        - Gene name (partial match)
        - Alias symbols

        Args:
            query: Search query string
            limit: Maximum number of results (default: 10, max: 50)

        Returns:
            HGNCSearchResponse with matching genes
        """
        try:
            # Normalize query
            query = query.strip()
            if not query:
                return HGNCSearchResponse(query=query, total_results=0, results=[])

            # Build search URL based on query type
            search_url = self._build_search_url(query)

            logger.debug(
                "HGNC search request",
                query=query,
                search_url=search_url,
                limit=limit,
            )

            response = await self.client.get(search_url)

            if response.status_code != 200:
                logger.error(
                    "HGNC search API error",
                    status_code=response.status_code,
                    query=query,
                )
                return HGNCSearchResponse(query=query, total_results=0, results=[])

            data = response.json()

            # Parse response
            results = self._parse_search_response(data, limit)

            logger.info(
                "HGNC search completed",
                query=query,
                total_results=len(results),
            )

            return HGNCSearchResponse(
                query=query,
                total_results=len(results),
                results=results,
            )

        except httpx.TimeoutException:
            logger.error("HGNC search timeout", query=query)
            return HGNCSearchResponse(query=query, total_results=0, results=[])
        except Exception as e:
            logger.error("HGNC search error", query=query, error=e)
            return HGNCSearchResponse(query=query, total_results=0, results=[])

    def _build_search_url(self, query: str) -> str:
        """Build appropriate HGNC search URL based on query type

        Args:
            query: User's search query

        Returns:
            Appropriate HGNC REST API URL
        """
        query_upper = query.upper()

        # Check if it's an HGNC ID (with or without prefix)
        if query_upper.startswith("HGNC:"):
            hgnc_num = query_upper.replace("HGNC:", "")
            return f"/fetch/hgnc_id/HGNC:{hgnc_num}"
        elif query.isdigit():
            # Just a number, treat as HGNC ID
            return f"/fetch/hgnc_id/HGNC:{query}"

        # For gene symbols and names, use search with wildcard
        # Search across symbol, alias_symbol, prev_symbol, and name fields
        search_term = query_upper
        if len(query) >= 2:
            # Add wildcard for partial matching
            search_term = f"{query_upper}*"

        # Use combined search across multiple fields
        search_query = (
            f"symbol:{search_term}+OR+"
            f"alias_symbol:{search_term}+OR+"
            f"prev_symbol:{search_term}+OR+"
            f"name:*{query_upper}*"
        )
        return f"/search/{search_query}"

    def _parse_search_response(
        self, data: dict[str, Any], limit: int
    ) -> list[HGNCGeneSearchResult]:
        """Parse HGNC API response into search results

        Args:
            data: Raw HGNC API response
            limit: Maximum results to return

        Returns:
            List of HGNCGeneSearchResult objects
        """
        results: list[HGNCGeneSearchResult] = []

        if "response" not in data or "docs" not in data["response"]:
            return results

        docs = data["response"]["docs"][:limit]

        for doc in docs:
            result = HGNCGeneSearchResult(
                hgnc_id=doc.get("hgnc_id", ""),
                symbol=doc.get("symbol", ""),
                name=doc.get("name"),
                alias_symbols=doc.get("alias_symbol", []) or [],
                previous_symbols=doc.get("prev_symbol", []) or [],
                chromosome=doc.get("location", "").split("q")[0].split("p")[0]
                if doc.get("location")
                else None,
                location=doc.get("location"),
                locus_type=doc.get("locus_type"),
                status=doc.get("status"),
            )
            results.append(result)

        return results

    async def fetch_gene_by_id(self, hgnc_id: str) -> HGNCGeneSearchResult | None:
        """Fetch complete gene data by HGNC ID

        Args:
            hgnc_id: HGNC ID (e.g., "HGNC:1100" or "1100")

        Returns:
            HGNCGeneSearchResult with full gene data, or None if not found
        """
        try:
            # Normalize HGNC ID
            if not hgnc_id.upper().startswith("HGNC:"):
                hgnc_id = f"HGNC:{hgnc_id}"

            response = await self.client.get(f"/fetch/hgnc_id/{hgnc_id}")

            if response.status_code != 200:
                return None

            data = response.json()

            if "response" not in data or "docs" not in data["response"]:
                return None

            docs = data["response"]["docs"]
            if not docs:
                return None

            doc = docs[0]
            return HGNCGeneSearchResult(
                hgnc_id=doc.get("hgnc_id", ""),
                symbol=doc.get("symbol", ""),
                name=doc.get("name"),
                alias_symbols=doc.get("alias_symbol", []) or [],
                previous_symbols=doc.get("prev_symbol", []) or [],
                chromosome=doc.get("location", "").split("q")[0].split("p")[0]
                if doc.get("location")
                else None,
                location=doc.get("location"),
                locus_type=doc.get("locus_type"),
                status=doc.get("status"),
            )

        except Exception as e:
            logger.error("HGNC fetch by ID error", hgnc_id=hgnc_id, error=e)
            return None

    async def close(self) -> None:
        """Close HTTP client"""
        await self.client.aclose()
