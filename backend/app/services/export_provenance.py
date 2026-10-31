"""Contributions and sources of the export (#593), from the stored curation and the
row provenance (services/row_provenance.py). Software contributions never approve:
the approver is always the person who approved."""

from collections.abc import Iterator
from datetime import datetime
from typing import Any

from app.core.source_field import DIRECTIONS, KINDS
from app.schemas.provenance import (
    Agent,
    Contribution,
    EvidenceLine,
    ExportSource,
    Extension,
    contribution,
)
from app.services.row_provenance import row_key, tables


def _person(by: dict[str, Any]) -> Agent:
    return Agent(name=by.get("name"), agentType="person")


def _software(agent: dict[str, Any]) -> Agent:
    tools = agent.get("tools_used")
    return Agent(
        name=agent.get("model"),
        agentType="software",
        description=agent.get("agent"),
        extensions=[Extension(name="tools_used", value=tools)] if tools else None,
    )


def _writes(stamp: dict[str, Any]) -> Iterator[Contribution]:
    for step in ("added", "changed"):
        by, at = stamp.get(f"{step}_by"), stamp.get(f"{step}_at")
        if not isinstance(by, dict):
            continue
        yield contribution("curator", _person(by), at)
        if isinstance(by.get("agent"), dict):
            yield contribution(
                "curator", _software(by["agent"]), at, actedOnBehalfOf=_person(by)
            )


def _is_source(value: Any) -> bool:
    return isinstance(value, dict) and value.get("kind") in KINDS


def _source(value: dict[str, Any]) -> ExportSource:
    kind, ident = value["kind"], str(value.get("id") or "").strip() or None
    url = value.get("url") or (ident if kind == "url" else None)
    return ExportSource(
        documentType=kind,
        id=ident,
        title=value.get("title"),
        urls=[url] if url else [],
        pmid=ident if kind == "pmid" else None,
        doi=ident if kind == "doi" else None,
        citation=value.get("citation"),
        retrieved_at=value.get("retrieved_at"),
        tool=value.get("tool"),
        record_sha256=value.get("record_sha256"),
    )


def _sources(row: dict[str, Any]) -> list[ExportSource]:
    found = [
        item
        for cell in row.values()
        for item in (cell if isinstance(cell, list) else [cell])
        if _is_source(item)
    ]
    return [_source(item) for item in found]


def evidence_lines(evidence: Any, stamps: dict[str, Any] | None) -> list[EvidenceLine]:
    """Each table row with a source, a direction or a provenance stamp, by path."""
    lines = []
    for path, rows in tables(evidence):
        for i, row in enumerate(rows):
            if _is_source(row):  # a list field of sources, not a table
                continue
            stamp = (stamps or {}).get(row_key(path, i, row))
            direction = row.get("direction")
            line = EvidenceLine(
                path=f"{path}[{i}]",
                row_id=str(row["id"]) if row.get("id") is not None else None,
                directionOfEvidenceProvided=direction
                if direction in DIRECTIONS
                else None,
                sources=_sources(row),
                contributions=list(_writes(stamp if isinstance(stamp, dict) else {})),
            )
            if line.sources or line.contributions or line.directionOfEvidenceProvided:
                lines.append(line)
    return lines


def curation_contributions(
    curator: str | None,
    created_at: datetime | None,
    approver: str | None,
    approved_at: datetime | None,
    lines: list[EvidenceLine],
    assessors: list[tuple[str | None, datetime | None]] | None = None,
) -> list[Contribution]:
    """Curator, each software agent that wrote rows, then the approving reviewers as
    assessors and the approver (persons). An agent never assesses or approves."""
    out = [contribution("curator", Agent(name=curator, agentType="person"), created_at)]
    software: dict[str, Contribution] = {}
    for line in lines:
        for c in line.contributions:
            key = c.model_dump_json(exclude={"date"})
            last = software.get(key)
            if c.contributor.agentType == "software" and (
                last is None or str(c.date or "") > str(last.date or "")
            ):
                software[key] = c  # one per agent and person, at its latest write
    out += software.values()
    if approved_at is None:
        return out
    for name, at in assessors or [(approver, approved_at)]:
        out.append(contribution("assessor", Agent(name=name, agentType="person"), at))
    out.append(
        contribution("approver", Agent(name=approver, agentType="person"), approved_at)
    )
    return out
