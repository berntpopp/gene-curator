"""The `url` field type's value checks (#538, #282)."""

from typing import Any
from urllib.parse import urlsplit


def valid_url(value: Any) -> bool:
    """Blank (a cleared optional field: `required` is its own rule) or an http(s) URL with a
    host without whitespace, like the form's `new URL` check (#538). Only spaces is not blank,
    so a required url of spaces fails here."""
    if value == "":
        return True
    text = value.strip() if isinstance(value, str) else None
    try:
        parts = urlsplit(text) if text else None
    except ValueError:  # e.g. an unclosed IPv6 bracket
        return False
    host = parts.hostname if parts and parts.scheme in ("http", "https") else None
    return bool(host) and not any(c.isspace() for c in host or "")


def url_errors(value: Any, config: dict[str, Any]) -> list[tuple[str, str]]:
    """(message, type) of a url field's value: its format, then its ``max_length`` (#282)."""
    if not valid_url(value):
        return [("Enter an http(s) URL with a host", "format")]
    limit = config.get("max_length")
    if isinstance(limit, int) and not isinstance(limit, bool) and len(value) > limit:
        return [(f"URL must not exceed {limit} characters", "length")]
    return []
