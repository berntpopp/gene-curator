# Enhancement: Backend Unified Logging System

**Priority**: High
**Complexity**: Medium
**Estimated Effort**: 6-8 hours
**Reference**: kidney-genetics-db unified logging system

## Overview

Implement a comprehensive, production-grade logging system for Gene Curator's FastAPI backend. This system provides structured logging with request correlation, database persistence, performance monitoring, and dual output (console + database).

**Why This Makes Development Easier:**
- **Request Correlation**: Track all logs for a single curator action via request_id
- **Performance Insights**: Automatic timing decorators show bottlenecks instantly
- **Database Persistence**: Query logs in production to debug issues after they happen
- **Structured Context**: Automatic injection of user, request, and operation context
- **Zero Boilerplate**: Drop-in replacement for `logging.getLogger(__name__)`

## Current State

- Basic Python logging used inconsistently across the codebase
- No request correlation or tracing
- No performance monitoring
- No database persistence for production analysis
- Difficult to trace issues across curator sessions or API calls

## Proposed Architecture

### Component Overview

```
app/core/logging/
├── __init__.py              # Public API exports & configure_logging()
├── unified_logger.py        # Main UnifiedLogger class with async/sync methods
├── context.py               # Request context management (contextvars)
├── database_logger.py       # Async PostgreSQL JSONB logging
├── formatters.py            # Custom log formatters
└── performance.py           # Performance monitoring decorators

app/middleware/
└── logging_middleware.py    # Request correlation middleware

database/sql/
└── 005_logging_tables.sql   # system_logs table schema
```

### Key Features

1. **Dual Output**: Console (immediate, sync) + Database (async, persistent)
2. **Request Correlation**: Unique request_id automatically added to all logs within a request
3. **Context Binding**: User ID, username, IP address, user agent automatically captured
4. **Performance Decorators**: `@timed_operation`, `@api_endpoint`, `@database_query`, `@batch_operation`
5. **Async/Sync Support**: Works in both FastAPI endpoints (async) and background tasks (sync)
6. **Structured Data**: JSONB storage for rich context (not just strings)
7. **Privacy**: Sanitization of sensitive fields (tokens, passwords, etc.)

## Detailed Implementation

### 1. Context Management (`app/core/logging/context.py`)

```python
"""
Request context management for unified logging.

Uses Python contextvars for request-scoped context that automatically
propagates through async operations within a request lifecycle.
"""

import contextvars
import uuid
from typing import Any

from fastapi import Request

# Context variables for request-scoped logging context
_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default=None)
_user_id_var: contextvars.ContextVar[int | None] = contextvars.ContextVar("user_id", default=None)
_username_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("username", default=None)
_ip_address_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "ip_address", default=None
)
_user_agent_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_agent", default=None
)
_endpoint_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("endpoint", default=None)
_method_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("method", default=None)


def bind_context(**kwargs) -> None:
    """
    Bind values to the current logging context.

    This uses context variables to store request-scoped logging context
    that will be automatically included in all log entries within the request.

    Args:
        **kwargs: Key-value pairs to bind to the context
    """
    for key, value in kwargs.items():
        if key == "request_id":
            _request_id_var.set(value)
        elif key == "user_id":
            _user_id_var.set(value)
        elif key == "username":
            _username_var.set(value)
        elif key == "ip_address":
            _ip_address_var.set(value)
        elif key == "user_agent":
            _user_agent_var.set(value)
        elif key == "endpoint":
            _endpoint_var.set(value)
        elif key == "method":
            _method_var.set(value)


def clear_context() -> None:
    """Clear all logging context variables."""
    _request_id_var.set(None)
    _user_id_var.set(None)
    _username_var.set(None)
    _ip_address_var.set(None)
    _user_agent_var.set(None)
    _endpoint_var.set(None)
    _method_var.set(None)


def get_context() -> dict[str, Any]:
    """Get the current logging context."""
    context = {}

    if request_id := _request_id_var.get(None):
        context["request_id"] = request_id
    if user_id := _user_id_var.get(None):
        context["user_id"] = user_id
    if username := _username_var.get(None):
        context["username"] = username
    if ip_address := _ip_address_var.get(None):
        context["ip_address"] = ip_address
    if user_agent := _user_agent_var.get(None):
        context["user_agent"] = user_agent
    if endpoint := _endpoint_var.get(None):
        context["endpoint"] = endpoint
    if method := _method_var.get(None):
        context["method"] = method

    return context


def extract_context_from_request(request: Request) -> dict[str, Any]:
    """
    Extract logging context from a FastAPI Request object.

    Args:
        request: FastAPI Request object

    Returns:
        Dictionary containing extracted context
    """
    context = {}

    # Generate request ID if not present
    request_id = getattr(request.state, "request_id", None)
    if not request_id:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

    context["request_id"] = request_id
    context["endpoint"] = request.url.path
    context["method"] = request.method

    # Extract IP address
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        context["ip_address"] = forwarded_for.split(",")[0].strip()
    elif request.client:
        context["ip_address"] = request.client.host

    # Extract user agent
    context["user_agent"] = request.headers.get("User-Agent")

    # Extract user from request state (if available)
    if hasattr(request.state, "current_user"):
        user = request.state.current_user
        if user:
            context["user_id"] = getattr(user, "id", None)
            context["username"] = getattr(user, "username", None) or getattr(user, "email", None)

    return context
```

