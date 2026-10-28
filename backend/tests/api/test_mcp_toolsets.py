"""MCP tool sets and lean output: /mcp curation core, /mcp/full every operation,
platform-admin tools hidden from others, lean and bounded results (token plan 1-6)."""

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.mcp import audit
from app.mcp.audit import AUDIT_KEYS, argument_errors, lean
from app.mcp.server import (
    CORE_TOOLS,
    EXCLUDED_OPERATIONS,
    INSTRUCTIONS,
    VARIANT_TYPES,
    admin_only_tools,
    tool_names,
)
from app.models import CurationNew, CurationSchema, Scope, UserNew
from tests.api.test_mcp import call, pat, rpc

pytestmark = pytest.mark.unit

CORE_SNAPSHOT = Path(__file__).with_name("mcp_tools_core.snapshot")
ADMIN_SNAPSHOT = Path(__file__).with_name("mcp_tools_admin_only.snapshot")


def _tools(client: TestClient, token: str, path: str) -> dict[str, dict]:
    tools = rpc(client, token, "tools/list", {}, path).json()["result"]["tools"]
    return {t["name"]: t for t in tools}


def test_core_tool_list_matches_snapshot(
    client: TestClient, db_session: Session, test_user_curator: UserNew
) -> None:
    tools = _tools(client, pat(db_session, test_user_curator), "/mcp")
    lines = sorted(
        f"{name} read_only={t['annotations'].get('readOnlyHint', False)} "
        f"destructive={t['annotations'].get('destructiveHint', False)}"
        for name, t in tools.items()
    )
    assert lines == CORE_SNAPSHOT.read_text().splitlines()
    assert set(tools) == CORE_TOOLS and len(tools) <= 80


# Every tool the study tasks need on /mcp (round 3 T1 failed without scope setup)
FLOW_TOOLS = {
    "pipeline setup": {
        "get_workflow_pairs", "create_scope", "update_scope", "list_scopes",
        "search_users_for_invitation", "add_member", "invite_member",
        "update_member_role", "list_members", "resolve_genes", "create_gene",
        "bulk_create_gene_assignments", "create_gene_assignment",
    },
    "curate a gene": {
        "create_precuration", "save_draft_precurations", "submit_precuration",
        "assign_peer_reviewer", "list_curations", "get_curation_schema",
        "save_draft_curations", "update_curation", "submit_curation",
        "search_mondo_diseases", "validate_pmids", "get_publication",
    },
    "review a curation": {
        "read_my_work", "get_my_review_assignments", "get_curation", "curation_diff",
        "calculate_score", "create_review_comment", "submit_peer_review",
        "approve_precuration", "reject_precuration", "execute_workflow_transition",
    },
}  # fmt: skip


@pytest.mark.parametrize("flow", FLOW_TOOLS)
def test_core_has_every_tool_a_flow_needs(flow: str) -> None:
    assert FLOW_TOOLS[flow] - CORE_TOOLS == set()


def test_platform_admin_tools_are_listed_for_admins_only(
    client: TestClient,
    db_session: Session,
    test_user_admin: UserNew,
    test_user_curator: UserNew,
) -> None:
    admin_only = admin_only_tools(app, tool_names(app.openapi()))
    # A normal tool can never be hidden by mistake: the hidden set is pinned
    assert sorted(admin_only) == ADMIN_SNAPSHOT.read_text().splitlines()
    curator = pat(db_session, test_user_curator)
    full = set(_tools(client, pat(db_session, test_user_admin), "/mcp/full"))
    assert set(_tools(client, curator, "/mcp/full")) == full - admin_only
    assert not admin_only & set(_tools(client, curator, "/mcp"))
    spec, names = app.openapi()["paths"], tool_names(app.openapi())
    excluded = {
        names[spec[p][m.lower()]["operationId"]] for m, p in EXCLUDED_OPERATIONS
    }
    assert admin_only - full <= excluded  # admins see every admin tool there is
    assert "list_llm_providers" in full
    # Hidden, not removed: the API still answers, with its own 403
    hidden = call(client, curator, "list_llm_providers")
    assert hidden["content"][0]["text"].startswith("forbidden: HTTP 403")


def test_lean_keeps_what_a_reviewer_needs() -> None:
    result = {
        "id": "c1",
        "lock_version": 0,
        "is_draft": False,
        "notes": "",
        "created_by": "u1",
        "record_hash": "h",
        "approved_at": None,
        "tags": [],
        "meta": {},
        "computed_scores": {
            "warnings": ["Segregation row 0: LOD score missing"],
            "trace": {
                "sections": [
                    {
                        "key": "genetic_evidence",
                        "score": 0,
                        "types": [
                            {"path": "segregation", "items": 1, "score": 0},
                            {"path": "case_control.single", "items": 0, "score": 0},
                        ],
                    }
                ],
                "out_of_range": [
                    {"path": "segregation[0].points", "value": 9, "range": [0, 3]}
                ],
                "excluded": [{"path": "segregation[1]", "reason": "no PMID"}],
            },
        },
        "evidence_data": {"segregation": [{"pmid": "1", "points": 0}, {}]},
    }
    out = lean(result, AUDIT_KEYS)
    assert out["computed_scores"] == result["computed_scores"]
    assert out["evidence_data"] == result["evidence_data"]  # rows keep their index
    assert out["lock_version"] == 0 and out["is_draft"] is False and out["notes"] == ""
    assert not {"record_hash", "approved_at"} & set(out) and out["meta"] == {}
    assert out["created_by"] == "u1" and out["tags"] == []  # [] is an answer
    assert lean(result)["record_hash"] == "h"  # /mcp/full keeps audit fields


