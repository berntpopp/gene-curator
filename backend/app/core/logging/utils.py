"""
Shared utilities for the logging system.

Fixes Issue #9: Eliminates DRY violation where IP extraction was duplicated
in context.py, database_logger.py, and logging_middleware.py.
"""

from fastapi import Request


def extract_client_ip(request: Request) -> str:
    """
    Extract client IP address from request, handling X-Forwarded-For.

    This eliminates the DRY violation where IP extraction was duplicated
    in multiple locations across the logging system.

    Args:
        request: FastAPI Request object

    Returns:
        Client IP address as string
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # First IP in X-Forwarded-For chain is the client
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "unknown"
