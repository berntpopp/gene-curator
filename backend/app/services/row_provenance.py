"""Row authorship of evidence tables (#593): who added and who last changed each row.

Kept beside the evidence in `curations.row_provenance` (080), never inside it, so the
evidence stays exactly what was entered (exports, diffs, importers with strict shapes).
Keys are `path#row id`, or `path[index]` for a row without an id. Every evidence write
recomputes the map: an unchanged row keeps its stamp, an edited one (matched by row id,
else by position) gets changed_by and changed_at, a new one added_by and added_at. The
actor is the person whose session or token wrote, plus the client-reported AI agent of
an MCP write (a software agent acting on that person's behalf).
"""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.mcp.audit import request_agent
from app.models import UserNew
from app.scoring.evidence_items import has_content


def actor(db: Session, user_id: UUID) -> dict[str, Any]:
    """{id, name} of the writing person, with `agent` when an AI agent wrote for them."""
    user = db.get(UserNew, user_id)
    out: dict[str, Any] = {
        "id": str(user_id),
        "name": (user.name or None) if user else None,  # never the email
    }
    if agent := request_agent.get():
        out["agent"] = agent
    return out


def row_key(path: str, index: int, row: dict[str, Any]) -> str:
    return f"{path}#{row['id']}" if row.get("id") is not None else f"{path}[{index}]"


def tables(node: Any, path: str = "") -> Iterator[tuple[str, list[dict[str, Any]]]]:
    """(path, rows) of every list of objects in the evidence (not inside rows)."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from tables(value, f"{path}.{key}" if path else str(key))
    elif node and isinstance(node, list) and all(isinstance(r, dict) for r in node):
        yield path, node


def stamped(
    db: Session, before: Any, after: Any, old: dict[str, Any] | None, user_id: UUID
) -> dict[str, Any]:
    """The row_provenance map for `after` (see the module docstring)."""
    return _stamp(
        before, after, old or {}, actor(db, user_id), datetime.now(UTC).isoformat()
    )


def _canon(row: dict[str, Any]) -> str:
    return json.dumps(row, sort_keys=True, default=str)


def _stamp(
    before: Any, after: Any, old: dict[str, Any], by: dict[str, Any], at: str
) -> dict[str, Any]:
    previous = dict(tables(before))
    out: dict[str, Any] = {}
    for path, rows in tables(after):
        old_rows = list(enumerate(previous.get(path, [])))
        by_id = {str(r["id"]): (i, r) for i, r in old_rows if r.get("id") is not None}
        by_content = {_canon(r): (i, r) for i, r in reversed(old_rows)}
        for i, row in enumerate(rows):
            if not has_content(row):
                continue
            match = by_id.get(str(row["id"])) if row.get("id") is not None else None
            match = match or by_content.get(_canon(row))
            if match is None and row.get("id") is None and i < len(old_rows):
                match = old_rows[i] if old_rows[i][1].get("id") is None else None
            prior = old.get(row_key(path, *match)) if match else None
            if match is not None and _canon(match[1]) == _canon(row):
                stamp = prior
            elif match is not None:
                stamp = {**(prior or {}), "changed_by": by, "changed_at": at}
            else:
                stamp = {"added_by": by, "added_at": at}
            if stamp:
                out[row_key(path, i, row)] = stamp
    return out
