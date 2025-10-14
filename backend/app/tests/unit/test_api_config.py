"""
Unit tests for API configuration system.

Tests YAML loading, validation, defaults, and environment variable overrides.
"""

import os
from typing import Generator
from unittest.mock import mock_open, patch

import pytest

from app.core.api_config import (
    APIConfig,
    CORSConfig,
    LoggingConfig,
    PaginationConfig,
    RateLimitConfig,
    TimeoutConfig,
    UploadConfig,
    get_api_config,
    get_cors_config,
    get_logging_config,
    get_pagination_config,
    get_rate_limit,
    get_timeout_config,
    get_upload_config,
    load_api_config,
    reload_config,
)


class TestCORSConfig:
    """Test CORS configuration model."""

    def test_cors_config_defaults(self) -> None:
        """Test CORS config with default values."""
        config = CORSConfig(allow_origins=["http://localhost:3000"])

        assert len(config.allow_origins) == 1
        assert config.allow_credentials is False
        assert "GET" in config.allow_methods
        assert "POST" in config.allow_methods
        assert "*" in config.allow_headers
        assert "X-Request-ID" in config.expose_headers

    def test_cors_config_trailing_slash_removal(self) -> None:
        """Test that trailing slashes are removed from origins."""
        config = CORSConfig(
            allow_origins=["http://localhost:3000/", "https://example.com/"]
        )

        assert config.allow_origins == ["http://localhost:3000", "https://example.com"]

    def test_cors_config_custom_values(self) -> None:
        """Test CORS config with custom values."""
        config = CORSConfig(
            allow_origins=["https://production.example.com"],
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization"],
            expose_headers=["X-Custom-Header"],
        )

        assert config.allow_origins == ["https://production.example.com"]
        assert config.allow_credentials is True
        assert config.allow_methods == ["GET", "POST"]
        assert config.allow_headers == ["Authorization"]
        assert config.expose_headers == ["X-Custom-Header"]


class TestRateLimitConfig:
    """Test rate limit configuration model."""

    def test_rate_limit_defaults(self) -> None:
        """Test rate limit with default values."""
        config = RateLimitConfig()

        assert config.requests_per_minute >= 1
        assert config.burst_size >= 1

    def test_rate_limit_custom_values(self) -> None:
        """Test rate limit with custom values."""
        config = RateLimitConfig(requests_per_minute=100, burst_size=20)

        assert config.requests_per_minute == 100
        assert config.burst_size == 20

    def test_rate_limit_validation(self) -> None:
        """Test validation of rate limit values."""
        with pytest.raises(ValueError):
            RateLimitConfig(requests_per_minute=0)

        with pytest.raises(ValueError):
            RateLimitConfig(burst_size=0)


class TestPaginationConfig:
    """Test pagination configuration model."""

    def test_pagination_defaults(self) -> None:
        """Test pagination with default values."""
        config = PaginationConfig()

        assert config.default_page_size >= 1
        assert config.max_page_size >= config.default_page_size
        assert config.min_page_size >= 1

    def test_pagination_resource_config(self) -> None:
        """Test resource-specific pagination."""
        config = PaginationConfig()

        assert config.genes.default >= 1
        assert config.genes.max >= config.genes.default
        assert config.logs.default >= 1
        assert config.logs.max >= config.logs.default
        assert config.search.default >= 1
        assert config.search.max >= config.search.default


class TestUploadConfig:
    """Test file upload configuration model."""

    def test_upload_defaults(self) -> None:
        """Test upload config with default values."""
        config = UploadConfig()

        assert config.max_file_size_mb >= 1
        assert config.max_file_size_mb <= 100
        assert len(config.allowed_extensions) > 0
        assert config.upload_dir
        assert config.validate_content is True

    def test_upload_extension_formatting(self) -> None:
        """Test that extensions are formatted with dots."""
        config = UploadConfig(allowed_extensions=["xlsx", ".csv", "json"])

        assert all(ext.startswith(".") for ext in config.allowed_extensions)
        assert ".xlsx" in config.allowed_extensions
        assert ".csv" in config.allowed_extensions
        assert ".json" in config.allowed_extensions


