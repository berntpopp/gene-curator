"""
ClinGen Standard Operating Procedure v11 scoring engine.
Implements evidence scoring per ClinGen SOP v11 requirements.
"""

from datetime import datetime
from typing import Any

from .base import ScoringEngine, ScoringResult


class ClinGenEngine(ScoringEngine):
    """ClinGen Standard Operating Procedure v11 scoring engine."""

    @property
    def name(self) -> str:
        return "clingen_sop_v11"

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
            "Refuted",
        ]

    def get_scoring_categories(self) -> list[str]:
        return ["genetic_evidence", "experimental_evidence", "contradictory_evidence"]

    def calculate_scores(
        self,
        evidence_data: dict[str, Any],
        schema_config: dict[str, Any],
        scope_context: dict[str, Any] | None = None,
    ) -> ScoringResult:
        """Calculate ClinGen SOP v11 scores."""

        # Extract evidence categories
        genetic_evidence = evidence_data.get("genetic_evidence", {})
        experimental_evidence = evidence_data.get("experimental_evidence", {})
        contradictory_evidence = evidence_data.get("contradictory_evidence", [])

        # Calculate genetic evidence score
        genetic_score = self._calculate_genetic_score(genetic_evidence)

        # Calculate experimental evidence score
        experimental_score = self._calculate_experimental_score(experimental_evidence)

        # Total score (max 18 per SOP v11)
        total_score = min(genetic_score + experimental_score, 18.0)

        # Determine verdict
        verdict = self._determine_verdict(total_score, contradictory_evidence)

        # Generate rationale
        rationale = self._generate_rationale(
            genetic_score, experimental_score, total_score, verdict
        )

        # Create detailed breakdown
        breakdown = self._create_breakdown(
            genetic_evidence, experimental_evidence, genetic_score, experimental_score
        )

        # Check for warnings
        warnings = self._check_warnings(evidence_data)

        return ScoringResult(
            scores={
                "genetic_evidence_score": genetic_score,
                "experimental_evidence_score": experimental_score,
                "total_score": total_score,
            },
            total_score=total_score,
            verdict=verdict,
            verdict_rationale=rationale,
            evidence_breakdown=breakdown,
            warnings=warnings,
            metadata={
                "sop_version": "v11",
                "engine_version": self.version,
                "calculated_at": datetime.utcnow().isoformat(),
                "scope_context": scope_context or {},
            },
        )

    def _calculate_genetic_score(self, genetic_evidence: dict[str, Any]) -> float:
        """Calculate genetic evidence score per SOP v11."""

        # Case-level data (max 12 points)
        case_level_data = genetic_evidence.get("case_level_data", [])
        case_level_score = 0.0

        for case in case_level_data:
            points = float(case.get("points", 0))
            case_level_score += points

        case_level_score = min(case_level_score, 12.0)

        # Segregation data (max 3 points)
        segregation_data = genetic_evidence.get("segregation_data", [])
        segregation_score = 0.0

        for seg in segregation_data:
            points = float(seg.get("points", 0))
            segregation_score += points

        segregation_score = min(segregation_score, 3.0)

        # Case-control data (max 6 points)
        case_control_data = genetic_evidence.get("case_control_data", [])
        case_control_score = 0.0

        for cc in case_control_data:
            points = float(cc.get("points", 0))
            case_control_score += points

        case_control_score = min(case_control_score, 6.0)

        # Total genetic score (overall max 12 per SOP v11)
        total_genetic = case_level_score + segregation_score + case_control_score
        return min(total_genetic, 12.0)

    def _calculate_experimental_score(
        self, experimental_evidence: dict[str, Any]
    ) -> float:
        """Calculate experimental evidence score per SOP v11."""

        # Function evidence (max 2 points)
        function_evidence = experimental_evidence.get("function", [])
        function_score = sum(float(item.get("points", 0)) for item in function_evidence)
        function_score = min(function_score, 2.0)

        # Model systems evidence (max 4 points)
        model_evidence = experimental_evidence.get("models", [])
        model_score = sum(float(item.get("points", 0)) for item in model_evidence)
        model_score = min(model_score, 4.0)

        # Rescue evidence (max 2 points)
        rescue_evidence = experimental_evidence.get("rescue", [])
        rescue_score = sum(float(item.get("points", 0)) for item in rescue_evidence)
        rescue_score = min(rescue_score, 2.0)

        # Total experimental score (overall max 6 per SOP v11)
        total_experimental = function_score + model_score + rescue_score
        return min(total_experimental, 6.0)

    def _determine_verdict(
        self, total_score: float, contradictory_evidence: list[dict]
    ) -> str:
        """Determine ClinGen verdict based on total score and contradictory evidence."""

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

    def _generate_rationale(
        self,
        genetic_score: float,
        experimental_score: float,
        total_score: float,
        verdict: str,
    ) -> str:
        """Generate human-readable rationale for verdict."""

        rationale = "Based on ClinGen SOP v11 scoring: "
        rationale += f"genetic evidence score = {genetic_score:.1f}, "
        rationale += f"experimental evidence score = {experimental_score:.1f}, "
        rationale += f"total score = {total_score:.1f}. "

        if verdict == "Definitive":
            rationale += "Total score ≥12 with no contradictory evidence supports Definitive classification."
        elif verdict == "Strong":
            rationale += "Total score 7-11 with no contradictory evidence supports Strong classification."
        elif verdict == "Moderate":
            rationale += "Total score 4-6 supports Moderate classification."
        elif verdict == "Limited":
            rationale += "Total score 1-3 supports Limited classification."
        elif verdict == "Disputed":
            rationale += (
                "Contradictory evidence present, resulting in Disputed classification."
            )
        else:
            rationale += "No evidence supporting gene-disease relationship."

        return rationale

    def _create_breakdown(
        self,
        genetic_evidence: dict,
        experimental_evidence: dict,
        genetic_score: float,
        experimental_score: float,
    ) -> dict[str, Any]:
        """Create detailed scoring breakdown."""

        return {
            "genetic_evidence": {
                "total_score": genetic_score,
                "case_level_items": len(genetic_evidence.get("case_level_data", [])),
                "segregation_items": len(genetic_evidence.get("segregation_data", [])),
                "case_control_items": len(
                    genetic_evidence.get("case_control_data", [])
                ),
                "case_level_score": min(
                    sum(
                        float(item.get("points", 0))
                        for item in genetic_evidence.get("case_level_data", [])
                    ),
                    12.0,
                ),
                "segregation_score": min(
                    sum(
                        float(item.get("points", 0))
                        for item in genetic_evidence.get("segregation_data", [])
                    ),
                    3.0,
                ),
                "case_control_score": min(
                    sum(
                        float(item.get("points", 0))
                        for item in genetic_evidence.get("case_control_data", [])
                    ),
                    6.0,
                ),
            },
            "experimental_evidence": {
                "total_score": experimental_score,
                "function_items": len(experimental_evidence.get("function", [])),
                "model_items": len(experimental_evidence.get("models", [])),
                "rescue_items": len(experimental_evidence.get("rescue", [])),
                "function_score": min(
                    sum(
                        float(item.get("points", 0))
                        for item in experimental_evidence.get("function", [])
                    ),
                    2.0,
                ),
                "model_score": min(
                    sum(
                        float(item.get("points", 0))
                        for item in experimental_evidence.get("models", [])
                    ),
                    4.0,
                ),
                "rescue_score": min(
                    sum(
                        float(item.get("points", 0))
                        for item in experimental_evidence.get("rescue", [])
                    ),
                    2.0,
                ),
            },
        }

    def _check_warnings(self, evidence_data: dict[str, Any]) -> list[str]:
        """Check for potential issues or warnings."""

        warnings = []

        # Check for missing evidence categories
        genetic_evidence = evidence_data.get("genetic_evidence", {})
        experimental_evidence = evidence_data.get("experimental_evidence", {})

        if not genetic_evidence:
            warnings.append("No genetic evidence provided")
        if not experimental_evidence:
            warnings.append("No experimental evidence provided")

        # Check for low evidence counts
        case_level_count = len(genetic_evidence.get("case_level_data", []))
        if case_level_count < 2:
            warnings.append(
                f"Only {case_level_count} case-level evidence items (consider adding more)"
            )

        # Check for missing PMIDs
        all_evidence_items = []
        all_evidence_items.extend(genetic_evidence.get("case_level_data", []))
        all_evidence_items.extend(genetic_evidence.get("segregation_data", []))
        all_evidence_items.extend(genetic_evidence.get("case_control_data", []))
        all_evidence_items.extend(experimental_evidence.get("function", []))
        all_evidence_items.extend(experimental_evidence.get("models", []))
        all_evidence_items.extend(experimental_evidence.get("rescue", []))

        for item in all_evidence_items:
            pmid = item.get("pmid", "")
            if not pmid or not pmid.isdigit() or len(pmid) < 7:
                warnings.append("Invalid or missing PMID in evidence item")
                break

        return warnings

    def validate_evidence(  # noqa: C901
        self, evidence_data: dict[str, Any], schema_config: dict[str, Any]
    ) -> list[str]:
        """Validate evidence data for ClinGen compliance."""

        errors = []

        # Validate genetic evidence
        genetic_evidence = evidence_data.get("genetic_evidence", {})
        case_level_data = genetic_evidence.get("case_level_data", [])

        for i, case in enumerate(case_level_data):
            # Validate PMID
            pmid = case.get("pmid", "")
            if not pmid or not pmid.isdigit() or len(pmid) < 7:
                errors.append(f"Case-level item {i + 1}: Invalid PMID format")

            # Validate points
            points = case.get("points", 0)
            if not isinstance(points, int | float) or points < 0 or points > 2:
                errors.append(f"Case-level item {i + 1}: Points must be 0-2")

            # Validate required fields
            if not case.get("proband_label"):
                errors.append(f"Case-level item {i + 1}: Proband label required")

        # Validate segregation data
        segregation_data = genetic_evidence.get("segregation_data", [])
        for i, seg in enumerate(segregation_data):
            pmid = seg.get("pmid", "")
            if not pmid or not pmid.isdigit() or len(pmid) < 7:
                errors.append(f"Segregation item {i + 1}: Invalid PMID format")

            points = seg.get("points", 0)
            if not isinstance(points, int | float) or points < 0 or points > 3:
                errors.append(f"Segregation item {i + 1}: Points must be 0-3")

        # Validate experimental evidence
        experimental_evidence = evidence_data.get("experimental_evidence", {})

        function_data = experimental_evidence.get("function", [])
        for i, func in enumerate(function_data):
            pmid = func.get("pmid", "")
            if not pmid or not pmid.isdigit() or len(pmid) < 7:
                errors.append(f"Function evidence item {i + 1}: Invalid PMID format")

            points = func.get("points", 0)
            if not isinstance(points, int | float) or points < 0 or points > 2:
                errors.append(f"Function evidence item {i + 1}: Points must be 0-2")

        return errors

    def supports_schema(self, schema_name: str, schema_version: str) -> bool:
        """Check if engine supports a specific schema version."""
        return schema_name.startswith("ClinGen_SOP") and schema_version.startswith("1.")
