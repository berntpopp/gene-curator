"""#596 and #593: docs/examples/export-page.json is written by the real export serializer
and validates against the committed JSON Schema snapshot of the export
(docs/examples/export-page.schema.json, VA-Spec field names). Both fail when stale;
regenerate with UPDATE_EXPORT_EXAMPLE=1 and commit the result."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from jsonschema import Draft202012Validator
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.curation_export import export_curations
from app.models import (
    ActiveCuration,
    CurationNew,
    CurationSchema,
    CurationStatus,
    Gene,
    Scope,
    ScopeMembership,
    UserNew,
    WorkflowPair,
)
from app.schemas.curation_export import CurationExportPage

pytestmark = pytest.mark.unit

DOCS = Path(__file__).parents[3] / "docs"
EXAMPLE = DOCS / "examples/export-page.json"
SNAPSHOT = DOCS / "examples/export-page.schema.json"
BUNDLE = json.loads(
    (DOCS / "schemas/kidney-genetics/kgdb-methodology.json").read_text()
)
TESTS = {
    t["name"].split(" ")[0]: t["evidence_data"]
    for s in BUNDLE["schemas"]
    if s.get("scoring_configuration")
    for t in s["scoring_configuration"].get("tests", [])
}
T = [datetime(2026, 10, d, 12, tzinfo=UTC) for d in range(1, 10)]
UPDATE = os.environ.get("UPDATE_EXPORT_EXAMPLE") == "1"


def _id(n: int) -> UUID:
    return UUID(int=n)


def _snapshot() -> str:
    schema = CurationExportPage.model_json_schema(mode="serialization")
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def _check(path: Path, text: str) -> None:
    if UPDATE:
        path.parent.mkdir(exist_ok=True)
        path.write_text(text)
    assert path.read_text() == text, (
        f"{path.name} is stale: run UPDATE_EXPORT_EXAMPLE=1 pytest {__file__}"
    )


def _cldn16() -> dict[str, Any]:
    evidence = json.loads(json.dumps(TESTS["CLDN16"]))
    by = {"id": str(_id(11)), "name": "Alice Curator"}
    first = evidence["genetic"]["probands"][0]
    first.update(
        id="row-p1",
        direction="supports",
        sources=[
            {
                "kind": "pmid",
                "id": first["pmid"],
                "title": "Paracellin-1 mutations in HOMG3",
                "tool": "genefoundry:pubtator_search_literature",
                "retrieved_at": "2026-10-02T09:00:00Z",
            },
            {
                "kind": "clinvar",
                "id": "VCV000012345",
                "url": "https://www.ncbi.nlm.nih.gov/clinvar/variation/12345/",
                "tool": "genefoundry:clinvar_get_variant",
                "retrieved_at": "2026-10-02T09:01:00Z",
                "record_sha256": "0" * 64,
                "citation": "ClinVar VCV000012345 (accessed 2026-10-02)",
            },
        ],
        provenance={
            "added_by": {
                **by,
                "agent": {
                    "model": "claude-opus-5-5",
                    "agent": "Claude Code",
                    "tools_used": [
                        "genefoundry:pubtator_search_literature",
                        "genefoundry:clinvar_get_variant",
                    ],
                },
            },
            "added_at": "2026-10-02T09:05:00+00:00",
            "changed_by": by,
            "changed_at": "2026-10-03T10:00:00+00:00",
        },
    )
    evidence["evidence_summary"] = (
        "Autosomal recessive familial hypomagnesemia with hypercalciuria and "
        "nephrocalcinosis (HOMG3); 10 probands, mouse and zebrafish models."
    )
    evidence["diagnostics"] = {
        "recommended_transcript": {"refseq": "NM_006580.4", "mane_status": "select"},
        "detectability": [
            {"challenge": "copy_number_variants", "methods": ["MLPA"], "sources": []}
        ],
        "resources": [],
    }
    return evidence


def _stamps(evidence: dict[str, Any]) -> dict[str, Any] | None:
    """The CLDN16 row's provenance moves beside the evidence, as the server keeps it."""
    rows = evidence.get("genetic", {}).get("probands", [])
    stamp = rows[0].pop("provenance", None) if rows else None
    return {"genetic.probands#row-p1": stamp} if stamp else None


