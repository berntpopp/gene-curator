"""MCP-only result shaping, so agents spend fewer tokens (MCP study round 7, finding 2).

The API answers as before; only the tool result an agent reads is reshaped.
"""

import difflib
from collections.abc import Callable
from typing import Any

# Arguments that exist on the tool only: popped before the API call
MCP_ONLY_ARGS: dict[str, dict[str, dict[str, Any]]] = {
    "get_curation": {
        "fields": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Return only these keys or dotted paths (id and "
            'lock_version always come along), e.g. ["evidence_data"] or '
            '["evidence_data.genetic_evidence.segregation"]. Default on /mcp: '
            "everything but evidence_data",
        }
    }
}
_ALWAYS = ("id", "lock_version")
_OMITTED = (
    'evidence_data: get_curation(fields=["evidence_data"]) or a dotted path such as '
    '"evidence_data.genetic_evidence.case_level" returns it'
)
_PMID_NEXT = (
    "fix or remove the PMID: a row that cites it scores 0 and submit refuses it "
    "(a draft still saves)"
)
_CONTEXT = 8  # unchanged words kept around each change
_LONG_TEXT = 200  # shorter changed strings stay as before/after


def pick(data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    """Only the given keys or dotted paths of data; unknown ones listed, not guessed."""
    out = {key: data[key] for key in _ALWAYS if key in data}
    unknown = []
    for field in fields:
        source: Any = data
        parts = field.split(".")
        for part in parts[:-1]:
            source = source.get(part) if isinstance(source, dict) else None
        if not isinstance(source, dict) or parts[-1] not in source:
            unknown.append(field)
            continue
        target = out
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = source[parts[-1]]
    if unknown:
        out["unknown_fields"] = unknown
    return out


def word_diff(before: str, after: str) -> str:
    """git --word-diff style: [-removed-]{+added+}, long unchanged runs cut to ..."""
    a, b = before.split(), after.split()
    if a == b:
        return "(whitespace changed only)"
    ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    parts = []
    for n, (tag, i1, i2, j1, j2) in enumerate(ops):
        if tag != "equal":
            if i2 > i1:
                parts.append(f"[-{' '.join(a[i1:i2])}-]")
            if j2 > j1:
                parts.append(f"{{+{' '.join(b[j1:j2])}+}}")
            continue
        words = a[i1:i2]
        head = words[:_CONTEXT] if n else []  # context after the previous change
        tail = words[-_CONTEXT:] if n < len(ops) - 1 else []  # before the next
        if len(head) + len(tail) < len(words):
            words = [*head, "...", *tail]
        parts.append(" ".join(words))
    return " ".join(p for p in parts if p)


def _short_diff(diff: Any) -> None:
    for item in (diff or {}).get("items", []):
        before, after = item.get("before"), item.get("after")
        if (
            isinstance(before, str)
            and isinstance(after, str)
            and len(before) + len(after) > _LONG_TEXT
        ):
            item["word_diff"] = word_diff(before, after)
            del item["before"], item["after"]


def _group_blocked(state: Any) -> None:
    """One entry per reason with every stage it blocks, not the reason per stage."""
    if not isinstance(state, dict) or not state.get("blocked"):
        return
    grouped: dict[str, list[str]] = {}
    for entry in state["blocked"]:
        grouped.setdefault(entry["reason"], []).append(entry["stage"])
    state["blocked"] = [{"stages": s, "reason": r} for r, s in grouped.items()]


def _concise(data: dict[str, Any]) -> None:
    if data.pop("evidence_data", None) is not None:
        data["omitted"] = _OMITTED


def _review(data: dict[str, Any]) -> None:
    _short_diff(data.get("diff"))
    _group_blocked(data.get("workflow"))


def _pmid_next(data: dict[str, Any]) -> None:
    for result in data.get("results", []):
        if result.get("status") == "not_found":
            result["next"] = _PMID_NEXT


# /mcp only, in place; /mcp/full keeps the API's shape
_LEAN_SHAPES: dict[str, Callable[[dict[str, Any]], None]] = {
    "get_curation": _concise,
    "curation_diff": _short_diff,
    "read_curation_for_review": _review,
    "get_workflow_state": _group_blocked,
    "validate_pmids": _pmid_next,
}


def shape(name: str, data: Any, *, lean: bool, args: dict[str, Any]) -> Any:
    """The tool result an agent reads; lean is /mcp, args the MCP-only arguments."""
    if not isinstance(data, dict):
        return data
    if args.get("fields") is not None:
        return pick(data, args["fields"])
    if lean and name in _LEAN_SHAPES:
        _LEAN_SHAPES[name](data)
    return data
