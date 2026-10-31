"""
Application configuration using Pydantic Settings.

Enhanced with YAML-based configuration and constants module for better
maintainability and deployment flexibility.
"""

from urllib.parse import urlparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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

    # ========================================
    # LLM CREDENTIAL KEY RING (never derived from SECRET_KEY)
    # ========================================
    # JSON object {kid: fernet_key}; empty means LLM credentials are unavailable.
    LLM_CREDENTIAL_KEYS: str = ""
    LLM_CREDENTIAL_ACTIVE_KID: str = ""
    # Background LLM run worker in the API lifespan; tests turn it off.
    LLM_WORKER_ENABLED: bool = True

    # ========================================
    # MCP OAUTH (#462): public origins MCP clients and browsers reach
    # ========================================
    # OAuth issuer and MCP resource base; HTTPS in production (loopback only for tests)
    GENE_CURATOR_PUBLIC_URL: str = "http://localhost:8051"
    # Web app origin serving /oauth/consent
    GENE_CURATOR_FRONTEND_URL: str = "http://localhost:5193"

    @model_validator(mode="after")
    def public_url_is_https_in_production(self) -> "Settings":
        """Fail closed: production never advertises a plain-HTTP OAuth issuer."""
        url = urlparse(self.GENE_CURATOR_PUBLIC_URL)
        loopback = url.hostname in {"localhost", "127.0.0.1", "::1"}
        if self.ENVIRONMENT == "production" and url.scheme != "https" and not loopback:
            raise ValueError("GENE_CURATOR_PUBLIC_URL must be https:// in production")
        return self

    @model_validator(mode="after")
    def secret_key_is_strong_in_production(self) -> "Settings":
        """Fail closed: production never signs tokens with a short or placeholder key."""
        weak = len(self.SECRET_KEY) < 32 or "change" in self.SECRET_KEY.lower()
        if self.ENVIRONMENT == "production" and weak:
            raise ValueError(
                "SECRET_KEY must be at least 32 random characters in production "
                "(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
            )
        return self

    @field_validator("PORT", mode="before")
    @classmethod
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

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
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

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith("postgresql://"):
            raise ValueError("DATABASE_URL must start with 'postgresql://'")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# Create global settings instance
settings = Settings()
