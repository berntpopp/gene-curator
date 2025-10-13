"""
GenCC-based gene-disease validity classification scoring engine.
Implements GenCC framework for gene-disease association scoring.
"""

from datetime import datetime
from typing import Any

from .base import ScoringEngine, ScoringResult


class GenCCEngine(ScoringEngine):
    """GenCC-based gene-disease validity classification scoring engine."""

    @property
    def name(self) -> str:
        return "gencc_based"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_supported_verdicts(self) -> list[str]:
        return [
            "Definitive",
            "Strong",
            "Moderate",
            "Limited",
            "No Known Disease Relationship",
            "Disputed",
        ]

    def get_scoring_categories(self) -> list[str]:
        return ["genetic_evidence", "experimental_evidence", "contradictory_evidence"]

    def calculate_scores(
        self,
        evidence_data: dict[str, Any],
        schema_config: dict[str, Any],
        scope_context: dict[str, Any] | None = None,
    ) -> ScoringResult:
        """Calculate GenCC-based classification."""

        genetic_evidence = evidence_data.get("genetic_evidence", {})
        experimental_evidence = evidence_data.get("experimental_evidence", {})
        contradictory_evidence = evidence_data.get("contradictory_evidence", [])

        # Calculate evidence scores using GenCC-adapted methodology
        genetic_score = self._calculate_genetic_score(genetic_evidence)
        experimental_score = self._calculate_experimental_score(experimental_evidence)

        # Total score
        total_score = genetic_score + experimental_score

        # Determine classification
        classification = self._determine_gencc_classification(
            total_score, contradictory_evidence
        )

        # Generate rationale
        rationale = self._generate_gencc_rationale(
            genetic_score, experimental_score, total_score, classification
        )

        # Create breakdown
        breakdown = self._create_gencc_breakdown(
            genetic_evidence, experimental_evidence, genetic_score, experimental_score
        )

        return ScoringResult(
            scores={
                "genetic_evidence_score": genetic_score,
                "experimental_evidence_score": experimental_score,
                "total_score": total_score,
            },
            total_score=total_score,
            verdict=classification,
            verdict_rationale=rationale,
            evidence_breakdown=breakdown,
            warnings=self._check_gencc_warnings(evidence_data),
            metadata={
                "guidelines": "GenCC_Based",
                "engine_version": self.version,
                "calculated_at": datetime.utcnow().isoformat(),
                "scope_context": scope_context or {},
            },
        )

    def _calculate_genetic_score(self, genetic_evidence: dict[str, Any]) -> float:
        """Calculate genetic evidence score using GenCC-adapted methodology."""

        # Similar to ClinGen but adapted for GenCC framework
        case_level_data = genetic_evidence.get("case_level_data", [])
        segregation_data = genetic_evidence.get("segregation_data", [])
        case_control_data = genetic_evidence.get("case_control_data", [])

        # Calculate scores with GenCC-specific maximums
        case_level_score = min(
            sum(float(item.get("points", 0)) for item in case_level_data), 12.0
        )
        segregation_score = min(
            sum(float(item.get("points", 0)) for item in segregation_data), 3.0
        )
        case_control_score = min(
            sum(float(item.get("points", 0)) for item in case_control_data), 6.0
        )

        return min(case_level_score + segregation_score + case_control_score, 12.0)

    def _calculate_experimental_score(
        self, experimental_evidence: dict[str, Any]
    ) -> float:
        """Calculate experimental evidence score using GenCC-adapted methodology."""

        function_evidence = experimental_evidence.get("function", [])
        model_evidence = experimental_evidence.get("models", [])
        rescue_evidence = experimental_evidence.get("rescue", [])

        function_score = min(
            sum(float(item.get("points", 0)) for item in function_evidence), 2.0
        )
        model_score = min(
            sum(float(item.get("points", 0)) for item in model_evidence), 4.0
        )
        rescue_score = min(
            sum(float(item.get("points", 0)) for item in rescue_evidence), 2.0
        )

        return min(function_score + model_score + rescue_score, 6.0)

    def _determine_gencc_classification(
        self, total_score: float, contradictory_evidence: list[dict]
    ) -> str:
        """Determine GenCC classification based on total score."""

        has_contradictory = len(contradictory_evidence) > 0

        if has_contradictory:
            return "Disputed"
        elif total_score >= 12:
            return "Definitive"
        elif total_score >= 7:
            return "Strong"
        elif total_score >= 4:
            return "Moderate"
        elif total_score >= 1:
            return "Limited"
        else:
            return "No Known Disease Relationship"

    def _generate_gencc_rationale(
        self,
        genetic_score: float,
        experimental_score: float,
        total_score: float,
        classification: str,
    ) -> str:
        """Generate GenCC classification rationale."""

        rationale = "GenCC-based classification: "
        rationale += f"genetic evidence = {genetic_score:.1f}, "
        rationale += f"experimental evidence = {experimental_score:.1f}, "
        rationale += f"total score = {total_score:.1f}. "

        if classification == "Definitive":
            rationale += "Total score ≥12 supports Definitive gene-disease validity."
        elif classification == "Strong":
            rationale += "Total score 7-11 supports Strong gene-disease validity."
        elif classification == "Moderate":
            rationale += "Total score 4-6 supports Moderate gene-disease validity."
        elif classification == "Limited":
            rationale += "Total score 1-3 supports Limited gene-disease validity."
        elif classification == "Disputed":
            rationale += (
                "Contradictory evidence present, resulting in Disputed classification."
            )
        else:
            rationale += "No evidence supporting gene-disease relationship."

        return rationale

    def _create_gencc_breakdown(
        self,
        genetic_evidence: dict,
        experimental_evidence: dict,
        genetic_score: float,
        experimental_score: float,
    ) -> dict[str, Any]:
        """Create detailed GenCC evidence breakdown."""

        return {
            "genetic_evidence": {
                "total_score": genetic_score,
                "case_level_items": len(genetic_evidence.get("case_level_data", [])),
                "segregation_items": len(genetic_evidence.get("segregation_data", [])),
                "case_control_items": len(
                    genetic_evidence.get("case_control_data", [])
                ),
            },
            "experimental_evidence": {
                "total_score": experimental_score,
                "function_items": len(experimental_evidence.get("function", [])),
                "model_items": len(experimental_evidence.get("models", [])),
                "rescue_items": len(experimental_evidence.get("rescue", [])),
            },
            "classification_methodology": "GenCC-based gene-disease validity framework",
        }

    def _check_gencc_warnings(self, evidence_data: dict[str, Any]) -> list[str]:
        """Check for potential issues in GenCC classification."""

        warnings = []

        genetic_evidence = evidence_data.get("genetic_evidence", {})
        experimental_evidence = evidence_data.get("experimental_evidence", {})

        # Check evidence categories
        if not genetic_evidence and not experimental_evidence:
            warnings.append("No evidence provided for classification")

        # Check case-level data sufficiency
        case_level_count = len(genetic_evidence.get("case_level_data", []))
        if case_level_count == 0:
            warnings.append("No case-level data provided")
        elif case_level_count == 1:
            warnings.append("Only one case-level evidence item (consider adding more)")

        # Check for experimental support
        exp_categories = ["function", "models", "rescue"]
        has_experimental = any(experimental_evidence.get(cat) for cat in exp_categories)
        if not has_experimental:
            warnings.append("No experimental evidence provided to support mechanism")

        return warnings

    def validate_evidence(
        self, evidence_data: dict[str, Any], schema_config: dict[str, Any]
    ) -> list[str]:
        """Validate evidence data for GenCC compliance."""

        errors = []

        # Basic validation similar to ClinGen but adapted for GenCC
        genetic_evidence = evidence_data.get("genetic_evidence", {})
        case_level_data = genetic_evidence.get("case_level_data", [])

        for i, case in enumerate(case_level_data):
            # Validate PMID
            pmid = case.get("pmid", "")
            if not pmid or not pmid.isdigit() or len(pmid) < 7:
                errors.append(f"Case-level item {i + 1}: Invalid PMID format")

            # Validate points (GenCC uses similar point system)
            points = case.get("points", 0)
            if not isinstance(points, int | float) or points < 0 or points > 2:
                errors.append(f"Case-level item {i + 1}: Points must be 0-2")

        # Validate required evidence for classification
        if not genetic_evidence and not evidence_data.get("experimental_evidence"):
            errors.append(
                "At least one evidence category required for GenCC classification"
            )

        return errors

    def supports_schema(self, schema_name: str, schema_version: str) -> bool:
        """Check if engine supports a specific schema version."""
        return schema_name.startswith("GenCC") and schema_version.startswith("1.")
