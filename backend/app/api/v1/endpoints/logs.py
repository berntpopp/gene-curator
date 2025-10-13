"""
System logs API endpoints for monitoring and debugging.

These endpoints provide access to system logs with request correlation,
statistics, and export capabilities. Access is restricted to admin and
reviewer roles.
"""

import csv
import io
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.crud import logs as crud_logs
from app.models.models import UserNew, UserRoleNew
from app.schemas.logs import LogEntry, LogStatsSummary

router = APIRouter()


def require_admin_or_reviewer(current_user: UserNew = Depends(get_current_active_user)):
    """
    Dependency to check if user is admin or reviewer.

    Args:
        current_user: Current authenticated user

    Returns:
        User if they have admin or reviewer role

    Raises:
        HTTPException: If user doesn't have required permissions
    """
    if current_user.role not in [UserRoleNew.ADMIN, UserRoleNew.REVIEWER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Reviewer access required to view logs",
        )
    return current_user


def require_admin(current_user: UserNew = Depends(get_current_active_user)):
    """
    Dependency to check if user is admin.

    Args:
        current_user: Current authenticated user

    Returns:
        User if they have admin role

    Raises:
        HTTPException: If user doesn't have required permissions
    """
    if current_user.role != UserRoleNew.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for this operation",
        )
    return current_user


@router.get("/", response_model=list[LogEntry])
async def search_logs(
    level: str | None = Query(None, description="Filter by log level"),
    logger_name: str | None = Query(
        None, description="Filter by logger name (partial match)"
    ),
    message: str | None = Query(None, description="Search in message (partial match)"),
    request_id: str | None = Query(None, description="Filter by request ID"),
    user_id: str | None = Query(None, description="Filter by user ID"),
    endpoint: str | None = Query(
        None, description="Filter by endpoint (partial match)"
    ),
    method: str | None = Query(None, description="Filter by HTTP method"),
    start_date: datetime | None = Query(None, description="Start date (inclusive)"),
    end_date: datetime | None = Query(None, description="End date (inclusive)"),
    min_duration_ms: float | None = Query(
        None, description="Minimum duration in milliseconds"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: UserNew = Depends(require_admin_or_reviewer),
) -> Any:
    """
    Search and filter system logs.

    This endpoint allows comprehensive filtering of system logs for monitoring
    and debugging. All filters are optional and can be combined.

    **Required Role:** Admin or Reviewer

    **Example queries:**
    - All errors: `?level=ERROR`
    - Slow operations: `?min_duration_ms=1000`
    - Specific user's activity: `?user_id=uuid`
    - Time range: `?start_date=2025-01-15T00:00:00Z&end_date=2025-01-15T23:59:59Z`
    """
    logs = await crud_logs.get_logs(
        db=db,
        skip=skip,
        limit=limit,
        level=level,
        logger_name=logger_name,
        message=message,
        request_id=request_id,
        user_id=user_id,
        endpoint=endpoint,
        method=method,
        start_date=start_date,
        end_date=end_date,
        min_duration_ms=min_duration_ms,
    )
    return logs


@router.get("/{log_id}", response_model=LogEntry)
async def get_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserNew = Depends(require_admin_or_reviewer),
) -> Any:
    """
    Get a specific log entry by ID.

    **Required Role:** Admin or Reviewer
    """
    log = await crud_logs.get_log_by_id(db=db, log_id=log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Log entry with ID {log_id} not found",
        )
    return log


@router.get("/request/{request_id}", response_model=list[LogEntry])
async def get_logs_by_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserNew = Depends(require_admin_or_reviewer),
) -> Any:
    """
    Get all logs for a specific request (request correlation).

    This is the key endpoint for request correlation - shows all logs
    that occurred during a single API request, ordered by timestamp.

    **Required Role:** Admin or Reviewer

    **Use case:** When debugging an issue, use the X-Request-ID header
    from the API response to fetch all logs for that request.
    """
    logs = await crud_logs.get_logs_by_request_id(db=db, request_id=request_id)
    if not logs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No logs found for request ID: {request_id}",
        )
    return logs


