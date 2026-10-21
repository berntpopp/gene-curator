"""Shared handling of free-text search input (catalogue, matrix, GET /search)."""

MAX_SEARCH = 100
# FastAPI `pattern=` for a search parameter: no NUL bytes (PostgreSQL rejects them with a 500)
NO_NUL = r"^[^\x00]*$"


def escape_like(text: str) -> str:
    """Escape LIKE wildcards so the text matches literally; pair with `escape="\\\\"`."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
