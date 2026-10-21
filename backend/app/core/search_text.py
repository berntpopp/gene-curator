"""Shared handling of free-text search input (catalogue, matrix, GET /search, user/gene/log search)."""

from typing import Annotated

from fastapi import Query

MAX_SEARCH = 100
# FastAPI `pattern=` for a search parameter: no NUL bytes (PostgreSQL rejects them with a 500)
NO_NUL = r"^[^\x00]*$"


# Optional free-text query parameter: literal text, no NUL, bounded length (422 otherwise)
SearchText = Annotated[str | None, Query(max_length=MAX_SEARCH, pattern=NO_NUL)]


def escape_like(text: str) -> str:
    """Escape LIKE wildcards so the text matches literally; pair with `escape="\\\\"`."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
