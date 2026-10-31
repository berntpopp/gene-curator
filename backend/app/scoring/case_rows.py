"""Case-level row checks (MCP study round 3, owner decision 2026-10-28): a variant is an HGVS
c./g./m./n./r./p. notation, an rsID or a genomic coordinate, not prose such as "truncating variant
(as reported)". A CNV or a repeat-region insertion described in prose counts when the text names its
extent or region (KGDB owner decision 2026-10-31: "deletion of exons 2-29", "C insertion in the
VNTR"). Warnings name the row's path; placeholder rows also score 0 (evidence_items)."""

import re
from collections import defaultdict
from typing import Any

# HGVS (optionally on a reference sequence), rsID, chr1:123 / 1-12345 (bare: 5+ digits), and
# structural: exon-level or whole-gene del/dup, ISCN (arr[GRCh37] 6p12.3(...)x1) or a cytoband,
# in either word order; a base inserted or duplicated in a named repeat region (MUC1 VNTR)
_BASE = (
    r"(?:(?-i:[ACGT]{1,3})|(?:cytosine|guanine|adenine|thymine)s?)"  # "a" is no base
)
_REPEAT = r"[^.;]{0,40}\b(?:VNTR|tandem repeat|repeat region)"
_VARIANT = re.compile(
    r"(?:^|[\s:(\[,;])(?:[cgmnr]\.\[?[\d*(?-]|p\.\[?\(?(?:[A-Z][a-z]{2}|[A-Z*])\d)"
    r"|\brs\d+\b"
    r"|\bchr(?:\d{1,2}|X|Y|MT?)[:-]\d{3,}|\b(?:\d{1,2}|X|Y|MT?)[:-]\d{5,}"
    r"|\bexons?\s*\d+(?:\s*[-\u2013]\s*\d+)?\s*(?:del|dup)"
    r"|\b(?:whole|entire)[- ]gene\s*(?:del|dup)"
    r"|\b(?:deletion|duplication)s?\s+(?:of|spanning|encompassing|including)\s+(?:the\s+)?"
    r"(?:exons?\s*\d+|(?:whole|entire)[- ]gene)"
    rf"|\b{_BASE}\s*(?:insertion|duplication|ins|dup)\b{_REPEAT}"
    rf"|\b(?:insertion|duplication)\s+of\s+(?:an?\s+|one\s+|\d+\s+)?{_BASE}\b{_REPEAT}"
    r"|\b(?:arr|seq)\s*\[|\b(?:\d{1,2}|X|Y)[pq]\d{1,2}(?:\.\d+)?\b"
    r"|\b(?:del|dup|inv|ins|t)\([\dXY;]+\)\([pq]\d",
    re.IGNORECASE,
)
_DIGIT_GROUPS = re.compile(r"(?<=\d),(?=\d{3})")  # chr6:51,775,000 -> chr6:51775000
# Predicted null: frameshift, stop gain, canonical +/-1,2 splice, exon or whole-gene deletion
_NULL = re.compile(
    r"fs\b|fs\*|p\.\(?[A-Z](?:[a-z]{2})?\d+(?:Ter|\*|X\b)"
    r"|c\.[\d*-]+[+-][12][ACGT]?>|exons?\s*\d+(?:-\d+)?\s*del|(?:whole|entire)[- ]gene"
    r"|\bdeletions?\s+(?:of|spanning|encompassing|including)\s+(?:the\s+)?exons?"
    r"|\b(?:nonsense|frameshift|stop[- ]gain)",
    re.IGNORECASE,
)
_MISSENSE = re.compile(
    r"p\.\(?[A-Z][a-z]{2}\d+(?!Ter)[A-Z][a-z]{2}\)?(?:\s|$|;|,)|\bmissense",
    re.IGNORECASE,
)
_COHORT = re.compile(
    r"cohort|\b\d+\s*(?:patients|individuals|probands|families|cases)\b", re.IGNORECASE
)
_VARIANT_KEYS = ("variant", "variant_1", "variant_2")


def is_variant(text: Any) -> bool:
    """True for an HGVS notation, an rsID, a genomic coordinate or a structural variant."""
    if not isinstance(text, str):
        return False
    return _VARIANT.search(_DIGIT_GROUPS.sub("", text)) is not None


def case_tables(evidence: Any) -> list[tuple[str, str, list[Any]]]:
    """(path, table name, rows) for the four SOP v11 case-level tables."""
    genetic = evidence.get("genetic_evidence") if isinstance(evidence, dict) else None
    case = genetic.get("case_level") if isinstance(genetic, dict) else None
    out = []
    for moi in ("autosomal_dominant_or_x_linked", "autosomal_recessive"):
        tables = case.get(moi) if isinstance(case, dict) else None
        for name in ("predicted_or_proven_null", "other_variant_type"):
            rows = tables.get(name) if isinstance(tables, dict) else None
            if isinstance(rows, list):
                path = f"genetic_evidence.case_level.{moi}.{name}"
                out.append((path, name, rows))
    return out


def _counted(row: dict[str, Any]) -> bool:
    try:
        return float(row.get("proband_counted_points") or 0) > 0
    except (TypeError, ValueError):
        return False


def _row_warnings(at: str, table: str, row: dict[str, Any]) -> list[str]:
    variants = {k: row[k] for k in _VARIANT_KEYS if str(row.get(k) or "").strip()}
    warnings = [
        f"{at}.{key}: {value!r} is not a variant; enter HGVS (c./p./g.), an rsID, a "
        "genomic coordinate, or a CNV or repeat insertion naming its extent"
        for key, value in variants.items()
        if not is_variant(value)
    ]
    if _counted(row) and not str(row.get("score_status") or "").strip():
        warnings.append(
            f"{at}.score_status: blank; set score, review or contradicts (only score "
            "counts points)"
        )
    texts = [str(v) for v in variants.values()]
    recessive = "autosomal_recessive" in at
    if table == "other_variant_type" and texts:
        # AR null + other is valid here: only every variant looking null is misfiled
        nulls = [bool(_NULL.search(t)) for t in texts]
        if all(nulls) if recessive else nulls[0]:
            warnings.append(
                f"{at}: variant looks null (frameshift, stop, canonical splice or "
                "deletion); record it under predicted_or_proven_null"
            )
    if table == "predicted_or_proven_null" and any(_MISSENSE.search(t) for t in texts):
        warnings.append(
            f"{at}: variant looks missense; record it under other_variant_type"
        )
    if _COHORT.search(str(row.get("proband_label") or "")):
        warnings.append(
            f"{at}.proband_label: names a cohort; record one row per described proband"
        )
    return warnings


def case_row_warnings(evidence: Any) -> list[str]:
    """Path-addressed lint of case-level rows: placeholder or misfiled variants, cohort
    labels, and one paper scored as many proband rows."""
    warnings: list[str] = []
    by_pmid: dict[str, list[str]] = defaultdict(list)
    for path, table, rows in case_tables(evidence):
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            warnings += _row_warnings(f"{path}[{i}]", table, row)
            if pmid := str(row.get("pmid") or "").strip():
                by_pmid[pmid].append(f"{path}[{i}]")
    for pmid, paths in by_pmid.items():
        if len(paths) >= 3:
            warnings.append(
                f"PMID {pmid} is scored as {len(paths)} proband rows ({', '.join(paths)}); "
                "confirm each is a distinct proband with its own variant"
            )
    return warnings
