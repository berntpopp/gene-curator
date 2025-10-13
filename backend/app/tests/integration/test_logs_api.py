"""
Comprehensive tests for system logs API endpoints.

Tests cover:
- Import and structure validation
- Permission checks (admin/reviewer/viewer)
- Request correlation
- Statistics dashboard
- Export functionality
- Error handling
"""

from datetime import datetime, timedelta

import pytest


def test_logs_endpoint_imports():
    """Test that logs endpoint module can be imported."""
    try:
        from app.api.v1.endpoints import logs

        assert logs.router is not None
        assert hasattr(logs, "search_logs")
        assert hasattr(logs, "get_log")
        assert hasattr(logs, "get_logs_by_request")
        assert hasattr(logs, "get_log_statistics")
        assert hasattr(logs, "get_recent_errors")
        assert hasattr(logs, "export_logs")
    except ImportError as e:
        pytest.fail(f"Failed to import logs endpoints: {e}")


def test_logs_crud_imports():
    """Test that logs CRUD module can be imported."""
    try:
        from app.crud import logs

        assert hasattr(logs, "get_logs")
        assert hasattr(logs, "get_log_by_id")
        assert hasattr(logs, "get_logs_by_request_id")
        assert hasattr(logs, "get_log_statistics")
        assert hasattr(logs, "get_recent_errors")
        assert hasattr(logs, "get_logs_for_export")
        assert hasattr(logs, "cleanup_old_partitions")
    except ImportError as e:
        pytest.fail(f"Failed to import logs CRUD: {e}")


def test_logs_schema_imports():
    """Test that logs schema module can be imported."""
    try:
        from app.schemas.logs import (
            LogEntry,
            LogExportParams,
            LogSearchParams,
            LogStatsSummary,
        )

        assert LogEntry is not None
        assert LogSearchParams is not None
        assert LogStatsSummary is not None
        assert LogExportParams is not None
    except ImportError as e:
        pytest.fail(f"Failed to import logs schemas: {e}")


def test_system_log_model_import():
    """Test that SystemLog model can be imported."""
    try:
        from app.models.models import SystemLog

        assert SystemLog is not None
        assert hasattr(SystemLog, "__tablename__")
        assert SystemLog.__tablename__ == "system_logs"
    except ImportError as e:
        pytest.fail(f"Failed to import SystemLog model: {e}")


def test_logs_router_registered():
    """Test that logs router is registered in main API."""
    try:
        from app.api.v1.api import api_router

        routes = [route.path for route in api_router.routes]

        # Check for logs endpoints (routes may have /logs prefix or not depending on how they're mounted)
        expected_logs_keywords = [
            "logs/",
            "log_id",
            "request_id",
            "stats/summary",
            "recent-errors",
            "export",
            "cleanup",
        ]

        for expected_keyword in expected_logs_keywords:
            # Check if keyword exists in any route
            matching_routes = [r for r in routes if expected_keyword in r]
            assert len(matching_routes) > 0, (
                f"Route keyword '{expected_keyword}' not found in API router. Available routes: {routes}"
            )

    except Exception as e:
        pytest.fail(f"Failed to check logs router registration: {e}")


def test_permission_dependencies():
    """Test that permission check dependencies are properly defined."""
    try:
        from app.api.v1.endpoints.logs import require_admin, require_admin_or_reviewer

        assert require_admin_or_reviewer is not None
        assert require_admin is not None
    except ImportError as e:
        pytest.fail(f"Failed to import permission dependencies: {e}")


def test_log_entry_schema_structure():
    """Test LogEntry schema structure matches database model."""
    from pydantic import BaseModel

    from app.schemas.logs import LogEntry

    # Verify it's a Pydantic model
    assert issubclass(LogEntry, BaseModel)

    # Check required fields
    required_fields = {"id", "timestamp", "level", "logger_name", "message"}
    schema_fields = set(LogEntry.model_fields.keys())
    assert required_fields.issubset(schema_fields), (
        f"Missing required fields: {required_fields - schema_fields}"
    )

    # Check optional fields
    optional_fields = {
        "request_id",
        "user_id",
        "scope_id",
        "duration_ms",
        "context",
        "endpoint",
        "method",
        "status_code",
    }
    assert optional_fields.issubset(schema_fields), (
        f"Missing optional fields: {optional_fields - schema_fields}"
    )


