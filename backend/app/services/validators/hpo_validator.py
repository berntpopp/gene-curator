"""HPO phenotype term validator with caching"""

import httpx

from app.core.logging import get_logger
from app.schemas.validation import (
    HPOValidationData,
    ValidationResult,
)
from app.services.validators.base import ExternalValidator

logger = get_logger(__name__)

# HPO API endpoint (using OLS - Ontology Lookup Service)
HPO_API_BASE = "https://www.ebi.ac.uk/ols/api"


class HPOValidator(ExternalValidator):
    """Validates HPO terms against Human Phenotype Ontology"""

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(
            base_url=HPO_API_BASE,
            headers={"Accept": "application/json"},
            timeout=10.0,
        )

    async def validate(self, hpo_term: str) -> ValidationResult:
        """Validate HPO term against HPO API

        Args:
            hpo_term: HPO term ID to validate (e.g., 'HP:0001250')

        Returns:
            ValidationResult with HPO data if valid
        """
        try:
            # Clean up term ID
            term_id = hpo_term.strip().upper()
            if not term_id.startswith("HP:"):
                term_id = f"HP:{term_id}"

            # Validate format (HP:NNNNNNN)
            if not term_id.startswith("HP:") or len(term_id) != 10:
                return ValidationResult(
                    is_valid=False,
                    status="invalid",
                    error_message=f"Invalid HPO term format: '{hpo_term}' (expected HP:NNNNNNN)",
                )

            # URL encode the term ID (replace : with %3A)
            term_id_encoded = term_id.replace(":", "_")

            # Fetch term from OLS API
            response = await self.client.get(
                f"/ontologies/hp/terms/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252F{term_id_encoded}"
            )

            if response.status_code == 404:
                # Try searching for suggestions
                search_response = await self.client.get(
                    "/search",
                    params={
                        "q": term_id,
                        "ontology": "hp",
                        "rows": 5,
                    },
                )
                suggestions = []
                if search_response.status_code == 200:
                    search_data = search_response.json()
                    if "response" in search_data and "docs" in search_data["response"]:
                        suggestions = [
                            doc.get("obo_id", "")
                            for doc in search_data["response"]["docs"][:5]
                            if "obo_id" in doc
                        ]

                return ValidationResult(
                    is_valid=False,
                    status="not_found",
                    suggestions={"did_you_mean": suggestions} if suggestions else None,
                    error_message=f"HPO term '{term_id}' not found",
                )

            if response.status_code != 200:
                logger.error(
                    "HPO API error",
                    status_code=response.status_code,
                    hpo_term=term_id,
                )
                return ValidationResult(
                    is_valid=False,
                    status="error",
                    error_message="HPO API request failed",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()

            # Extract HPO data
            term_name = data.get("label", "")
            description = ""
            if data.get("description"):
                description = (
                    data["description"][0]
                    if isinstance(data["description"], list)
                    else data["description"]
                )

            synonyms = []
            if data.get("synonyms"):
                synonyms = (
                    data["synonyms"]
                    if isinstance(data["synonyms"], list)
                    else [data["synonyms"]]
                )

            validation_data = HPOValidationData(
                term_id=term_id,
                term_name=term_name,
                definition=description,
                synonyms=synonyms,
            )

            logger.info(
                "HPO validation successful",
                hpo_term=term_id,
                term_name=term_name,
            )

            return ValidationResult(
                is_valid=True,
                status="valid",
                data=validation_data.model_dump(),
            )

        except httpx.TimeoutException:
            logger.error("HPO API timeout", hpo_term=hpo_term)
            return ValidationResult(
                is_valid=False,
                status="error",
                error_message="HPO API request timed out",
                error_code="TIMEOUT",
            )
        except Exception as e:
            logger.error(
                "HPO validation error",
                hpo_term=hpo_term,
                error=e,
            )
            return ValidationResult(
                is_valid=False,
                status="error",
                error_message=f"Validation error: {e!s}",
                error_code="EXCEPTION",
            )

    async def batch_validate(self, hpo_terms: list[str]) -> dict[str, ValidationResult]:
        """Validate multiple HPO terms

        Args:
            hpo_terms: List of HPO terms to validate

        Returns:
            Dictionary mapping HPO terms to ValidationResults
        """
        results = {}
        for term in hpo_terms:
            results[term] = await self.validate(term)

        logger.info(
            "HPO batch validation completed",
            total=len(hpo_terms),
            valid=sum(1 for r in results.values() if r.is_valid),
        )

        return results

    async def close(self) -> None:
        """Close HTTP client"""
        await self.client.aclose()
