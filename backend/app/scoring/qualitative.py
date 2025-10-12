"""
Qualitative assessment engine for institution-specific curation methodologies.
Provides qualitative scoring based on clinical and literature assessments.
"""

from datetime import datetime
from typing import Any

from .base import ScoringEngine, ScoringResult


class QualitativeEngine(ScoringEngine):
    """Qualitative assessment engine for institutional use."""

    @property
    def name(self) -> str:
        return "qualitative_assessment"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_supported_verdicts(self) -> list[str]:
        return [
            "Strong Association",
            "Moderate Association",
            "Weak Association",
            "Insufficient Evidence",
        ]

    def get_scoring_categories(self) -> list[str]:
        return ["clinical_assessment", "literature_review"]

    def calculate_scores(
        self,
        evidence_data: dict[str, Any],
        schema_config: dict[str, Any],
        scope_context: dict[str, Any] | None = None,
    ) -> ScoringResult:
        """Calculate qualitative assessment."""

        clinical_assessment = evidence_data.get("clinical_assessment", {})
        literature_review = evidence_data.get("literature_review", {})

        # Qualitative scoring based on categorical assessments
        clinical_score = self._assess_clinical_evidence(clinical_assessment)
        literature_score = self._assess_literature_evidence(literature_review)

        # Combine assessments
        overall_assessment = self._combine_assessments(clinical_score, literature_score)

        # Create detailed breakdown
        breakdown = self._create_assessment_breakdown(
            clinical_assessment, literature_review, clinical_score, literature_score
        )

        return ScoringResult(
            scores={
                "clinical_assessment_score": clinical_score,
                "literature_review_score": literature_score,
                "overall_score": overall_assessment["score"],
            },
            total_score=overall_assessment["score"],
            verdict=overall_assessment["verdict"],
            verdict_rationale=overall_assessment["rationale"],
            evidence_breakdown=breakdown,
            warnings=self._check_qualitative_warnings(evidence_data),
            metadata={
                "assessment_type": "qualitative",
                "engine_version": self.version,
                "calculated_at": datetime.utcnow().isoformat(),
                "scope_context": scope_context or {},
            },
        )

    def _assess_clinical_evidence(self, clinical_assessment: dict[str, Any]) -> float:
        """Assess clinical evidence quality."""

        phenotype_match = clinical_assessment.get("phenotype_match", "")
        inheritance_consistency = clinical_assessment.get("inheritance_consistency", "")

        score = 0.0

        # Phenotype match scoring
        if phenotype_match.lower() == "excellent":
            score += 3.0
        elif phenotype_match.lower() == "good":
            score += 2.0
        elif phenotype_match.lower() == "fair":
            score += 1.0
        elif phenotype_match.lower() == "poor":
            score += 0.0

        # Inheritance consistency scoring
        if inheritance_consistency.lower() == "consistent":
            score += 2.0
        elif inheritance_consistency.lower() == "partially_consistent":
            score += 1.0
        elif inheritance_consistency.lower() == "inconsistent":
            score += 0.0

        return score

    def _assess_literature_evidence(self, literature_review: dict[str, Any]) -> float:
        """Assess literature evidence quality."""

        evidence_quality = literature_review.get("evidence_quality", "")
        study_design = literature_review.get("study_design_strength", "")

        score = 0.0

        # Evidence quality scoring
        if evidence_quality.lower() == "high":
            score += 3.0
        elif evidence_quality.lower() == "moderate":
            score += 2.0
        elif evidence_quality.lower() == "low":
            score += 1.0

        # Study design scoring
        if study_design.lower() == "strong":
            score += 2.0
        elif study_design.lower() == "adequate":
            score += 1.0
        elif study_design.lower() == "weak":
            score += 0.0

        return score

    def _combine_assessments(
        self, clinical_score: float, literature_score: float
    ) -> dict[str, Any]:
        """Combine clinical and literature assessments."""

        total_score = clinical_score + literature_score

        # Determine verdict based on combined score
        if total_score >= 8:
            verdict = "Strong Association"
            rationale = "Excellent clinical and literature evidence support strong gene-disease association."
        elif total_score >= 5:
            verdict = "Moderate Association"
            rationale = "Good clinical and/or literature evidence support moderate gene-disease association."
        elif total_score >= 2:
            verdict = "Weak Association"
            rationale = "Limited evidence suggests possible gene-disease association."
        else:
            verdict = "Insufficient Evidence"
            rationale = "Insufficient evidence to support gene-disease association."

        # Add score-specific details to rationale
        rationale += f" Clinical assessment score: {clinical_score:.1f}/5. Literature review score: {literature_score:.1f}/5."

        return {"score": total_score, "verdict": verdict, "rationale": rationale}

    def _create_assessment_breakdown(
        self,
        clinical_assessment: dict[str, Any],
        literature_review: dict[str, Any],
        clinical_score: float,
        literature_score: float,
    ) -> dict[str, Any]:
        """Create detailed assessment breakdown."""

        return {
            "clinical_assessment": {
                "score": clinical_score,
                "max_score": 5.0,
                "phenotype_match": clinical_assessment.get(
                    "phenotype_match", "Not assessed"
                ),
                "inheritance_consistency": clinical_assessment.get(
                    "inheritance_consistency", "Not assessed"
                ),
                "components": {
                    "phenotype_match_score": self._get_phenotype_score(
                        clinical_assessment.get("phenotype_match", "")
                    ),
                    "inheritance_score": self._get_inheritance_score(
                        clinical_assessment.get("inheritance_consistency", "")
                    ),
                },
            },
            "literature_review": {
                "score": literature_score,
                "max_score": 5.0,
                "evidence_quality": literature_review.get(
                    "evidence_quality", "Not assessed"
                ),
                "study_design_strength": literature_review.get(
                    "study_design_strength", "Not assessed"
                ),
                "components": {
                    "evidence_quality_score": self._get_evidence_quality_score(
                        literature_review.get("evidence_quality", "")
                    ),
                    "study_design_score": self._get_study_design_score(
                        literature_review.get("study_design_strength", "")
                    ),
                },
            },
            "total_assessment": {
                "combined_score": clinical_score + literature_score,
                "max_possible_score": 10.0,
                "score_percentage": ((clinical_score + literature_score) / 10.0) * 100,
            },
        }

    def _get_phenotype_score(self, phenotype_match: str) -> float:
        """Get phenotype match score."""
        match = phenotype_match.lower()
        phenotype_scores = {"excellent": 3.0, "good": 2.0, "fair": 1.0}
        return phenotype_scores.get(match, 0.0)

    def _get_inheritance_score(self, inheritance_consistency: str) -> float:
        """Get inheritance consistency score."""
        consistency = inheritance_consistency.lower()
        if consistency == "consistent":
            return 2.0
        elif consistency == "partially_consistent":
            return 1.0
        else:
            return 0.0

    def _get_evidence_quality_score(self, evidence_quality: str) -> float:
        """Get evidence quality score."""
        quality = evidence_quality.lower()
        quality_scores = {"high": 3.0, "moderate": 2.0, "low": 1.0}
        return quality_scores.get(quality, 0.0)

    def _get_study_design_score(self, study_design: str) -> float:
        """Get study design strength score."""
        design = study_design.lower()
        if design == "strong":
            return 2.0
        elif design == "adequate":
            return 1.0
        else:
            return 0.0

    def _check_qualitative_warnings(self, evidence_data: dict[str, Any]) -> list[str]:  # noqa: C901
        """Check for potential issues in qualitative assessment."""

        warnings = []

        clinical_assessment = evidence_data.get("clinical_assessment", {})
        literature_review = evidence_data.get("literature_review", {})

        # Check for missing assessments
        if not clinical_assessment:
            warnings.append("No clinical assessment provided")
        if not literature_review:
            warnings.append("No literature review provided")

        # Check for incomplete clinical assessment
        if clinical_assessment:
            if not clinical_assessment.get("phenotype_match"):
                warnings.append("Phenotype match assessment missing")
            if not clinical_assessment.get("inheritance_consistency"):
                warnings.append("Inheritance consistency assessment missing")

        # Check for incomplete literature review
        if literature_review:
            if not literature_review.get("evidence_quality"):
                warnings.append("Evidence quality assessment missing")
            if not literature_review.get("study_design_strength"):
                warnings.append("Study design strength assessment missing")

        # Check for low confidence assessments
        if clinical_assessment.get("phenotype_match", "").lower() == "poor":
            warnings.append(
                "Poor phenotype match may indicate weak gene-disease association"
            )

        if (
            clinical_assessment.get("inheritance_consistency", "").lower()
            == "inconsistent"
        ):
            warnings.append(
                "Inconsistent inheritance pattern raises questions about association"
            )

        if literature_review.get("evidence_quality", "").lower() == "low":
            warnings.append("Low evidence quality limits confidence in assessment")

        return warnings

    def validate_evidence(
        self, evidence_data: dict[str, Any], schema_config: dict[str, Any]
    ) -> list[str]:
        """Validate evidence data for qualitative assessment."""

        errors = []

        clinical_assessment = evidence_data.get("clinical_assessment", {})
        literature_review = evidence_data.get("literature_review", {})

        # Validate clinical assessment
        if clinical_assessment:
            phenotype_match = clinical_assessment.get("phenotype_match", "")
            valid_phenotype_options = ["excellent", "good", "fair", "poor"]
            if (
                phenotype_match
                and phenotype_match.lower() not in valid_phenotype_options
            ):
                errors.append(f"Invalid phenotype match value: {phenotype_match}")

            inheritance_consistency = clinical_assessment.get(
                "inheritance_consistency", ""
            )
            valid_inheritance_options = [
                "consistent",
                "partially_consistent",
                "inconsistent",
            ]
            if (
                inheritance_consistency
                and inheritance_consistency.lower() not in valid_inheritance_options
            ):
                errors.append(
                    f"Invalid inheritance consistency value: {inheritance_consistency}"
                )

        # Validate literature review
        if literature_review:
            evidence_quality = literature_review.get("evidence_quality", "")
            valid_quality_options = ["high", "moderate", "low"]
            if (
                evidence_quality
                and evidence_quality.lower() not in valid_quality_options
            ):
                errors.append(f"Invalid evidence quality value: {evidence_quality}")

            study_design = literature_review.get("study_design_strength", "")
            valid_design_options = ["strong", "adequate", "weak"]
            if study_design and study_design.lower() not in valid_design_options:
                errors.append(f"Invalid study design strength value: {study_design}")

        # Validate that at least one assessment is provided
        if not clinical_assessment and not literature_review:
            errors.append(
                "At least one assessment category (clinical or literature) is required"
            )

        return errors

    def supports_schema(self, schema_name: str, schema_version: str) -> bool:
        """Check if engine supports a specific schema version."""
        return schema_name.startswith("Qualitative") and schema_version.startswith("1.")
