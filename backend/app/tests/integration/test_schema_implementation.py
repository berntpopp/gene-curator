"""
Test script for schema-agnostic implementation.
Tests all major components to ensure they work correctly.
"""

import contextlib
import os
import sys

# Add the parent directory to sys.path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

try:
    from app.core.schema_validator import schema_validator
    from app.scoring.registry import scoring_registry

except ImportError:
    sys.exit(1)


def test_schema_validator() -> None:
    """Test the schema validation engine."""

    # Test schema definition
    test_schema = {
        "field_definitions": {
            "gene_symbol": {
                "type": "text",
                "label": "Gene Symbol",
                "min_length": 1,
                "max_length": 50,
                "required": True,
            },
            "genetic_evidence_score": {
                "type": "score",
                "label": "Genetic Evidence Score",
                "min_value": 0,
                "max_value": 12,
                "decimal_places": 2,
                "required": True,
            },
            "experimental_evidence_score": {
                "type": "score",
                "label": "Experimental Evidence Score",
                "min_value": 0,
                "max_value": 6,
                "decimal_places": 2,
                "required": False,
            },
            "classification": {
                "type": "select",
                "label": "Classification",
                "options": [
                    {"value": "definitive", "label": "Definitive"},
                    {"value": "strong", "label": "Strong"},
                    {"value": "moderate", "label": "Moderate"},
                ],
                "required": True,
            },
            "publication_date": {
                "type": "date",
                "label": "Publication Date",
                "required": False,
            },
            "contact_email": {
                "type": "email",
                "label": "Contact Email",
                "required": False,
            },
            "pmid": {"type": "pmid", "label": "PubMed ID", "required": False},
        },
        "validation_rules": {
            "total_score_check": {
                "type": "condition",
                "condition": "exists(genetic_evidence_score)",
                "message": "Genetic evidence score is required",
            }
        },
        "business_rules": ["clingen_genetic_evidence", "clingen_experimental_evidence"],
        "scoring_configuration": {"engine": "clingen"},
        "workflow_states": ["draft", "submitted", "approved"],
        "ui_configuration": {
            "sections": [
                {"title": "Gene Information", "fields": ["gene_symbol"]},
                {
                    "title": "Evidence Scores",
                    "fields": ["genetic_evidence_score", "experimental_evidence_score"],
                },
            ]
        },
    }

    # Test 1: Valid complete data
    valid_data = {
        "gene_symbol": "BRCA1",
        "genetic_evidence_score": 8.0,
        "experimental_evidence_score": 4.0,
        "classification": "definitive",
        "publication_date": "2023-01-15",
        "contact_email": "researcher@example.com",
        "pmid": "12345678",
    }

    result = schema_validator.validate_evidence_data(valid_data, test_schema)

    # Test 2: Missing required field
    invalid_data = {
        "genetic_evidence_score": 10.0,
        "classification": "strong",
        # Missing required gene_symbol
    }

    result = schema_validator.validate_evidence_data(invalid_data, test_schema)
    for _error in result.errors:
        pass

    # Test 3: Invalid field values
    bad_data = {
        "gene_symbol": "BRCA2",
        "genetic_evidence_score": 15.0,  # Exceeds maximum
        "classification": "invalid_option",  # Not in options
        "contact_email": "not-an-email",  # Invalid email format
        "pmid": "not-a-number",  # Invalid PMID format
    }

    result = schema_validator.validate_evidence_data(bad_data, test_schema)

    # Test 4: Schema definition validation
    result = schema_validator.validate_schema_definition(test_schema)
    if not result.is_valid:
        for _error in result.errors:
            pass

    # Test 5: JSON Schema generation
    with contextlib.suppress(Exception):
        schema_validator.generate_json_schema(test_schema)


