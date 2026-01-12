"""
Unit tests for the unified logging system.
"""

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.core.logging import (
    bind_context,
    clear_context,
    get_context,
    get_logger,
    sanitize_dict,
    sanitize_for_logging,
)
from app.core.logging.rate_limiter import RateLimiter


class TestContextManagement:
    """Test context variable management."""

    def test_bind_context(self) -> None:
        """Test binding context variables."""
        clear_context()
        bind_context(request_id="test-123", user_id="user-456")

        context = get_context()
        assert context["request_id"] == "test-123"
        assert context["user_id"] == "user-456"

    def test_clear_context(self) -> None:
        """Test clearing context variables."""
        bind_context(request_id="test-123")
        clear_context()

        context = get_context()
        assert len(context) == 0

    def test_get_context_returns_copy(self) -> None:
        """Test that get_context returns a copy, not the original."""
        bind_context(request_id="test-123")

        context1 = get_context()
        context2 = get_context()

        # Modify one copy
        context1["modified"] = True

        # Other copy should be unchanged
        assert "modified" not in context2


class TestSanitization:
    """Test data sanitization for logging."""

    def test_sanitize_password(self) -> None:
        """Test password sanitization."""
        data = {"password": "secret123", "name": "John"}
        sanitized = sanitize_dict(data)

        assert sanitized["password"] == "[REDACTED]"  # noqa: S105
        assert sanitized["name"] == "John"

    def test_sanitize_token(self) -> None:
        """Test token sanitization."""
        data = {"access_token": "abc123", "name": "John"}
        sanitized = sanitize_dict(data)

        assert sanitized["access_token"] == "[REDACTED]"  # noqa: S105
        assert sanitized["name"] == "John"

    def test_sanitize_email(self) -> None:
        """Test email sanitization."""
        data = {"email": "test@example.com", "name": "John"}
        sanitized = sanitize_dict(data)

        assert sanitized["email"] == "[REDACTED]"
        assert sanitized["name"] == "John"

    def test_sanitize_nested_dict(self) -> None:
        """Test sanitization of nested dictionaries."""
        data = {
            "name": "John",
            "credentials": {"password": "secret123", "api_key": "key123"},
        }
        sanitized = sanitize_dict(data)

        assert sanitized["name"] == "John"
        # Nested dicts are converted to strings during sanitization
        assert "[REDACTED]" in str(sanitized["credentials"])

    def test_sanitize_list_of_dicts(self) -> None:
        """Test sanitization of lists containing dictionaries."""
        data = {
            "users": [
                {"name": "John", "password": "secret1"},
                {"name": "Jane", "password": "secret2"},
            ]
        }
        sanitized = sanitize_dict(data)

        assert sanitized["users"][0]["name"] == "John"
        assert sanitized["users"][0]["password"] == "[REDACTED]"  # noqa: S105
        assert sanitized["users"][1]["name"] == "Jane"
        assert sanitized["users"][1]["password"] == "[REDACTED]"  # noqa: S105

    def test_sanitize_for_logging_string(self) -> None:
        """Test sanitization of string values."""
        result = sanitize_for_logging("test@example.com")
        assert result == "[REDACTED_EMAIL]"

    def test_sanitize_for_logging_primitives(self) -> None:
        """Test sanitization preserves primitives."""
        assert sanitize_for_logging(123) == 123
        assert sanitize_for_logging(True) is True
        assert sanitize_for_logging(None) is None


class TestRateLimiter:
    """Test rate limiting functionality."""

    def test_rate_limiter_allows_under_limit(self) -> None:
        """Test that rate limiter allows logs under the limit."""
        limiter = RateLimiter(max_logs_per_second=10)

        # Should allow first 10 logs
        for _ in range(10):
            assert limiter.should_log() is True

    def test_rate_limiter_blocks_over_limit(self) -> None:
        """Test that rate limiter blocks logs over the limit."""
        limiter = RateLimiter(max_logs_per_second=10)

        # Allow first 10 logs
        for _ in range(10):
            limiter.should_log()

        # 11th log should be blocked
        assert limiter.should_log() is False


class TestUnifiedLogger:
    """Test unified logger functionality."""

    def test_get_logger_creates_logger(self) -> None:
        """Test that get_logger creates a logger instance."""
        logger = get_logger("test.module")
        assert logger is not None
        assert logger.name == "test.module"

    def test_get_logger_caches_loggers(self) -> None:
        """Test that get_logger returns cached loggers."""
        logger1 = get_logger("test.module")
        logger2 = get_logger("test.module")
        assert logger1 is logger2

    def test_logger_bind_creates_new_instance(self) -> None:
        """Test that logger.bind() creates a new logger instance."""
        logger1 = get_logger("test.module")
        logger2 = logger1.bind(request_id="test-123")

        # Should be different instances
        assert logger1 is not logger2

        # But same name
        assert logger1.name == logger2.name

    @patch("app.core.logging.unified_logger.logging.Logger")
    def test_logger_info_logs_to_console(self, mock_logger: Any) -> None:
        """Test that logger.info() logs to console."""
        logger = get_logger("test.module")
        logger._console_logger = MagicMock()

        logger.info("Test message", key="value")

        # Should call console logger
        logger._console_logger.info.assert_called_once()

    @patch("app.core.logging.unified_logger.logging.Logger")
    def test_logger_error_logs_to_console(self, mock_logger: Any) -> None:
        """Test that logger.error() logs to console."""
        logger = get_logger("test.module")
        logger._console_logger = MagicMock()

        logger.error("Error message", error=Exception("Test error"))

        # Should call console logger
        logger._console_logger.error.assert_called_once()


@pytest.mark.asyncio
class TestAsyncLogging:
    """Test async logging functionality."""

    async def test_logger_detects_async_context(self) -> None:
        """Test that logger detects async context."""
        logger = get_logger("test.async")
        logger._console_logger = MagicMock()
        logger._database_logger = None  # Disable DB logging for test

        # Should not raise in async context
        logger.info("Test message")

        # Give a moment for any async operations
        await asyncio.sleep(0.01)

        # Should have logged to console
        logger._console_logger.info.assert_called_once()

    async def test_logger_handles_sync_context(self) -> None:
        """Test that logger handles sync context gracefully."""

        def sync_function() -> None:
            logger = get_logger("test.sync")
            logger._console_logger = MagicMock()
            logger._database_logger = None

            # Should not raise in sync context
            logger.info("Test message")

            # Should have logged to console
            logger._console_logger.info.assert_called_once()

        sync_function()
