"""
Logging middleware for automatic request context tracking.

This middleware automatically extracts request context and binds it to the logging system,
ensuring all logs within a request include request_id, user_id, endpoint, etc.
"""

import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import bind_context, clear_context, get_logger

logger = get_logger(__name__)

# Client-supplied X-Request-ID is reused only if it is safe to log and echo back
SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")
MAX_PATH_LENGTH = 2048


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic request context tracking and logging.

    Automatically binds request metadata to all logs within the request lifecycle.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process request and bind context for logging.

        Args:
            request: FastAPI request object
            call_next: Next middleware or endpoint handler

        Returns:
            Response from the endpoint
        """
        client_id = request.headers.get("X-Request-ID", "")
        request_id = (
            client_id if SAFE_REQUEST_ID.fullmatch(client_id) else str(uuid.uuid4())
        )
        request.state.request_id = request_id

        # Path params reach PostgreSQL, which rejects NUL bytes with a 500 (#378)
        path = request.scope["path"]
        if "\x00" in path or len(path) > MAX_PATH_LENGTH:
            too_long = len(path) > MAX_PATH_LENGTH
            return JSONResponse(
                status_code=414 if too_long else 400,
                content={"detail": "Path too long" if too_long else "Invalid path"},
                headers={"X-Request-ID": request_id},
            )

        # Extract request context
        context = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "ip_address": self._extract_client_ip(request),
            "user_agent": request.headers.get("User-Agent"),
        }

        # Extract user from request state if available
        if hasattr(request.state, "current_user") and request.state.current_user:
            user = request.state.current_user
            context["user_id"] = str(getattr(user, "id", None))
            context["username"] = getattr(user, "username", None) or getattr(
                user, "email", None
            )

        # Bind context for all logs within this request
        bind_context(**context)

        # Track request timing
        start_time = time.perf_counter()

        try:
            # Log request start
            logger.info("Request started")

            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log request completion
            logger.info(
                "Request completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(round(duration_ms, 2))

            return response

        except Exception as e:
            # Calculate duration on error
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log request failure
            logger.error(
                "Request failed",
                error=e,
                duration_ms=round(duration_ms, 2),
            )
            raise

        finally:
            # Clear context after request
            clear_context()

    def _extract_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request.

        Args:
            request: FastAPI request object

        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header first (for proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"