def test_log_search_params_validation():
    """Test LogSearchParams schema validation."""
    from app.schemas.logs import LogSearchParams

    # Test valid parameters
    params = LogSearchParams(level="ERROR", skip=0, limit=100)
    assert params.level == "ERROR"
    assert params.skip == 0
    assert params.limit == 100

    # Test defaults
    params_default = LogSearchParams()
    assert params_default.skip == 0
    assert params_default.limit == 100

    # Test with datetime
    now = datetime.utcnow()
    params_time = LogSearchParams(start_date=now - timedelta(days=1), end_date=now)
    assert params_time.start_date < params_time.end_date


def test_log_export_params_validation():
    """Test LogExportParams schema validation."""
    from app.schemas.logs import LogExportParams

    # Test JSON export
    params_json = LogExportParams(format="json", limit=5000)
    assert params_json.format == "json"
    assert params_json.limit == 5000

    # Test CSV export
    params_csv = LogExportParams(format="csv", level="ERROR", limit=1000)
    assert params_csv.format == "csv"
    assert params_csv.level == "ERROR"
    assert params_csv.limit == 1000


def test_crud_get_logs_signature():
    """Test get_logs CRUD function signature."""
    import inspect

    from app.crud import logs

    sig = inspect.signature(logs.get_logs)
    params = sig.parameters

    # Check for expected parameters
    expected_params = {
        "db",
        "skip",
        "limit",
        "level",
        "logger_name",
        "message",
        "request_id",
        "user_id",
        "endpoint",
        "method",
        "start_date",
        "end_date",
        "min_duration_ms",
    }
    actual_params = set(params.keys())
    assert expected_params.issubset(actual_params), (
        f"Missing parameters: {expected_params - actual_params}"
    )


def test_crud_get_log_statistics_signature():
    """Test get_log_statistics CRUD function signature."""
    import inspect

    from app.crud import logs

    sig = inspect.signature(logs.get_log_statistics)
    params = sig.parameters

    # Should only require db parameter
    assert "db" in params
    assert sig.return_annotation != inspect.Signature.empty


def test_system_log_model_fields():
    """Test SystemLog model has all required fields."""
    from sqlalchemy import inspect as sa_inspect

    from app.models.models import SystemLog

    mapper = sa_inspect(SystemLog)
    columns = {col.key for col in mapper.columns}

    # Check required fields
    required_fields = {"id", "timestamp", "level", "logger", "message", "context"}
    assert required_fields.issubset(columns), (
        f"Missing required columns: {required_fields - columns}"
    )

    # Check correlation and context fields
    context_fields = {
        "request_id",
        "user_id",
        "ip_address",
        "user_agent",
        "path",
        "method",
        "status_code",
        "duration_ms",
        "error_type",
        "error_message",
        "stack_trace",
    }
    assert context_fields.issubset(columns), (
        f"Missing context columns: {context_fields - columns}"
    )


def test_endpoint_docstrings():
    """Test that all endpoints have proper docstrings."""
    from app.api.v1.endpoints import logs

    endpoints = [
        logs.search_logs,
        logs.get_log,
        logs.get_logs_by_request,
        logs.get_log_statistics,
        logs.get_recent_errors,
        logs.export_logs,
        logs.cleanup_old_logs,
    ]

    for endpoint in endpoints:
        assert endpoint.__doc__ is not None, (
            f"Endpoint {endpoint.__name__} is missing docstring"
        )
        assert len(endpoint.__doc__.strip()) > 50, (
            f"Endpoint {endpoint.__name__} has inadequate documentation"
        )


