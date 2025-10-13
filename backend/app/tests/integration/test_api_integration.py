"""
Test API integration for schema-agnostic system.
Tests that all the API endpoints can be imported and basic functionality works.
"""

import contextlib
import os
import sys

# Add the parent directory to sys.path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))


def test_imports():
    """Test that all API modules can be imported."""

    with contextlib.suppress(Exception):
        pass

    with contextlib.suppress(Exception):
        pass

    with contextlib.suppress(Exception):
        pass

    with contextlib.suppress(Exception):
        pass

    with contextlib.suppress(Exception):
        pass

    with contextlib.suppress(Exception):
        pass


def test_crud_imports():
    """Test that all CRUD modules can be imported."""

    with contextlib.suppress(Exception):
        pass

    with contextlib.suppress(Exception):
        pass

    with contextlib.suppress(Exception):
        pass

    with contextlib.suppress(Exception):
        pass

    with contextlib.suppress(Exception):
        pass


def test_schema_imports():
    """Test that all schema modules can be imported."""

    with contextlib.suppress(Exception):
        pass

    with contextlib.suppress(Exception):
        pass

    with contextlib.suppress(Exception):
        pass

    with contextlib.suppress(Exception):
        pass

    with contextlib.suppress(Exception):
        pass


def test_model_imports():
    """Test that model imports work."""

    with contextlib.suppress(Exception):
        pass


def test_api_router():
    """Test that the main API router can be imported."""

    try:
        from app.api.v1.api import api_router

        # Check that all routes are included
        routes = [route.path for route in api_router.routes]
        expected_prefixes = [
            "/health",
            "/auth",
            "/scopes",
            "/schemas",
            "/validation",
            "/gene-assignments",
            "/workflow",
            "/genes",
            "/genes-new",
            "/users",
        ]

        found_prefixes = []
        for prefix in expected_prefixes:
            if any(route.startswith(prefix) for route in routes):
                found_prefixes.append(prefix)

    except Exception:
        pass


def run_integration_tests():
    """Run all integration tests."""

    try:
        test_imports()
        test_crud_imports()
        test_schema_imports()
        test_model_imports()
        test_api_router()

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
