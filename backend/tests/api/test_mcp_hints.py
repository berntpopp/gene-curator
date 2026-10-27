"""MCP tool errors: a one-line next step (study F8) and arguments checked before
the call (round 3, T3-1)."""

from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.mcp.audit import _tool_error, argument_errors
from app.models import UserNew
from tests.api.test_mcp import call, pat

pytestmark = pytest.mark.unit


def _error(
    status: int, tool: str, detail: object = "nope", args: dict | None = None
) -> str:
    request = httpx.Request("GET", "http://test/api")
    response = httpx.Response(status, json={"detail": detail}, request=request)
    error = httpx.HTTPStatusError("x", request=request, response=response)
    return str(_tool_error(error, tool, args))


@pytest.mark.parametrize(
    ("tool", "detail", "args", "next_tool"),
    [
        ("get_gene", "Gene not found", {"gene_id": "x"}, "create_gene"),
        ("get_genes_by_symbol", "nope", {"symbol": "X"}, "add_genes_to_scope"),
        (
            "curation_diff",
            "No baseline",
            {"curation_id": "x"},
            "get_workflow_audit_trail",
        ),
        ("get_publication", "nope", {"pmid": "1"}, "search_pubmed"),
        (
            "get_scope_details",
            "Scope not found",
            {"scope_id": "x"},
            "list_scopes(name=",
        ),
        # the detail wins over argument names: the scope exists, the gene does not
        ("create_gene_assignment", "Gene not found", {"scope_id": "x"}, "create_gene"),
        ("get_curation", "Curation not found", {"curation_id": "x"}, "list_curations"),
    ],
)
def test_not_found_points_to_the_tool_for_that_resource(
    tool: str, detail: str, args: dict, next_tool: str
) -> None:
    assert next_tool in _error(404, tool, detail, args).split("\nnext: ")[1]


def test_errors_carry_a_next_step() -> None:
    stale = _error(409, "update_curation", {"current_lock_version": 3})
    assert stale.endswith(
        "next: re-read the item (get_curation or get_precuration), merge your change "
        "and retry"
    )
    assert _error(409, "delete_precuration", "Has linked curations").endswith(
        "next: the detail says why; a retry will not help"
    )
    assert "create_gene_assignment" in _error(403, "bulk_create_gene_assignments")
    assert "get_workflow_state" in _error(400, "execute_workflow_transition")
    assert "\nnext:" not in _error(500, "update_curation")


SCHEMA = {
    "type": "object",
    "properties": {
        "item_type": {"type": "string", "enum": ["curation", "precuration"]},
        "item_id": {"type": "string"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 50},
    },
    "required": ["item_type", "item_id"],
}


def test_argument_errors_name_the_field_and_the_bound() -> None:
    assert argument_errors(SCHEMA, {"item_type": "curation", "item_id": "x"}) == []
    problems = argument_errors(
        SCHEMA, {"item_type": "gene", "curation_id": "x", "limit": 51}
    )
    assert "unknown curation_id" in problems[0]
    assert "missing item_id" in problems
    assert any(
        p.startswith("limit: 51 is greater than the maximum of 50") for p in problems
    )
    assert any(p.startswith("item_type: 'gene' is not one of") for p in problems)
    assert "did you mean item_id?" in argument_errors(SCHEMA, {"itemid": "x"})[0]


def test_a_call_with_a_wrong_argument_never_reaches_the_api(
    client: TestClient, db_session: Session, test_user_curator: UserNew
) -> None:
    for path in ("/mcp", "/mcp/full"):
        result = call(
            client,
            pat(db_session, test_user_curator),
            "get_workflow_audit_trail",
            path=path,
            item_type="curation",
            curation_id=str(uuid4()),
        )
        text = result["content"][0]["text"]
        assert result["isError"] is True and "{item_id}" not in text
        assert text.startswith(
            "invalid_input: get_workflow_audit_trail: unknown curation_id (did you "
            "mean item_id?); missing item_id"
        ), text
        assert "accepts item_type (required), item_id (required)" in text