### 2. Database Logger (`app/core/logging/database_logger.py`)

```python
"""
Database logger for persistent log storage.

Handles async database writes for log entries with structured data
storage in PostgreSQL using JSONB for rich context information.
"""

import asyncio
import json
import traceback
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Global database logger instance
_db_logger: Optional["DatabaseLogger"] = None


class DatabaseLogger:
    """
    Async database logger for structured log persistence.

    Stores log entries in PostgreSQL with rich context data,
    request correlation, and performance metrics.
    """

    def __init__(self):
        self.enabled = True

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
        if not self.enabled:
            return

        try:
            # Use async task to avoid blocking
            asyncio.create_task(
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
        except Exception as e:
            # Fallback to console logging if database write fails
            import logging

            fallback_logger = logging.getLogger("database_logger")
            fallback_logger.error(f"Failed to write log to database: {e}")

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
        db = None
        try:
            # Import SessionLocal here to avoid circular import
            from app.core.database import SessionLocal

            # Create database session
            db = SessionLocal()

            # Extract request data if available
            endpoint = None
            method = None
            ip_address = None
            user_agent = None
            user_id = None

            if request:
                endpoint = request.url.path
                method = request.method

                # Extract IP address
                forwarded_for = request.headers.get("X-Forwarded-For")
                if forwarded_for:
                    ip_address = forwarded_for.split(",")[0].strip()
                elif request.client:
                    ip_address = request.client.host

                user_agent = request.headers.get("User-Agent")

                # Extract user if available
                if hasattr(request.state, "current_user") and request.state.current_user:
                    user_id = getattr(request.state.current_user, "id", None)

            # Prepare error data
            error_type = None
            error_traceback = None
            if error:
                if hasattr(error, "__traceback__"):
                    error_type = type(error).__name__
                    error_traceback = traceback.format_exception(
                        type(error), error, error.__traceback__
                    )
                    error_traceback = "".join(error_traceback)
                else:
                    error_type = "Error"
                    error_traceback = str(error)

            # Prepare extra data as JSONB
            jsonb_data = json.dumps(extra_data or {})

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

            db.execute(
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

            db.commit()

        except SQLAlchemyError as e:
            import logging
            fallback_logger = logging.getLogger("database_logger")
            fallback_logger.error(f"SQLAlchemy error writing log: {e}")

        except Exception as e:
            import logging
            fallback_logger = logging.getLogger("database_logger")
            fallback_logger.error(f"Unexpected error writing log: {e}")

        finally:
            if db:
                db.close()


def get_database_logger() -> DatabaseLogger:
    """Get the global database logger instance."""
    global _db_logger
    if _db_logger is None:
        _db_logger = DatabaseLogger()
    return _db_logger


def initialize_database_logger() -> DatabaseLogger:
    """Initialize the global database logger."""
    global _db_logger
    _db_logger = DatabaseLogger()
    return _db_logger
```

### 3. Unified Logger (`app/core/logging/unified_logger.py`)

