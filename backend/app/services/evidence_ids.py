"""PMID, MONDO, OMIM and HPO IDs in evidence: format and existence checks, scoring exclusion.

Drafts warn and never block; submit refuses malformed IDs. An unreachable upstream leaves an
ID unverified, never wrong.
"""

import re
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.schema_validator import schema_validator
from app.schemas.curation import EvidenceWarning
from app.scoring.evidence_lint import NOT_TEXT, PMID_TEXT
from app.services.ontology_service import lookup_terms
from app.services.publication_service import PMID_FORMAT, lookup_pmids

# kind: (format, message, upstream)
_KINDS: dict[str, tuple[re.Pattern[str], str, str]] = {
    "pmid": (PMID_FORMAT, "Expected 1-9 digits, e.g. 31558469", "PubMed"),
    "mondo": (
        re.compile(r"^MONDO:\d{7}$"),
        "Expected MONDO:NNNNNNN, e.g. MONDO:0007739",
        "MONDO",
    ),
    "omim": (
        re.compile(r"^(?:OMIM:|MIM:)?(\d{6})$", re.IGNORECASE),
        "Expected 6 digits, optionally prefixed OMIM: or MIM:, e.g. OMIM:143100",
        "OMIM",
    ),
    "hpo": (re.compile(r"^HP:\d{7}$"), "Expected HP:NNNNNNN, e.g. HP:0001250", "HPO"),
}


@dataclass(frozen=True)
class _Ref:
    path: str
    kind: str
    value: str
    id: str | None  # normalized; None when malformed


def _kind(key: str) -> str | None:
    # ponytail: the key name says what an ID is (pmid, *mondo_id, *omim_id, *hpo_id)
    if key == "pmid":
        return "pmid"
    return next((k for k in ("mondo", "omim", "hpo") if key.endswith(f"{k}_id")), None)


def _normalize(kind: str, text: str) -> str | None:
    match = _KINDS[kind][0].match(text)
    if not match:
        return None
    if kind == "pmid":
        return match.group(1)
    return f"OMIM:{match.group(1)}" if kind == "omim" else text


def _text(value: Any) -> str:
    return (
        str(value).strip()
        if isinstance(value, str | int) and not isinstance(value, bool)
        else ""
    )


def _refs(node: Any, path: str = "") -> Iterator[_Ref]:
    if isinstance(node, list):
        for i, value in enumerate(node):
            yield from _refs(value, f"{path}[{i}]")
        return
    if not isinstance(node, dict):
        return
    for key, value in node.items():
        sub = f"{path}.{key}" if path else str(key)
        kind = _kind(str(key))
        if kind is None and isinstance(value, str) and key not in NOT_TEXT:
            # PMIDs cited in free text are checked like pmid fields: warned, never refused
            for match in PMID_TEXT.finditer(value):
                yield _Ref(
                    sub, "pmid", match.group(0), match.group(1) or match.group(2)
                )
            continue
        if kind is None or isinstance(value, dict):
            yield from _refs(value, sub)
            continue
        items = (
            [(f"{sub}[{n}]", v) for n, v in enumerate(value)]
            if isinstance(value, list)
            else [(sub, value)]
        )
        for at, raw in items:
            if text := _text(raw):
                yield _Ref(at, kind, text, _normalize(kind, text))


def format_errors(evidence: Any) -> list[EvidenceWarning]:
    """Network-free: every malformed ID, by field path."""
    return [
        EvidenceWarning(path=r.path, message=_KINDS[r.kind][1])
        for r in _refs(evidence)
        if r.id is None
    ]


def check_ids(db: Session, evidence: Any) -> tuple[list[EvidenceWarning], set[str]]:
    """(warnings, unknown IDs): malformed, not found, or unverified (upstream unreachable).
    Unknown IDs are normalized: PMIDs as digits, OMIM as OMIM:NNNNNN."""
    refs = list(_refs(evidence))
    pmids = {r.id for r in refs if r.kind == "pmid" and r.id}
    terms = {r.id for r in refs if r.kind != "pmid" and r.id}
    with ThreadPoolExecutor(
        1
    ) as pool:  # both upstreams at once; the ontology side has no DB
        pending = pool.submit(lookup_terms, terms)
        unknown_pmids, failed_pmids = lookup_pmids(db, pmids) if pmids else ([], [])
        unknown_terms, failed_terms = pending.result()
    unknown = {*unknown_pmids, *unknown_terms}
    failed = {*failed_pmids, *failed_terms}
    warnings = []
    for r in refs:
        source = _KINDS[r.kind][2]
        if r.id is None:
            warnings.append(EvidenceWarning(path=r.path, message=_KINDS[r.kind][1]))
        elif r.id in unknown:
            warnings.append(
                EvidenceWarning(path=r.path, message=f"{r.value} not found in {source}")
            )
        elif r.id in failed:
            message = f"{r.value} unverified: {source} lookup unavailable, retry later"
            warnings.append(EvidenceWarning(path=r.path, message=message))
    return warnings, unknown


