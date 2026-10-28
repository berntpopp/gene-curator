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
from fastapi.routing import APIRoute, iter_route_contexts
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.server.providers.openapi import MCPType, RouteMap
from fastmcp.tools import Tool
from fastmcp.utilities.json_schema import dereference_refs
from fastmcp.utilities.openapi import HTTPRoute
from fastmcp.utilities.openapi.models import HttpMethod
from mcp import types as mt
from mcp.types import ToolAnnotations

from app.api.v1.endpoints.logs import require_admin, require_admin_or_reviewer
from app.core.deps import PAT_BLOCKED_OPERATIONS, get_current_admin_user
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
This endpoint (/mcp) serves pipeline setup, curation and review tools; /mcp/full
serves every other API operation (schema authoring, statistics, platform admin).

Scopes by name: tools with scope_name take the team name instead of scope_id
(create_precuration, add_genes_to_scope, list_precurations, list_curations,
get_peer_reviewers, get_my_review_assignments); list_scopes(name=) finds the id.

Set up a pipeline: get_workflow_pairs, create_scope (default_workflow_pair_id;
update_scope changes it later); members: search_users_for_invitation finds a user,
add_member adds them at once, invite_member sends an invitation, update_member_role
changes a role.

Workflow per gene and scope: Entry -> Precuration -> Curation -> Review -> Active.
1. Entry: add_genes_to_scope(symbols, scope_name) resolves HGNC symbols, creates
   missing genes and assigns them in one call.
2. Precuration: create_precuration, save_draft_precurations, then
   submit_precuration(reviewer_email=...) submits and routes it to a reviewer. The
   reviewer finds it in read_my_work and calls approve_precuration or
   reject_precuration.
3. Curation: the approval opens a draft curation (list_curations); create_curation
   only works with an approved precuration and no open curation. Evidence that scores
   lives in evidence_data (save_draft_curations or update_curation with
   lock_version); their descriptions list the evidence paths and
   get_curation_schema(path=) shows one table's fields.
4. Literature: find and read papers with a literature MCP such as GeneFoundry;
   validate_pmids(pmids) confirms the PMIDs exist. Cite the PMID that reports each proband.
5. Review: submit_curation(reviewer_email=...) submits and assigns the reviewer.
   The reviewer reads everything in one call with read_curation_for_review, then
   submit_peer_review(decision="approve" or "request_changes", with comments).
6. Active: one active curation per gene and scope.

4-eyes: nobody approves or reviews their own work, platform admins included; route it
to another reviewer of the scope.

