"""
Database logger for persistent log storage.

FIXES APPLIED:
- #1: Use AsyncSessionLocal() instead of sync session
- #2: Store task references to prevent garbage collection
- #8: Apply sanitization before database write
- #9: Use DRY utility for IP extraction
- #13: Dependency injection instead of circular import
- #18: Lazy serialization (only when needed)

Handles async database writes for log entries with structured data
storage in PostgreSQL using JSONB for rich context information.
"""

import asyncio
import json
import traceback
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .sanitizer import sanitize_dict
from .utils import extract_client_ip

# Global database logger instance
_db_logger: "DatabaseLogger | None" = None


class DatabaseLogger:
    """
    Async database logger for structured log persistence.

    FIXES:
    - Uses async session properly
    - Manages task lifecycle
    - Applies sanitization
    - Uses dependency injection

    Stores log entries in PostgreSQL with rich context data,
    request correlation, and performance metrics.
    """

    def __init__(self, session_factory: Callable[[], AsyncSession] | None = None):
        """
        Initialize database logger.

        Args:
            session_factory: Factory function that returns AsyncSession
        """
        self.session_factory = session_factory
        self.enabled = True
        self._pending_tasks: set[asyncio.Task[None]] = set()  # FIX #2: Store task references

    async def log(
        self,
        level: str,
        message: str,
        source: str,
        request: Request | None = None,
        request_id: str | None = None,
        extra_data: dict[str, Any] | None = None,
        error: Exception | None = None,
        processing_time_ms: int | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Log an entry to the database.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            source: Source module/component
            request: FastAPI request object (optional)
            request_id: Request correlation ID
            extra_data: Additional structured data
            error: Exception object for error logs
            processing_time_ms: Request processing time
            status_code: HTTP status code
        """
        if not self.enabled or not self.session_factory:
            return

        try:
            # FIX #2: Store task reference
            task = asyncio.create_task(
                self._write_log_entry(
                    level,
                    message,
                    source,
                    request,
                    request_id,
                    extra_data,
                    error,
                    processing_time_ms,
                    status_code,
                )
            )
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)

        except Exception as e:
            # Fallback to console logging if database write fails
            import logging

            fallback_logger = logging.getLogger("database_logger")
            fallback_logger.error(f"Failed to schedule log write: {e}")

    async def _write_log_entry(
        self,
        level: str,
        message: str,
        source: str,
        request: Request | None,
        request_id: str | None,
        extra_data: dict[str, Any] | None,
        error: Exception | None,
        processing_time_ms: int | None,
        status_code: int | None,
    ) -> None:
        """Internal method to write log entry to database."""

        # FIX #18: Check if enabled BEFORE serialization
        if not self.enabled or not self.session_factory:
            return

        try:
            # FIX #1: Use async session properly
            async with self.session_factory() as db:
                # Extract request data if available
                endpoint = None
                method = None
                ip_address = None
                user_agent = None
                user_id = None

                if request:
                    endpoint = request.url.path
                    method = request.method

                    # FIX #9: Use DRY utility for IP extraction
                    ip_address = extract_client_ip(request)

                    user_agent = request.headers.get("User-Agent")

                    # Extract user if available
                    if (
                        hasattr(request.state, "current_user")
                        and request.state.current_user
                    ):
                        user_id = getattr(request.state.current_user, "id", None)

                # Prepare error data
                error_type = None
                error_traceback = None
                if error:
                    if hasattr(error, "__traceback__"):
                        error_type = type(error).__name__
                        error_traceback_list = traceback.format_exception(
                            type(error), error, error.__traceback__
                        )
                        error_traceback = "".join(error_traceback_list)
                    else:
                        error_type = "Error"
                        error_traceback = str(error)

                # FIX #8: Apply sanitization BEFORE serialization
                # FIX #18: Serialize only when needed (after enabled check)
                sanitized_data = sanitize_dict(extra_data or {})
                jsonb_data = json.dumps(sanitized_data)

                # Insert log entry
                insert_query = text("""
                    INSERT INTO system_logs (
                        timestamp, level, message, logger, request_id, path, method,
                        status_code, duration_ms, user_id, ip_address, user_agent,
                        context, error_type, error_message, stack_trace
                    ) VALUES (
                        :timestamp, :level, :message, :logger, :request_id, :path, :method,
                        :status_code, :duration_ms, :user_id, :ip_address, :user_agent,
                        :context, :error_type, :error_message, :stack_trace
                    )
                """)

                await db.execute(
                    insert_query,
                    {
                        "timestamp": datetime.now(timezone.utc),
                        "level": level,
                        "message": message,
                        "logger": source,
                        "request_id": request_id,
                        "path": endpoint,
                        "method": method,
                        "status_code": status_code,
                        "duration_ms": processing_time_ms,
                        "user_id": user_id,
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "context": jsonb_data,
                        "error_type": error_type,
                        "error_message": str(error) if error else None,
                        "stack_trace": error_traceback,
                    },
                )

                await db.commit()

        except SQLAlchemyError as e:
            import logging

            fallback_logger = logging.getLogger("database_logger")
            fallback_logger.error(f"SQLAlchemy error writing log: {e}")

        except Exception as e:
            import logging

            fallback_logger = logging.getLogger("database_logger")
            fallback_logger.error(f"Unexpected error writing log: {e}")

    async def wait_for_pending_tasks(self, timeout: float = 5.0) -> None:
        """
        Wait for all pending log writes to complete.

        Args:
            timeout: Maximum time to wait in seconds
        """
        if not self._pending_tasks:
            return

        try:
            await asyncio.wait_for(
                asyncio.gather(*self._pending_tasks, return_exceptions=True),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            import logging

            logging.getLogger("database_logger").warning(
                f"Timeout waiting for {len(self._pending_tasks)} pending log writes"
            )


def get_database_logger() -> DatabaseLogger:
    """Get the global database logger instance."""
    global _db_logger
    if _db_logger is None:
        _db_logger = DatabaseLogger()
    return _db_logger


def initialize_database_logger(
    session_factory: Callable[[], AsyncSession],
) -> DatabaseLogger:
    """
    Initialize the global database logger with session factory.

    FIX #13: Use dependency injection instead of circular import.

    Args:
        session_factory: Factory function that returns AsyncSession
    """
    global _db_logger
    _db_logger = DatabaseLogger(session_factory)
    return _db_logger