def _unknown_pmid(row: dict[str, Any], unknown: set[str]) -> bool:
    """A PMID is entered but malformed or not in PubMed."""
    text = _text(row.get("pmid"))
    return bool(text) and _normalize("pmid", text) in (None, *unknown)


def scorable(
    evidence: Any, unknown: set[str], path: str = ""
) -> tuple[Any, list[dict[str, str]]]:
    """Evidence with each row whose PMID is malformed or unknown replaced by None (such rows
    score no points; later rows keep their index), and those rows' {path, pmid, reason}."""
    excluded: list[dict[str, str]] = []
    if isinstance(evidence, dict):
        out = {}
        for key, value in evidence.items():
            out[key], dropped = scorable(
                value, unknown, f"{path}.{key}" if path else str(key)
            )
            excluded += dropped
        return out, excluded
    if not isinstance(evidence, list):
        return evidence, excluded
    rows: list[Any] = []
    for i, value in enumerate(evidence):
        if isinstance(value, dict) and _unknown_pmid(value, unknown):
            excluded.append(
                {
                    "path": f"{path}[{i}]",
                    "pmid": _text(value.get("pmid")),
                    "reason": "unknown_pmid",
                }
            )
            rows.append(None)
            continue
        kept, dropped = scorable(value, unknown, f"{path}[{i}]")
        rows.append(kept)
        excluded += dropped
    return rows, excluded


def score_scorable(
    engine: Any, config: Any, evidence: dict[str, Any], unknown: set[str]
) -> Any:
    """Score without the rows whose PMID is malformed or unknown; the breakdown lists them
    with the engine's own exclusions (no_pmid, no_variant)."""
    data, excluded = scorable(evidence, unknown)
    result = engine.calculate_scores(data, config)
    excluded += result.evidence_breakdown.get("excluded", [])
    if excluded:
        result.evidence_breakdown = {**result.evidence_breakdown, "excluded": excluded}
    return result


def shrunk_arrays(old: Any, new: Any, path: str = "") -> list[EvidenceWarning]:
    """Arrays a merge patch made shorter: RFC 7396 replaces arrays whole, so sending one
    new row drops the others."""
    if isinstance(old, dict) and isinstance(new, dict):
        return [
            w
            for key in old.keys() & new.keys()
            for w in shrunk_arrays(old[key], new[key], f"{path}.{key}" if path else key)
        ]
    if isinstance(old, list) and isinstance(new, list) and len(new) < len(old):
        message = (
            f"Merge replaced {len(old)} items with {len(new)}; arrays are replaced "
            "whole, so send every row to keep it"
        )
        return [EvidenceWarning(path=path, message=message)]
    return []


class InvalidEvidenceError(ValueError):
    """Review entry refused: values that fail the schema or the ID formats, by path."""

    def __init__(self, errors: list[EvidenceWarning]) -> None:
        listed = "; ".join(f"{e.path}: {e.message}" for e in errors)
        super().__init__(f"Evidence has invalid values: {listed}")
        self.errors = errors


def unprocessable(error: InvalidEvidenceError) -> HTTPException:
    """422 listing each {path, message}."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={
            "message": "Evidence has invalid values; fix these fields and resubmit",
            "errors": [e.model_dump() for e in error.errors],
        },
    )


def evidence_errors(evidence: Any, definition: dict[str, Any]) -> list[EvidenceWarning]:
    """Network-free, by path: schema errors (required fields are checked separately) and
    malformed PMID, MONDO, OMIM and HPO IDs."""
    fields = {
        k: definition.get(k) or {} for k in ("field_definitions", "validation_rules")
    }
    result = schema_validator.validate_evidence_data(evidence or {}, fields)
    errors = [
        EvidenceWarning(path=e["field"], message=e["message"])
        for e in result.errors
        if e.get("type") != "required"
    ]
    seen = {e.path for e in errors}
    return errors + [e for e in format_errors(evidence) if e.path not in seen]


def ontology_ids(evidence: Any) -> set[str]:
    """Well-formed MONDO, OMIM and HPO IDs, normalized."""
    return {r.id for r in _refs(evidence) if r.kind != "pmid" and r.id}


def not_found(evidence: Any, unknown: set[str]) -> list[EvidenceWarning]:
    """Each path whose ID is in ``unknown``."""
    return [
        EvidenceWarning(
            path=r.path, message=f"{r.value} not found in {_KINDS[r.kind][2]}"
        )
        for r in _refs(evidence)
        if r.id in unknown
    ]