```python
"""
Unified Logger - Main logging interface for Gene Curator.

Provides a single interface for all logging needs that routes to multiple
destinations (console + database) while maintaining performance and
providing rich context information.
"""

import asyncio
import logging
from typing import Any

from fastapi import BackgroundTasks

from .context import get_context
from .database_logger import get_database_logger


class UnifiedLogger:
    """
    Unified logging interface that routes to multiple destinations.

    This class provides a single interface for all logging needs, automatically
    routing log entries to both console logging (immediate) and database logging
    (async) while including automatic context injection and structured logging.

    Drop-in replacement for standard Python logging with enhanced features.
    """

    def __init__(self, name: str):
        """
        Initialize the unified logger.

        Args:
            name: Logger name (typically __name__ from calling module)
        """
        self.name = name
        self._console_logger = logging.getLogger(name)
        self._database_logger = get_database_logger()
        self._bound_context: dict[str, Any] = {}

    def _get_current_context(self) -> dict[str, Any]:
        """Extract current context from context variables and bound context."""
        context = get_context()

        # Add bound context (takes precedence over context variables)
        context.update(self._bound_context)

        return context

    def _format_console_message(
        self, level: str, message: str, extra_data: dict[str, Any] | None = None
    ) -> str:
        """Format message for console logging with context."""
        context = self._get_current_context()

        # Start with the base message
        parts = [message]

        # Add request_id if available (most important for correlation)
        if request_id := context.get("request_id"):
            parts.append(f"request_id={request_id}")

        # Add user context if available
        if user_id := context.get("user_id"):
            parts.append(f"user_id={user_id}")
        elif username := context.get("username"):
            parts.append(f"username={username}")

        # Add extra data
        if extra_data:
            for key, value in extra_data.items():
                if key not in context:  # Avoid duplicates
                    parts.append(f"{key}={value}")

        return " | ".join(parts)

    async def _log_to_database(
        self,
        level: str,
        message: str,
        error: Exception | None = None,
        extra_data: dict[str, Any] | None = None,
        background_tasks: BackgroundTasks | None = None,
    ):
        """Log to database using the database logger."""
        # Get current context and merge with extra data
        context = self._get_current_context()
        combined_extra = {**context, **(extra_data or {})}

        try:
            await self._database_logger.log(
                level=level,
                message=message,
                source=self.name,
                request_id=context.get("request_id"),
                extra_data=combined_extra,
                error=error,
            )
        except Exception as e:
            # Fallback to console logging if database logging fails
            self._console_logger.error(f"Database logging failed: {e}. Original message: {message}")

    def _log_to_console(self, level: str, message: str, extra_data: dict[str, Any] | None = None):
        """Log to console using standard Python logging."""
        formatted_message = self._format_console_message(level, message, extra_data)
        log_method = getattr(self._console_logger, level.lower())
        log_method(formatted_message)

    def bind(self, **kwargs) -> "UnifiedLogger":
        """
        Create a new logger with additional bound context.

        This follows the structlog pattern of immutable context binding.

        Args:
            **kwargs: Key-value pairs to bind to the logger context

        Returns:
            New UnifiedLogger instance with the additional context
        """
        new_logger = UnifiedLogger(self.name)
        new_logger._bound_context = {**self._bound_context, **kwargs}
        return new_logger

    # ASYNC METHODS - For use in FastAPI endpoints and async contexts

    async def log(
        self,
        level: str,
        message: str,
        *,
        error: Exception | None = None,
        background_tasks: BackgroundTasks | None = None,
        extra: dict[str, Any] | None = None,
        **kwargs,
    ):
        """
        Log a message at the specified level (async version).

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            error: Exception object for error logs
            background_tasks: FastAPI BackgroundTasks for async processing
            extra: Additional structured data
            **kwargs: Additional key-value pairs for structured logging
        """
        # Combine extra data and kwargs
        extra_data = {**(extra or {}), **kwargs}

        # Log to console synchronously
        self._log_to_console(level, message, extra_data)

        # Log to database asynchronously
        if background_tasks:
            # Use background task for async processing
            background_tasks.add_task(
                self._log_to_database, level, message, error, extra_data, None
            )
        else:
            # Direct async call
            try:
                await self._log_to_database(level, message, error, extra_data, None)
            except Exception as e:
                # Don't let database logging failures break the application
                self._console_logger.error(f"Async database logging failed: {e}")

    async def debug(self, message: str, **kwargs):
        """Log a debug message (async)."""
        await self.log("DEBUG", message, **kwargs)

    async def info(self, message: str, **kwargs):
        """Log an info message (async)."""
        await self.log("INFO", message, **kwargs)

    async def warning(self, message: str, **kwargs):
        """Log a warning message (async)."""
        await self.log("WARNING", message, **kwargs)

    async def error(self, message: str, error: Exception | None = None, **kwargs):
        """Log an error message (async)."""
        await self.log("ERROR", message, error=error, **kwargs)

    async def critical(self, message: str, error: Exception | None = None, **kwargs):
        """Log a critical message (async)."""
        await self.log("CRITICAL", message, error=error, **kwargs)

    # SYNC METHODS - For backward compatibility and non-async contexts

    def sync_log(
        self,
        level: str,
        message: str,
        *,
        error: Exception | None = None,
        extra: dict[str, Any] | None = None,
        **kwargs,
    ):
        """
        Synchronous logging method for non-async contexts.

        This logs to console immediately and schedules database logging
        to run in the background without blocking.
        """
        # Combine extra data and kwargs
        extra_data = {**(extra or {}), **kwargs}

        # Log to console synchronously
        self._log_to_console(level, message, extra_data)

        # Schedule database logging in background
        try:
            # Check if we have an event loop running
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._log_to_database(level, message, error, extra_data, None))
            # Store task reference to prevent it from being garbage collected
            task.add_done_callback(lambda t: None)  # Simple done callback
        except RuntimeError:
            # No event loop running, log only to console
            # This can happen during application startup/shutdown
            pass

    def sync_debug(self, message: str, **kwargs):
        """Synchronous debug logging."""
        self.sync_log("DEBUG", message, **kwargs)

    def sync_info(self, message: str, **kwargs):
        """Synchronous info logging."""
        self.sync_log("INFO", message, **kwargs)

    def sync_warning(self, message: str, **kwargs):
        """Synchronous warning logging."""
        self.sync_log("WARNING", message, **kwargs)

    def sync_error(self, message: str, error: Exception | None = None, **kwargs):
        """Synchronous error logging."""
        self.sync_log("ERROR", message, error=error, **kwargs)

    def sync_critical(self, message: str, error: Exception | None = None, **kwargs):
        """Synchronous critical logging."""
        self.sync_log("CRITICAL", message, error=error, **kwargs)


# Global logger cache for performance
_logger_cache: dict[str, UnifiedLogger] = {}


def get_logger(name: str) -> UnifiedLogger:
    """
    Get a unified logger instance.

    This is a drop-in replacement for logging.getLogger() that provides
    unified logging to multiple destinations with automatic context injection.

    Args:
        name: Logger name (typically __name__ from calling module)

    Returns:
        UnifiedLogger instance
    """
    if name not in _logger_cache:
        _logger_cache[name] = UnifiedLogger(name)
    return _logger_cache[name]
```

### 4. Performance Monitoring (`app/core/logging/performance.py`)

