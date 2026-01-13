"""
Application-wide constants and magic numbers.

This module centralizes all hardcoded values to follow DRY principles and
make configuration management easier. Values are organized by domain.

Best Practice: Import specific constants rather than the entire module
to make dependencies explicit.

Example:
    from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
"""

# ========================================
# APPLICATION METADATA
# ========================================

APP_NAME = "Gene Curator API"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "Schema-agnostic genetic curation platform backend"

# ========================================
# PAGINATION DEFAULTS
# ========================================

DEFAULT_PAGE_SIZE = 50
"""Default number of items per page for list endpoints."""

MAX_PAGE_SIZE = 1000
"""Maximum number of items that can be requested per page."""

MIN_PAGE_SIZE = 1
"""Minimum number of items per page."""

DEFAULT_SKIP = 0
"""Default number of records to skip (for pagination)."""

# Common pagination limits for different resource types
GENES_DEFAULT_LIMIT = 100
"""Default limit for gene list endpoints."""

GENES_MAX_LIMIT = 500
"""Maximum limit for gene list endpoints."""

LOGS_DEFAULT_LIMIT = 100
"""Default limit for log list endpoints."""

LOGS_MAX_LIMIT = 1000
"""Maximum limit for log list endpoints."""

LOGS_EXPORT_MAX_LIMIT = 100000
"""Maximum limit for log export operations."""

LOGS_RECENT_ERRORS_DEFAULT_LIMIT = 20
"""Default limit for recent errors endpoint."""

LOGS_RECENT_ERRORS_MAX_LIMIT = 100
"""Maximum limit for recent errors endpoint."""

REVIEWS_DEFAULT_LIMIT = 50
"""Default limit for review list endpoints."""

REVIEWS_MAX_LIMIT = 200
"""Maximum limit for review list endpoints."""

ASSIGNMENTS_DEFAULT_LIMIT = 100
"""Default limit for gene assignment endpoints."""

ASSIGNMENTS_MAX_LIMIT = 1000
"""Maximum limit for gene assignment endpoints."""

CURATIONS_DEFAULT_LIMIT = 50
"""Default limit for curation list endpoints."""

CURATIONS_MAX_LIMIT = 500
"""Maximum limit for curation list endpoints."""

PRECURATIONS_DEFAULT_LIMIT = 50
"""Default limit for precuration list endpoints."""

PRECURATIONS_MAX_LIMIT = 200
"""Maximum limit for precuration list endpoints."""

MAX_OVERVIEW_LIMIT = 10000
"""Maximum limit for overview/analytics endpoints."""

# ========================================
# TIME AND DURATION
# ========================================

# Time unit conversions
SECONDS_PER_MINUTE = 60
"""Number of seconds in one minute."""

MILLISECONDS_PER_SECOND = 1000
"""Number of milliseconds in one second."""

DEFAULT_REQUEST_TIMEOUT_SECONDS = 30
"""Default timeout for API requests in seconds."""

LONG_RUNNING_OPERATION_TIMEOUT_SECONDS = 300
"""Timeout for long-running operations (5 minutes) in seconds."""

EXTERNAL_API_TIMEOUT_SECONDS = 10
"""Timeout for external API calls in seconds."""

ACCESS_TOKEN_EXPIRE_MINUTES = 30
"""JWT access token expiration time in minutes."""

REFRESH_TOKEN_EXPIRE_DAYS = 7
"""JWT refresh token expiration time in days."""

LOGS_DEFAULT_TIME_WINDOW_HOURS = 24
"""Default time window for log queries in hours."""

LOGS_MIN_TIME_WINDOW_HOURS = 1
"""Minimum time window for log queries in hours."""

LOGS_MAX_TIME_WINDOW_HOURS = 168
"""Maximum time window for log queries (7 days) in hours."""

LOG_RETENTION_MIN_DAYS = 30
"""Minimum log retention period in days."""

LOG_RETENTION_DEFAULT_DAYS = 90
"""Default log retention period in days."""

LOG_RETENTION_MAX_DAYS = 365
"""Maximum log retention period in days."""

# Statistics and analytics time windows
DEFAULT_STATS_DAYS = 30
"""Default time window for statistics queries in days."""

MIN_STATS_DAYS = 1
"""Minimum time window for statistics queries in days."""

MAX_STATS_DAYS = 365
"""Maximum time window for statistics queries in days."""

DEFAULT_ANALYTICS_DAYS = 90
"""Default time window for analytics queries in days."""

# ========================================
# FILE UPLOAD LIMITS
# ========================================

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
"""Maximum file upload size in bytes (10 MB)."""

MAX_FILE_SIZE_MB = 10
"""Maximum file upload size in megabytes."""

ALLOWED_FILE_EXTENSIONS = [".xlsx", ".csv", ".json"]
"""Allowed file extensions for uploads."""

# ========================================
# RATE LIMITING
# ========================================

DEFAULT_RATE_LIMIT_PER_MINUTE = 60
"""Default rate limit for unauthenticated users (requests per minute)."""

DEFAULT_RATE_LIMIT_BURST = 10
"""Default burst size for rate limiting."""

AUTHENTICATED_RATE_LIMIT_PER_MINUTE = 300
"""Rate limit for authenticated users (requests per minute)."""

AUTHENTICATED_RATE_LIMIT_BURST = 50
"""Burst size for authenticated users."""

ADMIN_RATE_LIMIT_PER_MINUTE = 1000
"""Rate limit for admin users (requests per minute)."""

ADMIN_RATE_LIMIT_BURST = 100
"""Burst size for admin users."""

# ========================================
# DATABASE SETTINGS
# ========================================

DB_POOL_SIZE = 5
"""Database connection pool size."""

