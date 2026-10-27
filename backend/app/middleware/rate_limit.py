"""Token-bucket rate limiting for every route, tiers from config/api.yaml (#377, #478)."""

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.api_config import get_feature_flags, get_rate_limit
from app.core.security import PAT_PREFIX, verify_token
from app.mcp.audit import is_internal
from app.mcp.auth import pat_user

MAX_BUCKETS = 10_000


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per user (valid JWT or personal access token) or per client IP; off unless features.enable_rate_limiting.

    ponytail: buckets live in process memory, so each uvicorn worker limits on its own;
    move to Redis if exact cross-worker limits matter. Anonymous clients are keyed by
    request.client, so run uvicorn with --forwarded-allow-ips for the proxy in front.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last seen)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # In-process MCP calls were already counted on their /mcp request
        if not get_feature_flags().enable_rate_limiting or is_internal(request.scope):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        bearer = auth[7:] if auth.lower().startswith("bearer ") else ""
        pat = (
            await run_in_threadpool(pat_user, request.app, bearer)
            if bearer.startswith(PAT_PREFIX)
            else None
        )
        payload = verify_token(bearer) if bearer and pat is None else None
        if pat:  # personal access tokens share their owner's bucket
            key, tier = f"user:{pat}", "authenticated"
        # Refresh tokens are not bearer credentials: they stay in the IP bucket
        elif payload and payload.get("sub") and payload.get("type") != "refresh":
            key = f"user:{payload['sub']}"
            tier = "admin" if payload.get("role") == "admin" else "authenticated"
        else:
            key = f"ip:{request.client.host if request.client else 'unknown'}"
            tier = "default"
        limit = get_rate_limit(tier)

        now = time.monotonic()
        if len(self.buckets) > MAX_BUCKETS:
            self.buckets.clear()  # bounded memory; worst case one free burst per client
        tokens, last = self.buckets.get(key, (float(limit.burst_size), now))
        tokens = min(
            float(limit.burst_size),
            tokens + (now - last) * limit.requests_per_minute / 60,
        )
        if tokens < 1:
            self.buckets[key] = (tokens, now)
            retry_after = int((1 - tokens) * 60 / limit.requests_per_minute) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={"Retry-After": str(retry_after)},
            )
        self.buckets[key] = (tokens - 1, now)
        return await call_next(request)