```python
"""
Performance monitoring decorators for the unified logging system.

Provides decorators for tracking operation performance, database queries,
and API endpoint response times with automatic logging integration.
"""

import asyncio
import time
from collections.abc import Callable
from functools import wraps

# Lazy import to avoid circular dependency
_logger = None


def _get_logger():
    """Get logger instance lazily to avoid circular import."""
    global _logger
    if _logger is None:
        from app.core.logging import get_logger

        _logger = get_logger(__name__)
    return _logger


def timed_operation(
    operation_name: str | None = None,
    warning_threshold_ms: float = 1000,
    error_threshold_ms: float = 5000,
    include_args: bool = False,
):
    """
    Decorator to time operations and log performance metrics.

    Args:
        operation_name: Name of the operation (defaults to function name)
        warning_threshold_ms: Log warning if operation takes longer than this (ms)
        error_threshold_ms: Log error if operation takes longer than this (ms)
        include_args: Whether to include function arguments in logs
    """

    def decorator(func: Callable) -> Callable:
        name = operation_name or func.__name__

        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.perf_counter()

                # Build context for logging
                context = {"operation": name}
                if include_args:
                    context["args"] = str(args)[:200]  # Limit arg length
                    context["kwargs"] = str(kwargs)[:200]

                try:
                    # Execute the operation
                    result = await func(*args, **kwargs)

                    # Calculate duration
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)

                    # Log based on duration
                    if duration_ms > error_threshold_ms:
                        await _get_logger().error("Operation exceeded error threshold", **context)
                    elif duration_ms > warning_threshold_ms:
                        await _get_logger().warning(
                            "Operation exceeded warning threshold", **context
                        )
                    else:
                        await _get_logger().info("Operation completed", **context)

                    return result

                except Exception as e:
                    # Log the error with timing
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)
                    context["error"] = str(e)
                    await _get_logger().error("Operation failed", **context)
                    raise

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.perf_counter()

                # Build context for logging
                context = {"operation": name}
                if include_args:
                    context["args"] = str(args)[:200]
                    context["kwargs"] = str(kwargs)[:200]

                try:
                    # Execute the operation
                    result = func(*args, **kwargs)

                    # Calculate duration
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)

                    # Log based on duration
                    if duration_ms > error_threshold_ms:
                        _get_logger().sync_error("Operation exceeded error threshold", **context)
                    elif duration_ms > warning_threshold_ms:
                        _get_logger().sync_warning(
                            "Operation exceeded warning threshold", **context
                        )
                    else:
                        _get_logger().sync_info("Operation completed", **context)

                    return result

                except Exception as e:
                    # Log the error with timing
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)
                    context["error"] = str(e)
                    _get_logger().sync_error("Operation failed", **context)
                    raise

            return sync_wrapper

    return decorator


def database_query(query_type: str = "SELECT"):
    """
    Decorator specifically for database operations.

    Args:
        query_type: Type of query (SELECT, INSERT, UPDATE, DELETE)
    """
    return timed_operation(
        operation_name=f"database_{query_type.lower()}",
        warning_threshold_ms=100,  # Warn on queries > 100ms
        error_threshold_ms=1000,  # Error on queries > 1s
        include_args=False,  # Don't log query parameters by default
    )


def api_endpoint(endpoint_name: str | None = None):
    """
    Decorator for API endpoint performance tracking.

    Args:
        endpoint_name: Name of the endpoint (defaults to function name)
    """
    return timed_operation(
        operation_name=endpoint_name,
        warning_threshold_ms=500,  # Warn on endpoints > 500ms
        error_threshold_ms=2000,  # Error on endpoints > 2s
        include_args=False,
    )


def batch_operation(batch_name: str, batch_size_getter: Callable | None = None):
    """
    Decorator for batch processing operations with per-item metrics.

    Args:
        batch_name: Name of the batch operation
        batch_size_getter: Function to extract batch size from arguments
    """

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.perf_counter()

                # Get batch size if getter provided
                batch_size = None
                if batch_size_getter:
                    try:
                        batch_size = batch_size_getter(*args, **kwargs)
                    except Exception:
                        pass

                context = {"operation": batch_name, "batch_size": batch_size}

                try:
                    await _get_logger().info("Batch operation started", **context)
                    result = await func(*args, **kwargs)

                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)

                    if batch_size:
                        context["ms_per_item"] = round(duration_ms / batch_size, 2)
                        context["items_per_second"] = round(batch_size / (duration_ms / 1000), 2)

                    await _get_logger().info("Batch operation completed", **context)
                    return result

                except Exception as e:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)
                    context["error"] = str(e)
                    await _get_logger().error("Batch operation failed", **context)
                    raise

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.perf_counter()

                # Get batch size if getter provided
                batch_size = None
                if batch_size_getter:
                    try:
                        batch_size = batch_size_getter(*args, **kwargs)
                    except Exception:
                        pass

                context = {"operation": batch_name, "batch_size": batch_size}

                try:
                    _get_logger().sync_info("Batch operation started", **context)
                    result = func(*args, **kwargs)

                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)

                    if batch_size:
                        context["ms_per_item"] = round(duration_ms / batch_size, 2)
                        context["items_per_second"] = round(batch_size / (duration_ms / 1000), 2)

                    _get_logger().sync_info("Batch operation completed", **context)
                    return result

                except Exception as e:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)
                    context["error"] = str(e)
                    _get_logger().sync_error("Batch operation failed", **context)
                    raise

            return sync_wrapper

    return decorator


class PerformanceMonitor:
    """Context manager for performance monitoring blocks of code."""

    def __init__(self, operation_name: str, **extra_context):
        self.operation_name = operation_name
        self.extra_context = extra_context
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        _get_logger().sync_debug(
            "Performance block started", operation=self.operation_name, **self.extra_context
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self.start_time) * 1000

        context = {
            "operation": self.operation_name,
            "duration_ms": round(duration_ms, 2),
            **self.extra_context,
        }

        if exc_type:
            context["error"] = str(exc_val)
            _get_logger().sync_error("Performance block failed", **context)
        else:
            _get_logger().sync_info("Performance block completed", **context)

        return False  # Don't suppress exceptions

    async def __aenter__(self):
        self.start_time = time.perf_counter()
        await _get_logger().debug(
            "Performance block started", operation=self.operation_name, **self.extra_context
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self.start_time) * 1000

        context = {
            "operation": self.operation_name,
            "duration_ms": round(duration_ms, 2),
            **self.extra_context,
        }

        if exc_type:
            context["error"] = str(exc_val)
            await _get_logger().error("Performance block failed", **context)
        else:
            await _get_logger().info("Performance block completed", **context)

        return False  # Don't suppress exceptions
```

