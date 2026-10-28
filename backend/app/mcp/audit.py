"""Channel stamping, audit metadata and tool-call logging for MCP (#462).

The MCP layer calls the API in process and marks those calls in the ASGI scope (a
key no network client can set). Only marked calls may carry X-GC-Channel/X-GC-Client;
they are stripped from every other request, so callers cannot spoof the channel.
The values reach PostgreSQL as app.channel/app.client (transaction-local), and the
audit_log trigger from 059 copies them into change_metadata.
"""

import difflib
import json
import time
from contextvars import ContextVar
from typing import Any
from urllib.parse import unquote

import httpx
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import ToolResult
from jsonschema import Draft202012Validator
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
# 404s route to the tool that finds or creates the missing thing (round 3, T2/T6);
# matched on the API detail only: the tool's arguments do not say what is missing
_NOT_FOUND_HINTS = (
    (
        ("audit", "baseline", "snapshot", "no active curation"),
        'get_workflow_audit_trail(item_type="curation", item_id) lists the '
        "submissions and review rounds a diff can start from",
    ),
    (
        ("schema",),
        "schema ids: curation_schema_id on get_curation, precuration_schema_id on "
        "get_precuration, or get_workflow_pair(the scope's default_workflow_pair_id)",
    ),
    (
        ("pmid", "publication"),
        "find papers with a literature MCP such as GeneFoundry; "
        "validate_pmids(pmids) checks them",
    ),
    (
        ("gene", "hgnc", "symbol"),
        "the gene is not in Gene Curator yet: add_genes_to_scope(symbols, "
        "scope_name) adds and assigns it, or create_gene(hgnc_id)",
    ),
    (
        ("scope",),
        "list_scopes(name=...) finds the scope id; tools with scope_name take the name",
    ),
)
_STALE_HINT = (
    "re-read the item (get_curation or get_precuration), merge your change and retry"
)


def _not_found_hint(detail: Any) -> str | None:
    said = str(detail or "").lower()
    for words, hint in _NOT_FOUND_HINTS:
        if any(word in said for word in words):
            return hint
    return None


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
    hint = (
        _TOOL_HINTS.get((tool, status))
        or (_not_found_hint(detail) if status == 404 else None)
        or _HINTS.get(status)
    )
    if isinstance(detail, dict) and "current_lock_version" in detail:  # stale save
        hint = _STALE_HINT
    return ToolError(f"{message}\nnext: {hint}" if hint else message)


# Lean results on /mcp only (token plan 3, 4); /mcp/full drops only null.
# Who created or submitted stays: reviewers need it for 4-eyes and feedback.
AUDIT_KEYS = frozenset({"auto_saved_at", "record_hash", "previous_hash"})
SLIM_KEYS = {
    "search_mondo_diseases": frozenset({"definition", "synonyms", "xrefs", "iri"}),
    "search_hpo_terms": frozenset({"definition", "synonyms", "descendant_count"}),
    "validate_pmids": frozenset(
        {
            "authors",
            "author_string",
            "journal_abbrev",
            "volume",
            "issue",
            "pages",
            "doi",
            "pmcid",
            "abstract",
            "pub_type",
            "is_open_access",
            "cited_by_count",
            "publication_date",
        }
    ),
    "list_members": frozenset(
        {"invited_by", "invited_at", "team_id", "user_username", "user_orcid"}
    ),
}
# About 8k tokens of JSON (~3 characters per token); Claude Code warns at 10k
MAX_RESULT_CHARS = 25_000
_TOO_LARGE = (
    "response_too_large: about {tokens} tokens, over the 8000-token limit\n"
    "next: narrow the request: page with skip and limit, add filters, or pass "
    "compact=true"
)


def lean(value: Any, drop: frozenset[str] = frozenset()) -> Any:
    """Drop null values and the keys in drop, at any depth.

    {}, [], False, 0 and "" stay (empty is an answer); list items are
    never removed, so row indexes hold.
    """
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key in drop:
                continue
            item = lean(item, drop)
            if item is not None:
                out[key] = item
        return out
    if isinstance(value, list):
        return [lean(item, drop) for item in value]
    return value


def _lean_block(block: mt.ContentBlock, drop: frozenset[str]) -> mt.ContentBlock:
    if not isinstance(block, mt.TextContent):
        return block
    try:
        data = json.loads(block.text)
    except ValueError:
        return block
    text = json.dumps(lean(data, drop), ensure_ascii=False, separators=(",", ":"))
    return mt.TextContent(type="text", text=text)


def _types(prop: dict[str, Any]) -> set[str]:
    kind = prop.get("type")
    found = {kind} if isinstance(kind, str) else set(kind or [])
    for alternative in prop.get("anyOf", []) + prop.get("oneOf", []):
        found |= _types(alternative)
    return found