@router.get("/stats/summary", response_model=LogStatsSummary)
async def get_log_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: UserNew = Depends(require_admin),
) -> Any:
    """
    Get comprehensive log statistics dashboard.

    Returns statistics including:
    - Total logs count
    - Logs by level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - Logs by hour (last 24 hours)
    - Average operation duration
    - Top 5 slowest endpoints
    - Error rate
    - Top 5 most common errors

    **Required Role:** Admin only

    **Use case:** Admin dashboard for system health monitoring.
    """
    stats = await crud_logs.get_log_statistics(db=db)
    return stats


@router.get("/recent-errors", response_model=list[LogEntry])
async def get_recent_errors(
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of errors to return"
    ),
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    db: AsyncSession = Depends(get_db),
    current_user: UserNew = Depends(require_admin_or_reviewer),
) -> Any:
    """
    Get recent error and critical logs for triage.

    Returns the most recent ERROR and CRITICAL level logs within the
    specified time window, ordered by most recent first.

    **Required Role:** Admin or Reviewer

    **Use case:** Quick triage of recent system errors.
    """
    logs = await crud_logs.get_recent_errors(db=db, limit=limit, hours=hours)
    return logs


@router.get("/export")
async def export_logs(
    format: str = Query(
        "json", regex="^(json|csv)$", description="Export format (json or csv)"
    ),
    level: str | None = Query(None, description="Filter by log level"),
    start_date: datetime | None = Query(None, description="Start date (inclusive)"),
    end_date: datetime | None = Query(None, description="End date (inclusive)"),
    limit: int = Query(10000, ge=1, le=100000, description="Maximum records to export"),
    db: AsyncSession = Depends(get_db),
    current_user: UserNew = Depends(require_admin),
) -> Any:
    """
    Export logs to JSON or CSV format.

    **Required Role:** Admin only

    **Formats:**
    - **JSON**: Returns an array of log objects
    - **CSV**: Returns CSV with headers

    **Use case:** Export logs for external analysis, archival, or reporting.
    """
    logs = await crud_logs.get_logs_for_export(
        db=db,
        level=level,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )

    if format == "json":
        # Export as JSON
        log_dicts = []
        for log in logs:
            log_dict = {
                "id": log.id,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "level": log.level,
                "logger": log.logger,
                "message": log.message,
                "request_id": log.request_id,
                "user_id": str(log.user_id) if log.user_id else None,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "path": log.path,
                "method": log.method,
                "status_code": log.status_code,
                "duration_ms": log.duration_ms,
                "context": log.context,
                "error_type": log.error_type,
                "error_message": log.error_message,
                "stack_trace": log.stack_trace,
            }
            log_dicts.append(log_dict)

        return Response(
            content=json.dumps(log_dicts, indent=2, default=str),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            },
        )

    elif format == "csv":
        # Export as CSV
        output = io.StringIO()
        fieldnames = [
            "id",
            "timestamp",
            "level",
            "logger",
            "message",
            "request_id",
            "user_id",
            "ip_address",
            "path",
            "method",
            "status_code",
            "duration_ms",
            "error_type",
            "error_message",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for log in logs:
            writer.writerow(
                {
                    "id": log.id,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else "",
                    "level": log.level or "",
                    "logger": log.logger or "",
                    "message": log.message or "",
                    "request_id": log.request_id or "",
                    "user_id": str(log.user_id) if log.user_id else "",
                    "ip_address": log.ip_address or "",
                    "path": log.path or "",
                    "method": log.method or "",
                    "status_code": log.status_code or "",
                    "duration_ms": log.duration_ms or "",
                    "error_type": log.error_type or "",
                    "error_message": log.error_message or "",
                }
            )

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            },
        )


@router.delete("/cleanup")
async def cleanup_old_logs(
    days: int = Query(90, ge=30, le=365, description="Retention period in days"),
    db: AsyncSession = Depends(get_db),
    current_user: UserNew = Depends(require_admin),
) -> Any:
    """
    Cleanup old log partitions (admin maintenance operation).

    This endpoint triggers the PostgreSQL cleanup_old_logs() function
    which drops log partitions older than the specified retention period.

    **Required Role:** Admin only

    **Default retention:** 90 days (configurable 30-365 days)

    **Use case:** Periodic maintenance to manage database size.

    **Warning:** This operation is irreversible and will permanently
    delete old log partitions.
    """
    result = await crud_logs.cleanup_old_partitions(db=db, days=days)
    return result
