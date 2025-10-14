"""
CRUD operations for system logs.

This module provides database operations for querying system logs,
supporting request correlation, filtering, and statistics.
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.models import SystemLog


async def get_logs(  # noqa: C901
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    level: str | None = None,
    logger_name: str | None = None,
    message: str | None = None,
    request_id: str | None = None,
    user_id: str | None = None,
    endpoint: str | None = None,
    method: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    min_duration_ms: float | None = None,
) -> list[SystemLog]:
    """
    Get system logs with optional filtering.

    Args:
        db: Database session
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        level: Filter by log level
        logger_name: Filter by logger name (partial match)
        message: Search in message (partial match)
        request_id: Filter by request ID
        user_id: Filter by user ID
        endpoint: Filter by endpoint (partial match)
        method: Filter by HTTP method
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        min_duration_ms: Minimum duration in milliseconds

    Returns:
        List of SystemLog records
    """
    query = select(SystemLog)

    # Build filters
    filters = []
    if level:
        filters.append(SystemLog.level == level)
    if logger_name:
        filters.append(SystemLog.logger.ilike(f"%{logger_name}%"))
    if message:
        filters.append(SystemLog.message.ilike(f"%{message}%"))
    if request_id:
        filters.append(SystemLog.request_id == request_id)
    if user_id:
        filters.append(SystemLog.user_id == user_id)
    if endpoint:
        filters.append(SystemLog.path.ilike(f"%{endpoint}%"))
    if method:
        filters.append(SystemLog.method == method)
    if start_date:
        filters.append(SystemLog.timestamp >= start_date)
    if end_date:
        filters.append(SystemLog.timestamp <= end_date)
    if min_duration_ms:
        filters.append(SystemLog.duration_ms >= min_duration_ms)

    if filters:
        query = query.where(and_(*filters))

    # Order by timestamp descending (most recent first)
    query = query.order_by(SystemLog.timestamp.desc())

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


async def get_log_by_id(db: AsyncSession, log_id: int) -> SystemLog | None:
    """
    Get a specific log entry by ID.

    Args:
        db: Database session
        log_id: Log entry ID

    Returns:
        SystemLog record or None if not found
    """
    query = select(SystemLog).where(SystemLog.id == log_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_logs_by_request_id(db: AsyncSession, request_id: str) -> list[SystemLog]:
    """
    Get all logs for a specific request (request correlation).

    This is the key function for request correlation - shows all logs
    that occurred during a single API request.

    Args:
        db: Database session
        request_id: Request correlation ID

    Returns:
        List of SystemLog records for the request
    """
    query = (
        select(SystemLog)
        .where(SystemLog.request_id == request_id)
        .order_by(SystemLog.timestamp.asc())
    )
    result = await db.execute(query)
    return result.scalars().all()


async def get_log_statistics(db: AsyncSession) -> dict[str, Any]:
    """
    Get comprehensive log statistics.

    Returns:
        Dictionary with statistics including:
        - total_logs: Total number of log entries
        - logs_by_level: Count of logs by level
        - logs_by_hour: Count of logs by hour (last 24h)
        - avg_duration_ms: Average operation duration
        - slow_endpoints: Top 5 slowest endpoints
        - error_rate: Error rate (errors / total)
        - top_errors: Top 5 most common error messages
    """
    # Total logs count
    total_query = select(func.count(SystemLog.id))
    total_result = await db.execute(total_query)
    total_logs = total_result.scalar() or 0

    # Logs by level
    level_query = select(SystemLog.level, func.count(SystemLog.id)).group_by(
        SystemLog.level
    )
    level_result = await db.execute(level_query)
    logs_by_level = {row[0]: row[1] for row in level_result.all()}

    # Logs by hour (last 24 hours)
    last_24h = datetime.utcnow() - timedelta(hours=24)
    hour_query = (
        select(
            func.date_trunc("hour", SystemLog.timestamp).label("hour"),
            func.count(SystemLog.id),
        )
        .where(SystemLog.timestamp >= last_24h)
        .group_by(func.date_trunc("hour", SystemLog.timestamp))
        .order_by(func.date_trunc("hour", SystemLog.timestamp))
    )
    hour_result = await db.execute(hour_query)
    logs_by_hour = {
        row[0].isoformat() if row[0] else "unknown": row[1] for row in hour_result.all()
    }

    # Average duration (only for requests with duration)
    avg_duration_query = select(func.avg(SystemLog.duration_ms)).where(
        SystemLog.duration_ms.isnot(None)
    )
    avg_duration_result = await db.execute(avg_duration_query)
    avg_duration_ms = avg_duration_result.scalar() or None

    # Top 5 slowest endpoints
    slow_endpoints_query = (
        select(
            SystemLog.path,
            func.avg(SystemLog.duration_ms).label("avg_duration"),
            func.count(SystemLog.id).label("count"),
        )
        .where(SystemLog.duration_ms.isnot(None))
        .where(SystemLog.path.isnot(None))
        .group_by(SystemLog.path)
        .order_by(func.avg(SystemLog.duration_ms).desc())
        .limit(5)
    )
    slow_endpoints_result = await db.execute(slow_endpoints_query)
    slow_endpoints = [
        {
            "endpoint": row[0],
            "avg_duration_ms": float(row[1]) if row[1] else 0.0,
            "count": row[2],
        }
        for row in slow_endpoints_result.all()
    ]

    # Error rate
    error_count_query = select(func.count(SystemLog.id)).where(
        or_(SystemLog.level == "ERROR", SystemLog.level == "CRITICAL")
    )
    error_count_result = await db.execute(error_count_query)
    error_count = error_count_result.scalar() or 0
    error_rate = error_count / total_logs if total_logs > 0 else 0.0

    # Top 5 most common error messages
    top_errors_query = (
        select(
            SystemLog.message,
            func.count(SystemLog.id).label("count"),
            func.max(SystemLog.timestamp).label("last_seen"),
        )
        .where(or_(SystemLog.level == "ERROR", SystemLog.level == "CRITICAL"))
        .group_by(SystemLog.message)
        .order_by(func.count(SystemLog.id).desc())
        .limit(5)
    )
    top_errors_result = await db.execute(top_errors_query)
    top_errors = [
        {
            "message": row[0],
            "count": row[1],
            "last_seen": row[2].isoformat() if row[2] else None,
        }
        for row in top_errors_result.all()
    ]

    return {
        "total_logs": total_logs,
        "logs_by_level": logs_by_level,
        "logs_by_hour": logs_by_hour,
        "avg_duration_ms": float(avg_duration_ms) if avg_duration_ms else None,
        "slow_endpoints": slow_endpoints,
        "error_rate": error_rate,
        "top_errors": top_errors,
    }


async def get_recent_errors(
    db: AsyncSession, limit: int = 20, hours: int = 24
) -> list[SystemLog]:
    """
    Get recent error and critical logs for triage.

    Args:
        db: Database session
        limit: Maximum number of errors to return
        hours: Time window in hours (default 24)

    Returns:
        List of recent error/critical SystemLog records
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    query = (
        select(SystemLog)
        .where(
            and_(
                or_(SystemLog.level == "ERROR", SystemLog.level == "CRITICAL"),
                SystemLog.timestamp >= cutoff_time,
            )
        )
        .order_by(SystemLog.timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()


async def get_logs_for_export(
    db: AsyncSession,
    level: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 10000,
) -> list[SystemLog]:
    """
    Get logs for export (JSON/CSV).

    Args:
        db: Database session
        level: Filter by log level
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        limit: Maximum records to export

    Returns:
        List of SystemLog records
    """
    query = select(SystemLog)

    # Build filters
    filters = []
    if level:
        filters.append(SystemLog.level == level)
    if start_date:
        filters.append(SystemLog.timestamp >= start_date)
    if end_date:
        filters.append(SystemLog.timestamp <= end_date)

    if filters:
        query = query.where(and_(*filters))

    # Order by timestamp descending
    query = query.order_by(SystemLog.timestamp.desc()).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


async def cleanup_old_partitions(db: AsyncSession, days: int = 90) -> dict[str, Any]:
    """
    Trigger cleanup of old log partitions.

    This calls the PostgreSQL function cleanup_old_logs() which drops
    partitions older than the specified number of days.

    Args:
        db: Database session
        days: Number of days to retain (default 90)

    Returns:
        Dictionary with cleanup results
    """
    # Call the PostgreSQL function
    query = "SELECT cleanup_old_logs()"
    await db.execute(query)
    await db.commit()

    return {
        "status": "success",
        "message": f"Cleaned up log partitions older than {days} days",
        "retention_days": days,
    }
