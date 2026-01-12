"""
FastAPI main application entry point.

Enhanced with YAML-based configuration and constants for better maintainability.
"""

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.api_config import get_cors_config, get_feature_flags
from app.core.config import settings
from app.core.constants import APP_DESCRIPTION, APP_NAME, APP_VERSION
from app.core.logging import configure_logging, get_logger
from app.middleware import LoggingMiddleware

# Configure unified logging system
configure_logging(
    log_level=settings.LOG_LEVEL,
    database_enabled=True,
    console_enabled=True,
)
logger = get_logger(__name__)

# Load feature flags
feature_flags = get_feature_flags()

# Create FastAPI application with configurable documentation URLs
app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    docs_url=(
        "/docs"
        if settings.ENVIRONMENT == "development"
        or feature_flags.enable_docs_in_production
        else None
    ),
    redoc_url=(
        "/redoc"
        if settings.ENVIRONMENT == "development"
        or feature_flags.enable_docs_in_production
        else None
    ),
    openapi_url=(
        "/openapi.json"
        if settings.ENVIRONMENT == "development"
        or feature_flags.enable_docs_in_production
        else None
    ),
)

# Load CORS configuration from YAML
cors_config = get_cors_config()

# Add CORS middleware (first, so it wraps all responses including errors)
# Configuration is now loaded from config/api.yaml
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config.allow_origins,
    allow_credentials=cors_config.allow_credentials,
    allow_methods=cors_config.allow_methods,
    allow_headers=cors_config.allow_headers,
    expose_headers=cors_config.expose_headers,
)

# Add logging middleware (second, to capture all requests after CORS)
app.add_middleware(LoggingMiddleware)


# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root() -> dict[str, str | None]:
    """Root endpoint providing API information."""
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "description": APP_DESCRIPTION,
        "environment": settings.ENVIRONMENT,
        "clingen_sop_version": settings.CLINGEN_SOP_VERSION,
        "docs_url": (
            "/docs"
            if settings.ENVIRONMENT == "development"
            or feature_flags.enable_docs_in_production
            else None
        ),
    }


# Health check endpoint
@app.get("/health")
async def health_check() -> dict[str, str | float]:
    """Health check endpoint for monitoring."""
    try:
        # Test database connection
        from sqlalchemy import text

        from app.core.database import get_db

        db = next(get_db())
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error("Database health check failed", error=e)
        db_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "timestamp": time.time(),
        "database": db_status,
        "environment": settings.ENVIRONMENT,
        "version": APP_VERSION,
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Global exception caught", error=exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": "internal_error",
            "request_id": id(request),
        },
    )


# Startup event
@app.on_event("startup")
async def startup_event() -> None:
    logger.info(
        "Starting Gene Curator API...",
        environment=settings.ENVIRONMENT,
        database_url=settings.DATABASE_URL,
        clingen_sop_version=settings.CLINGEN_SOP_VERSION,
    )


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Shutting down Gene Curator API...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
    )