class TestLoggingConfig:
    """Test logging configuration model."""

    def test_logging_defaults(self) -> None:
        """Test logging config with default values."""
        config = LoggingConfig()

        assert 30 <= config.retention_days <= 365
        assert config.min_retention_days >= 1
        assert config.max_retention_days >= config.retention_days
        assert config.default_time_window_hours >= 1
        assert config.max_time_window_hours >= config.default_time_window_hours


class TestAPIConfig:
    """Test complete API configuration container."""

    def test_api_config_creation(self) -> None:
        """Test creation of complete API config."""
        config = APIConfig()

        assert isinstance(config.cors, CORSConfig)
        assert isinstance(config.rate_limits, dict)
        assert isinstance(config.timeouts, TimeoutConfig)
        assert isinstance(config.pagination, PaginationConfig)
        assert isinstance(config.uploads, UploadConfig)
        assert isinstance(config.logging, LoggingConfig)

    def test_api_config_rate_limit_tiers(self) -> None:
        """Test that all rate limit tiers are present."""
        config = APIConfig()

        assert "default" in config.rate_limits
        assert "authenticated" in config.rate_limits
        assert "curator" in config.rate_limits
        assert "admin" in config.rate_limits

        # Verify rates increase with privilege
        assert (
            config.rate_limits["admin"].requests_per_minute
            > config.rate_limits["authenticated"].requests_per_minute
        )
        assert (
            config.rate_limits["authenticated"].requests_per_minute
            > config.rate_limits["default"].requests_per_minute
        )


class TestConfigLoading:
    """Test configuration loading from YAML files."""

    def test_load_config_with_missing_file(self) -> None:
        """Test loading config when file doesn't exist uses defaults."""
        with patch("pathlib.Path.exists", return_value=False):
            config = load_api_config("/nonexistent/path.yaml")

            assert isinstance(config, APIConfig)
            # Should have defaults
            assert len(config.cors.allow_origins) > 0

    def test_load_config_with_valid_yaml(self) -> None:
        """Test loading config from valid YAML file."""
        yaml_content = """
api:
  cors:
    allow_origins:
      - "https://test.example.com"
    allow_credentials: true
  rate_limits:
    default:
      requests_per_minute: 50
      burst_size: 5
  timeouts:
    default_seconds: 20
  pagination:
    default_page_size: 25
    max_page_size: 500
    min_page_size: 1
    genes:
      default: 50
      max: 200
    logs:
      default: 50
      max: 500
    search:
      default: 25
      max: 250
  uploads:
    max_file_size_mb: 5
    allowed_extensions:
      - ".xlsx"
  logging:
    retention_days: 60
    min_retention_days: 30
    max_retention_days: 365
    default_time_window_hours: 12
    max_time_window_hours: 100
    max_export_limit: 50000
    recent_errors_default_limit: 10
    recent_errors_max_limit: 50
  database:
    pool_size: 3
    max_overflow: 5
    pool_timeout: 20
    pool_recycle: 1800
    echo: false
  security:
    access_token_expire_minutes: 15
    refresh_token_expire_days: 3
    min_password_length: 10
    max_password_length: 100
    session_timeout_minutes: 30
    max_concurrent_sessions: 3
  bulk_operations:
    max_genes_create: 500
    default_batch_size: 50
    enable_parallel: false
    parallel_workers: 2
  external_apis:
    hgnc:
      base_url: "https://test.api.example.com"
      timeout_seconds: 5
      retry_attempts: 2
      retry_delay_seconds: 2
    enabled: false
    cache_enabled: false
    cache_ttl_seconds: 1800
  performance:
    enabled: false
    slow_operation_threshold_ms: 500
    track_db_queries: false
    track_external_apis: false
  features:
    enable_docs_in_production: true
    enable_debug_endpoints: true
    enable_experimental: true
    enable_rate_limiting: true
    enable_request_correlation: false
"""

        with (
            patch("builtins.open", mock_open(read_data=yaml_content)),
            patch("pathlib.Path.exists", return_value=True),
        ):
            # Clear cache before loading
            load_api_config.cache_clear()
            config = load_api_config("test.yaml")

            assert "https://test.example.com" in config.cors.allow_origins
            assert config.cors.allow_credentials is True
            assert config.rate_limits["default"].requests_per_minute == 50
            assert config.timeouts.default_seconds == 20
            assert config.pagination.default_page_size == 25
            assert config.uploads.max_file_size_mb == 5
            assert config.logging.retention_days == 60

    def test_load_config_with_invalid_yaml(self) -> None:
        """Test loading config with invalid YAML uses defaults."""
        with (
            patch("builtins.open", mock_open(read_data="invalid: yaml: content: :")),
            patch("pathlib.Path.exists", return_value=True),
        ):
            load_api_config.cache_clear()
            config = load_api_config("test.yaml")

            # Should fallback to defaults
            assert isinstance(config, APIConfig)

    def test_config_caching(self) -> None:
        """Test that configuration is cached."""
        with patch("pathlib.Path.exists", return_value=False):
            load_api_config.cache_clear()

            config1 = load_api_config()
            config2 = load_api_config()

            # Should return the same instance (cached)
            assert config1 is config2

    def test_reload_config_clears_cache(self) -> None:
        """Test that reload_config clears the cache."""
        with patch("pathlib.Path.exists", return_value=False):
            load_api_config.cache_clear()

            load_api_config()
            config2 = reload_config()

            # After reload, should potentially be different instances
            assert isinstance(config2, APIConfig)


