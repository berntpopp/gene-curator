"""
Health check endpoints.
"""

import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "2.0.0",
        "environment": settings.ENVIRONMENT,
    }


@router.get("/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check including database connectivity."""
    start_time = time.time()

    # Test database connection
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
        db_response_time = time.time() - start_time
    except Exception as e:
        db_status = f"unhealthy: {e!s}"
        db_response_time = None

    # Test ClinGen scoring function
    clingen_status = "healthy"
    try:
        result = db.execute(
            text(
                """
            SELECT calculate_genetic_evidence_score('{"genetic_evidence": {"case_level_data": []}}')
        """
            )
        )
        clingen_test = result.fetchone()[0] == 0.0
        if not clingen_test:
            clingen_status = "unhealthy: scoring function error"
    except Exception as e:
        clingen_status = f"unhealthy: {e!s}"

    return {
        "status": (
            "healthy"
            if db_status == "healthy" and clingen_status == "healthy"
            else "unhealthy"
        ),
        "timestamp": time.time(),
        "version": "2.0.0",
        "environment": settings.ENVIRONMENT,
        "components": {
            "database": {
                "status": db_status,
                "response_time_ms": (
                    db_response_time * 1000 if db_response_time else None
                ),
            },
            "clingen_engine": {
                "status": clingen_status,
                "sop_version": settings.CLINGEN_SOP_VERSION,
            },
        },
    }
