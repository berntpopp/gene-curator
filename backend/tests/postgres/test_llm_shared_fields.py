"""Every field key in the seeded schemas is either shared with the LLM or deliberately
excluded (#489), so a new seeded field is never dropped from runs silently."""

import os
from collections.abc import Iterator
from typing import Any

import psycopg2
import pytest

from app.services.llm_runs import SHARED_EVIDENCE_KEYS

pytestmark = pytest.mark.postgres

# Never sent to a provider: the curator's judgement and conclusion (blind view, #464).
EXCLUDED: frozenset[str] = frozenset(
    {
        "decision",
        "evidence_quality",
        "evidence_summary",
        "explanation",
        "impact",
        "inheritance_consistency",
        "phenotype_match",
        "points",
        "preliminary_verdict",
        "proband_counted_points",
        "proband_not_counted_points",
        "rationale",
        "replicated_over_time",
        "score_status",
        "segregations_counted",
        "segregations_not_counted",
        "study_design_strength",
    }
)


def _keys(fields: Any) -> Iterator[str]:
    if isinstance(fields, list):  # list-shaped definitions: [{"name": ..., ...}]
        for spec in fields:
            if isinstance(spec, dict) and "name" in spec:
                yield str(spec["name"])
                yield from _keys(spec.get("properties"))
                yield from _keys((spec.get("items") or {}).get("properties"))
        return
    if not isinstance(fields, dict):
        return
    for name, spec in fields.items():
        yield name
        if isinstance(spec, dict):
            yield from _keys(spec.get("properties"))
            items = spec.get("items")
            if isinstance(items, dict):
                yield from _keys(items.get("properties"))


def test_seeded_schema_fields_are_shared_or_excluded() -> None:
    with (
        psycopg2.connect(os.environ["OWNER_DATABASE_URL"]) as conn,
        conn.cursor() as cur,
    ):
        cur.execute("SELECT field_definitions FROM curation_schemas")
        keys = {k for (fields,) in cur.fetchall() for k in _keys(fields)}
        cur.execute("SELECT snapshot->'field_definitions' FROM methodology_versions")
        keys |= {k for (fields,) in cur.fetchall() for k in _keys(fields)}
    assert keys, "no seeded schema fields found"
    unlisted = sorted(keys - SHARED_EVIDENCE_KEYS - EXCLUDED)
    assert unlisted == [], ", ".join(unlisted)
    assert not SHARED_EVIDENCE_KEYS & EXCLUDED
