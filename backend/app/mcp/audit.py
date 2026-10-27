"""Channel stamping, audit metadata and tool-call logging for MCP (#462).

The MCP layer calls the API in process and marks those calls in the ASGI scope (a
key no network client can set). Only marked calls may carry X-GC-Channel/X-GC-Client;
they are stripped from every other request, so callers cannot spoof the channel.
The values reach PostgreSQL as app.channel/app.client (transaction-local), and the
audit_log trigger from 059 copies them into change_metadata.
"""

import time
from contextvars import ContextVar
from typing import Any
from urllib.parse import unquote

import httpx
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import ToolResult
from mcp import types as mt
from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, SessionTransaction
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.logging import get_logger

logger = get_logger(__name__)

INTERNAL_SCOPE_KEY = "gene_curator.mcp_internal"
CHANNEL_HEADER = "x-gc-channel"
CLIENT_HEADER = "x-gc-client"
_CHANNEL_HEADERS = {CHANNEL_HEADER.encode(), CLIENT_HEADER.encode()}

# (channel, client) of the request being served; None outside MCP calls
request_channel: ContextVar[tuple[str, str] | None] = ContextVar(
    "request_channel", default=None
)


def mark_internal(app: ASGIApp) -> ASGIApp:
    """Wrap app so every request through it is marked as an in-process MCP call."""

    async def marked(scope: Scope, receive: Receive, send: Send) -> None:
        await app({**scope, INTERNAL_SCOPE_KEY: True}, receive, send)

    return marked


def is_internal(scope: Scope) -> bool:
    return bool(scope.get(INTERNAL_SCOPE_KEY))


class ChannelHeaderMiddleware:
    """Strip channel headers from outside requests; bind them for internal calls."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if not is_internal(scope):
            headers = [h for h in scope["headers"] if h[0] not in _CHANNEL_HEADERS]
            await self.app({**scope, "headers": headers}, receive, send)
            return
        found = {k.decode(): v.decode() for k, v in scope["headers"]}
        channel = found.get(CHANNEL_HEADER)
        reset = request_channel.set(
            (channel, unquote(found.get(CLIENT_HEADER, ""))) if channel else None
        )
        try:
            await self.app(scope, receive, send)
        finally:
            request_channel.reset(reset)


@event.listens_for(Session, "after_begin")
def _apply_channel(
    session: Session, transaction: SessionTransaction, connection: Connection
) -> None:
    found = request_channel.get()
    if found and connection.dialect.name == "postgresql":
        connection.execute(
            text(
                "SELECT set_config('app.channel', :channel, true), "
                "set_config('app.client', :client, true)"
            ),
            {"channel": found[0], "client": found[1]},
        )


# Closed set of error codes a client may branch on (fleet envelope plus conflict)
_STATUS_CODES = {
    400: "invalid_input",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "invalid_input",
    409: "conflict",
    413: "invalid_input",
    422: "invalid_input",
    429: "rate_limited",
}


def error_code(status: int) -> str:
    if status in _STATUS_CODES:
        return _STATUS_CODES[status]
    return "upstream_unavailable" if status in (502, 503, 504) else "internal"


# One-line next step per error, so an agent recovers without probing (MCP study F8)
_HINTS = {
    400: "fix what the detail names and retry",
    401: "the access token is invalid or expired; create a new one in the web app",
    403: "check your role with list_scopes (user_role); nobody approves their own work",
    404: "check the id; list_scopes and list_curations return valid ids",
    409: "the detail says why; a retry will not help",
    422: "fix the arguments the detail names and retry",
    429: "wait a minute and retry",
}
_TOOL_HINTS = {
    (
        "bulk_create_gene_assignments",
        403,
    ): "scope admins only; curators assign one gene "
    "at a time with create_gene_assignment",
    ("execute_workflow_transition", 400): "get_workflow_state lists the moves you may "
    "make and why the others are blocked",
}
_STALE_HINT = (
    "re-read the item (get_curation or get_precuration), merge your change and retry"
)


def _tool_error(cause: httpx.HTTPStatusError, tool: str) -> ToolError:
    status = cause.response.status_code
    message = f"{error_code(status)}: HTTP {status}"
    detail: Any = None
    if status < 500:  # the API's own detail, as the same user would see it
        try:
            detail = cause.response.json().get("detail")
        except ValueError:
            detail = None
        if detail:
            message += f": {detail}"
    hint = _TOOL_HINTS.get((tool, status)) or _HINTS.get(status)
    if isinstance(detail, dict) and "current_lock_version" in detail:  # stale save
        hint = _STALE_HINT
    return ToolError(f"{message}\nnext: {hint}" if hint else message)


def correlation_id() -> str | None:
    try:
        return getattr(get_http_request().state, "request_id", None)
    except RuntimeError:
        return None


class ToolAuditMiddleware(Middleware):
    """Logs tool, outcome, duration and correlation id (never arguments); maps errors."""

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        start = time.perf_counter()
        outcome = "ok"
        try:
            result = await call_next(context)
            # Text only: clients bill structuredContent again on top of its text copy
            return ToolResult(content=result.content, meta=result.meta)
        except Exception as exc:
            cause: BaseException | None = exc
            while cause is not None and not isinstance(cause, httpx.HTTPStatusError):
                cause = cause.__cause__
            if cause is None:
                outcome = "error"
                raise  # mask_error_details hides unexpected details
            error = _tool_error(cause, context.message.name)
            outcome = str(error).split(":", 1)[0]
            raise error from exc
        finally:
            logger.info(
                "MCP tool call",
                tool=context.message.name,
                outcome=outcome,
                duration_ms=round((time.perf_counter() - start) * 1000, 2),
                request_id=correlation_id(),
            )
