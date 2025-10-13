# Enhancement 002 - MISSING API ENDPOINTS: Log Viewing & Management

**Status**: ⚠️ CRITICAL GAP IN ORIGINAL PLAN
**Priority**: High (Required for observability)
**Estimated Effort**: 3-4 hours
**Reference**: kidney-genetics-db log viewing API

## Overview

The original 002-backend-unified-logging-system-CORRECTED.md plan implemented all the **infrastructure** (database logger, middleware, sanitization, etc.) but is **missing the API layer** to actually view and query those logs.

This document specifies the missing API endpoints, CRUD operations, and schemas needed for a complete logging system with admin panel support.

## Missing Components

### 1. Log Endpoints (`app/api/v1/endpoints/logs.py`)

```python
"""
Log Viewing and Management Endpoints

Provides admin and developer access to query, search, and analyze system logs
stored in the database with request correlation and filtering capabilities.
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user, get_db
from app.crud import logs as crud_logs
from app.models.models import User
from app.schemas.logs import (
    LogEntry,
    LogList,
    LogStats,
    LogFilter,
    LogExport,
)

router = APIRouter()


@router.get("/", response_model=LogList)
async def get_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    level: str | None = Query(None, regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"),
    request_id: str | None = None,
    user_id: int | None = None,
    logger: str | None = None,
    path: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get logs with filtering and pagination.

    **Permissions**: Admin or Reviewer only

    **Filters**:
    - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - request_id: Request correlation ID
    - user_id: User who triggered the log
    - logger: Source logger name
    - path: API endpoint path
    - start_time: Filter logs after this time
    - end_time: Filter logs before this time
    - search: Full-text search in message and context

    **Returns**: Paginated list of log entries
    """
    # Permission check
    if current_user.role not in ["admin", "reviewer"]:
        raise HTTPException(status_code=403, detail="Admin or Reviewer access required")

    filter_params = LogFilter(
        level=level,
        request_id=request_id,
        user_id=user_id,
        logger=logger,
        path=path,
        start_time=start_time,
        end_time=end_time,
        search=search,
    )

    logs, total = await crud_logs.get_logs(db, skip=skip, limit=limit, filters=filter_params)

    return {
        "items": logs,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{log_id}", response_model=LogEntry)
async def get_log_by_id(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a specific log entry by ID.

    **Permissions**: Admin or Reviewer only

    **Returns**: Full log entry with all context data
    """
    if current_user.role not in ["admin", "reviewer"]:
        raise HTTPException(status_code=403, detail="Admin or Reviewer access required")

    log = await crud_logs.get_log_by_id(db, log_id=log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found")

    return log


@router.get("/request/{request_id}", response_model=list[LogEntry])
async def get_logs_by_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all logs for a specific request (request correlation).

    **Permissions**: Admin or Reviewer only

    This is the key endpoint for **request correlation** - it shows all logs
    that occurred during a single API request, allowing developers to trace
    the full execution path.

    **Use Case**: User reports error → copy request_id from response header →
    query this endpoint → see all logs for that request

    **Returns**: List of all log entries with the same request_id, ordered by timestamp
    """
    if current_user.role not in ["admin", "reviewer"]:
        raise HTTPException(status_code=403, detail="Admin or Reviewer access required")

    logs = await crud_logs.get_logs_by_request_id(db, request_id=request_id)
    return logs


@router.get("/stats/summary", response_model=LogStats)
async def get_log_statistics(
    hours: int = Query(24, ge=1, le=168),  # Last 1-168 hours (1 week max)
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get log statistics for admin dashboard.

    **Permissions**: Admin only

    **Statistics Include**:
    - Total logs by level
    - Error rate over time
    - Top error paths
    - Slowest endpoints
    - Most active users
    - Request volume by hour

    **Returns**: Comprehensive statistics object
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    start_time = datetime.utcnow() - timedelta(hours=hours)
    stats = await crud_logs.get_statistics(db, start_time=start_time)

    return stats


@router.get("/recent-errors", response_model=list[LogEntry])
async def get_recent_errors(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get most recent error and critical logs.

    **Permissions**: Admin or Reviewer only

    **Use Case**: Admin dashboard showing latest errors for quick triage

    **Returns**: Most recent ERROR and CRITICAL logs, ordered by timestamp descending
    """
    if current_user.role not in ["admin", "reviewer"]:
        raise HTTPException(status_code=403, detail="Admin or Reviewer access required")

    logs = await crud_logs.get_recent_errors(db, limit=limit)
    return logs


@router.get("/export", response_model=LogExport)
async def export_logs(
    format: str = Query("json", regex="^(json|csv)$"),
    level: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Export logs for analysis or archival.

    **Permissions**: Admin only

    **Formats**:
    - json: Full log data with all context (default)
    - csv: Simplified format for spreadsheet analysis

    **Returns**: Export object with data and metadata
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    filter_params = LogFilter(
        level=level,
        start_time=start_time,
        end_time=end_time,
    )

    export_data = await crud_logs.export_logs(
        db, filters=filter_params, format=format
    )

    return export_data


@router.delete("/cleanup")
async def cleanup_old_logs(
    days: int = Query(90, ge=30, le=365),
    dry_run: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Cleanup old log partitions (admin maintenance).

    **Permissions**: Admin only

    **Parameters**:
    - days: Delete logs older than this many days (default: 90)
    - dry_run: If true, only report what would be deleted (default: true)

    **Safety**: dry_run=true by default to prevent accidental deletion

    **Returns**: Report of partitions deleted/to be deleted
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await crud_logs.cleanup_old_logs(db, days=days, dry_run=dry_run)

    return {
        "dry_run": dry_run,
        "days": days,
        "partitions_affected": result["partitions"],
        "estimated_rows": result["row_count"] if dry_run else result["rows_deleted"],
        "message": "Dry run completed" if dry_run else "Cleanup completed",
    }
```