_BOOLEANS = {"true": True, "false": False, "1": True, "0": False}
_PARSERS: tuple[tuple[str, Any], ...] = (
    ("integer", int),
    ("number", float),
    ("boolean", lambda text: _BOOLEANS[text.lower()]),
)


def coerce_arguments(schema: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    """Numbers and booleans sent as strings ("20", "true"), parsed as FastAPI did.

    Only where the argument cannot be a string and the text parses cleanly; anything
    else is left for argument_errors to report.
    """
    props: dict[str, Any] = schema.get("properties", {})
    out = dict(args)
    for key, value in args.items():
        types = _types(props.get(key) or {})
        if not isinstance(value, str) or "string" in types:
            continue
        for kind, parse in _PARSERS:
            if kind in types:
                try:
                    out[key] = parse(value.strip())
                    break
                except (KeyError, ValueError):
                    continue
    return out


def argument_errors(schema: dict[str, Any], args: dict[str, Any]) -> list[str]:
    """What is wrong with a tool call's arguments, naming each field (empty: fine).

    Checked before the API is called, so a missing path parameter never reaches
    it as a literal "{item_id}" (MCP study round 3, T3-1).
    """
    props: dict[str, Any] = schema.get("properties", {})
    missing = [key for key in schema.get("required", []) if key not in args]
    problems = []
    for key in args:
        if key not in props:
            # A lone missing argument is the likely meant one (curation_id -> item_id)
            close = difflib.get_close_matches(key, props, n=1) or (
                missing if len(missing) == 1 else []
            )
            hint = f" (did you mean {close[0]}?)" if close else ""
            problems.append(f"unknown {key}{hint}")
    problems += [f"missing {key}" for key in missing]
    known = {key: value for key, value in args.items() if key in props}
    for error in Draft202012Validator(schema).iter_errors(known):
        if error.validator != "required":
            field = ".".join(map(str, error.absolute_path)) or "arguments"
            problems.append(f"{field}: {error.message[:200]}")
    return problems


def _invalid_arguments(
    tool: str, schema: dict[str, Any], problems: list[str]
) -> ToolError:
    required = set(schema.get("required", []))
    accepts = ", ".join(
        f"{key} (required)" if key in required else key
        for key in schema.get("properties", {})
    )
    return ToolError(
        f"invalid_input: {tool}: {'; '.join(problems)}\n"
        f"next: fix the arguments; {tool} accepts {accepts or 'no arguments'}"
    )


def correlation_id() -> str | None:
    try:
        return getattr(get_http_request().state, "request_id", None)
    except RuntimeError:
        return None


class ToolAuditMiddleware(Middleware):
    """Logs tool, outcome, duration and correlation id (never arguments); maps errors,
    applies MCP-only argument defaults and keeps results lean and bounded."""

    def __init__(
        self,
        *,
        lean: bool = False,
        defaults: dict[str, dict[str, Any]] | None = None,
        capped: frozenset[str] = frozenset(),
    ) -> None:
        self.lean = lean
        self.defaults = defaults or {}
        self.capped = capped  # tools that can be narrowed; /mcp only

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        start = time.perf_counter()
        outcome = "ok"
        name = context.message.name
        if name in self.defaults:
            context.message.arguments = {
                **self.defaults[name],
                **(context.message.arguments or {}),
            }
        drop = (
            AUDIT_KEYS | SLIM_KEYS.get(name, frozenset()) if self.lean else frozenset()
        )
        try:
            server = (
                context.fastmcp_context.fastmcp if context.fastmcp_context else None
            )
            tool = await server.get_tool(name) if server else None
            if tool is not None:  # unknown tools: FastMCP answers
                context.message.arguments = coerce_arguments(
                    tool.parameters, context.message.arguments or {}
                )
                problems = argument_errors(tool.parameters, context.message.arguments)
                if problems:
                    outcome = "invalid_input"
                    raise _invalid_arguments(name, tool.parameters, problems)
            result = await call_next(context)
            # Text only: clients bill structuredContent again on top of its text copy
            content = [_lean_block(block, drop) for block in result.content]
            size = sum(len(b.text) for b in content if isinstance(b, mt.TextContent))
            if self.lean and name in self.capped and size > MAX_RESULT_CHARS:
                outcome = "response_too_large"
                raise ToolError(_TOO_LARGE.format(tokens=size // 3))
            return ToolResult(content=content, meta=result.meta)
        except Exception as exc:
            if outcome != "ok":  # our own refusal, already a ToolError
                raise
            cause: BaseException | None = exc
            while cause is not None and not isinstance(cause, httpx.HTTPStatusError):
                cause = cause.__cause__
            if cause is None:
                outcome = "error"
                raise  # mask_error_details hides unexpected details
            error = _tool_error(cause, name)
            outcome = str(error).split(":", 1)[0]
            raise error from exc
        finally:
            logger.info(
                "MCP tool call",
                tool=name,
                outcome=outcome,
                duration_ms=round((time.perf_counter() - start) * 1000, 2),
                request_id=correlation_id(),
            )
