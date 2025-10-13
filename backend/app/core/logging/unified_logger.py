"""
Unified Logger - Main logging interface for Gene Curator.

FIXES APPLIED:
- #11: Auto-detect async context (no dual sync/async methods)
- #15: Dependency Injection for database logger
- #17: Optimized string formatting

Provides a single interface for all logging needs that routes to multiple
destinations (console + database) while maintaining performance and
providing rich context information.
"""

import asyncio
import logging

# Type hint for database logger (avoid circular import)
from typing import TYPE_CHECKING, Any

from .context import get_context
from .rate_limiter import RateLimiter

if TYPE_CHECKING:
    from .database_logger import DatabaseLogger


class UnifiedLogger:
    """
    Unified logging interface that routes to multiple destinations.

    SIMPLIFIED: Auto-detects async vs sync context.
    No more dual methods (info/sync_info).

    This class provides a single interface for all logging needs, automatically
    routing log entries to both console logging (immediate) and database logging
    (async) while including automatic context injection and structured logging.

    Drop-in replacement for standard Python logging with enhanced features.
    """

    def __init__(
        self,
        name: str,
        console_logger: logging.Logger | None = None,
        database_logger: "DatabaseLogger | None" = None,
        rate_limiter: RateLimiter | None = None,
    ):
        """
        Initialize the unified logger.

        FIX #15: Dependency injection for logger dependencies.

        Args:
            name: Logger name (typically __name__ from calling module)
            console_logger: Console logger instance (optional)
            database_logger: Database logger instance (optional)
            rate_limiter: Rate limiter instance (optional)
        """
        self.name = name
        self._console_logger = console_logger or logging.getLogger(name)
        self._database_logger = database_logger
        self._rate_limiter = rate_limiter or RateLimiter(max_logs_per_second=100)
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
        """
        Format message for console logging with context.

        FIX #17: Optimized string formatting using single f-string.
        """
        context = self._get_current_context()

        # Build parts list with conditional inclusion
        parts = [
            message,
            f"request_id={context['request_id']}"
            if context.get("request_id")
            else None,
            f"user_id={context['user_id']}" if context.get("user_id") else None,
        ]

        # Add extra data
        if extra_data:
            for key, value in extra_data.items():
                if key not in context:  # Avoid duplicates
                    parts.append(f"{key}={value}")

        # Filter out None values and join
        return " | ".join(p for p in parts if p is not None)

    async def _log_to_database_async(
        self,
        level: str,
        message: str,
        error: Exception | None = None,
        extra_data: dict[str, Any] | None = None,
    ):
        """Log to database using async database logger."""
        if not self._database_logger:
            return

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
            self._console_logger.error(
                f"Database logging failed: {e}. Original message: {message}"
            )

    def _handle_db_log_exception(self, task: asyncio.Task) -> None:
        """
        Handle exceptions from database logging tasks.

        Following asyncio best practices (Python 3.14 guidelines):
        1. Check if task is cancelled (not an error condition)
        2. Check if task is done before calling exception()
        3. Log exceptions with full context for debugging
        4. Handle callback exceptions safely (safety net)

        Args:
            task: The completed asyncio Task
        """
        try:
            # 1. Handle cancellation separately (not an error)
            if task.cancelled():
                self._console_logger.debug(
                    "Database logging task was cancelled (expected during shutdown)"
                )
                return

            # 2. Check if task is done before calling exception()
            if not task.done():
                self._console_logger.warning(
                    "Callback fired on non-completed task (unexpected state)"
                )
                return

            # 3. Check for exceptions and log with context
            exc = task.exception()
            if exc is not None:
                # Log with full traceback and context for debugging
                self._console_logger.error(
                    f"Database logging task failed: {type(exc).__name__}: {exc}",
                    exc_info=exc,
                    extra={
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
                        "logger_name": self.name,
                    },
                )

        except Exception as callback_exc:
            # 4. Safety net: callback itself shouldn't crash
            # This protects against bugs in the callback code
            self._console_logger.critical(
                f"Critical: Exception in database logging callback: {callback_exc}",
                exc_info=callback_exc,
            )

    def _log_to_console(
        self, level: str, message: str, extra_data: dict[str, Any] | None = None
    ):
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
        new_logger = UnifiedLogger(
            self.name, self._console_logger, self._database_logger, self._rate_limiter
        )
        new_logger._bound_context = {**self._bound_context, **kwargs}
        return new_logger

    # FIX #11: Auto-detect async context (single method set, not dual)

    def log(
        self,
        level: str,
        message: str,
        *,
        error: Exception | None = None,
        extra: dict[str, Any] | None = None,
        **kwargs,
    ):
        """
        Log a message at the specified level.

        FIX #11: Auto-detects async vs sync context - no more sync_log() method.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            error: Exception object for error logs
            extra: Additional structured data
            **kwargs: Additional key-value pairs for structured logging
        """
        # Check rate limit
        if not self._rate_limiter.should_log():
            return

        # Combine extra data and kwargs
        extra_data = {**(extra or {}), **kwargs}

        # Log to console synchronously
        self._log_to_console(level, message, extra_data)

        # Log to database asynchronously (auto-detect context)
        try:
            # Try to get running loop
            loop = asyncio.get_running_loop()
            # In async context - schedule as task
            task = loop.create_task(
                self._log_to_database_async(level, message, error, extra_data)
            )
            # Add done callback to handle exceptions properly
            task.add_done_callback(self._handle_db_log_exception)
        except RuntimeError:
            # Not in async context - can't write to database
            # This is expected in sync contexts (startup, tests, etc.)
            pass

    def debug(self, message: str, **kwargs):
        """Log a debug message."""
        self.log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log an info message."""
        self.log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log a warning message."""
        self.log("WARNING", message, **kwargs)

    def error(self, message: str, error: Exception | None = None, **kwargs):
        """Log an error message."""
        self.log("ERROR", message, error=error, **kwargs)

    def critical(self, message: str, error: Exception | None = None, **kwargs):
        """Log a critical message."""
        self.log("CRITICAL", message, error=error, **kwargs)


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
        # Import here to avoid circular dependency
        from .database_logger import get_database_logger

        _logger_cache[name] = UnifiedLogger(name, database_logger=get_database_logger())
    return _logger_cache[name]
