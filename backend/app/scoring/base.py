"""
Base interface for pluggable scoring engines.
Provides the foundation for schema-agnostic scoring methodologies.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ScoringResult(BaseModel):
    """Result of scoring calculation."""

    scores: dict[str, float]  # e.g., {"genetic_score": 8.5, "experimental_score": 3.0}
    total_score: float  # Combined total score
    verdict: str  # Final classification
    verdict_rationale: str  # Explanation of verdict determination
    evidence_breakdown: dict[str, Any]  # Detailed scoring breakdown
    warnings: list[str] = []  # Any scoring warnings or issues
    metadata: dict[str, Any] = {}  # Additional scoring metadata


class ScoringEngine(ABC):
    """Base class for all scoring engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine identifier (matches schema configuration)."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Engine version for compatibility tracking."""
        pass

    @abstractmethod
    def calculate_scores(
        self,
        evidence_data: dict[str, Any],
        schema_config: dict[str, Any],
        scope_context: dict[str, Any] | None = None,
    ) -> ScoringResult:
        """Calculate scores and verdict from evidence data."""
        pass

    @abstractmethod
    def validate_evidence(
        self, evidence_data: dict[str, Any], schema_config: dict[str, Any]
    ) -> list[str]:
        """Validate evidence data. Returns list of validation errors."""
        pass

    def supports_schema(self, schema_name: str, schema_version: str) -> bool:
        """Check if engine supports a specific schema version."""
        return True  # Override for version-specific support

    def get_supported_verdicts(self) -> list[str]:
        """Get list of verdicts this engine can produce."""
        return []  # Override in implementations

    def get_scoring_categories(self) -> list[str]:
        """Get list of evidence categories this engine scores."""
        return []  # Override in implementations