DB_MAX_OVERFLOW = 10
"""Maximum overflow connections in database pool."""

DB_POOL_TIMEOUT = 30
"""Database pool connection timeout in seconds."""

DB_POOL_RECYCLE = 3600
"""Database pool recycle time in seconds (1 hour)."""

# ========================================
# CLINGEN SETTINGS
# ========================================

CLINGEN_SOP_VERSION = "v11"
"""ClinGen Standard Operating Procedures version."""

CLINGEN_TEMPLATE_VERSION = "v5.1"
"""ClinGen template version."""

# ========================================
# HTTP STATUS CODES
# ========================================

HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_204_NO_CONTENT = 204
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404
HTTP_422_UNPROCESSABLE_ENTITY = 422
HTTP_500_INTERNAL_SERVER_ERROR = 500

# ========================================
# CORS SETTINGS
# ========================================

DEFAULT_CORS_ALLOW_CREDENTIALS = False
"""Default CORS allow credentials setting."""

DEFAULT_CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
"""Default allowed HTTP methods for CORS."""

DEFAULT_CORS_HEADERS = ["*"]
"""Default allowed headers for CORS."""

DEFAULT_CORS_EXPOSED_HEADERS = ["X-Request-ID", "X-Process-Time"]
"""Default exposed headers for CORS."""

# Development CORS origins (non-standard ports to avoid conflicts)
DEFAULT_CORS_ORIGINS_DEV = [
    "http://localhost:3051",  # Frontend Docker
    "http://localhost:5193",  # Vite dev server (non-standard)
    "http://localhost:8051",  # Backend API (non-standard)
]
"""Default CORS origins for development environment."""

# ========================================
# LOGGING SETTINGS
# ========================================

LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"
LOG_LEVEL_CRITICAL = "CRITICAL"

DEFAULT_LOG_LEVEL = LOG_LEVEL_INFO
"""Default application log level."""

# ========================================
# VALIDATION LIMITS
# ========================================

MIN_PASSWORD_LENGTH = 8
"""Minimum password length for user accounts."""

MAX_PASSWORD_LENGTH = 128
"""Maximum password length for user accounts."""

MIN_USERNAME_LENGTH = 3
"""Minimum username length."""

MAX_USERNAME_LENGTH = 50
"""Maximum username length."""

MAX_EMAIL_LENGTH = 255
"""Maximum email address length."""

MAX_STRING_FIELD_LENGTH = 255
"""Maximum length for standard string fields."""

MAX_TEXT_FIELD_LENGTH = 10000
"""Maximum length for text fields."""

# ========================================
# SEARCH AND QUERY
# ========================================

MIN_SEARCH_QUERY_LENGTH = 2
"""Minimum length for search queries."""

MAX_SEARCH_QUERY_LENGTH = 100
"""Maximum length for search queries."""

DEFAULT_SEARCH_LIMIT = 50
"""Default limit for search results."""

MAX_SEARCH_LIMIT = 500
"""Maximum limit for search results."""

# Default filter settings
DEFAULT_ACTIVE_ONLY_FILTER = True
"""Default value for active-only filtering in list endpoints."""

DEFAULT_INCLUDE_ARCHIVED = False
"""Default value for including archived items in queries."""

# ========================================
# CHROMOSOMES
# ========================================

VALID_CHROMOSOMES = [str(i) for i in range(1, 23)] + ["X", "Y", "M"]
"""Valid human chromosome designations."""

# ========================================
# SORTING
# ========================================

DEFAULT_SORT_ORDER = "asc"
"""Default sort order (ascending)."""

VALID_SORT_ORDERS = ["asc", "desc"]
"""Valid sort order values."""

DEFAULT_GENE_SORT_FIELD = "approved_symbol"
"""Default field for sorting gene lists."""

# ========================================
# EXPORT FORMATS
# ========================================

EXPORT_FORMAT_JSON = "json"
EXPORT_FORMAT_CSV = "csv"
VALID_EXPORT_FORMATS = [EXPORT_FORMAT_JSON, EXPORT_FORMAT_CSV]
"""Valid export format options."""

# ========================================
# ALGORITHM AND ENCODING
# ========================================

JWT_ALGORITHM = "HS256"
"""JWT token signing algorithm."""

PASSWORD_HASH_ALGORITHM = "bcrypt"  # noqa: S105  # nosec B105 - Algorithm name, not a password
"""Password hashing algorithm."""

# ========================================
# NETWORK SETTINGS
# ========================================

DEFAULT_HOST = "0.0.0.0"  # nosec B104 - Default for Docker
"""Default host binding (0.0.0.0 for Docker, override with 127.0.0.1 for local-only)."""

DEFAULT_PORT = 8000
"""Default API server port."""

DEFAULT_BACKEND_PORT = 8051
"""Default backend port (non-standard to avoid conflicts)."""

# ========================================
# EMAIL SETTINGS
# ========================================

DEFAULT_SMTP_PORT = 587
"""Default SMTP port for email sending."""

DEFAULT_EMAIL_FROM = "noreply@gene-curator.org"
"""Default sender email address."""

# ========================================
# REDIS SETTINGS
# ========================================

REDIS_DEFAULT_PORT = 6379
"""Default Redis port."""

REDIS_DEFAULT_DB = 0
"""Default Redis database number."""

REDIS_DEFAULT_TIMEOUT = 5
"""Default Redis operation timeout in seconds."""

# ========================================
# BULK OPERATIONS
# ========================================

MAX_BULK_GENE_CREATE = 1000
"""Maximum number of genes that can be created in a single bulk operation."""

DEFAULT_BULK_GENE_CREATE = 100
"""Default batch size for bulk gene creation."""