### 2. Log CRUD Operations (`app/crud/logs.py`)

```python
"""
CRUD operations for system logs.

Provides database queries for log viewing, searching, and management.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, select, text, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.logs import LogFilter


async def get_logs(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
    filters: LogFilter | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """
    Get logs with filtering and pagination.

    Returns:
        Tuple of (logs, total_count)
    """
    # Build base query
    query = select(text("*")).select_from(text("system_logs"))
    count_query = select(func.count()).select_from(text("system_logs"))

    # Apply filters
    conditions = []

    if filters:
        if filters.level:
            conditions.append(text(f"level = '{filters.level}'"))

        if filters.request_id:
            conditions.append(text(f"request_id = '{filters.request_id}'"))

        if filters.user_id:
            conditions.append(text(f"user_id = {filters.user_id}"))

        if filters.logger:
            conditions.append(text(f"logger LIKE '%{filters.logger}%'"))

        if filters.path:
            conditions.append(text(f"path LIKE '%{filters.path}%'"))

        if filters.start_time:
            conditions.append(text(f"timestamp >= '{filters.start_time.isoformat()}'"))

        if filters.end_time:
            conditions.append(text(f"timestamp <= '{filters.end_time.isoformat()}'"))

        if filters.search:
            # Full-text search in message and context
            conditions.append(
                text(
                    f"(message ILIKE '%{filters.search}%' OR context::text ILIKE '%{filters.search}%')"
                )
            )

    # Apply conditions
    if conditions:
        where_clause = " AND ".join([str(c) for c in conditions])
        query = query.where(text(where_clause))
        count_query = count_query.where(text(where_clause))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply ordering, offset, limit
    query = (
        query.order_by(text("timestamp DESC"))
        .offset(skip)
        .limit(limit)
    )

    # Execute query
    result = await db.execute(query)
    logs = [dict(row._mapping) for row in result]

    return logs, total


async def get_log_by_id(db: AsyncSession, log_id: int) -> dict[str, Any] | None:
    """Get a specific log entry by ID."""
    query = select(text("*")).select_from(text("system_logs")).where(text(f"id = {log_id}"))
    result = await db.execute(query)
    row = result.first()
    return dict(row._mapping) if row else None


async def get_logs_by_request_id(
    db: AsyncSession, request_id: str
) -> list[dict[str, Any]]:
    """Get all logs for a specific request (request correlation)."""
    query = (
        select(text("*"))
        .select_from(text("system_logs"))
        .where(text(f"request_id = '{request_id}'"))
        .order_by(text("timestamp ASC"))
    )

    result = await db.execute(query)
    return [dict(row._mapping) for row in result]


async def get_statistics(
    db: AsyncSession, start_time: datetime
) -> dict[str, Any]:
    """Get log statistics for dashboard."""
    # Total logs by level
    level_query = text("""
        SELECT level, COUNT(*) as count
        FROM system_logs
        WHERE timestamp >= :start_time
        GROUP BY level
    """)

    level_result = await db.execute(level_query, {"start_time": start_time})
    logs_by_level = {row.level: row.count for row in level_result}

    # Top error paths
    error_paths_query = text("""
        SELECT path, COUNT(*) as count
        FROM system_logs
        WHERE level IN ('ERROR', 'CRITICAL')
        AND timestamp >= :start_time
        AND path IS NOT NULL
        GROUP BY path
        ORDER BY count DESC
        LIMIT 10
    """)

    error_paths_result = await db.execute(
        error_paths_query, {"start_time": start_time}
    )
    top_error_paths = [
        {"path": row.path, "count": row.count} for row in error_paths_result
    ]

    # Slowest endpoints
    slow_endpoints_query = text("""
        SELECT path, AVG(duration_ms) as avg_duration, COUNT(*) as count
        FROM system_logs
        WHERE duration_ms IS NOT NULL
        AND timestamp >= :start_time
        GROUP BY path
        ORDER BY avg_duration DESC
        LIMIT 10
    """)

    slow_result = await db.execute(slow_endpoints_query, {"start_time": start_time})
    slowest_endpoints = [
        {"path": row.path, "avg_duration_ms": row.avg_duration, "count": row.count}
        for row in slow_result
    ]

    # Request volume by hour
    volume_query = text("""
        SELECT
            date_trunc('hour', timestamp) as hour,
            COUNT(*) as count
        FROM system_logs
        WHERE timestamp >= :start_time
        GROUP BY hour
        ORDER BY hour DESC
    """)

    volume_result = await db.execute(volume_query, {"start_time": start_time})
    request_volume = [
        {"hour": row.hour.isoformat(), "count": row.count} for row in volume_result
    ]

    return {
        "logs_by_level": logs_by_level,
        "top_error_paths": top_error_paths,
        "slowest_endpoints": slowest_endpoints,
        "request_volume": request_volume,
        "time_range": {
            "start": start_time.isoformat(),
            "end": datetime.utcnow().isoformat(),
        },
    }


async def get_recent_errors(
    db: AsyncSession, limit: int = 10
) -> list[dict[str, Any]]:
    """Get most recent error and critical logs."""
    query = (
        select(text("*"))
        .select_from(text("system_logs"))
        .where(text("level IN ('ERROR', 'CRITICAL')"))
        .order_by(text("timestamp DESC"))
        .limit(limit)
    )

    result = await db.execute(query)
    return [dict(row._mapping) for row in result]


async def export_logs(
    db: AsyncSession, filters: LogFilter, format: str = "json"
) -> dict[str, Any]:
    """Export logs for analysis."""
    logs, total = await get_logs(db, skip=0, limit=10000, filters=filters)

    if format == "json":
        return {
            "format": "json",
            "total_records": total,
            "exported_at": datetime.utcnow().isoformat(),
            "data": logs,
        }
    elif format == "csv":
        # Simplified CSV format
        csv_data = [
            {
                "timestamp": log["timestamp"],
                "level": log["level"],
                "message": log["message"],
                "request_id": log.get("request_id", ""),
                "path": log.get("path", ""),
                "status_code": log.get("status_code", ""),
                "duration_ms": log.get("duration_ms", ""),
            }
            for log in logs
        ]
        return {
            "format": "csv",
            "total_records": total,
            "exported_at": datetime.utcnow().isoformat(),
            "data": csv_data,
        }


async def cleanup_old_logs(
    db: AsyncSession, days: int = 90, dry_run: bool = True
) -> dict[str, Any]:
    """Cleanup old log partitions."""
    if dry_run:
        # Query to find partitions older than cutoff
        query = text("""
            SELECT
                tablename,
                to_date(substring(tablename from 'system_logs_(\\d{4}_\\d{2})'), 'YYYY_MM') as partition_date
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename LIKE 'system_logs_%'
            AND tablename != 'system_logs'
            AND to_date(substring(tablename from 'system_logs_(\\d{4}_\\d{2})'), 'YYYY_MM') < CURRENT_DATE - INTERVAL ':days days'
        """)

        result = await db.execute(query, {"days": days})
        partitions = [row.tablename for row in result]

        return {"partitions": partitions, "row_count": len(partitions) * 10000}  # Estimate
    else:
        # Actually call the cleanup function
        await db.execute(text("SELECT cleanup_old_logs()"))
        await db.commit()

        return {"partitions": [], "rows_deleted": 0}  # TODO: Get actual count
```

