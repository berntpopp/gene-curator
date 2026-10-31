"""`source` field type (#593): where an evidence row comes from, shaped like a GA4GH
VA-Spec Document plus the provenance GeneFoundry returns (tool, retrieved_at,
record_sha256, recommended citation). Usable as a table cell and as a list (an array
field with `items: {type: source}`, or a list in one cell). Gene Curator never fetches
the record; it checks the identifier's format and keeps what the client sent.
"""

import re
from datetime import datetime
from typing import Any

from app.core.schema_validation_result import SchemaValidationResult
from app.core.url_field import valid_url

# kind -> identifier format (NCBI, Crossref and ClinGen identifier docs)
ID_FORMATS: dict[str, tuple[re.Pattern[str], str]] = {
    "pmid": (re.compile(r"\d{1,10}"), "a PMID is 1-10 digits (PMID: prefix optional)"),
    "doi": (re.compile(r"10\.\d{4,9}/\S+"), "a DOI looks like 10.1234/abc"),
    "clinvar": (
        re.compile(r"(VCV|RCV|SCV)\d{9}(\.\d+)?"),
        "a ClinVar accession looks like VCV000012345 (VCV, RCV or SCV, 9 digits)",
    ),
    "clingen_allele": (
        re.compile(r"CA\d+"),
        "a ClinGen Allele Registry id looks like CA123",
    ),
    "clingen_validity": (
        re.compile(r"CGGV:assertion_\S+"),
        "a ClinGen gene validity id looks like CGGV:assertion_<uuid>",
    ),
    "database": (re.compile(r"\S.*"), "name the database record"),
}
KINDS = (*ID_FORMATS, "url")
DIRECTIONS = ("supports", "disputes", "neutral")  # VA-Spec directionOfEvidenceProvided
_SHA256 = re.compile(r"[0-9a-f]{64}")
TEXT_KEYS = ("title", "tool", "citation")


_PMID_PREFIX = re.compile(r"^pmid:\s*", re.IGNORECASE)


def source_id(kind: Any, ident: Any) -> str:
    """The identifier as checked and exported: trimmed, a PMID without "PMID:" (MUI-15)."""
    text = str(ident or "").strip()
    return _PMID_PREFIX.sub("", text, count=1) if kind == "pmid" else text


def _blank(value: Any) -> bool:
    return value in (None, "") or (
        isinstance(value, dict) and all(v in (None, "") for v in value.values())
    )


def _datetime(value: Any) -> bool:
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _id_error(kind: Any, ident: str, value: dict[str, Any]) -> tuple[str, str] | None:
    """(part, message) when kind or id is wrong, else None."""
    if kind not in KINDS:
        return "kind", f"kind must be one of {', '.join(KINDS)}"
    if kind == "url":
        ok = valid_url(ident or value.get("url")) and bool(ident or value.get("url"))
        return None if ok else ("id", "Enter an http(s) URL with a host")
    if not ident:
        return "id", "id is required"
    pattern, hint = ID_FORMATS[kind]
    return (
        None if pattern.fullmatch(ident) else ("id", f"{ident!r} is not valid: {hint}")
    )


def _detail_errors(value: dict[str, Any]) -> list[tuple[str, str]]:
    out = []
    if value.get("url") and not valid_url(value["url"]):
        out.append(("url", "Enter an http(s) URL with a host"))
    if value.get("retrieved_at") and not _datetime(value["retrieved_at"]):
        out.append(("retrieved_at", "Use an ISO 8601 date or time"))
    sha = value.get("record_sha256")
    if sha and not _SHA256.fullmatch(str(sha)):
        out.append(("record_sha256", "64 lowercase hex characters"))
    out += [
        (key, f"{key} must be text")
        for key in TEXT_KEYS
        if value.get(key) is not None and not isinstance(value[key], str)
    ]
    return out


def source_errors(
    path: str, value: Any, config: dict[str, Any], res: SchemaValidationResult
) -> None:
    """Add each bad part of a source (or a list of sources) to `res`, by field path."""
    if isinstance(value, list):
        for i, item in enumerate(value):
            source_errors(f"{path}[{i}]", item, config, res)
        return
    if _blank(value):
        return
    if not isinstance(value, dict):
        res.add_error(path, "A source is an object with kind and id", "type")
        return
    bad = _id_error(
        value.get("kind"), source_id(value.get("kind"), value.get("id")), value
    )
    for part, message in ([bad] if bad else []) + _detail_errors(value):
        res.add_error(f"{path}.{part}", message, "format")
