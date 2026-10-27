"""MCP tool sets and lean output: /mcp curation core, /mcp/full every operation,
platform-admin tools hidden from others, lean and bounded results (token plan 1-6)."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.mcp import audit
from app.mcp.audit import AUDIT_KEYS, lean
from app.mcp.server import (
    CORE_TOOLS,
    EXCLUDED_OPERATIONS,
    admin_only_tools,
    tool_names,
)
from app.models import CurationNew, CurationSchema, Scope, UserNew
from tests.api.test_mcp import call, pat, rpc

pytestmark = pytest.mark.unit

CORE_SNAPSHOT = Path(__file__).with_name("mcp_tools_core.snapshot")


def _tools(client: TestClient, token: str, path: str) -> dict[str, dict]:
    tools = rpc(client, token, "tools/list", {}, path).json()["result"]["tools"]
    return {t["name"]: t for t in tools}


def test_core_tool_list_matches_snapshot(
    client: TestClient, db_session: Session, test_user_curator: UserNew
) -> None:
    tools = _tools(client, pat(db_session, test_user_curator), "/mcp")
    lines = sorted(
        f"{name} read_only={t['annotations']['readOnlyHint']} "
        f"destructive={t['annotations']['destructiveHint']}"
        for name, t in tools.items()
    )
    assert lines == CORE_SNAPSHOT.read_text().splitlines()
    assert set(tools) == CORE_TOOLS and len(tools) <= 80


def test_platform_admin_tools_are_listed_for_admins_only(
    client: TestClient,
    db_session: Session,
    test_user_admin: UserNew,
    test_user_curator: UserNew,
) -> None:
    admin_only = admin_only_tools(app, tool_names(app.openapi()))
    assert {"create_curation_schema", "list_llm_providers", "search_logs"} <= admin_only
    curator = pat(db_session, test_user_curator)
    for path in ("/mcp", "/mcp/full"):
        assert not admin_only & set(_tools(client, curator, path)), path
    full = set(_tools(client, pat(db_session, test_user_admin), "/mcp/full"))
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
    assert not {"created_by", "record_hash", "approved_at", "tags", "meta"} & set(out)
    assert lean(result)["created_by"] == "u1"  # /mcp/full keeps audit fields


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
    assert "created_by" not in core and full["created_by"] == str(test_user_curator.id)
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

    assert "ui_configuration" not in read()
    assert read(compact=False)["ui_configuration"] == {"layout": "tabs"}


def test_tool_definitions_are_lean_and_curation_saves_name_the_evidence(
    client: TestClient, db_session: Session, test_user_curator: UserNew
) -> None:
    tools = _tools(client, pat(db_session, test_user_curator), "/mcp")
    text = json.dumps(list(tools.values()))
    assert '"title"' not in text and ".0," not in text
    for name in ("save_draft_curations", "update_curation", "create_curation"):
        assert "genetic_evidence.case_level" in tools[name]["description"], name
    assert tools["read_my_work"]["description"].startswith("My work queue")
    assert "get_publication" in tools["validate_pmids"]["description"]


def test_a_result_over_the_limit_is_a_typed_error(
    client: TestClient,
    db_session: Session,
    test_user_curator: UserNew,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(audit, "MAX_RESULT_CHARS", 10)
    result = call(client, pat(db_session, test_user_curator), "read_users_me")
    assert result["isError"] is True
    text = result["content"][0]["text"]
    assert text.startswith("response_too_large:") and "\nnext: narrow" in text
