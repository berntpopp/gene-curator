"""
Qualitative Assessment Warning Checker.

Following SOLID principles:
- Single Responsibility: Each method checks ONE specific concern
- Open/Closed: Easy to add new checkers without modifying existing code
- Liskov Substitution: Checker methods are substitutable
- Interface Segregation: Focused, single-purpose interface
- Dependency Inversion: Depends on dict abstraction, not concrete types

This module extracts the complex _check_qualitative_warnings logic into
a maintainable, testable, and extensible checker class.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class AssessmentWarning:
    """
    Represents a warning from qualitative assessment.

    Provides structure and context for warnings, making them easier
    to log, filter, and test.
    """

    severity: str  # "error", "warning", "info"
    category: str  # "missing", "incomplete", "low_confidence"
    message: str
    field: str  # JSON path to the field (e.g., "clinical_assessment.phenotype_match")


class QualitativeWarningChecker:
    """
    Checks qualitative assessment data for potential issues.

    Follows Single Responsibility Principle - each method checks ONE thing.
    Each method has low cyclomatic complexity (≤4) for maintainability.
    """

    def check_all(self, evidence_data: dict[str, Any]) -> list[AssessmentWarning]:
        """
        Run all warning checks on evidence data.

        Complexity: 2 (simple iteration)

        Args:
            evidence_data: The evidence data to check

        Returns:
            List of AssessmentWarning objects
        """
        warnings = []

        # Strategy pattern - each checker is independent
        # Easy to add/remove checkers without modifying this method (OCP)
        checkers = [
            self._check_missing_assessments,
            self._check_incomplete_clinical,
            self._check_incomplete_literature,
            self._check_low_confidence_indicators,
        ]

        for checker in checkers:
            warnings.extend(checker(evidence_data))

        return warnings

    def _check_missing_assessments(
        self, evidence_data: dict[str, Any]
    ) -> list[AssessmentWarning]:
        """
        Check for missing top-level assessments.

        Complexity: 3 (two simple if statements)

        Args:
            evidence_data: The evidence data to check

        Returns:
            List of warnings for missing assessments
        """
        warnings = []
        clinical = evidence_data.get("clinical_assessment", {})
        literature = evidence_data.get("literature_review", {})

        if not clinical:
            warnings.append(
                AssessmentWarning(
                    severity="error",
                    category="missing",
                    message="No clinical assessment provided",
                    field="clinical_assessment",
                )
            )

        if not literature:
            warnings.append(
                AssessmentWarning(
                    severity="error",
                    category="missing",
                    message="No literature review provided",
                    field="literature_review",
                )
            )

        return warnings

    def _check_incomplete_clinical(
        self, evidence_data: dict[str, Any]
    ) -> list[AssessmentWarning]:
        """
        Check for incomplete clinical assessment fields.

        Complexity: 3 (guard clause + lookup table iteration)

        Args:
            evidence_data: The evidence data to check

        Returns:
            List of warnings for incomplete clinical fields
        """
        warnings = []
        clinical = evidence_data.get("clinical_assessment")

        # If clinical_assessment key doesn't exist at all, skip (caught by missing check)
        # But if it exists as empty dict, we should check for required fields
        if clinical is None:
            return warnings  # Already caught by missing check

        # Lookup table approach (KISS principle)
        # Easy to add/remove required fields
        required_fields = {
            "phenotype_match": "Phenotype match assessment missing",
            "inheritance_consistency": "Inheritance consistency assessment missing",
        }

        for field, message in required_fields.items():
            # Check if field is missing, None, or empty string
            field_value = clinical.get(field)
            if not field_value or (
                isinstance(field_value, str) and not field_value.strip()
            ):
                warnings.append(
                    AssessmentWarning(
                        severity="warning",
                        category="incomplete",
                        message=message,
                        field=f"clinical_assessment.{field}",
                    )
                )

        return warnings

    def _check_incomplete_literature(
        self, evidence_data: dict[str, Any]
    ) -> list[AssessmentWarning]:
        """
        Check for incomplete literature review fields.

        Complexity: 3 (guard clause + lookup table)

        Args:
            evidence_data: The evidence data to check

        Returns:
            List of warnings for incomplete literature fields
        """
        warnings = []
        literature = evidence_data.get("literature_review")

        # If literature_review key doesn't exist at all, skip (caught by missing check)
        # But if it exists as empty dict, we should check for required fields
        if literature is None:
            return warnings  # Already caught by missing check

        required_fields = {
            "evidence_quality": "Evidence quality assessment missing",
            "study_design_strength": "Study design strength assessment missing",
        }

        for field, message in required_fields.items():
            # Check if field is missing, None, or empty string
            field_value = literature.get(field)
            if not field_value or (
                isinstance(field_value, str) and not field_value.strip()
            ):
                warnings.append(
                    AssessmentWarning(
                        severity="warning",
                        category="incomplete",
                        message=message,
                        field=f"literature_review.{field}",
                    )
                )

        return warnings

    def _check_low_confidence_indicators(
        self, evidence_data: dict[str, Any]
    ) -> list[AssessmentWarning]:
        """
        Check for indicators of low confidence in assessment.

        Complexity: 4 (guard clause + three pattern checks)

        Args:
            evidence_data: The evidence data to check

        Returns:
            List of warnings for low confidence indicators
        """
        warnings = []
        clinical = evidence_data.get("clinical_assessment", {})
        literature = evidence_data.get("literature_review", {})

        if not (clinical or literature):
            return warnings

        # Confidence indicator checks (data-driven approach)
        # Using a list of patterns makes it easy to add/modify checks
        low_confidence_patterns = [
            {
                "field": "phenotype_match",
                "data": clinical,
                "bad_values": ["poor", "weak"],
                "message": "Poor phenotype match may indicate weak gene-disease association",
                "path": "clinical_assessment.phenotype_match",
            },
            {
                "field": "inheritance_consistency",
                "data": clinical,
                "bad_values": ["inconsistent", "conflicting"],
                "message": "Inconsistent inheritance pattern raises questions about association",
                "path": "clinical_assessment.inheritance_consistency",
            },
            {
                "field": "evidence_quality",
                "data": literature,
                "bad_values": ["low", "poor", "insufficient"],
                "message": "Low evidence quality limits confidence in assessment",
                "path": "literature_review.evidence_quality",
            },
        ]

        for pattern in low_confidence_patterns:
            field_value = pattern["data"].get(pattern["field"], "").lower()
            if any(bad_val in field_value for bad_val in pattern["bad_values"]):
                warnings.append(
                    AssessmentWarning(
                        severity="warning",
                        category="low_confidence",
                        message=pattern["message"],
                        field=pattern["path"],
                    )
                )

        return warnings


def check_qualitative_warnings(evidence_data: dict[str, Any]) -> list[str]:
    """
    Convenience function for backward compatibility.

    Checks qualitative assessment data and returns warning messages.

    Complexity: 2 (simple delegation + list comprehension)

    Args:
        evidence_data: The evidence data to check

    Returns:
        List of warning message strings
    """
    checker = QualitativeWarningChecker()
    warnings = checker.check_all(evidence_data)
    return [w.message for w in warnings]
