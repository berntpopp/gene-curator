"""Reviewer warnings on saved evidence, by path (MCP study round 4): PMIDs written into free
text, a summary claiming another total than the computed one, and an experimental row that
reuses a case row's PMID and variant or mentions a proband, patient, individual or family
(a patient filed as experimental evidence; patient_cells rows excepted); and the hint
that Definitive needs replicated_over_time once the total reaches 12 points."""

import re
from collections.abc import Iterator
from typing import Any

from .case_rows import case_row_warnings, case_tables

# "PMID: 12345678", "PMID12345678", "pubmed 1234567" or a PubMed URL; not bare numbers.
# Group 1 or 2 is the PMID.
PMID_TEXT = re.compile(
    r"\b(?:PMID|PubMed)\s*(?:ID)?\s*[:#]?\s*(\d{1,9})\b"
    r"|pubmed\.ncbi\.nlm\.nih\.gov/(\d{1,9})",
    re.IGNORECASE,
)
# Fields that hold IDs or variants, not prose
NOT_TEXT = {"id", "pmid", "variant", "variant_1", "variant_2"}
# A described person in an experimental row (text lowercased): likely a misfiled patient.
# "family" only in patient context, not "gene family" or "family of proteins".
_PERSON = re.compile(
    r"\b(?:proband|patient|individual)s?\b|\b(?:pedigree|kindred)s?\b"
    r"|\bfamil(?:y|ies)\s+(?:[ivx]+|\d+|[a-z])\b(?!\s+of\b)"
    r"|\b(?:affected|consanguineous|index|two|three|four|five|several|multiple|\d+)"
    r"\s+famil(?:y|ies)\b"
)
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
                if key not in NOT_TEXT and not key.endswith(("_id", "_ids")):
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
        reused = next(
            (
                (case_at, pmid, variant)
                for case_at, pmid, variant in cases
                if _pmid(row.get("pmid")) == pmid and variant.lower() in text
            ),
            None,
        )
        if reused:
            case_at, pmid, variant = reused
            warnings.append(
                f"{at}: reuses PMID {pmid} and variant {variant} of {case_at}; a "
                "patient's variant is case-level evidence, not experimental"
            )
        elif "patient_cells" not in at and (person := _PERSON.search(text)):
            warnings.append(
                f"{at}: mentions {person.group(0)!r}; a described patient is case-level "
                "evidence (or patient_cells), not a model or experimental row"
            )
    return warnings


def evidence_warnings(evidence: dict[str, Any], result: dict[str, Any]) -> list[str]:
    """Case-row lint plus the reviewer checks above, each naming its path; ``result`` is the
    point model's (total, sections)."""
    total = result["total"]
    warnings = case_row_warnings(evidence)
    if total >= 12 and evidence.get("replicated_over_time") is not True:
        warnings.append(  # the Definitive band reads the total (R6/R7 T7-3)
            "replicated_over_time: the total reaches 12 points; Definitive needs "
            "replication over time. If the first evidence is over 3 years old and "
            "later independent papers replicate it, set replicated_over_time to true; "
            "else the class stays Strong"
        )
    warnings += [
        f"{at}: mentions a PMID in free text; record each paper in a row's pmid field"
        for at, text in _texts(evidence)
        # the summary cites papers by design (MCP study round 5: the warning was ignored)
        if at != "evidence_summary" and PMID_TEXT.search(text)
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
