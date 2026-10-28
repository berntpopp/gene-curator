"""Reviewer warnings on saved evidence, by path (MCP study round 4): PMIDs written into free
text, a summary claiming another total than the computed one, and an experimental row that
reuses a case row's PMID and variant (a patient filed as experimental evidence)."""

import re
from collections.abc import Iterator
from typing import Any

from .case_rows import case_row_warnings, case_tables

_PMID_TEXT = re.compile(r"\bPMID\b|(?<![\w.:/-])\d{7,8}(?![\w.:/-])", re.IGNORECASE)
# Fields that hold IDs or variants, not prose
_NOT_TEXT = {"id", "pmid", "variant", "variant_1", "variant_2"}
_CLAIM = re.compile(
    r"\btotal(?:\s+score)?(?:\s+(?:of|is|=|:))?\s*(\d+(?:\.\d+)?)"
    r"|(\d+(?:\.\d+)?)\s*points?\s+(?:in\s+)?total\b",
    re.IGNORECASE,
)


def _texts(node: Any, path: str = "") -> Iterator[tuple[str, str]]:
    """(path, text) of every free-text string under ``node``."""
    if isinstance(node, dict):
        for key, value in node.items():
            sub = f"{path}.{key}" if path else str(key)
            if isinstance(value, str):
                if key not in _NOT_TEXT and not key.endswith(("_id", "_ids")):
                    yield sub, value
            else:
                yield from _texts(value, sub)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _texts(value, f"{path}[{i}]")


def _rows(node: Any, path: str) -> Iterator[tuple[str, dict[str, Any]]]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _rows(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, row in enumerate(node):
            if isinstance(row, dict):
                yield f"{path}[{i}]", row


def _pmid(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _misfiled_patients(evidence: dict[str, Any]) -> list[str]:
    cases = [
        (f"{path}[{i}]", _pmid(row.get("pmid")), str(row.get(key)).strip())
        for path, _, rows in case_tables(evidence)
        for i, row in enumerate(rows)
        if isinstance(row, dict)
        for key in ("variant", "variant_1", "variant_2")
        if len(str(row.get(key) or "").strip()) >= 4 and _pmid(row.get("pmid"))
    ]
    warnings = []
    for at, row in _rows(
        evidence.get("experimental_evidence"), "experimental_evidence"
    ):
        text = " ".join(str(v) for v in row.values() if isinstance(v, str)).lower()
        for case_at, pmid, variant in cases:
            if _pmid(row.get("pmid")) == pmid and variant.lower() in text:
                warnings.append(
                    f"{at}: reuses PMID {pmid} and variant {variant} of {case_at}; a "
                    "patient's variant is case-level evidence, not experimental"
                )
                break
    return warnings


def evidence_warnings(evidence: dict[str, Any], total: float) -> list[str]:
    """Case-row lint plus the reviewer checks above, each naming its path."""
    warnings = case_row_warnings(evidence)
    warnings += [
        f"{at}: mentions a PMID in free text; record each paper in a row's pmid field"
        for at, text in _texts(evidence)
        if _PMID_TEXT.search(text)
    ]
    summary = evidence.get("evidence_summary")
    claim = _CLAIM.search(summary) if isinstance(summary, str) else None
    if claim and abs(float(claim.group(1) or claim.group(2)) - total) > 0.05:
        claimed = float(claim.group(1) or claim.group(2))
        warnings.append(
            f"evidence_summary: claims a total of {claimed:g} points; the computed total "
            f"is {total:g}"
        )
    return warnings + _misfiled_patients(evidence)
