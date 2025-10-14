"""
Performance monitoring decorators for the unified logging system.

Provides decorators for tracking operation performance, database queries,
and API endpoint response times with automatic logging integration.
"""

import asyncio
import contextlib
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, Literal, ParamSpec, TypeVar, cast

P = ParamSpec("P")
R = TypeVar("R")

# Lazy import to avoid circular dependency
_logger = None


def _get_logger() -> Any:
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
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator to time operations and log performance metrics.

    Args:
        operation_name: Name of the operation (defaults to function name)
        warning_threshold_ms: Log warning if operation takes longer than this (ms)
        error_threshold_ms: Log error if operation takes longer than this (ms)
        include_args: Whether to include function arguments in logs
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        name = operation_name or func.__name__

        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                start_time = time.perf_counter()

                # Build context for logging
                context: dict[str, Any] = {"operation": name}
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
                        _get_logger().error(
                            "Operation exceeded error threshold", **context
                        )
                    elif duration_ms > warning_threshold_ms:
                        _get_logger().warning(
                            "Operation exceeded warning threshold", **context
                        )
                    else:
                        _get_logger().info("Operation completed", **context)

                    return cast(R, result)

                except Exception as e:
                    # Log the error with timing
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)
                    context["error"] = str(e)
                    _get_logger().error("Operation failed", **context)
                    raise

            return cast(Callable[P, R], async_wrapper)
        else:

            @wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                start_time = time.perf_counter()

                # Build context for logging
                context: dict[str, Any] = {"operation": name}
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
                        _get_logger().error(
                            "Operation exceeded error threshold", **context
                        )
                    elif duration_ms > warning_threshold_ms:
                        _get_logger().warning(
                            "Operation exceeded warning threshold", **context
                        )
                    else:
                        _get_logger().info("Operation completed", **context)

                    return result

                except Exception as e:
                    # Log the error with timing
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)
                    context["error"] = str(e)
                    _get_logger().error("Operation failed", **context)
                    raise

            return cast(Callable[P, R], sync_wrapper)

    return decorator


def database_query(
    query_type: str = "SELECT",
) -> Callable[[Callable[P, R]], Callable[P, R]]:
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


def api_endpoint(
    endpoint_name: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
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


def batch_operation(
    batch_name: str, batch_size_getter: Callable[..., int] | None = None
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator for batch processing operations with per-item metrics.

    Args:
        batch_name: Name of the batch operation
        batch_size_getter: Function to extract batch size from arguments
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                start_time = time.perf_counter()

                # Get batch size if getter provided
                batch_size: int | None = None
                if batch_size_getter:
                    with contextlib.suppress(Exception):
                        batch_size = batch_size_getter(*args, **kwargs)

                context: dict[str, Any] = {
                    "operation": batch_name,
                    "batch_size": batch_size,
                }

                try:
                    _get_logger().info("Batch operation started", **context)
                    result = await func(*args, **kwargs)

                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)

                    if batch_size:
                        context["ms_per_item"] = round(duration_ms / batch_size, 2)
                        context["items_per_second"] = round(
                            batch_size / (duration_ms / 1000), 2
                        )

                    _get_logger().info("Batch operation completed", **context)
                    return cast(R, result)

                except Exception as e:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)
                    context["error"] = str(e)
                    _get_logger().error("Batch operation failed", **context)
                    raise

            return cast(Callable[P, R], async_wrapper)
        else:

            @wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                start_time = time.perf_counter()

                # Get batch size if getter provided
                batch_size: int | None = None
                if batch_size_getter:
                    with contextlib.suppress(Exception):
                        batch_size = batch_size_getter(*args, **kwargs)

                context: dict[str, Any] = {
                    "operation": batch_name,
                    "batch_size": batch_size,
                }

                try:
                    _get_logger().info("Batch operation started", **context)
                    result = func(*args, **kwargs)

                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)

                    if batch_size:
                        context["ms_per_item"] = round(duration_ms / batch_size, 2)
                        context["items_per_second"] = round(
                            batch_size / (duration_ms / 1000), 2
                        )

                    _get_logger().info("Batch operation completed", **context)
                    return result

                except Exception as e:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)
                    context["error"] = str(e)
                    _get_logger().error("Batch operation failed", **context)
                    raise

            return cast(Callable[P, R], sync_wrapper)

    return decorator


class PerformanceMonitor:
    """Context manager for performance monitoring blocks of code."""

    def __init__(self, operation_name: str, **extra_context: Any) -> None:
        self.operation_name = operation_name
        self.extra_context = extra_context
        self.start_time: float | None = None

    def __enter__(self) -> "PerformanceMonitor":
        self.start_time = time.perf_counter()
        _get_logger().debug(
            "Performance block started",
            operation=self.operation_name,
            **self.extra_context,
        )
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Literal[False]:
        assert self.start_time is not None
        duration_ms = (time.perf_counter() - self.start_time) * 1000

        context: dict[str, Any] = {
            "operation": self.operation_name,
            "duration_ms": round(duration_ms, 2),
            **self.extra_context,
        }

        if exc_type:
            context["error"] = str(exc_val)
            _get_logger().error("Performance block failed", **context)
        else:
            _get_logger().info("Performance block completed", **context)

        return False  # Don't suppress exceptions

    async def __aenter__(self) -> "PerformanceMonitor":
        self.start_time = time.perf_counter()
        _get_logger().debug(
            "Performance block started",
            operation=self.operation_name,
            **self.extra_context,
        )
        return self

    async def __aexit__(
        self, exc_type: Any, exc_val: Any, exc_tb: Any
    ) -> Literal[False]:
        assert self.start_time is not None
        duration_ms = (time.perf_counter() - self.start_time) * 1000

        context: dict[str, Any] = {
            "operation": self.operation_name,
            "duration_ms": round(duration_ms, 2),
            **self.extra_context,
        }

        if exc_type:
            context["error"] = str(exc_val)
            _get_logger().error("Performance block failed", **context)
        else:
            _get_logger().info("Performance block completed", **context)

        return False  # Don't suppress exceptions