Scope roles (yours: user_role on each list_scopes row; everyone's: list_members):
| role     | may                                                                  |
| viewer   | read the scope                                                       |
| curator  | read; add genes; create, edit and submit precurations and curations  |
| reviewer | read; approve or reject precurations; review others' curations       |
| admin    | all of the above; members and scope edits                            |

Your queue: read_my_work and get_my_review_assignments.
Errors start with a closed code (invalid_input, unauthorized, forbidden, not_found,
conflict, rate_limited, upstream_unavailable, internal, response_too_large), then the
detail and a next: line naming the tool to call. On conflict, re-read the item and
retry with its lock_version. Results omit null fields. Confirm destructive tools with
the user.
"""

# /mcp: the two primary flows (curate a gene end to end, check and review a
# curation) plus lookups; /mcp/full keeps every operation (owner decision 2026-10-27)
CORE_TOOLS = frozenset(
    {
        # you, your queue, invitations
        "read_users_me", "read_my_work", "get_my_review_assignments",
        "list_notifications", "mark_notification_read",
        "get_my_pending_invitations", "accept_invitation",
        # scopes and people
        "list_scopes", "get_scope_details", "list_members", "get_peer_reviewers",
        # pipeline setup: the scope and its members
        "create_scope", "update_scope", "add_member", "invite_member",
        "update_member_role", "search_users_for_invitation",
        # genes
        "resolve_genes", "get_genes_by_symbol", "search_genes", "get_gene",
        "get_gene_by_hgnc_id", "create_gene", "search_hgnc_genes", "fetch_hgnc_gene",
        "get_scope_genes", "get_gene_full_summary",
        # gene assignments
        "create_gene_assignment", "bulk_create_gene_assignments",
        "get_scope_assignments", "get_gene_assignment", "update_gene_assignment",
        "assign_curator_to_gene", "get_available_genes_for_scope",
        # precurations
        "create_precuration", "get_precuration", "list_precurations",
        "update_precuration", "save_draft_precurations", "submit_precuration",
        "approve_precuration", "reject_precuration", "delete_precuration",
        # curations
        "create_curation", "get_curation", "list_curations", "update_curation",
        "save_draft_curations", "submit_curation", "delete_curation",
        "curation_diff", "calculate_score",
        # review and workflow
        "assign_peer_reviewer", "submit_peer_review", "list_review_comments",
        "create_review_comment", "update_review_comment", "get_workflow_state",
        "execute_workflow_transition", "validate_workflow_transition",
        "get_workflow_audit_trail",
        # methodology
        "get_curation_schema", "get_workflow_pairs", "get_workflow_pair",
        "get_methodology_version", "validate_evidence_data", "get_scoring_engine_info",
        # ontology and literature
        "search_mondo_diseases", "search_hpo_terms", "validate_hpo_term",
        "get_inheritance_patterns", "search_omim_diseases", "get_omim_disease",
        "validate_pmids", "get_publication",
        # one-call round trips (token plan 2)
        "add_genes_to_scope", "read_curation_for_review",
    }
)  # fmt: skip

# Dependencies that admit platform admins only: their tools are hidden from others
_ADMIN_DEPENDENCIES = {get_current_admin_user, require_admin, require_admin_or_reviewer}

# Query parameters that narrow a result, named in the response_too_large advice
_NARROWING = {"skip", "limit", "compact"}

# MCP-only argument defaults; the REST defaults stay as they are
MCP_DEFAULTS: dict[str, dict[str, Any]] = {"get_curation_schema": {"compact": True}}

# Where scored evidence lives, so agents need no example curation (token plan 6)
# variant_type options of the seeded ClinGen schema (046), per case-level table
VARIANT_TYPES = {
    "autosomal_dominant_or_x_linked.predicted_or_proven_null": (
        "nonsense", "frameshift", "canonical_splice", "initiation_codon",
        "single_exon_deletion", "multi_exon_deletion", "whole_gene_deletion",
    ),
    "autosomal_dominant_or_x_linked.other_variant_type": (
        "missense", "in_frame_indel", "cryptic_splice", "synonymous", "5_utr",
        "3_utr", "intronic", "other",
    ),
    "autosomal_recessive.predicted_or_proven_null": ("two_null", "null_and_null"),
    "autosomal_recessive.other_variant_type": (
        "null_and_other", "two_other", "homozygous_other",
    ),
}  # fmt: skip

_EVIDENCE_PATHS = """

Evidence that scores (ClinGen SOP v11 pairs), in evidence_data:
- genetic_evidence.case_level.autosomal_dominant_or_x_linked.{predicted_or_proven_null|
  other_variant_type}[]: proband_label, variant, variant_type, pmid,
  proband_counted_points, score_status ("score" counts; "review"/"contradicts" count
  nothing; blank scores 0); .autosomal_recessive.{...}[]: variant_1 and variant_2
- One row per proband the paper describes, never one per paper or cohort; each row
  has its own variant(s) as HGVS (c./p.), rsID or genomic coordinate, and the PMID
  that reports that proband.
- variant_type values per table:
{variant_types}
- genetic_evidence.segregation[]: family_label, lod_score or segregations_counted, pmid
- genetic_evidence.case_control.{single_variant_analysis|aggregate_variant_analysis}[]
- experimental_evidence.function.{biochemical_function|protein_interaction|expression}[],
  .functional_alteration.{patient_cells|non_patient_cells}[],
  .models.{non_human_model_organism|cell_culture_model}[],
  .rescue.{human|non_human_model_organism|cell_culture|patient_cells}[]: label, pmid,
  points, explanation
- contradictory_evidence[]: pmid, impact
- evidence_summary: free-text summary and notes of the curation (never scored);
  submit notes go to the reviewer.
Row fields, options and point ranges of one table: get_curation_schema(schema_id,
path="genetic_evidence.case_level.autosomal_recessive.predicted_or_proven_null").""".replace(
    "{variant_types}",
    "\n".join(f"  {table}: {', '.join(vs)}" for table, vs in VARIANT_TYPES.items()),
)
# Routes without a docstring: lead with the words an agent searches for
_DESCRIPTIONS = {
    "read_users_me": "Me: the current user's profile (id, name, application role).",
    "read_my_work": "My work queue across scopes: my drafts, my submissions and the "
    "precurations and curations waiting for my review, with counts per tab.",
    "list_review_comments": "Review comments on a curation: the reviewer's queries "
    "and feedback per evidence item, with their status.",
    "create_review_comment": "Review comment: add a query or feedback on a curation "
    "evidence item (item_path), e.g. when requesting changes.",
    "update_review_comment": "Review comment: edit the body or change the status of a "
    "comment on a curation.",
}
# Said once, on the tool agents save evidence with (round 4: list size)
_SEE_SAVE = (
    "\n\nOne row per proband, each with its own variant (HGVS c./p., rsID or genomic "
    "coordinate) and the PMID that reports it; exact variant_type values per table, "
    "paths and evidence_summary: see save_draft_curations."
)
_DESCRIPTION_EXTRAS = {
    "save_draft_curations": _EVIDENCE_PATHS,
    "update_curation": _SEE_SAVE,
    "create_curation": _SEE_SAVE,
    "validate_pmids": "\n\nResults list title, journal and year; get_publication "
    "returns the abstract.",
}

# Docstring sections that describe the Python function, not the tool
_DOC_NOISE = re.compile(r"\n\s*(Args|Returns|Raises|Example[^\n:]*):\s*\n.*", re.S)
# REST routes in parentheses and paragraphs about the web UI or caching: an agent
# calls tools, not routes
_REST_NOISE = re.compile(
    r" \((?:GET|POST|PUT|PATCH|DELETE) /[^)]*\)"
    r"|\n\n(?:Use this endpoint (?:for|to populate)|This endpoint is useful for "
    r"populating|Rate limiting:|Results are cached)[^\n]*(?:\n[^\n]+)*"
)

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
    tool.output_schema = None  # results go out once, as text (no structuredContent)
    tool.description = (
        _DESCRIPTIONS.get(tool.name)
        or _REST_NOISE.sub("", _DOC_NOISE.sub("", tool.description or "")).strip()
        or route.summary
        or ""
    ) + _DESCRIPTION_EXTRAS.get(tool.name, "")
    tool.parameters = dereference_refs(tool.parameters)  # inline first, then shrink
    _lean_schema(tool.parameters)
    for arg, value in MCP_DEFAULTS.get(tool.name, {}).items():
        tool.parameters["properties"][arg]["default"] = value
    read_only = route.method == "GET"
    destructive = (
        route.method == "DELETE"
        or (route.method == "POST" and bool(_DESTRUCTIVE.search(route.path)))
        or (route.method in ("PUT", "PATCH") and not _SAFE_UPDATE.search(route.path))
    )
    # Spec defaults are left out: a write is neither read-only nor idempotent, and
    # destructiveHint means nothing on a read
    tool.annotations = ToolAnnotations(
        readOnlyHint=read_only or None,
        destructiveHint=None if read_only else destructive,
        idempotentHint=read_only or None,
        openWorldHint=False,
    )
    tool.tags = set()  # nothing selects by tag; each tag repeats in the list


def _merge_nullable(schema: dict[str, Any]) -> None:
    """anyOf [X, null] -> X with type [X's type, "null"]: the same values, a third of
    the bytes (round 4: the tool list was 20-36% of input tokens)."""
    options = schema.get("anyOf")
    if (
        not isinstance(options, list)
        or len(options) != 2
        or {"type": "null"} not in options
    ):
        return
    (other,) = [o for o in options if o != {"type": "null"}]
    if not isinstance(other.get("type"), str) or other["type"] == "null":
        return
    del schema["anyOf"]
    schema.update({**other, "type": [other["type"], "null"]})
    if "enum" in other:
        schema["enum"] = [*other["enum"], None]


def _lean_schema(schema: Any) -> None:
    """Shrink a JSON Schema in place: no titles (the property name says it), no
    empty required list, integral bounds as ints. A property named title stays."""
    if isinstance(schema, list):
        for item in schema:
            _lean_schema(item)
    elif isinstance(schema, dict):
        _merge_nullable(schema)
        if isinstance(schema.get("title"), str):
            del schema["title"]
        if schema.get("required") == []:
            del schema["required"]
        for key, value in schema.items():
            if isinstance(value, float) and value.is_integer():
                schema[key] = int(value)
            for child in value.values() if key == "properties" else [value]:
                _lean_schema(child)


def admin_only_tools(app: FastAPI, names: dict[str, str]) -> frozenset[str]:
    """Tools whose route depends on a platform-admin check (never usable by others)."""

    def calls(dependant: Any) -> Any:
        yield dependant.call
        for sub in dependant.dependencies:
            yield from calls(sub)

    spec = app.openapi()["paths"]
    return frozenset(
        names[spec[context.path_format][method.lower()]["operationId"]]
        for context in iter_route_contexts(app.routes)
        if isinstance(context.original_route, APIRoute)
        and _ADMIN_DEPENDENCIES & set(calls(context.original_route.dependant))
        for method in context.methods or ()
        if spec.get(context.path_format, {}).get(method.lower())
    )


class CallerToolFilter(Middleware):
    """tools/list hides platform-admin tools from non-admins (the spec lets the list
    vary by authorization); calling one still reaches the API, which answers 403."""

    def __init__(self, admin_only: frozenset[str]) -> None:
        self.admin_only = admin_only

    async def on_list_tools(
        self,
        context: MiddlewareContext[mt.ListToolsRequest],
        call_next: CallNext[mt.ListToolsRequest, Any],
    ) -> Any:
        tools = await call_next(context)
        token = get_access_token()
        if token is not None and token.claims.get("role") == "admin":
            return tools
        return [tool for tool in tools if tool.name not in self.admin_only]


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


def create_mcp(app: FastAPI, *, core: bool = False) -> FastMCP:
    """core=True: the /mcp curation set with lean results; else every operation."""
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
    names = tool_names(spec)
    mcp = FastMCP.from_openapi(
        spec,
        client=client,
        name="gene-curator",
        instructions=INSTRUCTIONS,
        route_maps=route_maps,
        mcp_component_fn=_annotate,
        mcp_names=names,
        validate_output=False,  # response_model already validates; keep 3.1 nullables
        auth=PersonalAccessTokenVerifier(app),
        mask_error_details=True,
    )
    mcp.add_middleware(CallerToolFilter(admin_only_tools(app, names)))
    # Only tools with a way to narrow are capped; a whole curation is always readable
    capped = frozenset(
        names[op["operationId"]]
        for operations in spec["paths"].values()
        for op in operations.values()
        if op.get("operationId") in names
        and _NARROWING & {p["name"] for p in op.get("parameters", [])}
    )
    mcp.add_middleware(
        ToolAuditMiddleware(lean=core, defaults=MCP_DEFAULTS, capped=capped)
    )
    if core:
        mcp.enable(names=set(CORE_TOOLS), only=True)
    return mcp
