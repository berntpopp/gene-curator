"""
Request context management for unified logging.

FIXES:
- Issue #3: Context variable default handling
- Issue #10: Over-engineered (7 ContextVars → 1 dict, 130 lines → 40 lines)

Uses Python contextvars for request-scoped context that automatically
propagates through async operations within a request lifecycle.
"""

import contextvars
from typing import Any

# Single context variable with dict (instead of 7 separate ones)
# FIX B039: Use None as default (not mutable {})
_log_context: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "log_context", default=None
)


def bind_context(**kwargs) -> None:
    """
    Bind values to the current logging context.

    This uses a context variable to store request-scoped logging context
    that will be automatically included in all log entries within the request.

    Args:
        **kwargs: Key-value pairs to bind to the context
    """
    current = _log_context.get() or {}
    _log_context.set({**current, **kwargs})


def clear_context() -> None:
    """Clear all logging context variables."""
    _log_context.set({})


def get_context() -> dict[str, Any]:
    """
    Get the current logging context.

    Returns a copy to prevent external mutation.
    """
    context = _log_context.get() or {}
    return context.copy()