### 5. Logging Middleware (`app/middleware/logging_middleware.py`)

```python
"""
Logging middleware for comprehensive request/response logging with correlation.

Replaces the existing error handling middleware with enhanced logging
capabilities, request correlation, and automatic context binding.
"""

import time
import traceback
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger
from app.core.logging.context import bind_context, clear_context, extract_context_from_request


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive logging middleware for request/response lifecycle tracking.

    Provides:
    - Unique request ID generation for correlation
    - Automatic context binding for all logs in request
    - Request/response timing and performance tracking
    - Enhanced error logging with full context
    - Replaces existing error handling middleware
    """

    def __init__(
        self,
        app,
        log_request_body: bool = False,
        log_response_body: bool = False,
        max_body_size: int = 10000,
        slow_request_threshold_ms: int = 1000,
        exclude_paths: list = None,
    ):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_size = max_body_size
        self.slow_request_threshold_ms = slow_request_threshold_ms
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
        self.logger = get_logger("request_middleware")

    def _should_log_request(self, request: Request) -> bool:
        """Determine if request should be logged."""
        return request.url.path not in self.exclude_paths

    def _sanitize_headers(self, headers: dict) -> dict:
        """Remove sensitive headers from logging."""
        sensitive_headers = {
            "authorization",
            "cookie",
            "x-api-key",
            "x-auth-token",
            "x-access-token",
            "authentication",
        }
        return {
            key: "[REDACTED]" if key.lower() in sensitive_headers else value
            for key, value in headers.items()
        }

    def _extract_client_info(self, request: Request) -> dict:
        """Extract client information from request."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        elif request.client:
            client_ip = request.client.host
        else:
            client_ip = "unknown"

        return {
            "ip_address": client_ip,
            "user_agent": request.headers.get("User-Agent", "unknown"),
            "referer": request.headers.get("Referer", ""),
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and response with comprehensive logging."""
        if not self._should_log_request(request):
            return await call_next(request)

        # Clear any existing context and set up request context
        clear_context()

        # Extract and bind request context
        context = extract_context_from_request(request)
        bind_context(**context)

        # Record start time
        start_time = time.perf_counter()

        # Extract request information
        client_info = self._extract_client_info(request)

        # Log request start
        await self.logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            path=request.url.path,
            query_params=dict(request.query_params),
            client_info=client_info,
        )

        # Process request
        response = None
        try:
            response = await call_next(request)

        except Exception as e:
            # Calculate processing time for error case
            processing_time = (time.perf_counter() - start_time) * 1000

            # Log the error with full context
            await self.logger.error(
                "Request failed with unhandled exception",
                error=e,
                method=request.method,
                path=request.url.path,
                url=str(request.url),
                processing_time_ms=int(processing_time),
                error_type=e.__class__.__name__,
                error_message=str(e),
                traceback=traceback.format_exc(),
                client_info=client_info,
            )

            # Return standardized error response
            return JSONResponse(
                status_code=500,
                content={
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred",
                    "request_id": context.get("request_id", "unknown"),
                    "timestamp": time.time(),
                },
            )

        # Calculate processing time
        processing_time = (time.perf_counter() - start_time) * 1000

        # Determine log level based on status code and processing time
        status_code = response.status_code
        if status_code >= 500:
            log_level = "ERROR"
        elif status_code >= 400 or processing_time > self.slow_request_threshold_ms:
            log_level = "WARNING"
        else:
            log_level = "INFO"

        # Log request completion
        log_message = f"Request completed: {request.method} {request.url.path}"

        if log_level == "ERROR":
            await self.logger.error(
                log_message,
                status_code=status_code,
                processing_time_ms=int(processing_time),
            )
        elif log_level == "WARNING":
            await self.logger.warning(
                log_message,
                status_code=status_code,
                processing_time_ms=int(processing_time),
            )
        else:
            await self.logger.info(
                log_message,
                status_code=status_code,
                processing_time_ms=int(processing_time),
            )

        # Add performance and correlation headers
        response.headers["X-Request-ID"] = context.get("request_id", "unknown")
        response.headers["X-Processing-Time"] = f"{processing_time:.1f}ms"

        return response
```

### 6. Module Exports (`app/core/logging/__init__.py`)