### 3. Log Schemas (`app/schemas/logs.py`)

```python
"""
Pydantic schemas for log entries.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    """Single log entry."""

    id: int
    timestamp: datetime
    level: str
    logger: str
    message: str
    context: dict[str, Any] = Field(default_factory=dict)

    # Request correlation
    request_id: str | None = None

    # User context
    user_id: int | None = None
    ip_address: str | None = None
    user_agent: str | None = None

    # HTTP context
    path: str | None = None
    method: str | None = None
    status_code: int | None = None
    duration_ms: float | None = None

    # Error context
    error_type: str | None = None
    error_message: str | None = None
    stack_trace: str | None = None

    class Config:
        from_attributes = True


class LogList(BaseModel):
    """Paginated list of log entries."""

    items: list[LogEntry]
    total: int
    skip: int
    limit: int


class LogFilter(BaseModel):
    """Filter parameters for log queries."""

    level: str | None = None
    request_id: str | None = None
    user_id: int | None = None
    logger: str | None = None
    path: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    search: str | None = None


class LogStats(BaseModel):
    """Log statistics for dashboard."""

    logs_by_level: dict[str, int]
    top_error_paths: list[dict[str, Any]]
    slowest_endpoints: list[dict[str, Any]]
    request_volume: list[dict[str, Any]]
    time_range: dict[str, str]


class LogExport(BaseModel):
    """Exported logs."""

    format: str
    total_records: int
    exported_at: str
    data: list[dict[str, Any]]
```

