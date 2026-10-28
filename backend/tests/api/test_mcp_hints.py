"""MCP tool errors: a one-line next step (study F8) and arguments checked before
the call (round 3, T3-1)."""

from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.mcp.audit import (
    _api_problems,
    _tool_error,
    argument_errors,
    coerce_arguments,
)
from app.models import UserNew
from tests.api.test_mcp import call, pat

pytestmark = pytest.mark.unit


def _error(status: int, tool: str, detail: object = "nope") -> str:
    request = httpx.Request("GET", "http://test/api")
    response = httpx.Response(status, json={"detail": detail}, request=request)
    error = httpx.HTTPStatusError("x", request=request, response=response)
    return str(_tool_error(error, tool))


@pytest.mark.parametrize(
    ("tool", "detail", "next_tool"),
    [
        ("get_gene", "Gene not found", "create_gene"),
        (
            "curation_diff",
            "No submitted snapshot of this curation",
            "get_workflow_audit_trail",
        ),
        ("curation_diff", "No active curation for this gene and scope", "audit_trail"),
        ("get_publication", "Publication not found: 1", "validate_pmids(pmids"),
        ("get_scope_details", "Scope not found", "list_scopes(name="),
        ("create_gene_assignment", "Gene not found", "create_gene"),
        # the detail decides, never the tool's arguments: a missing precuration is
        # not a missing gene
        ("create_curation", "Approved precuration not found", "list_curations"),
        ("get_curation", "Curation not found", "list_curations"),
    ],
)
def test_not_found_points_to_the_tool_for_that_resource(
    tool: str, detail: str, next_tool: str
) -> None:
    assert next_tool in _error(404, tool, detail).split("\nnext: ")[1]


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
    long = {"type": "object", "properties": {"comments": {"maxLength": 2000}}}
    assert argument_errors(long, {"comments": "x" * 2037}) == [LONG]


LONG = (
    "comments: 2037 characters, max 2000; shorten, or put details in suggested_changes"
)


def test_a_too_long_review_comment_says_why_via_rest_and_mcp(
    client: TestClient, db_session: Session, test_user_curator: UserNew
) -> None:
    """MCP study round 6, T8: 2037 characters failed with the comment echoed, not why."""
    token = pat(db_session, test_user_curator)
    comment = "x" * 2037
    rest = client.post(
        f"/api/v1/workflow/reviews/{uuid4()}/submit",
        json={"decision": "request_changes", "comments": comment},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rest.status_code == 422
    (item,) = rest.json()["detail"]
    assert (item["loc"], item["msg"]) == (["body", "comments"], LONG.split(": ", 1)[1])
    assert "x" * 100 not in rest.text
    mcp = call(
        client,
        token,
        "submit_peer_review",
        "/mcp",
        review_id=str(uuid4()),
        decision="request_changes",
        comments=comment,
    )
    text = mcp["content"][0]["text"]
    assert LONG in text and "x" * 100 not in text


def test_api_422_items_read_field_then_message() -> None:
    detail = [
        {"loc": ["body", "decision"], "msg": "Input should be ... (got 'ok')"},
        {"loc": ["body", "lock_version"], "msg": "Field required"},
    ]
    assert _api_problems(detail) == (
        "decision: Input should be ... (got 'ok'); lock_version: Field required"
    )
    assert _api_problems(["plain"]) == "['plain']"
    assert "decision: Input" in _error(422, "submit_peer_review", detail)


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


def test_numbers_and_booleans_sent_as_text_are_parsed_like_fastapi_did() -> None:
    schema = {
        "properties": {
            "limit": {"type": "integer"},
            "score": {"anyOf": [{"type": "number"}, {"type": "null"}]},
            "active_only": {"type": "boolean"},
            "name": {"type": "string"},
            "id": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
        }
    }
    args = {
        "limit": " 20",
        "score": "1.5",
        "active_only": "True",
        "name": "7",
        "id": "7",
    }
    assert coerce_arguments(schema, args) == {
        "limit": 20,
        "score": 1.5,
        "active_only": True,
        "name": "7",  # a string field keeps its text
        "id": "7",
    }
    # Text that does not parse is left for argument_errors to name
    bad = coerce_arguments(schema, {"limit": "many", "active_only": "maybe"})
    assert bad == {"limit": "many", "active_only": "maybe"}
    assert argument_errors(schema, bad)[0].startswith("limit: 'many' is not of type")


def test_a_call_with_numbers_as_text_still_works(
    client: TestClient, db_session: Session, test_user_curator: UserNew
) -> None:
    for path in ("/mcp", "/mcp/full"):
        result = call(
            client,
            pat(db_session, test_user_curator),
            "list_scopes",
            path=path,
            limit="20",
            active_only="true",
        )
        assert not result.get("isError"), result
