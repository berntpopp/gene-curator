"""MCP study F8: tool errors end with a one-line next step (tool-specific first)."""

import httpx
import pytest

from app.mcp.audit import _tool_error

pytestmark = pytest.mark.unit


def _error(status: int, tool: str) -> str:
    request = httpx.Request("GET", "http://test/api")
    response = httpx.Response(status, json={"detail": "nope"}, request=request)
    return str(
        _tool_error(
            httpx.HTTPStatusError("x", request=request, response=response), tool
        )
    )


def test_errors_carry_a_next_step() -> None:
    assert _error(409, "update_curation") == (
        "conflict: HTTP 409: nope\nnext: re-read the item (get_curation), merge your "
        "change, retry with its lock_version"
    )
    assert "create_gene_assignment" in _error(403, "bulk_create_gene_assignments")
    assert "get_workflow_state" in _error(400, "execute_workflow_transition")
    assert "\nnext:" not in _error(500, "update_curation")