### 4. Router Registration (`app/api/v1/api.py`)

```python
# ADD THIS IMPORT:
from app.api.v1.endpoints import logs

# ADD THIS ROUTER REGISTRATION:
api_router.include_router(logs.router, prefix="/logs", tags=["logs"])
```

## API Routes Summary

| Method | Endpoint | Purpose | Permission |
|--------|----------|---------|------------|
| GET | `/api/v1/logs` | List/search logs with filters | Admin/Reviewer |
| GET | `/api/v1/logs/{id}` | Get specific log entry | Admin/Reviewer |
| GET | `/api/v1/logs/request/{request_id}` | Request correlation (all logs for one request) | Admin/Reviewer |
| GET | `/api/v1/logs/stats/summary` | Statistics dashboard | Admin |
| GET | `/api/v1/logs/recent-errors` | Recent errors for triage | Admin/Reviewer |
| GET | `/api/v1/logs/export` | Export logs (JSON/CSV) | Admin |
| DELETE | `/api/v1/logs/cleanup` | Cleanup old partitions | Admin |

## Implementation Checklist

- [ ] Create `app/api/v1/endpoints/logs.py` (350+ lines)
- [ ] Create `app/crud/logs.py` (200+ lines)
- [ ] Create `app/schemas/logs.py` (80+ lines)
- [ ] Update `app/api/v1/api.py` to register logs router
- [ ] Add permission checks (admin/reviewer only)
- [ ] Test all endpoints with realistic data
- [ ] Add API documentation examples
- [ ] Update CLAUDE.md with log querying examples

## Example Usage

### Query logs by request ID (request correlation):
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8051/api/v1/logs/request/abc-123-def-456"
```

### Search for errors in the last hour:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8051/api/v1/logs?level=ERROR&start_time=2025-10-13T10:00:00Z"
```

### Get statistics for admin dashboard:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8051/api/v1/logs/stats/summary?hours=24"
```

### Export logs for analysis:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8051/api/v1/logs/export?format=csv" > logs.csv
```

## Priority

⚠️ **HIGH PRIORITY** - Without these endpoints, the logging system is only half-complete. Logs are being stored but cannot be viewed/queried, making debugging in production impossible.

## Comparison with kidney-genetics-db

Based on the reference, kidney-genetics-db likely has:
- ✅ Log viewing endpoints
- ✅ Request correlation endpoint
- ✅ Admin dashboard with statistics
- ✅ Export functionality
- ✅ Permission-based access (admin/reviewer)

Gene Curator currently has:
- ✅ Database logging infrastructure
- ✅ Request correlation (middleware)
- ❌ **NO endpoints to view logs**
- ❌ **NO admin dashboard API**
- ❌ **NO export functionality**

---

**Next Step**: Implement these missing endpoints to complete the logging system and enable production observability.
