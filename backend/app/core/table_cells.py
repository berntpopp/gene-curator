"""Evidence-table cells checked at submit as the form does (#538, monkey L2): blank
required cells, whole numbers, calendar dates, and every column kind the validator knows
(number, url, source, select, text length, ...; #611), each named table[row].column. A
fully blank row is dropped, not validated."""

import re
from collections.abc import Callable
from datetime import date
from typing import Any

from app.core.schema_validation_result import SchemaValidationResult
from app.crud.precuration_required import visible_when
from app.scoring.evidence_items import has_content

Check = Callable[..., None]  # (path, value, config, result)
_WHOLE = re.compile(r"\s*[+-]?\d+(\.0*)?\s*")


def cell_errors(
    name: str,
    rows: Any,
    config: dict[str, Any],
    res: SchemaValidationResult,
    checks: dict[str, Check],
) -> None:
    """Add each bad cell of `rows` to `res`; `checks` are the validator's field checks."""
    cols = config.get("columns") or {}
    if isinstance(cols, list):  # the seeds' [{"id": ..., "type": ...}] form
        cols = {c.get("id"): c for c in cols}
    for i, row in enumerate(rows if isinstance(rows, list) else []):
        if not isinstance(row, dict) or not has_content(row):
            continue
        for key, col in cols.items():
            at, value, kind = f"{name}[{i}].{key}", row.get(key), col.get("type")
            if value in (None, ""):
                # ponytail: a conditional column (visible_when) is never required here
                if col.get("required") and not visible_when(col):
                    res.add_error(at, "Required field is missing", "required_cell")
            elif kind == "integer" and (
                isinstance(value, bool) or not _WHOLE.fullmatch(str(value))
            ):
                res.add_error(at, "Value must be a whole number", "type")
            elif kind == "date" and not _calendar_date(value):
                res.add_error(at, "Use a date: YYYY-MM-DD", "format")
            elif kind in checks:
                checks[kind](at, value, col, res)


def _calendar_date(value: Any) -> bool:
    """A date cell holds a day, not a timestamp (KGDB's Diagnostics schema, #611)."""
    try:
        date.fromisoformat(str(value))
    except ValueError:
        return False
    return len(str(value)) == 10
