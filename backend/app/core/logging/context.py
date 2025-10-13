"""
Request context management for unified logging.

FIXES:
- Issue #3: Context variable default handling
- Issue #10: Over-engineered (7 ContextVars → 1 dict, 130 lines → 40 lines)

Uses Python contextvars for request-scoped context that automatically
propagates through async operations within a request lifecycle.
"""

import contextvars
import uuid
from typing import Any

from fastapi import Request

from .utils import extract_client_ip

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

    # Extract IP address using DRY utility
    context["ip_address"] = extract_client_ip(request)

    # Extract user agent
    context["user_agent"] = request.headers.get("User-Agent")

    # Extract user from request state (if available)
    if hasattr(request.state, "current_user"):
        user = request.state.current_user
        if user:
            context["user_id"] = getattr(user, "id", None)
            context["username"] = getattr(user, "username", None) or getattr(
                user, "email", None
            )

    return context