def test_core_results_are_lean_and_full_results_complete(
    client: TestClient,
    db_session: Session,
    test_user_curator: UserNew,
    test_curation: CurationNew,
    test_scope: Scope,
) -> None:
    token = pat(db_session, test_user_curator)

    def read(path: str, name: str, **args: str) -> dict:
        result = call(client, token, name, path=path, **args)
        assert not result.get("isError"), result
        return json.loads(result["content"][0]["text"])

    core = read("/mcp", "get_curation", curation_id=str(test_curation.id))
    full = read("/mcp/full", "get_curation", curation_id=str(test_curation.id))
    assert core["created_by"] == full["created_by"] == str(test_user_curator.id)
    assert core["id"] == full["id"] and "lock_version" in core
    assert None not in full.values()

    scope_id = str(test_scope.id)
    core_members = read("/mcp", "list_members", scope_id=scope_id)["members"]
    full_members = read("/mcp/full", "list_members", scope_id=scope_id)["members"]
    assert "invited_at" in full_members[0] and "invited_at" not in core_members[0]
    assert {"user_id", "role"} <= set(core_members[0])


def test_curation_schema_is_compact_by_default_on_mcp(
    client: TestClient,
    db_session: Session,
    test_user_curator: UserNew,
    evidence_schema: CurationSchema,
) -> None:
    token = pat(db_session, test_user_curator)
    listed = _tools(client, token, "/mcp")["get_curation_schema"]
    assert listed["inputSchema"]["properties"]["compact"]["default"] is True
    evidence_schema.ui_configuration = {"layout": "tabs"}  # compact answers {}
    db_session.commit()

    def read(**args: object) -> dict:
        result = call(
            client, token, "get_curation_schema", path="/mcp",
            schema_id=str(evidence_schema.id), **args,
        )  # fmt: skip
        return json.loads(result["content"][0]["text"])

    assert read()["ui_configuration"] == {}
    assert read(compact=False)["ui_configuration"] == {"layout": "tabs"}


def test_tool_definitions_are_lean_and_curation_saves_name_the_evidence(
    client: TestClient, db_session: Session, test_user_curator: UserNew
) -> None:
    tools = _tools(client, pat(db_session, test_user_curator), "/mcp")
    text = json.dumps(list(tools.values()))
    assert '"title"' not in text and ".0," not in text
    text = tools["save_draft_curations"]["description"]
    assert "genetic_evidence.case_level" in text
    assert "One row per proband" in text and "variant_1 and variant_2" in text
    assert "evidence_summary: free-text summary and notes" in text
    assert "frameshift, canonical" in text and "missense" in text
    assert "get_curation_schema(schema_id,\npath=" in text
    for name in ("update_curation", "create_curation"):  # said once (list size)
        assert "see save_draft_curations" in tools[name]["description"], name
        assert "One row per proband" in tools[name]["description"], name
    # Nullable arguments are a type list, still accepting null (and enum values)
    status = tools["list_curations"]["inputSchema"]["properties"]["curation_status"]
    assert status["type"] == ["string", "null"] and None in status["enum"]
    schema = tools["list_curations"]["inputSchema"]
    assert argument_errors(schema, {"scope_id": None, "curation_status": None}) == []
    assert argument_errors(schema, {"curation_status": "draft"}) == []
    assert argument_errors(schema, {"curation_status": "nope"})
    assert '"anyOf"' not in json.dumps(schema)
    assert tools["read_my_work"]["description"].startswith("My work queue")
    assert "get_publication" in tools["validate_pmids"]["description"]


