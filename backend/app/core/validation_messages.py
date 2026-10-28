"""422 messages that name the limit and what was received, never the value itself
(MCP study round 6: a 2037-character comment failed without saying why)."""

from typing import Any

# Where to put text that does not fit, per field
_ROOM = {"comments": "shorten, or put details in suggested_changes"}


def size_message(field: str, got: int, unit: str, bound: str, limit: Any) -> str:
    """'2037 characters, max 2000; shorten ...' (bound: max or min)."""
    advice = _ROOM.get(field, "shorten it" if bound == "max" else "add more")
    return f"{got} {unit}, {bound} {limit}; {advice}"


_PYDANTIC = {
    "string_too_long": ("characters", "max", "max_length"),
    "string_too_short": ("characters", "min", "min_length"),
    "too_long": ("items", "max", "max_length"),
    "too_short": ("items", "min", "min_length"),
}


_CHOICES = {"literal_error", "enum"}  # the msg already lists the allowed values


def explain(errors: Any) -> list[dict[str, Any]]:
    """FastAPI validation errors with a msg that states the limit and received size; the
    input is never echoed (it may be a password), except a value checked against an
    allowed list."""
    out = []
    for error in errors:
        item = dict(error)
        field = str(item.get("loc", ["?"])[-1])
        value, ctx = item.get("input"), item.get("ctx") or {}
        if item.get("type") in _PYDANTIC and isinstance(value, (str, list, dict)):
            unit, bound, key = _PYDANTIC[item["type"]]
            item["msg"] = size_message(field, len(value), unit, bound, ctx.get(key))
        elif item.get("type") in _CHOICES and isinstance(value, (str, int)):
            item["msg"] = f"{item.get('msg')} (got {str(value)[:50]!r})"
        item.pop("input", None)
        out.append(item)
    return out
