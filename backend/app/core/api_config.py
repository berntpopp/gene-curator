"""
YAML-based API configuration for deployment-specific settings.

This module provides type-safe loading of API configuration from YAML files
with environment variable overrides. It follows modern Python best practices:
- Type safety via Pydantic v2
- Immutable configuration with caching
- Clear separation of concerns (API vs schema configuration)
- DRY principle with constants module

Best Practices:
    - Use specific accessor functions rather than direct config access
    - Configuration is loaded once and cached (immutable)
    - Environment variables override YAML values
    - Falls back to sensible defaults if YAML file is missing

Example:
    from app.core.api_config import get_cors_config, get_pagination_config

    cors = get_cors_config()
    pagination = get_pagination_config()

References:
    - pydantic-settings v2: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
    - Enhancement doc: docs/enhancements/006-simple-api-configuration.md
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from app.core.constants import (
    ADMIN_RATE_LIMIT_BURST,
    ADMIN_RATE_LIMIT_PER_MINUTE,
    ALLOWED_FILE_EXTENSIONS,
    AUTHENTICATED_RATE_LIMIT_BURST,
    AUTHENTICATED_RATE_LIMIT_PER_MINUTE,
    DEFAULT_CORS_ALLOW_CREDENTIALS,
    DEFAULT_CORS_EXPOSED_HEADERS,
    DEFAULT_CORS_HEADERS,
    DEFAULT_CORS_METHODS,
    DEFAULT_CORS_ORIGINS_DEV,
    DEFAULT_PAGE_SIZE,
    DEFAULT_RATE_LIMIT_BURST,
    DEFAULT_RATE_LIMIT_PER_MINUTE,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    EXTERNAL_API_TIMEOUT_SECONDS,
    GENES_DEFAULT_LIMIT,
    GENES_MAX_LIMIT,
    LOGS_DEFAULT_LIMIT,
    LOGS_MAX_LIMIT,
    LONG_RUNNING_OPERATION_TIMEOUT_SECONDS,
    MAX_FILE_SIZE_MB,
    MAX_PAGE_SIZE,
    MIN_PAGE_SIZE,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


# ========================================
# PYDANTIC MODELS FOR TYPE-SAFE CONFIG
# ========================================


class CORSConfig(BaseModel):
    """
    CORS (Cross-Origin Resource Sharing) configuration.

    Controls which origins can access the API from browsers.
    Essential for frontend-backend communication.
    """

    allow_origins: list[str] = Field(
        default_factory=lambda: DEFAULT_CORS_ORIGINS_DEV,
        description="List of allowed origins (frontend URLs)",
    )
    allow_credentials: bool = Field(
        default=DEFAULT_CORS_ALLOW_CREDENTIALS,
        description="Allow credentials (cookies, auth headers)",
    )
    allow_methods: list[str] = Field(
        default_factory=lambda: DEFAULT_CORS_METHODS.copy(),
        description="Allowed HTTP methods",
    )
    allow_headers: list[str] = Field(
        default_factory=lambda: DEFAULT_CORS_HEADERS.copy(),
        description="Allowed request headers",
    )
    expose_headers: list[str] = Field(
        default_factory=lambda: DEFAULT_CORS_EXPOSED_HEADERS.copy(),
        description="Headers exposed to frontend",
    )

    @field_validator("allow_origins")
    @classmethod
    def validate_origins(cls, v: list[str]) -> list[str]:
        """Ensure origins don't have trailing slashes."""
        return [origin.rstrip("/") for origin in v]


class RateLimitConfig(BaseModel):
    """
    Rate limiting configuration for a specific user type.

    Prevents API abuse by limiting requests per time window.
    """

    requests_per_minute: int = Field(
        default=DEFAULT_RATE_LIMIT_PER_MINUTE,
        ge=1,
        description="Maximum requests per minute",
    )
    burst_size: int = Field(
        default=DEFAULT_RATE_LIMIT_BURST, ge=1, description="Burst allowance"
    )


class TimeoutConfig(BaseModel):
    """
    Timeout configuration for various operation types.

    Different operations have different timeout requirements.
    """

    default_seconds: int = Field(
        default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
        ge=1,
        description="Default request timeout",
    )
    long_running_seconds: int = Field(
        default=LONG_RUNNING_OPERATION_TIMEOUT_SECONDS,
        ge=1,
        description="Timeout for bulk operations",
    )
    external_api_seconds: int = Field(
        default=EXTERNAL_API_TIMEOUT_SECONDS,
        ge=1,
        description="Timeout for external API calls",
    )
    database_query_seconds: int = Field(
        default=30, ge=1, description="Database query timeout"
    )
    file_upload_seconds: int = Field(
        default=60, ge=1, description="File upload timeout"
    )


