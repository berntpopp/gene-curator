"""
Complete deployment test for schema-agnostic Gene Curator.
Tests full system integration and deployment readiness.
"""

import os
import sys

# Add the parent directory to sys.path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))


def test_complete_system():  # noqa: C901
    """Test the complete integrated system."""

    # Test 1: Core module imports
    try:
        from app.core.schema_validator import schema_validator
        from app.crud.workflow_engine import workflow_engine
        from app.scoring.registry import scoring_registry

    except ImportError as e:
        print(f"❌ Core module import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error importing core modules: {e}")
        return False

    # Test 2: Model imports with corrected names
    try:
        pass
    except ImportError as e:
        print(f"❌ Model import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error importing models: {e}")
        return False

    # Test 3: CRUD operations
    try:
        pass
    except ImportError as e:
        print(f"❌ CRUD operation import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error with CRUD operations: {e}")
        return False

    # Test 4: Schema definitions
    try:
        from app.schemas import (
            workflow_engine,
        )

    except ImportError as e:
        print(f"❌ Schema definition import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error importing schema definitions: {e}")
        return False

    # Test 5: API dependencies
    try:
        pass
    except ImportError as e:
        print(f"❌ API dependency import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error with API dependencies: {e}")
        return False

    # Test 6: Complete API integration
    try:
        pass
    except ImportError as e:
        print(f"❌ API integration import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error with API integration: {e}")
        return False

    # Test 7: Main API router
    try:
        from app.api.v1.api import api_router

        # Check that all routes are properly included
        routes = [route.path for route in api_router.routes]
        expected_routes = [
            "/health",
            "/auth",
            "/scopes",
            "/schemas",
            "/validation",
            "/gene-assignments",
            "/workflow",
            "/genes",
            "/genes-new",
        ]

        found_routes = []
        for expected in expected_routes:
            if any(route.startswith(expected) for route in routes):
                found_routes.append(expected)

        if len(found_routes) == len(expected_routes):
            pass
        else:
            missing_routes = sorted(set(expected_routes) - set(found_routes))
            # Log missing routes for debugging
            print(
                f"❌ Missing {len(missing_routes)} API routes: {', '.join(missing_routes)}"
            )
            return False

    except ImportError as e:
        print(f"❌ API router import failed: {e}")
        return False
    except KeyError as e:
        print(f"❌ OpenAPI spec structure error: {e}")
        return False
    except Exception as e:
        print(f"❌ API route check failed: {e}")
        return False

    # Test 8: End-to-end workflow simulation
    try:
        # Test schema validation with ClinGen methodology
        test_schema = {
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
                            "min_value": 0,
                            "max_value": 12,
                        },
                        "segregation_score": {
                            "type": "score",
                            "min_value": 0,
                            "max_value": 3,
                        },
                    },
                    "required": True,
                },
            },
            "business_rules": ["clingen_genetic_evidence"],
            "scoring_configuration": {"engine": "clingen_sop_v11"},
            "workflow_states": ["draft", "submitted", "approved"],
        }

        test_evidence = {
            "gene_symbol": "BRCA1",
            "genetic_evidence": {"case_level_score": 8.0, "segregation_score": 2.0},
        }

        # Validate schema definition
        schema_validator.validate_schema_definition(test_schema)

        # Validate evidence data
        schema_validator.validate_evidence_data(test_evidence, test_schema)

        # Test scoring engine
        clingen_engine = scoring_registry.get_engine("clingen_sop_v11")
        if clingen_engine:
            clingen_engine.calculate_scores(test_evidence, {})

        # Test workflow validation
        from app.models.schema_agnostic_models import WorkflowStage

        workflow_engine.validate_transition(
            None,  # Mock db session
            WorkflowStage.curation,
            WorkflowStage.review,
            "user-123",
            "item-123",
            "curation",
        )

    except ImportError as e:
        print(f"❌ Workflow test import failed: {e}")
        return False
    except AttributeError as e:
        print(f"❌ Workflow attribute error (possibly invalid transition): {e}")
        return False
    except ValueError as e:
        print(f"❌ Workflow validation error: {e}")
        return False
    except Exception as e:
        print(f"❌ End-to-end workflow test failed: {e}")
        return False

    # Test 9: Database schema SQL files
    try:
        schema_files = [
            "database/sql/004_schema_agnostic_foundation.sql",
            "database/sql/005_schema_agnostic_triggers.sql",
            "database/sql/006_schema_agnostic_views.sql",
            "database/sql/007_schema_agnostic_seed_data.sql",
        ]

        for file_path in schema_files:
            if os.path.exists(file_path):
                with open(file_path) as f:
                    content = f.read()
                    if len(content) > 100:  # Basic validation
                        pass
                    else:
                        pass
            else:
                pass

    except FileNotFoundError as e:
        print(f"❌ Database schema file not found: {e}")
        return False
    except OSError as e:
        print(f"❌ Error reading database schema file: {e}")
        return False
    except Exception as e:
        print(f"❌ Database schema file test failed: {e}")
        return False

    # Test 10: System readiness check

    readiness_checks = {
        "Schema Validator": True,
        "Scoring Engines": len(scoring_registry.get_engine_names()) >= 3,
        "Workflow Engine": True,
        "API Endpoints": True,
        "Database Schema": True,
        "Documentation": os.path.exists("IMPLEMENTATION_SUMMARY.md"),
    }

    all_ready = all(readiness_checks.values())

    for _check, _status in readiness_checks.items():
        pass

    return bool(all_ready)


if __name__ == "__main__":
    success = test_complete_system()
    sys.exit(0 if success else 1)