def _page(db: Session) -> dict[str, Any]:
    scope = Scope(id=_id(1), name="kidney-genetics", display_name="Kidney Genetics")
    alice = UserNew(
        id=_id(11),
        email="alice@example.org",
        name="Alice Curator",
        hashed_password="x",
        role="user",
    )
    bob = UserNew(
        id=_id(12),
        email="bob@example.org",
        name="Bob Reviewer",
        hashed_password="x",
        role="user",
    )
    schema = CurationSchema(
        id=_id(21),
        name="KGDB Mendelian Curation",
        version="alpha",
        schema_type="curation",
        field_definitions={},
        workflow_states={},
        ui_configuration={"synopsis_field": "evidence_summary"},
        schema_hash="0" * 64,
    )
    pair = WorkflowPair(id=_id(22), name="KGDB Mendelian", version="alpha")
    db.add_all([scope, alice, bob, schema])
    db.flush()
    pair.curation_schema_id = schema.id
    db.add(pair)
    db.add(
        ScopeMembership(
            scope_id=scope.id, user_id=alice.id, role="curator", accepted_at=T[0]
        )
    )
    genes = {
        sym: Gene(
            id=_id(30 + i),
            hgnc_id=hgnc,
            approved_symbol=sym,
            record_hash=sym,
            previous_symbols=[],
            alias_symbols=[],
        )
        for i, (sym, hgnc) in enumerate(
            [("CLDN16", "HGNC:2037"), ("APOL1", "HGNC:618"), ("NEK8", "HGNC:13387")]
        )
    }
    db.add_all(genes.values())
    db.flush()
    rows = [
        # (n, gene, entity, evidence, scores, verdict, status, archive_reason)
        (41, "CLDN16", "MONDO:0009461|HP:0000007", _cldn16(), 16, "definitive",
         CurationStatus.ACTIVE, None),
        (42, "APOL1", "MONDO:0011308|HP:0000007|SUSCEPTIBILITY",
         TESTS["Established:"], 4, "established", CurationStatus.ACTIVE, None),
        (43, "NEK8", "MONDO:0013727|HP:0000006", TESTS["NEK8"], 14, "strong",
         CurationStatus.ARCHIVED, "Curation deleted"),
    ]  # fmt: skip
    for i, (n, sym, key, evidence, total, verdict, status, reason) in enumerate(rows):
        c = CurationNew(
            id=_id(n),
            scope_id=scope.id,
            gene_id=genes[sym].id,
            workflow_pair_id=pair.id,
            entity_key=key,
            workflow_stage="active",
            status=status,
            evidence_data=evidence,
            row_provenance=_stamps(evidence),
            computed_scores={"total_score": total},
            computed_verdict=verdict,
            created_by=alice.id,
            created_at=T[i],
            approved_by=bob.id,
            approved_at=T[i + 3],
            updated_at=T[i + 3],
        )
        db.add(c)
        db.flush()
        db.add(
            ActiveCuration(
                id=_id(50 + i),
                gene_id=c.gene_id,
                scope_id=scope.id,
                curation_id=c.id,
                entity_key=key,
                activated_at=T[i + 3],
                updated_at=T[i + 3],
                archived_at=T[8] if reason else None,
                archive_reason=reason,
            )
        )
    db.commit()
    page = export_curations(db, alice.id, None, None, None, 100)
    return page.model_dump(mode="json")


def test_example_export_page_is_fresh_and_valid(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        settings, "GENE_CURATOR_FRONTEND_URL", "https://curator.example"
    )
    _check(SNAPSHOT, _snapshot())
    page = _page(db_session)
    statuses = [(i["relationship_type"], i["status"]) for i in page["items"]]
    assert statuses == [
        ("mendelian", "active"),
        ("susceptibility", "active"),
        ("mendelian", "archived"),
    ]
    assert page["items"][0]["evidence"]["diagnostics"]
    assert page["items"][0]["synopsis"].startswith("Autosomal recessive")
    Draft202012Validator(json.loads(SNAPSHOT.read_text())).validate(page)
    _check(EXAMPLE, json.dumps(page, indent=2, ensure_ascii=False) + "\n")


def test_snapshot_names_the_va_spec_fields() -> None:
    text = SNAPSHOT.read_text()
    for field in (
        "contributions",
        "contributor",
        "agentType",
        "activityType",
        "primaryCoding",
        "actedOnBehalfOf",
        "directionOfEvidenceProvided",
        "documentType",
        "evidence_lines",
    ):
        assert f'"{field}"' in text, field