class PaginationResourceConfig(BaseModel):
    """Pagination configuration for a specific resource type."""

    default: int = Field(ge=1, description="Default page size")
    max: int = Field(ge=1, description="Maximum page size")

    @field_validator("max")
    @classmethod
    def validate_max_ge_default(cls, v: int, info: Any) -> int:
        """Ensure max is greater than or equal to default."""
        if "default" in info.data and v < info.data["default"]:
            raise ValueError("max must be >= default")
        return v


class PaginationConfig(BaseModel):
    """
    Pagination configuration for list endpoints.

    Controls how many items are returned per page.
    """

    default_page_size: int = Field(
        default=DEFAULT_PAGE_SIZE, ge=1, description="Default items per page"
    )
    max_page_size: int = Field(
        default=MAX_PAGE_SIZE, ge=1, description="Maximum items per page"
    )
    min_page_size: int = Field(
        default=MIN_PAGE_SIZE, ge=1, description="Minimum items per page"
    )

    # Resource-specific pagination
    genes: PaginationResourceConfig = Field(
        default_factory=lambda: PaginationResourceConfig(
            default=GENES_DEFAULT_LIMIT, max=GENES_MAX_LIMIT
        )
    )
    logs: PaginationResourceConfig = Field(
        default_factory=lambda: PaginationResourceConfig(
            default=LOGS_DEFAULT_LIMIT, max=LOGS_MAX_LIMIT
        )
    )
    search: PaginationResourceConfig = Field(
        default_factory=lambda: PaginationResourceConfig(default=50, max=500)
    )


class UploadConfig(BaseModel):
    """
    File upload configuration.

    Controls file size limits and allowed file types.
    """

    max_file_size_mb: int = Field(
        default=MAX_FILE_SIZE_MB, ge=1, le=100, description="Max file size in MB"
    )
    allowed_extensions: list[str] = Field(
        default_factory=lambda: ALLOWED_FILE_EXTENSIONS.copy(),
        description="Allowed file extensions",
    )
    upload_dir: str = Field(default="./uploads", description="Upload directory path")
    validate_content: bool = Field(
        default=True, description="Validate file content (not just extension)"
    )
    max_filename_length: int = Field(
        default=255, ge=1, le=1000, description="Maximum filename length"
    )

    @field_validator("allowed_extensions")
    @classmethod
    def validate_extensions(cls, v: list[str]) -> list[str]:
        """Ensure extensions start with a dot."""
        return [ext if ext.startswith(".") else f".{ext}" for ext in v]


class LoggingConfig(BaseModel):
    """
    Logging system configuration.

    Controls log retention and query limits.
    """

    retention_days: int = Field(default=90, ge=30, le=365, description="Log retention")
    min_retention_days: int = Field(default=30, ge=1, description="Minimum retention")
    max_retention_days: int = Field(default=365, ge=30, description="Maximum retention")
    default_time_window_hours: int = Field(
        default=24, ge=1, description="Default log query window"
    )
    max_time_window_hours: int = Field(
        default=168, ge=1, description="Maximum log query window"
    )
    max_export_limit: int = Field(
        default=100000, ge=1000, description="Maximum logs to export"
    )
    recent_errors_default_limit: int = Field(
        default=20, ge=1, description="Default recent errors limit"
    )
    recent_errors_max_limit: int = Field(
        default=100, ge=1, description="Maximum recent errors limit"
    )


class DatabaseConfig(BaseModel):
    """
    Database connection pool configuration.

    Controls how the application manages database connections.
    """

    pool_size: int = Field(default=5, ge=1, description="Connection pool size")
    max_overflow: int = Field(default=10, ge=0, description="Max overflow connections")
    pool_timeout: int = Field(default=30, ge=1, description="Pool timeout (seconds)")
    pool_recycle: int = Field(
        default=3600, ge=60, description="Pool recycle time (seconds)"
    )
    echo: bool = Field(default=False, description="Echo SQL queries (debug)")


class SecurityConfig(BaseModel):
    """
    Security-related configuration.

    JWT tokens, passwords, and session settings.
    """

    access_token_expire_minutes: int = Field(
        default=30, ge=1, description="Access token expiration"
    )
    refresh_token_expire_days: int = Field(
        default=7, ge=1, description="Refresh token expiration"
    )
    min_password_length: int = Field(
        default=8, ge=6, description="Minimum password length"
    )
    max_password_length: int = Field(
        default=128, ge=8, description="Maximum password length"
    )
    session_timeout_minutes: int = Field(
        default=60, ge=1, description="Session timeout"
    )
    max_concurrent_sessions: int = Field(
        default=5, ge=1, description="Max concurrent sessions per user"
    )


