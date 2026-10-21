"""Tolerant reading of stored evidence items."""

from typing import Any


def rows(value: Any) -> list[dict[str, Any]]:
    """Evidence items from stored data: lists lose non-dict entries; a legacy
    ``{count, points}`` summary dict counts as one item; anything else is empty."""
    if isinstance(value, dict):
        return [value] if "points" in value else []
    if isinstance(value, list):
        return [i for i in value if isinstance(i, dict)]
    return []


def has_content(value: Any) -> bool:
    """True if the value holds anything; blank rows from an untouched form row do not count."""
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(has_content(v) for v in value)
    if isinstance(value, dict):
        return any(has_content(v) for v in value.values())
    return value is not None and value is not False
