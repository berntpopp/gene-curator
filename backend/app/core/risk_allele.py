"""Susceptibility risk allele (#614, KGDB end-to-end): one canonical text, so the stored
value, the entity_key and the export agree. Migration 091 holds the same rule in SQL."""

import re
from typing import Any

# ASCII digits and whitespace, as the PostgreSQL rule in 091
_RSID = re.compile(r"\s*rs\s*(\d+)\s*([ACGT])\s*", re.IGNORECASE | re.ASCII)
_SPACE = re.compile(r"\s+", re.ASCII)


def canonical_allele(text: str) -> str:
    """rs<digits> <BASE> for an rsID with its base ("RS17831251c" -> "rs17831251 C");
    any other form (HGVS, haplotype, an rsID without base) trimmed, whitespace collapsed."""
    if m := _RSID.fullmatch(text):
        return f"rs{m[1]} {m[2].upper()}"
    return _SPACE.sub(" ", text).strip(" ")


def canonical_risk_alleles(evidence: dict[str, Any]) -> dict[str, Any]:
    """Evidence as saved: risk_allele (flat or under entity_definition) made canonical."""
    for node in (evidence, evidence.get("entity_definition")):
        if isinstance(node, dict) and isinstance(node.get("risk_allele"), str):
            node["risk_allele"] = canonical_allele(node["risk_allele"])
    return evidence