```python
"""
Unified Logging System for Gene Curator

This module provides a modern, structured logging system with:
- Dual output: Console (sync) + Database (async)
- Request correlation and context binding
- Drop-in replacement for standard Python logging
- Enterprise-grade observability

Usage:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("Operation completed", operation_id="123", duration_ms=456)
"""

from .context import bind_context, clear_context, get_context
from .database_logger import DatabaseLogger, initialize_database_logger
from .performance import (
    PerformanceMonitor,
    api_endpoint,
    batch_operation,
    database_query,
    timed_operation,
)
from .unified_logger import UnifiedLogger, get_logger

# Main interface - drop-in replacement for logging.getLogger()
__all__ = [
    # Core functionality
    "get_logger",
    "UnifiedLogger",
    "bind_context",
    "clear_context",
    "get_context",
    "DatabaseLogger",
    "configure_logging",
    # Performance monitoring
    "timed_operation",
    "database_query",
    "api_endpoint",
    "batch_operation",
    "PerformanceMonitor",
]


def configure_logging(
    log_level: str = "INFO",
    database_enabled: bool = True,
    console_enabled: bool = True,
) -> None:
    """
    Configure the unified logging system.

    This replaces multiple logging.basicConfig() calls throughout the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        database_enabled: Enable database logging
        console_enabled: Enable console logging
    """
    import logging

    # Set up console logging with unified format
    if console_enabled:
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            force=True,
        )

    # Configure application loggers
    logging.getLogger("app").setLevel(getattr(logging, log_level.upper()))
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

    # Initialize database logger if enabled
    if database_enabled:
        initialize_database_logger()
```

### 7. Database Schema (`database/sql/005_logging_tables.sql`)

```sql
-- System Logs Table for Persistent Log Storage
-- Stores structured logs with JSONB context for rich querying

CREATE TABLE IF NOT EXISTS system_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    logger TEXT NOT NULL,
    message TEXT NOT NULL,
    context JSONB DEFAULT '{}'::JSONB NOT NULL,

    -- Request correlation
    request_id TEXT,

    -- User context
    user_id INTEGER REFERENCES users_new(id) ON DELETE SET NULL,
    ip_address TEXT,
    user_agent TEXT,

    -- HTTP context
    path TEXT,
    method TEXT,
    status_code INTEGER,
    duration_ms DOUBLE PRECISION,

    -- Error context
    error_type TEXT,
    error_message TEXT,
    stack_trace TEXT
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_request_id ON system_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_user_id ON system_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_logger ON system_logs(logger);
CREATE INDEX IF NOT EXISTS idx_system_logs_path ON system_logs(path);

-- JSONB GIN index for efficient context queries
CREATE INDEX IF NOT EXISTS idx_system_logs_context_gin ON system_logs USING GIN (context);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_system_logs_level_timestamp ON system_logs(level, timestamp DESC);

-- Partition management function (optional, for large-scale deployments)
-- Automatically partition by month for better query performance
-- (Implementation can be added later if needed)

COMMENT ON TABLE system_logs IS 'Unified logging system for request correlation, performance tracking, and error analysis';
COMMENT ON COLUMN system_logs.context IS 'JSONB field for structured logging data - supports rich queries';
COMMENT ON COLUMN system_logs.request_id IS 'Correlation ID for tracking all logs within a single request';
COMMENT ON COLUMN system_logs.duration_ms IS 'Request processing time in milliseconds';
```

### 8. Configuration Updates (`app/core/config.py`)

```python
# Add to Settings class

# Logging Configuration
LOG_LEVEL: str = Field(default="INFO", description="Logging level")
LOG_DATABASE_ENABLED: bool = Field(
    default=True,
    description="Enable database logging persistence"
)
LOG_CONSOLE_ENABLED: bool = Field(
    default=True,
    description="Enable console logging output"
)
LOG_REQUEST_BODY: bool = Field(
    default=False,
    description="Log request bodies (disable in production for privacy)"
)
LOG_RESPONSE_BODY: bool = Field(
    default=False,
    description="Log response bodies (disable in production for privacy)"
)
SLOW_REQUEST_THRESHOLD_MS: int = Field(
    default=1000,
    description="Threshold for slow request warnings (ms)"
)
```

### 9. Main Application Integration (`app/main.py`)

```python
from app.core.logging import configure_logging
from app.middleware.logging_middleware import LoggingMiddleware

# Configure logging on startup
configure_logging(
    log_level=settings.LOG_LEVEL,
    database_enabled=settings.LOG_DATABASE_ENABLED,
    console_enabled=settings.LOG_CONSOLE_ENABLED,
)

# Add logging middleware (BEFORE other middleware)
app.add_middleware(
    LoggingMiddleware,
    log_request_body=settings.LOG_REQUEST_BODY,
    log_response_body=settings.LOG_RESPONSE_BODY,
    slow_request_threshold_ms=settings.SLOW_REQUEST_THRESHOLD_MS,
    exclude_paths=["/health", "/docs", "/redoc", "/openapi.json", "/metrics"],
)
```

## Usage Examples

### Basic Logging

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# In async endpoint
@router.post("/curations")
async def create_curation(data: CurationCreate):
    await logger.info("Creating curation", scope_id=data.scope_id, gene_id=data.gene_id)

    try:
        curation = await crud_curation.create(db, data)
        await logger.info("Curation created successfully", curation_id=curation.id)
        return curation
    except Exception as e:
        await logger.error("Failed to create curation", error=e, scope_id=data.scope_id)
        raise

