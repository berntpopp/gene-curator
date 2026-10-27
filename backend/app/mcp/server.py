"""Gene Curator as an MCP server: every tool is an existing API route (#462).

FastMCP builds the tools from the app's OpenAPI and calls the routes in process over
httpx.ASGITransport, so routers, Depends, capabilities, D1, lock_version and RLS apply
exactly as in the API. There is no second code path and no new endpoint.
"""

import re
from collections import Counter
from typing import Any, cast
from urllib.parse import quote

import httpx
from fastapi import FastAPI
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.providers.openapi import MCPType, RouteMap
from fastmcp.tools import Tool
from fastmcp.utilities.openapi import HTTPRoute
from fastmcp.utilities.openapi.models import HttpMethod
from mcp.types import ToolAnnotations

from app.core.deps import PAT_BLOCKED_OPERATIONS
from app.mcp.audit import (
    CHANNEL_HEADER,
    CLIENT_HEADER,
    ToolAuditMiddleware,
    correlation_id,
    mark_internal,
)
from app.mcp.auth import PersonalAccessTokenVerifier

# Routes no MCP tool exposes, with the reason (the parity test imports this)
EXCLUDED_OPERATIONS: dict[tuple[str, str], str] = {
    ("POST", "/api/v1/auth/login"): "session login; MCP authenticates with a token",
    ("POST", "/api/v1/auth/refresh"): "session refresh; tokens are not refreshed",
    ("POST", "/api/v1/auth/logout"): "session logout; revoke the token instead",
    ("POST", "/api/v1/auth/register"): "anonymous account creation",
    ("GET", "/api/v1/auth/"): "REST login URLs; the instructions cover MCP",
    **dict.fromkeys(PAT_BLOCKED_OPERATIONS, "blocked for personal access tokens"),
}

INSTRUCTIONS = """\
Gene Curator: gene-disease validity curation in scopes (teams). Every tool calls the
REST API as you, so your scope role, row-level security and the 4-eyes rule apply.

Workflow per gene and scope: Entry -> Precuration -> Curation -> Review -> Active.
1. Entry: resolve_genes (create_gene if missing), then create_gene_assignment adds the
   gene to the scope.
2. Precuration: create_precuration, save_draft_precurations, submit_precuration, then
   assign_peer_reviewer(item_type="precuration"). The reviewer finds it in read_my_work
   and calls approve_precuration or reject_precuration.
3. Curation: the approval opens a draft curation (list_curations); create_curation
   only works with an approved precuration and no open curation. Record evidence with
   save_draft_curations (evidence_data + lock_version); only that path is scored.
4. Review: submit_curation, then assign_peer_reviewer(item_type="curation"). The
   reviewer approves with submit_peer_review(decision="approve") or
   execute_workflow_transition(target_stage="active").
5. Active: one active curation per gene and scope.

4-eyes: nobody approves or reviews their own work, platform admins included; route it
to another reviewer of the scope.

Scope roles (yours: read_users_me, the scope's: list_members):
| role     | may                                                                  |
| viewer   | read the scope                                                       |
| curator  | read; add genes one at a time (create_gene_assignment); create, edit  |
|          | and submit precurations and curations                                |
| reviewer | read; approve or reject precurations; review others' curations       |
| admin    | all of the above; members, bulk_create_gene_assignments, scope edits |

Look up before acting: a scope by name in list_scopes, a gene by symbol with
resolve_genes or get_genes_by_symbol; pass their ids on. Check PMIDs with validate_pmids.
Your queue: read_my_work and get_my_review_assignments.
Errors start with a closed code (invalid_input, unauthorized, forbidden, not_found,
conflict, rate_limited, upstream_unavailable, internal), then the API detail. On
conflict, re-read the item and retry with its lock_version. Confirm destructive tools
with the user.
"""