class TestConvenienceAccessors:
    """Test convenience accessor functions."""

    def test_get_api_config(self) -> None:
        """Test get_api_config accessor."""
        config = get_api_config()
        assert isinstance(config, APIConfig)

    def test_get_cors_config(self) -> None:
        """Test get_cors_config accessor."""
        config = get_cors_config()
        assert isinstance(config, CORSConfig)

    def test_get_rate_limit(self) -> None:
        """Test get_rate_limit accessor."""
        default = get_rate_limit()
        assert isinstance(default, RateLimitConfig)

        admin = get_rate_limit("admin")
        assert isinstance(admin, RateLimitConfig)
        assert admin.requests_per_minute > default.requests_per_minute

        # Non-existent type should fallback to default
        fallback = get_rate_limit("nonexistent")
        assert isinstance(fallback, RateLimitConfig)

    def test_get_timeout_config(self) -> None:
        """Test get_timeout_config accessor."""
        config = get_timeout_config()
        assert isinstance(config, TimeoutConfig)

    def test_get_pagination_config(self) -> None:
        """Test get_pagination_config accessor."""
        config = get_pagination_config()
        assert isinstance(config, PaginationConfig)

    def test_get_upload_config(self) -> None:
        """Test get_upload_config accessor."""
        config = get_upload_config()
        assert isinstance(config, UploadConfig)

    def test_get_logging_config(self) -> None:
        """Test get_logging_config accessor."""
        config = get_logging_config()
        assert isinstance(config, LoggingConfig)


class TestEnvironmentVariableOverrides:
    """Test environment variable override functionality."""

    def test_env_override_not_applied_without_prefix(self) -> None:
        """Test that env vars without correct prefix are ignored."""
        os.environ["RANDOM_VAR"] = "should_be_ignored"

        load_api_config.cache_clear()
        config = load_api_config()

        # Config should use defaults, not the random env var
        assert isinstance(config, APIConfig)

        # Clean up
        del os.environ["RANDOM_VAR"]


@pytest.fixture(autouse=True)
def clear_cache_after_test() -> Generator[None, None, None]:
    """Clear configuration cache after each test."""
    yield
    load_api_config.cache_clear()
