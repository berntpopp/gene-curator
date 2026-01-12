"""HGNC gene symbol validator with caching"""

import httpx

from app.core.logging import get_logger
from app.schemas.validation import (
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

    async def close(self) -> None:
        """Close HTTP client"""
        await self.client.aclose()