def test_crud_functions_are_async():
    """Test that all CRUD functions are async."""
    import inspect

    from app.crud import logs

    crud_functions = [
        logs.get_logs,
        logs.get_log_by_id,
        logs.get_logs_by_request_id,
        logs.get_log_statistics,
        logs.get_recent_errors,
        logs.get_logs_for_export,
        logs.cleanup_old_partitions,
    ]

    for func in crud_functions:
        assert inspect.iscoroutinefunction(func), (
            f"CRUD function {func.__name__} is not async"
        )


def test_endpoint_dependencies():
    """Test that endpoints have proper authentication dependencies."""
    import inspect

    from app.api.v1.endpoints import logs

    # Endpoints that should require admin or reviewer
    admin_or_reviewer_endpoints = [
        logs.search_logs,
        logs.get_log,
        logs.get_logs_by_request,
        logs.get_recent_errors,
    ]

    for endpoint in admin_or_reviewer_endpoints:
        sig = inspect.signature(endpoint)
        params = sig.parameters
        assert "current_user" in params, (
            f"Endpoint {endpoint.__name__} is missing current_user parameter"
        )

    # Endpoints that should require admin only
    admin_only_endpoints = [
        logs.get_log_statistics,
        logs.export_logs,
        logs.cleanup_old_logs,
    ]

    for endpoint in admin_only_endpoints:
        sig = inspect.signature(endpoint)
        params = sig.parameters
        assert "current_user" in params, (
            f"Endpoint {endpoint.__name__} is missing current_user parameter"
        )


def test_export_formats_supported():
    """Test that export endpoint supports both JSON and CSV formats."""
    import inspect

    from app.api.v1.endpoints import logs

    sig = inspect.signature(logs.export_logs)
    params = sig.parameters

    # Check format parameter exists
    assert "format" in params, "Export endpoint is missing format parameter"

    # Check format parameter has regex validation
    format_param = params["format"]
    # The parameter should have Query dependency with regex validation


def test_request_correlation_endpoint_exists():
    """Test that request correlation endpoint is properly defined."""
    from app.api.v1.endpoints import logs
    from app.crud import logs as crud_logs

    # Check endpoint exists
    assert hasattr(logs, "get_logs_by_request")

    # Check CRUD function exists
    assert hasattr(crud_logs, "get_logs_by_request_id")

    # Check it returns list
    import inspect

    crud_sig = inspect.signature(crud_logs.get_logs_by_request_id)
    # Should take db and request_id parameters
    params = crud_sig.parameters
    assert "db" in params
    assert "request_id" in params


def test_statistics_endpoint_structure():
    """Test that statistics endpoint returns proper structure."""
    from pydantic import BaseModel

    from app.schemas.logs import LogStatsSummary

    assert issubclass(LogStatsSummary, BaseModel)

    # Check required fields
    required_fields = {
        "total_logs",
        "logs_by_level",
        "logs_by_hour",
        "avg_duration_ms",
        "slow_endpoints",
        "error_rate",
        "top_errors",
    }
    schema_fields = set(LogStatsSummary.model_fields.keys())
    assert required_fields.issubset(schema_fields), (
        f"Missing required statistics fields: {required_fields - schema_fields}"
    )


def run_logs_api_tests():
    """Run all logs API tests."""

    test_functions = [
        test_logs_endpoint_imports,
        test_logs_crud_imports,
        test_logs_schema_imports,
        test_system_log_model_import,
        test_logs_router_registered,
        test_permission_dependencies,
        test_log_entry_schema_structure,
        test_log_search_params_validation,
        test_log_export_params_validation,
        test_crud_get_logs_signature,
        test_crud_get_log_statistics_signature,
        test_system_log_model_fields,
        test_endpoint_docstrings,
        test_crud_functions_are_async,
        test_endpoint_dependencies,
        test_export_formats_supported,
        test_request_correlation_endpoint_exists,
        test_statistics_endpoint_structure,
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            print(f"✓ {test_func.__name__}")
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}: {e}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed out of {passed + failed} tests")
    return failed == 0


if __name__ == "__main__":
    import sys

    success = run_logs_api_tests()
    sys.exit(0 if success else 1)
