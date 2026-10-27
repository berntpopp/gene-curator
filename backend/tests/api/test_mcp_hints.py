"""MCP study F8: tool errors end with a one-line next step (tool-specific first)."""

import httpx
import pytest

from app.mcp.audit import _tool_error

pytestmark = pytest.mark.unit


def _error(status: int, tool: str, detail: object = "nope") -> str:
    request = httpx.Request("GET", "http://test/api")
    response = httpx.Response(status, json={"detail": detail}, request=request)
    error = httpx.HTTPStatusError("x", request=request, response=response)
    return str(_tool_error(error, tool))


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
