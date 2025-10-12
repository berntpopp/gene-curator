# Enhancement: Simple Structured Logging

**Priority**: High
**Complexity**: Low
**Estimated Effort**: 2-3 hours
**Reference**: Simplified from kidney-genetics-db logging system

## Overview

Implement structured logging with request correlation for Gene Curator's interactive curation workflows. Unlike kidney-genetics-db's full system (533 lines + database persistence), this provides just what's needed for ~20 curators: console-based structured logging with context binding.

## Current State

- Basic Python logging used inconsistently
- No request correlation tracking
- Difficult to trace issues across curator sessions

## Why Simplified?

**kidney-genetics-db needs**:
- Database log persistence (analyzing 10,000+ pipeline operations)
- Performance decorators (optimizing high-throughput operations)
- 533 lines of infrastructure

**Gene Curator needs**:
- Console-based structured logging (20 interactive curators)
- Request correlation (trace curator actions)
- ~100-150 lines, not 533

**Key Difference**: Gene Curator's bottleneck is curator time (5-10 min/curation), not system performance. Database log persistence and performance decorators are unnecessary.

## Proposed Implementation

### Core Component

**Structured Logger** (`backend/app/core/logging.py`)

```python
"""
Simple structured logging for Gene Curator.

Console-only output with request correlation. No database persistence.
"""

import logging
import sys
from contextvars import ContextVar
from typing import Any, Dict

# Request context for correlation
_request_context: ContextVar[Dict[str, Any]] = ContextVar("request_context", default={})


class StructuredFormatter(logging.Formatter):
    """Format logs with structured context"""

    def format(self, record: logging.LogRecord) -> str:
        # Get context
        context = _request_context.get()

        # Build message with context
        parts = [record.getMessage()]

        # Add request_id if available
        if request_id := context.get("request_id"):
            parts.append(f"request_id={request_id}")

        # Add user context
        if user_id := context.get("user_id"):
            parts.append(f"user_id={user_id}")
        elif username := context.get("username"):
            parts.append(f"username={username}")

        # Add extra attributes from logging call
        if hasattr(record, "extra_data"):
            for key, value in record.extra_data.items():
                parts.append(f"{key}={value}")

        message = " | ".join(parts)

        # Standard log format
        return f"{self.formatTime(record)} - {record.name} - {record.levelname} - {message}"


def get_logger(name: str) -> logging.Logger:
    """
    Get a structured logger instance.

    Drop-in replacement for logging.getLogger() with structured output.
    """
    logger = logging.getLogger(name)

    # Configure only once
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


def bind_context(**kwargs) -> None:
    """Bind context for current request/operation"""
    context = _request_context.get().copy()
    context.update(kwargs)
    _request_context.set(context)


def clear_context() -> None:
    """Clear request context"""
    _request_context.set({})


def get_context() -> Dict[str, Any]:
    """Get current context"""
    return _request_context.get().copy()


# Convenience function for structured logging
def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs):
    """Log with additional structured data"""
    # Create log record with extra data
    record = logger.makeRecord(
        logger.name,
        getattr(logging, level.upper()),
        "(unknown file)",
        0,
        message,
        (),
        None
    )
    record.extra_data = kwargs
    logger.handle(record)
```

### Middleware for Request Correlation

**Logging Middleware** (`backend/app/middleware/logging.py`)

```python
"""Request correlation middleware"""

import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import bind_context, clear_context, get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Add request correlation to all API requests"""

    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Bind to context
        bind_context(request_id=request_id)

        # Log request start
        logger.info(f"{request.method} {request.url.path}")

        try:
            response = await call_next(request)

            # Log response
            logger.info(f"Response {response.status_code}")

            return response
        finally:
            # Clear context after request
            clear_context()
```

### Usage Pattern

```python
from app.core.logging import get_logger, log_with_context

logger = get_logger(__name__)

# Simple logging (context automatically included from middleware)
logger.info("Curation created")

# Structured logging with extra data
log_with_context(
    logger,
    "info",
    "Curation created",
    curation_id=curation.id,
    scope_id=scope.id,
    curator_email=user.email
)

# Output:
# 2025-01-12 10:30:15 - app.crud.curation - INFO - Curation created | request_id=abc-123 | user_id=5 | curation_id=42 | scope_id=1 | curator_email=curator@example.com
```

### Configuration

**Add to Settings** (`backend/app/core/config.py`)

```python
# Logging configuration
LOG_LEVEL: str = "INFO"
LOG_FORMAT: str = "structured"  # or "json" for production
```

## Implementation Steps

1. **Create logging module** (`backend/app/core/logging.py`)
   - StructuredFormatter class (~40 lines)
   - get_logger(), bind_context(), clear_context() (~60 lines)
   - Total: ~100 lines (vs 533 in kidney-genetics-db)

2. **Add middleware** (`backend/app/middleware/logging.py`)
   - RequestLoggingMiddleware (~30 lines)
   - Register in main.py

3. **Replace existing logging**
   ```bash
   # Find all logging.getLogger() calls
   rg "logging\.getLogger" backend/app

   # Replace with get_logger()
   from app.core.logging import get_logger
   logger = get_logger(__name__)
   ```

4. **Update CLAUDE.md**
   ```markdown
   ## Logging (MUST USE)
   - ALWAYS use `get_logger(__name__)`
   - NEVER use `logging.getLogger()` or `print()`
   - Logs automatically include request_id from middleware
   ```

## Benefits

- **Request Correlation**: Trace all logs for a curator's action via request_id
- **Structured Output**: Easily parsable logs for debugging
- **Simple**: 100-150 lines total, not 533 + database persistence
- **DRY**: Single logging interface throughout codebase
- **Zero Overhead**: No database writes, no performance decorators

## What We're NOT Implementing (vs kidney-genetics-db)

❌ **Database log persistence** (20 curators don't need PostgreSQL logging)
❌ **Performance decorators** (@timed_operation) - curator time is bottleneck, not API latency
❌ **Async/sync dual methods** - unnecessary complexity for Gene Curator's use case
❌ **DatabaseLogger class** (150 lines we don't need)

## Testing

```python
# tests/unit/test_logging.py
def test_structured_logging():
    """Test structured log output"""
    from app.core.logging import get_logger, bind_context

    logger = get_logger("test")
    bind_context(request_id="test-123", user_id=5)

    # Verify context in log output
    logger.info("Test message")
    # Output should include: request_id=test-123 | user_id=5

def test_request_middleware():
    """Test request correlation middleware"""
    # Verify middleware adds request_id to context
    # Verify context cleared after request
```

## Dependencies

- Standard library: `logging`, `contextvars`, `uuid`

## Acceptance Criteria

- [ ] StructuredFormatter and get_logger() implemented (~100 lines)
- [ ] RequestLoggingMiddleware for automatic request_id binding
- [ ] At least 10 existing logging calls replaced
- [ ] Request correlation working (all logs in one request share request_id)
- [ ] CLAUDE.md updated with DRY logging guidelines
- [ ] Unit tests for structured formatting and context binding
- [ ] No database persistence, no performance decorators (KISS principle)

---

**Key Difference from kidney-genetics-db**: Console-only, ~100 lines, optimized for interactive workflows, not high-throughput pipelines.