# State-changing actions a client should confirm (besides every DELETE)
_DESTRUCTIVE = re.compile(
    r"/(approve|reject|transition|bulk-transition|submit|merge|deactivate|publish)$"
    r"|/curation-schemas/[^/]+/versions$"  # publishes a methodology version
)
# Updates overwrite (PUT/PATCH) and are flagged too, except saving a draft or reading
_SAFE_UPDATE = re.compile(r"/(draft|read|read-all)$")
# Endpoint names that are not verb_noun or too generic on their own
_RENAMES = {
    "resolve": "resolve_genes",
    "usage": "get_llm_usage",
    "get_options": "get_llm_options",
    "get_settings": "get_llm_settings",
    "put_settings": "update_llm_settings",
    "list_providers": "list_llm_providers",
    "create_provider": "create_llm_provider",
    "update_provider": "update_llm_provider",
    "set_key": "set_llm_provider_key",
    "ping_provider": "ping_llm_provider",
    "list_models": "list_llm_models",
    "create_model": "create_llm_model",
    "update_model": "update_llm_model",
    "list_runs": "list_llm_runs",
    "get_run": "get_llm_run",
    "preview": "preview_llm_request",
    "test_run": "test_run_prompt_version",
    "list_templates": "list_prompt_templates",
    "create_template": "create_prompt_template",
    "list_versions": "list_prompt_versions",
    "create_version": "create_prompt_version",
    "update_version": "update_prompt_version",
    "publish_version": "publish_prompt_version",
    "diff_versions": "diff_prompt_versions",
}


def tool_names(spec: dict[str, Any]) -> dict[str, str]:
    """operationId -> verb_noun (the endpoint function); clashes get the resource.

    FastAPI's default operationId is name + path (non-word chars as _) + _method.
    """
    found: dict[str, tuple[str, str]] = {}
    for path, operations in spec["paths"].items():
        if not path.startswith("/api/v1/"):
            continue
        for method, op in operations.items():
            suffix = re.sub(r"\W", "_", path) + "_" + method
            name = op["operationId"].removesuffix(suffix)
            found[op["operationId"]] = (_RENAMES.get(name, name), path)
    counts = Counter(name for name, _ in found.values())
    return {
        op_id: name
        if counts[name] == 1
        else f"{name}_{path.split('/')[3].replace('-', '_')}"
        for op_id, (name, path) in found.items()
    }


def _annotate(route: HTTPRoute, tool: Any) -> None:
    if not isinstance(tool, Tool):
        return
    read_only = route.method == "GET"
    destructive = (
        route.method == "DELETE"
        or (route.method == "POST" and bool(_DESTRUCTIVE.search(route.path)))
        or (route.method in ("PUT", "PATCH") and not _SAFE_UPDATE.search(route.path))
    )
    tool.annotations = ToolAnnotations(
        readOnlyHint=read_only,
        destructiveHint=destructive,
        idempotentHint=read_only,
        openWorldHint=False,
    )
    if destructive:
        tool.description = (
            "Destructive or irreversible: confirm with the user first.\n\n"
            + (tool.description or "")
        )


async def _as_caller(request: httpx.Request) -> None:
    """Every internal call carries the caller's own token and the MCP channel.

    FastMCP strips Authorization before calling the API; never replace it with a
    service token, which would bypass RLS and D1.
    """
    token = get_access_token()
    if token is None:
        return  # the API answers 401
    request.headers["Authorization"] = f"Bearer {token.token}"
    request.headers[CHANNEL_HEADER] = "mcp"
    request.headers[CLIENT_HEADER] = quote(token.client_id, safe=" ")
    rid = correlation_id()
    if rid:
        request.headers["X-Request-ID"] = rid


def create_mcp(app: FastAPI) -> FastMCP:
    route_maps = [
        RouteMap(
            methods=[cast(HttpMethod, method)],
            pattern=rf"^{re.escape(path)}$",
            mcp_type=MCPType.EXCLUDE,
        )
        for method, path in EXCLUDED_OPERATIONS
    ] + [
        RouteMap(pattern=r"^/api/v1/", mcp_type=MCPType.TOOL),
        RouteMap(mcp_type=MCPType.EXCLUDE),  # /, /health: not API operations
    ]
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(
            app=mark_internal(app),
            raise_app_exceptions=False,  # a 500 stays a 500
        ),
        base_url="http://gene-curator",
        timeout=60,
        event_hooks={"request": [_as_caller]},
    )
    spec = app.openapi()
    mcp = FastMCP.from_openapi(
        spec,
        client=client,
        name="gene-curator",
        instructions=INSTRUCTIONS,
        route_maps=route_maps,
        mcp_component_fn=_annotate,
        mcp_names=tool_names(spec),
        validate_output=False,  # response_model already validates; keep 3.1 nullables
        auth=PersonalAccessTokenVerifier(app),
        mask_error_details=True,
    )
    mcp.add_middleware(ToolAuditMiddleware())
    return mcp
