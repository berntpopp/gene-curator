"""
Application configuration using Pydantic Settings.

Enhanced with YAML-based configuration and constants module for better
maintainability and deployment flexibility.
"""

from pydantic import validator
from pydantic_settings import BaseSettings

from app.core.constants import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
    CLINGEN_SOP_VERSION,
    CLINGEN_TEMPLATE_VERSION,
    DEFAULT_EMAIL_FROM,
    DEFAULT_HOST,
    DEFAULT_LOG_LEVEL,
    DEFAULT_PORT,
    DEFAULT_SMTP_PORT,
    JWT_ALGORITHM,
    MAX_FILE_SIZE_BYTES,
)


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    This class provides base configuration loaded from environment variables.
    For API-specific configuration (CORS, rate limits, etc.), use api_config.py.

    Separation of Concerns:
        - Settings: Core app config (database, secrets, environment)
        - api_config: API-level config (CORS, pagination, timeouts)
        - constants: Immutable application constants
    """

    # ========================================
    # APPLICATION METADATA
    # ========================================
    APP_NAME: str = APP_NAME
    APP_VERSION: str = APP_VERSION
    APP_DESCRIPTION: str = APP_DESCRIPTION

    # ========================================
    # DATABASE SETTINGS
    # ========================================
    DATABASE_URL: str

    # ========================================
    # SECURITY SETTINGS
    # ========================================
    SECRET_KEY: str
    ALGORITHM: str = JWT_ALGORITHM
    ACCESS_TOKEN_EXPIRE_MINUTES: int = ACCESS_TOKEN_EXPIRE_MINUTES

    # ========================================
    # APPLICATION SETTINGS
    # ========================================
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    LOG_LEVEL: str = DEFAULT_LOG_LEVEL
    HOST: str = DEFAULT_HOST  # nosec B104 - Default for Docker, override with HOST=127.0.0.1 for local-only
    PORT: int = DEFAULT_PORT  # Override with BACKEND_PORT in .env

    # ========================================
    # CLINGEN SETTINGS
    # ========================================
    CLINGEN_SOP_VERSION: str = CLINGEN_SOP_VERSION
    CLINGEN_TEMPLATE_VERSION: str = CLINGEN_TEMPLATE_VERSION

    # ========================================
    # CORS SETTINGS (Deprecated - use api_config)
    # ========================================
    # NOTE: CORS configuration should be managed via config/api.yaml
    # This field is kept for backward compatibility but will be removed
    # in a future version. Use get_cors_config() from api_config instead.
    ALLOWED_ORIGINS: list[str] = []

    # ========================================
    # REDIS SETTINGS (OPTIONAL)
    # ========================================
    REDIS_URL: str | None = None

    # ========================================
    # FILE UPLOAD SETTINGS (Deprecated - use api_config)
    # ========================================
    # NOTE: Upload configuration should be managed via config/api.yaml
    # These fields are kept for backward compatibility.
    MAX_FILE_SIZE: int = MAX_FILE_SIZE_BYTES
    UPLOAD_DIR: str = "./uploads"

    # ========================================
    # EMAIL SETTINGS
    # ========================================
    SMTP_SERVER: str | None = None
    SMTP_PORT: int = DEFAULT_SMTP_PORT
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAIL_FROM: str = DEFAULT_EMAIL_FROM

    @validator("PORT", pre=True)
    def get_port(cls, v: int | str | None) -> int:
        """Support both PORT and BACKEND_PORT environment variables."""
        import os

        # If PORT is provided, use it
        if v is not None:
            return int(v)

        # Otherwise, check for BACKEND_PORT (for backward compatibility)
        backend_port = os.getenv("BACKEND_PORT")
        if backend_port:
            return int(backend_port)

        # Default to 8000
        return 8000

    @validator("ALLOWED_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        elif isinstance(v, str):
            # Handle JSON-like string format
            import json
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            return [v]
        raise ValueError(v)

    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith("postgresql://"):
            raise ValueError("DATABASE_URL must start with 'postgresql://'")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Create global settings instance
settings = Settings()  # type: ignore[call-arg]
