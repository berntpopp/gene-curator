"""RFC 7396 JSON merge patch of evidence saves (moved from crud/curation.py)."""

from typing import Any


def merge_patch(target: Any, patch: Any) -> Any:
    """RFC 7396 JSON merge patch: objects merge, null deletes, anything else replaces."""
    if not isinstance(patch, dict):
        return patch
    out = dict(target) if isinstance(target, dict) else {}
    for key, value in patch.items():
        if value is None:
            out.pop(key, None)
        else:
            out[key] = merge_patch(out.get(key), value)
    return out
