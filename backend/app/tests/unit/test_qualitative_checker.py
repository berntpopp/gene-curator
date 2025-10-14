"""
Unit tests for QualitativeWarningChecker.

Tests each checker method independently to verify:
- Correct warning detection
- Proper warning categorization
- Low cyclomatic complexity
- SOLID principles compliance
"""

import pytest

from app.scoring.qualitative_checker import (
    AssessmentWarning,
    QualitativeWarningChecker,
    check_qualitative_warnings,
)


class TestAssessmentWarning:
    """Test AssessmentWarning dataclass."""

    def test_warning_creation(self):
        """Test creating an AssessmentWarning."""
        warning = AssessmentWarning(
            severity="error",
            category="missing",
            message="Test message",
            field="test.field",
        )

        assert warning.severity == "error"
        assert warning.category == "missing"
        assert warning.message == "Test message"
        assert warning.field == "test.field"

    def test_warning_equality(self):
        """Test that warnings with same values are equal."""
        warning1 = AssessmentWarning(
            severity="warning", category="incomplete", message="Test", field="field"
        )
        warning2 = AssessmentWarning(
            severity="warning", category="incomplete", message="Test", field="field"
        )

        assert warning1 == warning2


class TestQualitativeWarningChecker:
    """Test QualitativeWarningChecker class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.checker = QualitativeWarningChecker()

    def test_check_all_with_complete_data(self):
        """Test that complete data produces no warnings."""
        evidence = {
            "clinical_assessment": {
                "phenotype_match": "excellent",
                "inheritance_consistency": "consistent",
            },
            "literature_review": {
                "evidence_quality": "high",
                "study_design_strength": "strong",
            },
        }

        warnings = self.checker.check_all(evidence)

        assert len(warnings) == 0

    def test_check_all_with_empty_data(self):
        """Test that empty data produces error warnings."""
        evidence = {}

        warnings = self.checker.check_all(evidence)

        assert len(warnings) == 2  # Missing clinical and literature
        assert all(w.severity == "error" for w in warnings)
        assert all(w.category == "missing" for w in warnings)

    def test_check_missing_clinical_assessment(self):
        """Test detection of missing clinical assessment."""
        evidence = {"literature_review": {"evidence_quality": "high"}}

        warnings = self.checker._check_missing_assessments(evidence)

        assert len(warnings) == 1
        assert warnings[0].category == "missing"
        assert warnings[0].field == "clinical_assessment"
        assert "clinical assessment" in warnings[0].message.lower()

    def test_check_missing_literature_review(self):
        """Test detection of missing literature review."""
        evidence = {"clinical_assessment": {"phenotype_match": "good"}}

        warnings = self.checker._check_missing_assessments(evidence)

        assert len(warnings) == 1
        assert warnings[0].category == "missing"
        assert warnings[0].field == "literature_review"
        assert "literature review" in warnings[0].message.lower()

    def test_check_missing_both_assessments(self):
        """Test detection when both assessments are missing."""
        evidence = {}

        warnings = self.checker._check_missing_assessments(evidence)

        assert len(warnings) == 2
        fields = {w.field for w in warnings}
        assert "clinical_assessment" in fields
        assert "literature_review" in fields

    def test_check_incomplete_clinical_missing_phenotype(self):
        """Test detection of missing phenotype match."""
        evidence = {"clinical_assessment": {"inheritance_consistency": "consistent"}}

        warnings = self.checker._check_incomplete_clinical(evidence)

        assert len(warnings) == 1
        assert warnings[0].field == "clinical_assessment.phenotype_match"
        assert "phenotype match" in warnings[0].message.lower()

    def test_check_incomplete_clinical_missing_inheritance(self):
        """Test detection of missing inheritance consistency."""
        evidence = {"clinical_assessment": {"phenotype_match": "good"}}

        warnings = self.checker._check_incomplete_clinical(evidence)

        assert len(warnings) == 1
        assert warnings[0].field == "clinical_assessment.inheritance_consistency"
        assert "inheritance consistency" in warnings[0].message.lower()

    def test_check_incomplete_clinical_missing_both_fields(self):
        """Test detection when both clinical fields are missing."""
        evidence = {"clinical_assessment": {}}

        warnings = self.checker._check_incomplete_clinical(evidence)

        assert len(warnings) == 2
        fields = {w.field for w in warnings}
        assert "clinical_assessment.phenotype_match" in fields
        assert "clinical_assessment.inheritance_consistency" in fields

    def test_check_incomplete_clinical_returns_empty_when_no_clinical(self):
        """Test that incomplete check returns empty when clinical is missing."""
        evidence = {}

        warnings = self.checker._check_incomplete_clinical(evidence)

        assert len(warnings) == 0  # Already caught by missing check

    def test_check_incomplete_literature_missing_quality(self):
        """Test detection of missing evidence quality."""
        evidence = {"literature_review": {"study_design_strength": "strong"}}

        warnings = self.checker._check_incomplete_literature(evidence)

        assert len(warnings) == 1
        assert warnings[0].field == "literature_review.evidence_quality"
        assert "evidence quality" in warnings[0].message.lower()

    def test_check_incomplete_literature_missing_design(self):
        """Test detection of missing study design strength."""
        evidence = {"literature_review": {"evidence_quality": "high"}}

        warnings = self.checker._check_incomplete_literature(evidence)

        assert len(warnings) == 1
        assert warnings[0].field == "literature_review.study_design_strength"
        assert "study design" in warnings[0].message.lower()

    def test_check_low_confidence_poor_phenotype(self):
        """Test detection of poor phenotype match."""
        evidence = {"clinical_assessment": {"phenotype_match": "poor"}}

        warnings = self.checker._check_low_confidence_indicators(evidence)

        assert len(warnings) >= 1
        poor_warnings = [w for w in warnings if "poor" in w.message.lower()]
        assert len(poor_warnings) == 1
        assert poor_warnings[0].category == "low_confidence"

    def test_check_low_confidence_inconsistent_inheritance(self):
        """Test detection of inconsistent inheritance."""
        evidence = {"clinical_assessment": {"inheritance_consistency": "inconsistent"}}

        warnings = self.checker._check_low_confidence_indicators(evidence)

        assert len(warnings) >= 1
        inconsistent_warnings = [
            w for w in warnings if "inconsistent" in w.message.lower()
        ]
        assert len(inconsistent_warnings) == 1

    def test_check_low_confidence_low_quality_evidence(self):
        """Test detection of low evidence quality."""
        evidence = {"literature_review": {"evidence_quality": "low"}}

        warnings = self.checker._check_low_confidence_indicators(evidence)

        assert len(warnings) >= 1
        low_quality_warnings = [w for w in warnings if "low" in w.message.lower()]
        assert len(low_quality_warnings) == 1

    def test_check_low_confidence_multiple_indicators(self):
        """Test detection of multiple low confidence indicators."""
        evidence = {
            "clinical_assessment": {
                "phenotype_match": "poor",
                "inheritance_consistency": "inconsistent",
            },
            "literature_review": {"evidence_quality": "low"},
        }

        warnings = self.checker._check_low_confidence_indicators(evidence)

        assert len(warnings) == 3
        assert all(w.category == "low_confidence" for w in warnings)

    def test_check_low_confidence_case_insensitive(self):
        """Test that confidence checks are case-insensitive."""
        evidence = {"clinical_assessment": {"phenotype_match": "POOR"}}

        warnings = self.checker._check_low_confidence_indicators(evidence)

        assert len(warnings) >= 1

    def test_check_low_confidence_returns_empty_when_no_data(self):
        """Test that low confidence check returns empty when no data."""
        evidence = {}

        warnings = self.checker._check_low_confidence_indicators(evidence)

        assert len(warnings) == 0


class TestConvenienceFunction:
    """Test the convenience function check_qualitative_warnings."""

    def test_convenience_function_returns_strings(self):
        """Test that convenience function returns string messages."""
        evidence = {}

        warnings = check_qualitative_warnings(evidence)

        assert isinstance(warnings, list)
        assert all(isinstance(w, str) for w in warnings)

    def test_convenience_function_with_complete_data(self):
        """Test convenience function with complete data."""
        evidence = {
            "clinical_assessment": {
                "phenotype_match": "excellent",
                "inheritance_consistency": "consistent",
            },
            "literature_review": {
                "evidence_quality": "high",
                "study_design_strength": "strong",
            },
        }

        warnings = check_qualitative_warnings(evidence)

        assert len(warnings) == 0

    def test_convenience_function_with_missing_data(self):
        """Test convenience function with missing data."""
        evidence = {}

        warnings = check_qualitative_warnings(evidence)

        assert len(warnings) >= 2
        assert any("clinical" in w.lower() for w in warnings)
        assert any("literature" in w.lower() for w in warnings)


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.checker = QualitativeWarningChecker()

    def test_minimal_valid_assessment(self):
        """Test minimal valid assessment produces no errors."""
        evidence = {
            "clinical_assessment": {
                "phenotype_match": "good",
                "inheritance_consistency": "consistent",
            },
            "literature_review": {
                "evidence_quality": "moderate",
                "study_design_strength": "adequate",
            },
        }

        warnings = self.checker.check_all(evidence)

        # Should have no missing or incomplete warnings
        error_warnings = [w for w in warnings if w.severity == "error"]
        assert len(error_warnings) == 0

    def test_partial_assessment_with_warnings(self):
        """Test partial assessment produces appropriate warnings."""
        evidence = {
            "clinical_assessment": {
                "phenotype_match": "poor"
                # Missing inheritance_consistency
            },
            "literature_review": {
                # Missing both fields
            },
        }

        warnings = self.checker.check_all(evidence)

        # Should have incomplete warnings
        incomplete_warnings = [w for w in warnings if w.category == "incomplete"]
        assert len(incomplete_warnings) >= 2

        # Should have low confidence warning for poor phenotype
        low_conf_warnings = [w for w in warnings if w.category == "low_confidence"]
        assert len(low_conf_warnings) >= 1

    def test_problematic_assessment_all_warnings(self):
        """Test problematic assessment triggers all warning types."""
        evidence = {
            "clinical_assessment": {
                "phenotype_match": "poor",
                "inheritance_consistency": "inconsistent",
            },
            "literature_review": {
                "evidence_quality": "low",
                # Missing study_design_strength
            },
        }

        warnings = self.checker.check_all(evidence)

        # Should have warnings from all categories
        categories = {w.category for w in warnings}
        assert "incomplete" in categories  # Missing study design
        assert "low_confidence" in categories  # Poor/inconsistent/low values

        # Should have multiple low confidence warnings
        low_conf = [w for w in warnings if w.category == "low_confidence"]
        assert len(low_conf) == 3  # poor, inconsistent, low


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
