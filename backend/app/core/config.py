"""
Application configuration using Pydantic Settings.
"""

from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Database settings
    DATABASE_URL: str

    # Security settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Application settings
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    LOG_LEVEL: str = "info"
    HOST: str = "0.0.0.0"  # nosec B104 - Default for Docker, override with HOST=127.0.0.1 for local-only
    PORT: int = 8000  # Override with BACKEND_PORT in .env

    # ClinGen settings
    CLINGEN_SOP_VERSION: str = "v11"
    CLINGEN_TEMPLATE_VERSION: str = "v5.1"

    # CORS settings
    ALLOWED_ORIGINS: list[str] = []

    # Redis settings (optional)
    REDIS_URL: str | None = None

    # File upload settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "./uploads"

    # Email settings
    SMTP_SERVER: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAIL_FROM: str = "noreply@gene-curator.org"

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
        elif isinstance(v, list | str):
            return v
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
settings = Settings()