class BulkOperationsConfig(BaseModel):
    """
    Configuration for bulk data operations.

    Controls batch sizes and parallelization.
    """

    max_genes_create: int = Field(
        default=1000, ge=1, description="Max genes in bulk create"
    )
    default_batch_size: int = Field(
        default=100, ge=1, description="Default batch size"
    )
    enable_parallel: bool = Field(default=True, description="Enable parallel processing")
    parallel_workers: int = Field(
        default=4, ge=1, le=16, description="Number of parallel workers"
    )


class ExternalAPIHGNCConfig(BaseModel):
    """HGNC API specific configuration."""

    base_url: str = Field(default="https://rest.genenames.org")
    timeout_seconds: int = Field(default=10, ge=1)
    retry_attempts: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=1, ge=0)


class ExternalAPIsConfig(BaseModel):
    """
    External API integration configuration.

    Settings for calling external services like HGNC.
    """

    hgnc: ExternalAPIHGNCConfig = Field(default_factory=ExternalAPIHGNCConfig)
    enabled: bool = Field(default=True, description="Enable external API calls")
    cache_enabled: bool = Field(default=True, description="Cache API responses")
    cache_ttl_seconds: int = Field(default=3600, ge=60, description="Cache TTL")


class PerformanceConfig(BaseModel):
    """
    Performance monitoring configuration.

    Controls performance tracking and alerting.
    """

    enabled: bool = Field(default=True, description="Enable performance monitoring")
    slow_operation_threshold_ms: int = Field(
        default=1000, ge=100, description="Slow operation threshold"
    )
    track_db_queries: bool = Field(
        default=True, description="Track database query performance"
    )
    track_external_apis: bool = Field(
        default=True, description="Track external API performance"
    )


class FeatureFlagsConfig(BaseModel):
    """
    Feature flags for toggling functionality.

    Enable/disable features without code changes.
    """

    enable_docs_in_production: bool = Field(
        default=False, description="Show API docs in production"
    )
    enable_debug_endpoints: bool = Field(
        default=False, description="Enable debug endpoints"
    )
    enable_experimental: bool = Field(
        default=False, description="Enable experimental features"
    )
    enable_rate_limiting: bool = Field(
        default=False, description="Enable rate limiting"
    )
    enable_request_correlation: bool = Field(
        default=True, description="Enable request correlation tracking"
    )


