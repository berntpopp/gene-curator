"""PubMed PMID validator with caching"""

import httpx

from app.core.logging import get_logger
from app.schemas.validation import (
    PubMedValidationData,
    ValidationResult,
)
from app.services.validators.base import ExternalValidator

logger = get_logger(__name__)

# NCBI E-utilities API
PUBMED_API_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedValidator(ExternalValidator):
    """Validates PMIDs against PubMed database"""

    def __init__(self, email: str | None = None, api_key: str | None = None) -> None:
        """Initialize PubMed validator

        Args:
            email: Email for NCBI API (polite usage)
            api_key: NCBI API key (optional, increases rate limit)
        """
        self.email = email or "gene-curator@example.com"
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=10.0)

    async def validate(self, pmid: str) -> ValidationResult:
        """Validate PMID against PubMed API

        Args:
            pmid: PubMed ID to validate (e.g., '12345678')

        Returns:
            ValidationResult with publication data if valid
        """
        try:
            # Remove 'PMID:' prefix if present
            pmid_clean = pmid.replace("PMID:", "").strip()

            # Validate PMID format (numeric)
            if not pmid_clean.isdigit():
                return ValidationResult(
                    is_valid=False,
                    status="invalid",
                    error_message=f"Invalid PMID format: '{pmid}' (must be numeric)",
                )

            # Fetch publication summary
            params = {
                "db": "pubmed",
                "id": pmid_clean,
                "retmode": "xml",
                "email": self.email,
            }
            if self.api_key:
                params["api_key"] = self.api_key

            response = await self.client.get(
                f"{PUBMED_API_BASE}/efetch.fcgi",
                params=params,
            )

            if response.status_code != 200:
                logger.error(
                    "PubMed API error",
                    status_code=response.status_code,
                    pmid=pmid_clean,
                )
                return ValidationResult(
                    is_valid=False,
                    status="error",
                    error_message="PubMed API request failed",
                    error_code=f"HTTP_{response.status_code}",
                )

            # Parse XML response
            import defusedxml.ElementTree as ET  # noqa: N817

            try:
                root = ET.fromstring(response.text)
            except ET.ParseError:
                return ValidationResult(
                    is_valid=False,
                    status="error",
                    error_message="Failed to parse PubMed API response",
                )

            # Check if article exists
            article = root.find(".//PubmedArticle")
            if article is None:
                return ValidationResult(
                    is_valid=False,
                    status="not_found",
                    error_message=f"PMID '{pmid_clean}' not found in PubMed",
                )

            # Extract publication data
            medline_citation = article.find(".//MedlineCitation")
            if medline_citation is None:
                return ValidationResult(
                    is_valid=False,
                    status="error",
                    error_message="Invalid PubMed response structure",
                )

            article_elem = medline_citation.find(".//Article")
            if article_elem is None:
                return ValidationResult(
                    is_valid=False,
                    status="error",
                    error_message="Article data missing from PubMed response",
                )

            # Extract title
            title_elem = article_elem.find(".//ArticleTitle")
            title = (
                title_elem.text
                if title_elem is not None and title_elem.text
                else "Title not available"
            )

            # Extract authors
            authors = []
            author_list = article_elem.find(".//AuthorList")
            if author_list is not None:
                for author in author_list.findall(".//Author"):
                    last_name = author.find(".//LastName")
                    fore_name = author.find(".//ForeName")
                    if last_name is not None:
                        author_name = last_name.text or ""
                        if fore_name is not None and fore_name.text:
                            author_name = f"{last_name.text} {fore_name.text}"
                        authors.append(author_name)

            # Extract journal
            journal_elem = article_elem.find(".//Journal/Title")
            journal = (
                journal_elem.text
                if journal_elem is not None and journal_elem.text
                else "Journal not available"
            )

            # Extract publication date
            pub_date = article_elem.find(".//Journal/JournalIssue/PubDate")
            pub_date_str = "Date not available"
            if pub_date is not None:
                year = pub_date.find(".//Year")
                month = pub_date.find(".//Month")
                day = pub_date.find(".//Day")
                date_parts = []
                if year is not None and year.text:
                    date_parts.append(year.text)
                if month is not None and month.text:
                    date_parts.append(month.text)
                if day is not None and day.text:
                    date_parts.append(day.text)
                if date_parts:
                    pub_date_str = " ".join(date_parts)

            # Extract DOI
            doi = None
            article_id_list = article.find(".//PubmedData/ArticleIdList")
            if article_id_list is not None:
                for article_id in article_id_list.findall(".//ArticleId"):
                    if article_id.get("IdType") == "doi":
                        doi = article_id.text
                        break

            validation_data = PubMedValidationData(
                pmid=pmid_clean,
                title=title,
                authors=authors,
                journal=journal,
                pub_date=pub_date_str,
                doi=doi,
            )

            logger.info(
                "PubMed validation successful",
                pmid=pmid_clean,
                title=title[:50],
            )

            return ValidationResult(
                is_valid=True,
                status="valid",
                data=validation_data.model_dump(),
            )

        except httpx.TimeoutException:
            logger.error("PubMed API timeout", pmid=pmid)
            return ValidationResult(
                is_valid=False,
                status="error",
                error_message="PubMed API request timed out",
                error_code="TIMEOUT",
            )
        except Exception as e:
            logger.error(
                "PubMed validation error",
                pmid=pmid,
                error=e,
            )
            return ValidationResult(
                is_valid=False,
                status="error",
                error_message=f"Validation error: {e!s}",
                error_code="EXCEPTION",
            )

    async def batch_validate(self, pmids: list[str]) -> dict[str, ValidationResult]:
        """Validate multiple PMIDs

        Args:
            pmids: List of PMIDs to validate

        Returns:
            Dictionary mapping PMIDs to ValidationResults
        """
        results = {}
        for pmid in pmids:
            results[pmid] = await self.validate(pmid)

        logger.info(
            "PubMed batch validation completed",
            total=len(pmids),
            valid=sum(1 for r in results.values() if r.is_valid),
        )

        return results

    async def close(self) -> None:
        """Close HTTP client"""
        await self.client.aclose()
