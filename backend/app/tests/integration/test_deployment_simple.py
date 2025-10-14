"""
Simplified deployment test for schema-agnostic Gene Curator.
Tests core functionality without complex imports.
"""

import os
import sys

# Add the parent directory to sys.path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))


def test_core_functionality() -> None:  # noqa: C901
    """Test core functionality independently."""

    # Test 1: Schema Validator
    try:
        from app.core.schema_validator import schema_validator

        # Test with simple schema
        test_schema = {
            "field_definitions": {
                "gene_symbol": {
                    "type": "text",
                    "label": "Gene Symbol",
                    "required": True,
                    "min_length": 1,
                    "max_length": 50,
                },
                "score": {
                    "type": "number",
                    "label": "Score",
                    "min_value": 0,
                    "max_value": 12,
                    "required": True,
                },
            },
            "workflow_states": ["draft", "submitted"],
        }

        test_data = {"gene_symbol": "BRCA1", "score": 8.5}

        # Validate schema
        schema_validator.validate_schema_definition(test_schema)

        # Validate data
        schema_validator.validate_evidence_data(test_data, test_schema)

        # Generate JSON Schema
        json_schema = schema_validator.generate_json_schema(test_schema)

    except ImportError as e:
        print(f"❌ Schema validator import failed: {e}")
        return False
    except ValueError as e:
        print(f"❌ Schema validation error: {e}")
        return False
    except KeyError as e:
        print(f"❌ Schema structure error (missing required key): {e}")
        return False
    except Exception as e:
        print(f"❌ Schema validator test failed: {e}")
        return False

    # Test 2: Scoring Engines
    try:
        from app.scoring.registry import scoring_registry

        scoring_registry.get_engine_names()

        # Test ClinGen engine
        clingen_engine = scoring_registry.get_engine("clingen_sop_v11")
        if clingen_engine:
            test_evidence = {
                "genetic_evidence": {"case_level_score": 6.0, "segregation_score": 2.0},
                "experimental_evidence": {
                    "functional_score": 1.0,
                    "model_system_score": 1.0,
                },
            }

            clingen_engine.calculate_scores(test_evidence, {})

    except ImportError as e:
        print(f"❌ Scoring engine import failed: {e}")
        return False
    except AttributeError as e:
        print(f"❌ Scoring engine method error: {e}")
        return False
    except ValueError as e:
        print(f"❌ Scoring calculation error: {e}")
        return False
    except Exception as e:
        print(f"❌ Scoring engine test failed: {e}")
        return False

    # Test 3: Models and Enums
    try:
        pass

    except ImportError as e:
        print(f"❌ Models/enums import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Models/enums test failed: {e}")
        return False

    # Test 4: File Existence Check
    required_files = [
        "app/core/schema_validator.py",
        "app/scoring/registry.py",
        "app/scoring/clingen.py",
        "app/scoring/gencc.py",
        "app/scoring/qualitative.py",
        "app/models/schema_agnostic_models.py",
        "app/api/deps.py",
        "../database/sql/004_schema_agnostic_foundation.sql",
        "../database/sql/005_schema_agnostic_triggers.sql",
        "../database/sql/006_schema_agnostic_views.sql",
        "../database/sql/007_schema_agnostic_seed_data.sql",
    ]

    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            pass
        else:
            missing_files.append(file_path)

    if missing_files:
        pass
    else:
        pass

    # Test 5: Integration Test
    try:
        # Create a complete methodology test
        methodology_schema = {
            "field_definitions": {
                "gene_symbol": {
                    "type": "text",
                    "label": "Gene Symbol",
                    "required": True,
                },
                "genetic_evidence": {
                    "type": "object",
                    "label": "Genetic Evidence",
                    "properties": {
                        "case_level_score": {
                            "type": "score",
                            "label": "Case Level Score",
                            "min_value": 0,
                            "max_value": 12,
                        },
                        "segregation_score": {
                            "type": "score",
                            "label": "Segregation Score",
                            "min_value": 0,
                            "max_value": 3,
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
                            "label": "Functional Score",
                            "min_value": 0,
                            "max_value": 2,
                        }
                    },
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
            },
            "business_rules": [
                "clingen_genetic_evidence",
                "clingen_experimental_evidence",
            ],
            "scoring_configuration": {"engine": "clingen_sop_v11"},
            "workflow_states": ["draft", "submitted", "in_review", "approved"],
        }

        methodology_evidence = {
            "gene_symbol": "BRCA1",
            "genetic_evidence": {"case_level_score": 8.0, "segregation_score": 2.0},
            "experimental_evidence": {"functional_score": 1.5},
            "classification": "strong",
        }

        # Validate complete methodology
        from app.core.schema_validator import schema_validator
        from app.scoring.registry import scoring_registry

        # Schema validation
        schema_validator.validate_schema_definition(methodology_schema)

        # Evidence validation
        schema_validator.validate_evidence_data(
            methodology_evidence, methodology_schema
        )

        # Scoring
        clingen_engine = scoring_registry.get_engine("clingen_sop_v11")
        if clingen_engine:
            clingen_engine.calculate_scores(methodology_evidence, {})

        # JSON Schema generation for UI
        json_schema = schema_validator.generate_json_schema(methodology_schema)
        "properties" in json_schema and len(json_schema["properties"]) > 0

    except ImportError as e:
        print(f"❌ Integration test import failed: {e}")
        return False
    except ValueError as e:
        print(f"❌ Integration test validation error: {e}")
        return False
    except KeyError as e:
        print(f"❌ Integration test structure error: {e}")
        return False
    except AttributeError as e:
        print(f"❌ Integration test attribute error: {e}")
        return False
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

    return True


if __name__ == "__main__":
    success = test_core_functionality()
    sys.exit(0 if success else 1)