def test_only_narrowable_mcp_reads_are_capped(
    client: TestClient,
    db_session: Session,
    test_user_curator: UserNew,
    test_curation: CurationNew,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_curation.evidence_data = {"notes": "x" * 30_000}
    db_session.commit()
    token = pat(db_session, test_user_curator)
    curation_id = str(test_curation.id)

    def text(path: str, name: str, **args: str) -> str:
        return str(call(client, token, name, path=path, **args)["content"][0]["text"])

    # A whole curation is always readable; /mcp/full is never capped (parity)
    for path in ("/mcp", "/mcp/full"):
        assert len(text(path, "get_curation", curation_id=curation_id)) > 25_000

    monkeypatch.setattr(audit, "MAX_RESULT_CHARS", 10)
    assert text("/mcp/full", "list_curations").startswith('{"curations"')
    capped = text("/mcp", "list_curations")
    assert capped.startswith("response_too_large:") and "skip and limit" in capped


def _keys(schema: object) -> set[str]:
    """Every property name at any depth: argument names are not tool names."""
    if isinstance(schema, list):
        return set().union(*map(_keys, schema)) if schema else set()
    if not isinstance(schema, dict):
        return set()
    own = (
        set(schema.get("properties", {}))
        if isinstance(schema.get("properties"), dict)
        else set()
    )
    return own.union(*map(_keys, schema.values()))


@pytest.mark.parametrize("path", ["/mcp", "/mcp/full"])
def test_every_tool_named_in_a_hint_description_or_instructions_exists(
    path: str, client: TestClient, db_session: Session, test_user_admin: UserNew
) -> None:
    tools = _tools(client, pat(db_session, test_user_admin), path)
    every = set(_tools(client, pat(db_session, test_user_admin), "/mcp/full"))
    verbs = {name.split("_")[0] for name in every}  # get, list, add, curation, ...
    arguments = set().union(*(_keys(t["inputSchema"]) for t in tools.values()))
    arguments |= {"curation_schema_id"}  # a response field ("curation" is a verb here)

    def named(text: str) -> set[str]:
        words = set(re.findall(r"\b[a-z]+(?:_[a-z0-9]+)+\b", text))
        return {w for w in words if w.split("_")[0] in verbs} - arguments

    hints = json.dumps(
        [
            audit._HINTS,
            list(audit._TOOL_HINTS.values()),
            audit._NOT_FOUND_HINTS,
            audit._STALE_HINT,
            audit._TOO_LARGE,
        ]
    )
    assert named(INSTRUCTIONS + hints) - set(tools) == set()  # shared by both
    missing = {
        name: named(t["description"] + json.dumps(t["inputSchema"])) - set(tools)
        for name, t in tools.items()
    }
    assert {name: found for name, found in missing.items() if found} == {}
    assert "create_scope" in named(INSTRUCTIONS)  # the check sees real names


def test_instructions_name_the_shortcuts_and_fit_the_client_limit() -> None:
    assert len(INSTRUCTIONS) < 4096  # Claude Code cuts server instructions there
    for shortcut in (
        "scope_name",
        "submit_curation(reviewer_email=",
        "submit_precuration(reviewer_email=",
        "add_genes_to_scope(symbols, scope_name)",
        "read_curation_for_review",
        "search_pubmed(gene_symbol",
        "validate_pmids(pmids, gene_symbol)",
        "get_curation_schema(path=)",
    ):
        assert shortcut in INSTRUCTIONS, shortcut
    # Round 4: roles come from list_scopes; evidence-item tools are not on /mcp
    assert "user_role on each list_scopes row" in INSTRUCTIONS
    assert "read_users_me" not in INSTRUCTIONS and "evidence-item" not in INSTRUCTIONS
    # Round 5: literature from a literature MCP, which ClinGen pair, diff baselines
    assert "GeneFoundry (PubTator, LitVar, ClinVar)" in INSTRUCTIONS
    assert '"ClinGen\nGene-Disease Validity" is_default' in INSTRUCTIONS
    assert "previous_submission the one before it" in INSTRUCTIONS
    # the old multi-step gene entry and reviewer routing are gone
    assert "create_gene_assignment" not in INSTRUCTIONS
    assert "assign_peer_reviewer" not in INSTRUCTIONS


# Surface budget for /mcp (token plan 1, 5): a regression fails CI; raise a budget
# only on purpose. Bytes are the tools/list response as a client receives it.
SURFACE_BUDGET = {"curator": (78, 55_000), "admin": (78, 55_000)}


@pytest.mark.parametrize("role", SURFACE_BUDGET)
def test_core_tool_surface_stays_in_budget(
    role: str,
    client: TestClient,
    db_session: Session,
    test_user_admin: UserNew,
    test_user_curator: UserNew,
) -> None:
    user = test_user_admin if role == "admin" else test_user_curator
    response = rpc(client, pat(db_session, user), "tools/list", {}, "/mcp")
    count, max_bytes = SURFACE_BUDGET[role]
    tools = response.json()["result"]["tools"]
    assert (len(tools), len(response.content) <= max_bytes) == (count, True), (
        len(tools),
        len(response.content),
    )


def test_variant_types_in_descriptions_are_the_seeded_enum_values() -> None:
    """The four case-level tables' variant_type options in the seeded schema (046)."""
    sql = Path(__file__).parents[3] / "database/sql/046_clingen_v1_correction.sql"
    seeded = [
        re.findall(r'"value": "([^"]+)"', line)
        for line in sql.read_text().splitlines()
        if '"variant_type": {"type": "select"' in line
    ]
    assert seeded == [list(values) for values in VARIANT_TYPES.values()]
    # no later migration redefines them
    later = [
        f.name
        for f in sorted(sql.parent.glob("*.sql"))
        if f.name > sql.name and '"variant_type": {"type": "select"' in f.read_text()
    ]
    assert later == []
