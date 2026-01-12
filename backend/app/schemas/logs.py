"""
Pydantic schemas for system log API endpoints.
"""

from datetime import datetime
from typing import Any, ClassVar

from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    """Schema for a single log entry."""

    id: int = Field(..., description="Log entry ID")
    timestamp: datetime = Field(..., description="Log timestamp")
    level: str = Field(
        ..., description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    logger_name: str = Field(..., description="Logger name (module path)")
    message: str = Field(..., description="Log message")
    request_id: str | None = Field(None, description="Request correlation ID")
    user_id: str | None = Field(None, description="User UUID")
    scope_id: int | None = Field(None, description="Scope ID")
    duration_ms: float | None = Field(
        None, description="Operation duration in milliseconds"
    )
    context: dict[str, Any] | None = Field(
        None, description="Additional context (JSONB)"
    )
    endpoint: str | None = Field(None, description="API endpoint")
    method: str | None = Field(None, description="HTTP method")
    status_code: int | None = Field(None, description="HTTP status code")

    class Config:
        from_attributes = True
        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "id": 12345,
                "timestamp": "2025-01-15T10:30:45.123Z",
                "level": "INFO",
                "logger_name": "app.api.v1.endpoints.curations",
                "message": "Curation created successfully",
                "request_id": "abc-123-def-456",
                "user_id": "user-uuid-here",
                "scope_id": 1,
                "duration_ms": 45.6,
                "context": {"curation_id": 42, "gene_symbol": "TP53"},
                "endpoint": "/api/v1/curations",
                "method": "POST",
                "status_code": 201,
            }
        }


class LogSearchParams(BaseModel):
    """Search parameters for log queries."""

    level: str | None = Field(None, description="Filter by log level")
    logger_name: str | None = Field(
        None, description="Filter by logger name (partial match)"
    )
    message: str | None = Field(None, description="Search in message (partial match)")
    request_id: str | None = Field(None, description="Filter by request ID")
    user_id: str | None = Field(None, description="Filter by user ID")
    scope_id: int | None = Field(None, description="Filter by scope ID")
    endpoint: str | None = Field(None, description="Filter by endpoint (partial match)")
    method: str | None = Field(None, description="Filter by HTTP method")
    start_date: datetime | None = Field(None, description="Start date (inclusive)")
    end_date: datetime | None = Field(None, description="End date (inclusive)")
    min_duration_ms: float | None = Field(
        None, description="Minimum duration in milliseconds"
    )
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(
        100, ge=1, le=1000, description="Maximum number of records to return"
    )

    class Config:
        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "level": "ERROR",
                "start_date": "2025-01-15T00:00:00Z",
                "end_date": "2025-01-15T23:59:59Z",
                "skip": 0,
                "limit": 100,
            }
        }


class LogStatsSummary(BaseModel):
    """Statistics summary for system logs."""

    total_logs: int = Field(..., description="Total number of log entries")
    logs_by_level: dict[str, int] = Field(..., description="Count of logs by level")
    logs_by_hour: dict[str, int] = Field(
        ..., description="Count of logs by hour (last 24h)"
    )
    avg_duration_ms: float | None = Field(
        None, description="Average operation duration"
    )
    slow_endpoints: list[dict[str, Any]] = Field(
        ..., description="Top 5 slowest endpoints with avg duration"
    )
    error_rate: float = Field(..., description="Error rate (errors / total)")
    top_errors: list[dict[str, Any]] = Field(
        ..., description="Top 5 most common error messages"
    )

    class Config:
        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "total_logs": 50000,
                "logs_by_level": {
                    "DEBUG": 20000,
                    "INFO": 25000,
                    "WARNING": 3000,
                    "ERROR": 1500,
                    "CRITICAL": 500,
                },
                "logs_by_hour": {"2025-01-15T10:00": 2500, "2025-01-15T11:00": 3200},
                "avg_duration_ms": 125.5,
                "slow_endpoints": [
                    {
                        "endpoint": "/api/v1/curations",
                        "avg_duration_ms": 450.2,
                        "count": 100,
                    }
                ],
                "error_rate": 0.04,
                "top_errors": [
                    {
                        "message": "Database connection timeout",
                        "count": 50,
                        "last_seen": "2025-01-15T12:30:00Z",
                    }
                ],
            }
        }


class LogExportParams(BaseModel):
    """Parameters for log export."""

    format: str = Field("json", description="Export format (json or csv)")
    level: str | None = Field(None, description="Filter by log level")
    start_date: datetime | None = Field(None, description="Start date (inclusive)")
    end_date: datetime | None = Field(None, description="End date (inclusive)")
    limit: int = Field(10000, ge=1, le=100000, description="Maximum records to export")

    class Config:
        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "format": "csv",
                "level": "ERROR",
                "start_date": "2025-01-15T00:00:00Z",
                "end_date": "2025-01-15T23:59:59Z",
                "limit": 1000,
            }
        }
