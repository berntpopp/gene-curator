"""
FastAPI main application entry point.
"""

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.middleware import LoggingMiddleware

# Configure unified logging system
configure_logging(
    log_level=settings.LOG_LEVEL,
    database_enabled=True,
    console_enabled=True,
)
logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Gene Curator API",
    description="ClinGen-compliant genetic curation platform backend",
    version="2.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT == "development" else None,
)

# Add CORS middleware (first, so it wraps all responses including errors)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=False,  # Changed to False to fix CORS
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=[
        "X-Request-ID",
        "X-Process-Time",
    ],  # Expose correlation ID and timing headers
)

# Add logging middleware (second, to capture all requests after CORS)
app.add_middleware(LoggingMiddleware)


# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint providing API information."""
    return {
        "name": "Gene Curator API",
        "version": "2.0.0",
        "description": "ClinGen-compliant genetic curation platform backend",
        "environment": settings.ENVIRONMENT,
        "clingen_sop_version": settings.CLINGEN_SOP_VERSION,
        "docs_url": "/docs" if settings.ENVIRONMENT == "development" else None,
    }


# Health check endpoint
@app.get("/health")
async def health_check():
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
        "version": "2.0.0",
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
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
async def startup_event():
    logger.info(
        "Starting Gene Curator API...",
        environment=settings.ENVIRONMENT,
        database_url=settings.DATABASE_URL,
        clingen_sop_version=settings.CLINGEN_SOP_VERSION,
    )


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Gene Curator API...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
    )
