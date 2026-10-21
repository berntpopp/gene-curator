"""Structured diff of two evidence_data snapshots, one item per changed path.

Paths: dict keys joined with '.', list items as `[i]`, or `[id]` when every item of both lists is
a record with an "id" (so an inserted case does not shift the rest). A subtree that appears or
disappears is one item, not one per leaf.
"""

from typing import Any

_MISSING = object()


def _by_id(items: list[Any]) -> dict[str, Any] | None:
    if all(isinstance(i, dict) and "id" in i for i in items):
        return {str(i["id"]): i for i in items}
    return None


def _walk(path: str, before: Any, after: Any, out: list[dict[str, Any]]) -> None:
    if before is _MISSING or after is _MISSING:
        added = before is _MISSING
        out.append(
            {
                "path": path,
                "change": "added" if added else "removed",
                "before": None if added else before,
                "after": after if added else None,
            }
        )
    elif isinstance(before, dict) and isinstance(after, dict):
        for key in [*before, *(k for k in after if k not in before)]:
            _walk(
                f"{path}.{key}" if path else str(key),
                before.get(key, _MISSING),
                after.get(key, _MISSING),
                out,
            )
    elif isinstance(before, list) and isinstance(after, list):
        old, new = _by_id(before), _by_id(after)
        if old is not None and new is not None:
            for key in [*old, *(k for k in new if k not in old)]:
                _walk(
                    f"{path}[{key}]",
                    old.get(key, _MISSING),
                    new.get(key, _MISSING),
                    out,
                )
        else:
            for i in range(max(len(before), len(after))):
                _walk(
                    f"{path}[{i}]",
                    before[i] if i < len(before) else _MISSING,
                    after[i] if i < len(after) else _MISSING,
                    out,
                )
    elif before != after:
        out.append(
            {"path": path, "change": "changed", "before": before, "after": after}
        )


def diff_evidence(
    before: dict[str, Any], after: dict[str, Any]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    _walk("", before, after, out)
    return out