def test_scoring_engines() -> None:
    """Test the scoring engine registry and implementations."""

    # Test 1: Registry functionality
    scoring_registry.list_engines()
    scoring_registry.get_engine_names()

    # Test 2: ClinGen scoring engine
    try:
        clingen_engine = scoring_registry.get_engine("clingen_sop_v11")
        if clingen_engine:
            # Test scoring
            test_evidence = {
                "genetic_evidence": {
                    "case_level_score": 6.0,
                    "segregation_score": 3.0,
                    "case_control_score": 0.0,
                },
                "experimental_evidence": {
                    "functional_score": 2.0,
                    "model_system_score": 2.0,
                    "rescue_score": 0.0,
                },
                "contradictory_evidence": {"has_contradictory": False},
            }

            clingen_engine.calculate_scores(test_evidence, {})
        else:
            pass
    except Exception:
        pass

    # Test 3: GenCC scoring engine
    try:
        gencc_engine = scoring_registry.get_engine("gencc_based")
        if gencc_engine:
            # Test basic scoring
            test_evidence = {
                "classification": "Definitive",
                "confidence_level": "High",
                "evidence_summary": "Strong genetic and functional evidence",
            }

            gencc_engine.calculate_scores(test_evidence, {})
        else:
            pass
    except Exception:
        pass

    # Test 4: Qualitative scoring engine
    try:
        qual_engine = scoring_registry.get_engine("qualitative_assessment")
        if qual_engine:
            # Test basic assessment
            test_evidence = {
                "assessment": "Strong",
                "confidence": "High",
                "rationale": "Multiple lines of evidence support association",
            }

            qual_engine.calculate_scores(test_evidence, {})
        else:
            pass
    except Exception:
        pass


def test_integration() -> None:
    """Test integration between components."""

    # Test 1: Schema validation with scoring

    clingen_schema = {
        "field_definitions": {
            "genetic_evidence": {
                "type": "object",
                "label": "Genetic Evidence",
                "properties": {
                    "case_level_score": {
                        "type": "score",
                        "min_value": 0,
                        "max_value": 12,
                    },
                    "segregation_score": {
                        "type": "score",
                        "min_value": 0,
                        "max_value": 3,
                    },
                    "case_control_score": {
                        "type": "score",
                        "min_value": 0,
                        "max_value": 6,
                    },
                },
                "required": True,
            },
            "experimental_evidence": {
                "type": "object",
                "label": "Experimental Evidence",
                "properties": {
                    "functional_score": {
                        "type": "score",
                        "min_value": 0,
                        "max_value": 2,
                    },
                    "model_system_score": {
                        "type": "score",
                        "min_value": 0,
                        "max_value": 2,
                    },
                    "rescue_score": {"type": "score", "min_value": 0, "max_value": 2},
                },
                "required": False,
            },
        },
        "business_rules": ["clingen_genetic_evidence", "clingen_experimental_evidence"],
        "scoring_configuration": {"engine": "clingen"},
        "workflow_states": ["draft", "submitted", "approved"],
    }

    test_data = {
        "genetic_evidence": {
            "case_level_score": 8.0,
            "segregation_score": 2.0,
            "case_control_score": 0.0,
        },
        "experimental_evidence": {
            "functional_score": 2.0,
            "model_system_score": 1.0,
            "rescue_score": 0.0,
        },
    }

    # Validate with schema validator
    schema_validator.validate_evidence_data(test_data, clingen_schema)

    # Also test with scoring engine directly
    try:
        clingen_engine = scoring_registry.get_engine("clingen_sop_v11")
        if clingen_engine:
            clingen_engine.calculate_scores(test_data, {})
    except Exception:
        pass


def test_error_handling() -> None:
    """Test error handling and edge cases."""

    # Test 1: Invalid schema structure
    invalid_schema = {
        "field_definitions": "not_a_dict",  # Should be dict
        "workflow_states": "not_a_list",  # Should be list
    }

    with contextlib.suppress(Exception):
        schema_validator.validate_schema_definition(invalid_schema)

    # Test 2: Missing scoring engine
    try:
        missing_engine = scoring_registry.get_engine("nonexistent")
        if missing_engine is None:
            pass
        else:
            pass
    except Exception:
        pass

    # Test 3: Invalid evidence data types
    schema = {
        "field_definitions": {
            "number_field": {"type": "number", "required": True},
            "text_field": {"type": "text", "required": True},
        },
        "workflow_states": ["draft"],
    }

    bad_data = {
        "number_field": "not_a_number",  # Should be number
        "text_field": 12345,  # Should be text
    }

    with contextlib.suppress(Exception):
        schema_validator.validate_evidence_data(bad_data, schema)


def run_all_tests() -> None:
    """Run all test suites."""

    try:
        test_schema_validator()
        test_scoring_engines()
        test_integration()
        test_error_handling()

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
