"""
FastAPI main application entry point.

Enhanced with YAML-based configuration and constants for better maintainability.
"""

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.engine import make_url

from app.api.v1.api import api_router
from app.core.api_config import get_cors_config, get_feature_flags
from app.core.config import settings
from app.core.constants import APP_DESCRIPTION, APP_NAME, APP_VERSION
from app.core.database import async_engine
from app.core.logging import configure_logging, get_logger
from app.core.logging.database_logger import get_database_logger
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


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "Starting Gene Curator API...",
        environment=settings.ENVIRONMENT,
        database_url=make_url(settings.DATABASE_URL).render_as_string(
            hide_password=True
        ),
        clingen_sop_version=settings.CLINGEN_SOP_VERSION,
    )
    yield
    logger.info("Shutting down Gene Curator API...")
    await get_database_logger().flush()
    await async_engine.dispose()


# Create FastAPI application with configurable documentation URLs
app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
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
    # ServerErrorMiddleware sits outside CORSMiddleware, so add the headers here
    rid = getattr(request.state, "request_id", None)
    headers: dict[str, str] = {"X-Request-ID": rid} if rid else {}
    origin = request.headers.get("origin")
    if origin and origin in cors_config.allow_origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Vary"] = "Origin"
        if cors_config.expose_headers:
            headers["Access-Control-Expose-Headers"] = ", ".join(
                cors_config.expose_headers
            )
        if cors_config.allow_credentials:
            headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        headers=headers,
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": "internal_error",
            "request_id": rid,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
    )
