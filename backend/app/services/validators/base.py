"""Base class for external validators"""

from abc import ABC, abstractmethod

from app.schemas.validation import ValidationResult


class ExternalValidator(ABC):
    """Abstract base class for external validators"""

    @abstractmethod
    async def validate(self, input_value: str) -> ValidationResult:
        """Validate input value against external API

        Args:
            input_value: Value to validate (gene symbol, PMID, HPO term, etc.)

        Returns:
            ValidationResult with status and data
        """
        pass

    @abstractmethod
    async def batch_validate(self, values: list[str]) -> dict[str, ValidationResult]:
        """Validate multiple values in batch

        Args:
            values: List of values to validate

        Returns:
            Dictionary mapping input values to ValidationResults
        """
        pass