# In sync context
def process_batch_data(items):
    logger.sync_info("Processing batch", batch_size=len(items))
    # ... processing logic
    logger.sync_info("Batch processed successfully")
```

### Performance Monitoring

```python
from app.core.logging import get_logger, timed_operation, api_endpoint

logger = get_logger(__name__)

@router.get("/genes/{gene_id}/curations")
@api_endpoint("get_gene_curations")  # Automatic performance tracking
async def get_gene_curations(gene_id: int):
    return await crud_gene.get_curations(db, gene_id)

@timed_operation("calculate_clingen_score", warning_threshold_ms=200)
async def calculate_score(evidence_data: dict):
    # Complex scoring logic
    return computed_score
```

### Context Binding

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# Bind context for a specific operation
curation_logger = logger.bind(curation_id=42, scope_id=1)

# All logs from this logger instance will include curation_id and scope_id
await curation_logger.info("Starting validation")
# Output: ... Starting validation | request_id=abc-123 | user_id=5 | curation_id=42 | scope_id=1

await curation_logger.info("Validation complete")
# Output: ... Validation complete | request_id=abc-123 | user_id=5 | curation_id=42 | scope_id=1
```

### Database Query Logging

```python
from app.core.logging import database_query

@database_query("SELECT")
async def get_active_curations(db: Session, scope_id: int):
    # Query automatically timed and logged
    return db.query(Curation).filter(...).all()
```

### Performance Context Manager

```python
from app.core.logging import PerformanceMonitor

async with PerformanceMonitor("complex_calculation", gene_count=100):
    # Complex operation
    result = await perform_calculation()
# Automatically logs duration and any errors
```

## Implementation Steps

1. **Phase 1: Core Infrastructure** (2 hours)
   - [ ] Create `app/core/logging/` directory structure
   - [ ] Implement `context.py` (contextvars for request context)
   - [ ] Implement `unified_logger.py` (main logger class)
   - [ ] Implement `__init__.py` (public API)
   - [ ] Update `app/core/config.py` with logging settings

2. **Phase 2: Database Integration** (1.5 hours)
   - [ ] Create database schema `005_logging_tables.sql`
   - [ ] Implement `database_logger.py` (async PostgreSQL logging)
   - [ ] Run migration: `make db-migrate`
   - [ ] Test database logging with sample entries

3. **Phase 3: Performance Monitoring** (1.5 hours)
   - [ ] Implement `performance.py` (decorators and context managers)
   - [ ] Add `@timed_operation` to 3-5 key functions as examples
   - [ ] Test performance monitoring in dev environment

4. **Phase 4: Middleware Integration** (1.5 hours)
   - [ ] Implement `logging_middleware.py`
   - [ ] Integrate middleware in `main.py`
   - [ ] Test request correlation (all logs in one request share request_id)
   - [ ] Verify X-Request-ID and X-Processing-Time headers

5. **Phase 5: Migration & Testing** (1.5 hours)
   - [ ] Replace existing logging calls in 10+ files
   - [ ] Test async logging in endpoints
   - [ ] Test sync logging in CRUD operations
   - [ ] Verify database persistence
   - [ ] Test error logging with full context

## Testing Strategy

```python
# tests/unit/test_logging.py
import pytest
from app.core.logging import get_logger, bind_context, get_context, clear_context

def test_context_management():
    """Test context binding and retrieval"""
    clear_context()
    bind_context(request_id="test-123", user_id=42)

    context = get_context()
    assert context["request_id"] == "test-123"
    assert context["user_id"] == 42

    clear_context()
    assert get_context() == {}

@pytest.mark.asyncio
async def test_async_logging():
    """Test async logging methods"""
    logger = get_logger("test")
    bind_context(request_id="async-test")

    await logger.info("Test message", test_data="value")
    # Verify log appears in console and database

def test_sync_logging():
    """Test sync logging methods"""
    logger = get_logger("test_sync")
    logger.sync_info("Sync test message", sync_data="value")
    # Verify log appears in console

@pytest.mark.asyncio
async def test_performance_decorator():
    """Test performance monitoring decorator"""
    from app.core.logging import timed_operation

    @timed_operation("test_operation", warning_threshold_ms=10)
    async def slow_operation():
        import asyncio
        await asyncio.sleep(0.02)  # 20ms

    await slow_operation()
    # Verify warning logged for slow operation

@pytest.mark.asyncio
async def test_database_logger():
    """Test database log persistence"""
    from app.core.logging.database_logger import get_database_logger

    db_logger = get_database_logger()
    await db_logger.log(
        level="INFO",
        message="Test database log",
        source="test",
        request_id="db-test-123",
        extra_data={"test_key": "test_value"}
    )

    # Query database to verify log entry
    # SELECT * FROM system_logs WHERE request_id = 'db-test-123'
```

## Querying Logs in Production

