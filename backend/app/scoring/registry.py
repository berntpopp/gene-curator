"""
Scoring engine registry for managing pluggable scoring methodologies.
Provides centralized registration and selection of scoring engines.
"""

from .base import ScoringEngine, ScoringResult
from .clingen import ClinGenEngine
from .gencc import GenCCEngine
from .qualitative import QualitativeEngine


class ScoringEngineRegistry:
    """Registry for scoring engines."""

    def __init__(self):
        self._engines: dict[str, ScoringEngine] = {}
        self._register_default_engines()

    def _register_default_engines(self):
        """Register built-in scoring engines."""
        self.register(ClinGenEngine())
        self.register(GenCCEngine())
        self.register(QualitativeEngine())

    def register(self, engine: ScoringEngine):
        """Register a scoring engine."""
        self._engines[engine.name] = engine

    def get_engine(self, name: str) -> ScoringEngine | None:
        """Get a scoring engine by name."""
        return self._engines.get(name)

    def list_engines(self) -> list[dict[str, str]]:
        """List all registered engines with their metadata."""
        return [
            {
                "name": engine.name,
                "version": engine.version,
                "supported_verdicts": engine.get_supported_verdicts(),
                "scoring_categories": engine.get_scoring_categories(),
            }
            for engine in self._engines.values()
        ]

    def get_engine_names(self) -> list[str]:
        """Get list of all registered engine names."""
        return list(self._engines.keys())

    def supports_schema(
        self, engine_name: str, schema_name: str, schema_version: str
    ) -> bool:
        """Check if an engine supports a specific schema."""
        engine = self.get_engine(engine_name)
        return engine.supports_schema(schema_name, schema_version) if engine else False

    def calculate_scores(
        self,
        engine_name: str,
        evidence_data: dict,
        schema_config: dict,
        scope_context: dict | None = None,
    ) -> ScoringResult | None:
        """Calculate scores using the specified engine."""
        engine = self.get_engine(engine_name)
        if not engine:
            return None

        return engine.calculate_scores(evidence_data, schema_config, scope_context)

    def validate_evidence(
        self, engine_name: str, evidence_data: dict, schema_config: dict
    ) -> list[str]:
        """Validate evidence using the specified engine."""
        engine = self.get_engine(engine_name)
        if not engine:
            return [f"Unknown scoring engine: {engine_name}"]

        return engine.validate_evidence(evidence_data, schema_config)

    def get_supported_verdicts(self, engine_name: str) -> list[str]:
        """Get supported verdicts for a specific engine."""
        engine = self.get_engine(engine_name)
        return engine.get_supported_verdicts() if engine else []

    def get_scoring_categories(self, engine_name: str) -> list[str]:
        """Get scoring categories for a specific engine."""
        engine = self.get_engine(engine_name)
        return engine.get_scoring_categories() if engine else []

    def find_engines_for_schema(
        self, schema_name: str, schema_version: str
    ) -> list[str]:
        """Find all engines that support a specific schema."""
        compatible_engines = []
        for engine_name, engine in self._engines.items():
            if engine.supports_schema(schema_name, schema_version):
                compatible_engines.append(engine_name)
        return compatible_engines

    def get_engine_info(self, engine_name: str) -> dict[str, any] | None:
        """Get detailed information about a specific engine."""
        engine = self.get_engine(engine_name)
        if not engine:
            return None

        return {
            "name": engine.name,
            "version": engine.version,
            "supported_verdicts": engine.get_supported_verdicts(),
            "scoring_categories": engine.get_scoring_categories(),
            "description": (
                f"{engine.__class__.__name__} - {engine.__doc__}"
                if engine.__doc__
                else engine.__class__.__name__
            ),
        }


# Global registry instance
scoring_registry = ScoringEngineRegistry()