class APIConfig(BaseModel):
    """
    Complete API configuration container.

    This is the top-level configuration object that contains all
    API-related settings. It's loaded from YAML and cached.
    """

    cors: CORSConfig = Field(default_factory=CORSConfig)
    rate_limits: dict[str, RateLimitConfig] = Field(
        default_factory=lambda: {
            "default": RateLimitConfig(
                requests_per_minute=DEFAULT_RATE_LIMIT_PER_MINUTE,
                burst_size=DEFAULT_RATE_LIMIT_BURST,
            ),
            "authenticated": RateLimitConfig(
                requests_per_minute=AUTHENTICATED_RATE_LIMIT_PER_MINUTE,
                burst_size=AUTHENTICATED_RATE_LIMIT_BURST,
            ),
            "curator": RateLimitConfig(requests_per_minute=500, burst_size=75),
            "admin": RateLimitConfig(
                requests_per_minute=ADMIN_RATE_LIMIT_PER_MINUTE,
                burst_size=ADMIN_RATE_LIMIT_BURST,
            ),
        }
    )
    timeouts: TimeoutConfig = Field(default_factory=TimeoutConfig)
    pagination: PaginationConfig = Field(default_factory=PaginationConfig)
    uploads: UploadConfig = Field(default_factory=UploadConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    bulk_operations: BulkOperationsConfig = Field(
        default_factory=BulkOperationsConfig
    )
    external_apis: ExternalAPIsConfig = Field(default_factory=ExternalAPIsConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    features: FeatureFlagsConfig = Field(default_factory=FeatureFlagsConfig)


# ========================================
# CONFIGURATION LOADER
# ========================================


@lru_cache(maxsize=1)
def load_api_config(config_file: str | None = None) -> APIConfig:
    """
    Load API configuration from YAML file with caching.

    The configuration is loaded once and cached for the lifetime of the
    application. Environment variables can override YAML values.

    Args:
        config_file: Path to YAML config file. If None, uses default location.

    Returns:
        APIConfig: Loaded and validated configuration.

    Raises:
        ValueError: If configuration validation fails.

    Example:
        >>> config = load_api_config()
        >>> print(config.cors.allow_origins)
        ['http://localhost:3051', 'http://localhost:5193']
    """
    if config_file is None:
        # Default config location
        config_file = str(Path(__file__).parent.parent.parent / "config" / "api.yaml")

    config_path = Path(config_file)

    # If config file doesn't exist, use defaults
    if not config_path.exists():
        logger.warning(
            "API config file not found, using defaults",
            config_path=str(config_path),
        )
        return APIConfig()

    try:
        # Load YAML configuration
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None or "api" not in data:
            logger.warning(
                "Invalid config file structure, using defaults",
                config_path=str(config_path),
            )
            return APIConfig()

        # Support environment variable overrides
        config_data = data["api"]
        _apply_env_overrides(config_data)

        # Validate and create config object
        config = APIConfig(**config_data)

        logger.info(
            "API configuration loaded successfully",
            config_path=str(config_path),
            cors_origins=len(config.cors.allow_origins),
            rate_limit_tiers=len(config.rate_limits),
        )

        return config

    except Exception as e:
        logger.error(
            "Failed to load API configuration, using defaults",
            config_path=str(config_path),
            error=str(e),
        )
        return APIConfig()


def _apply_env_overrides(config_data: dict[str, Any]) -> None:
    """
    Apply environment variable overrides to configuration.

    Environment variables follow the pattern:
        GENE_CURATOR_API__<section>__<key>

    Examples:
        GENE_CURATOR_API__CORS__ALLOW_ORIGINS='["https://prod.example.com"]'
        GENE_CURATOR_API__PAGINATION__DEFAULT_PAGE_SIZE=100

    Args:
        config_data: Configuration dictionary to modify in-place.
    """
    prefix = "GENE_CURATOR_API__"

    for env_key, env_value in os.environ.items():
        if not env_key.startswith(prefix):
            continue

        # Parse environment variable key
        # Example: GENE_CURATOR_API__CORS__ALLOW_ORIGINS -> ["cors", "allow_origins"]
        parts = env_key[len(prefix) :].lower().split("__")

        if len(parts) < 2:
            continue

        section = parts[0]
        key = "_".join(parts[1:])

        if section not in config_data:
            continue

        # Try to parse as JSON first (for lists/dicts)
        try:
            import json

            parsed_value = json.loads(env_value)
            config_data[section][key] = parsed_value
            logger.debug(
                "Applied environment variable override",
                env_key=env_key,
                section=section,
                key=key,
            )
        except (json.JSONDecodeError, ValueError):
            # Not JSON, use as string
            config_data[section][key] = env_value
            logger.debug(
                "Applied environment variable override (string)",
                env_key=env_key,
                section=section,
                key=key,
            )


# ========================================
# CONVENIENCE ACCESSOR FUNCTIONS
# ========================================


def get_api_config() -> APIConfig:
    """Get complete API configuration."""
    return load_api_config()


def get_cors_config() -> CORSConfig:
    """Get CORS configuration."""
    return load_api_config().cors


def get_rate_limit(limit_type: str = "default") -> RateLimitConfig:
    """
    Get rate limit configuration for specific user type.

    Args:
        limit_type: Type of rate limit (default, authenticated, curator, admin).

    Returns:
        RateLimitConfig for the requested type, falls back to default.
    """
    config = load_api_config()
    return config.rate_limits.get(limit_type, config.rate_limits["default"])


def get_timeout_config() -> TimeoutConfig:
    """Get timeout configuration."""
    return load_api_config().timeouts


def get_pagination_config() -> PaginationConfig:
    """Get pagination configuration."""
    return load_api_config().pagination


def get_upload_config() -> UploadConfig:
    """Get file upload configuration."""
    return load_api_config().uploads


def get_logging_config() -> LoggingConfig:
    """Get logging configuration."""
    return load_api_config().logging


def get_database_config() -> DatabaseConfig:
    """Get database configuration."""
    return load_api_config().database


def get_security_config() -> SecurityConfig:
    """Get security configuration."""
    return load_api_config().security


def get_bulk_operations_config() -> BulkOperationsConfig:
    """Get bulk operations configuration."""
    return load_api_config().bulk_operations


def get_external_apis_config() -> ExternalAPIsConfig:
    """Get external APIs configuration."""
    return load_api_config().external_apis


def get_performance_config() -> PerformanceConfig:
    """Get performance monitoring configuration."""
    return load_api_config().performance


def get_feature_flags() -> FeatureFlagsConfig:
    """Get feature flags configuration."""
    return load_api_config().features


def reload_config() -> APIConfig:
    """
    Force reload of configuration (clears cache).

    Use this sparingly, typically only in tests or when configuration
    needs to be updated at runtime.

    Returns:
        Newly loaded APIConfig.
    """
    load_api_config.cache_clear()
    return load_api_config()