```sql
-- Find all logs for a specific request
SELECT * FROM system_logs
WHERE request_id = 'abc-123-def-456'
ORDER BY timestamp;

-- Find slow requests (> 1 second)
SELECT request_id, path, method, duration_ms, timestamp
FROM system_logs
WHERE duration_ms > 1000
ORDER BY duration_ms DESC
LIMIT 50;

-- Error analysis by user
SELECT user_id, COUNT(*) as error_count,
       array_agg(DISTINCT error_type) as error_types
FROM system_logs
WHERE level IN ('ERROR', 'CRITICAL')
  AND timestamp > NOW() - INTERVAL '24 hours'
GROUP BY user_id
ORDER BY error_count DESC;

-- Performance analysis by endpoint
SELECT path,
       COUNT(*) as request_count,
       AVG(duration_ms) as avg_duration,
       MAX(duration_ms) as max_duration,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_duration
FROM system_logs
WHERE path IS NOT NULL
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY path
ORDER BY avg_duration DESC;

-- JSONB context queries (find logs with specific context)
SELECT * FROM system_logs
WHERE context @> '{"curation_id": 42}'::jsonb
ORDER BY timestamp DESC;
```

## Benefits Summary

### For Development
- **Request Tracing**: Track all logs for a curator's action via request_id
- **Performance Insights**: Instantly see which operations are slow
- **Rich Context**: Automatic user, request, and operation context in every log
- **Zero Boilerplate**: Drop-in replacement for `logging.getLogger()`
- **Async/Sync Support**: Works everywhere in FastAPI

### For Production
- **Database Persistence**: Query logs after issues occur
- **Error Analysis**: Full stack traces with request context
- **Performance Monitoring**: Identify bottlenecks with real production data
- **Audit Trail**: Complete record of all operations
- **Structured Data**: JSONB queries for complex analysis

### For Operations
- **Request Correlation**: Trace issues across multiple services
- **Performance Headers**: X-Request-ID and X-Processing-Time in responses
- **Automatic Metrics**: Duration, status codes, error rates
- **Log Rotation**: PostgreSQL partitioning (optional, for scale)

## Configuration

```bash
# .env.dev
LOG_LEVEL=DEBUG
LOG_DATABASE_ENABLED=true
LOG_CONSOLE_ENABLED=true
LOG_REQUEST_BODY=false  # Privacy: don't log request bodies
LOG_RESPONSE_BODY=false  # Privacy: don't log response bodies
SLOW_REQUEST_THRESHOLD_MS=1000

# .env.production
LOG_LEVEL=INFO
LOG_DATABASE_ENABLED=true
LOG_CONSOLE_ENABLED=true
LOG_REQUEST_BODY=false  # NEVER enable in production
LOG_RESPONSE_BODY=false  # NEVER enable in production
SLOW_REQUEST_THRESHOLD_MS=500
```

## Dependencies

- **Standard Library**: `logging`, `contextvars`, `uuid`, `asyncio`, `time`, `traceback`
- **Existing**: `sqlalchemy`, `fastapi`, `starlette`
- **No New Dependencies Required**

## Acceptance Criteria

- [ ] All logging components implemented and documented
- [ ] Database schema created and migrated
- [ ] Middleware integrated and tested
- [ ] Request correlation working (same request_id across logs)
- [ ] Performance decorators applied to 5+ key operations
- [ ] Database logging verified with sample queries
- [ ] At least 20 existing logging calls migrated
- [ ] Unit tests passing with >80% coverage
- [ ] CLAUDE.md updated with logging guidelines
- [ ] No performance degradation (async database writes)

## CLAUDE.md Update

```markdown
## Logging System (MUST ALWAYS USE)

Gene Curator uses a unified logging system with request correlation and database persistence.

### Basic Usage

```python
from app.core.logging import get_logger

logger = get_logger(__name__)  # NOT logging.getLogger()

# In async contexts (FastAPI endpoints)
await logger.info("Message", key="value", another_key=123)
await logger.error("Error occurred", error=exception, context_data="value")

# In sync contexts (CRUD, utilities)
logger.sync_info("Message", key="value")
logger.sync_error("Error", error=exception)
```

### NEVER Use These
- ❌ `logging.getLogger()` - Use `get_logger()` instead
- ❌ `print()` - Always use logger
- ❌ Manual context building - Context is automatic via middleware

### Performance Monitoring

```python
from app.core.logging import timed_operation, api_endpoint, database_query

@api_endpoint()  # Automatic endpoint timing
async def my_endpoint():
    pass

@timed_operation("complex_calculation", warning_threshold_ms=200)
async def calculate():
    pass

@database_query("SELECT")
async def query_data():
    pass
```

### Request Correlation

All logs within a request automatically include the same `request_id`.
Query logs: `SELECT * FROM system_logs WHERE request_id = 'abc-123'`

### Context Binding

```python
# Bind context for a specific operation
curation_logger = logger.bind(curation_id=42, scope_id=1)
await curation_logger.info("Message")  # Includes curation_id and scope_id
```

### When to Log
- **INFO**: Normal operations (curation created, gene assigned)
- **WARNING**: Slow operations, deprecated usage, recoverable errors
- **ERROR**: Failed operations, caught exceptions
- **DEBUG**: Detailed operation flow (disabled in production)

### Privacy
- NEVER log passwords, tokens, or sensitive user data
- Use structured logging (kwargs) for context
- Database logging is automatic - no manual writes needed
```

---

**Implementation Note**: This is a complete, production-ready logging system. Unlike the simplified version in `001-simple-structured-logging.md`, this includes database persistence, performance monitoring, and full production-grade features that make development and debugging significantly easier.
