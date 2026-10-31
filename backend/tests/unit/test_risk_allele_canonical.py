"""KGDB end-to-end: a risk allele is stored, keyed and exported in one canonical form,
rs<digits> <BASE> (lower-case rs, one space, upper-case A/C/G/T); other allele names are
trimmed with whitespace collapsed. An rsID without its base is refused at submit."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.crud.precuration_entity import entity_key_of
from app.schemas.curation import CurationDraftSave, risk_allele
from app.schemas.precuration import PrecurationCreate, PrecurationDraftSave
from app.services.evidence_ids import evidence_errors

pytestmark = pytest.mark.unit

BUNDLE = (
    Path(__file__).parents[3] / "docs/schemas/kidney-genetics/kgdb-methodology.json"
)
[SUS] = [
    s
    for s in json.loads(BUNDLE.read_text())["schemas"]
    if s["name"] == "KGDB Susceptibility Precuration"
]
ENTITY = {
    "mondo_id": "MONDO:0009633",
    "mode_of_inheritance": "HP:0000005",
    "relationship_type": "susceptibility",
}


@pytest.mark.parametrize(
    ("typed", "stored"),
    [
        ("RS17831251c", "rs17831251 C"),
        ("rs17831251  C", "rs17831251 C"),
        ("rs17831251 C", "rs17831251 C"),
        (" rs 17831251\tg ", "rs17831251 G"),
        ("  APOL1   G1 ", "APOL1 G1"),
        ("rs17831251", "rs17831251"),  # kept as typed; submit refuses it
    ],
)
def test_saved_bodies_store_the_canonical_allele(typed: str, stored: str) -> None:
    lock = {"lock_version": 0}
    bodies = [
        PrecurationCreate(gene_id=uuid4(), evidence_data={"risk_allele": typed}),
        PrecurationDraftSave(evidence_data={"risk_allele": typed}, **lock),
        CurationDraftSave(
            evidence_data={"entity_definition": {"risk_allele": typed}}, **lock
        ),
    ]
    assert [
        b.evidence_data.get("risk_allele")
        or b.evidence_data["entity_definition"]["risk_allele"]
        for b in bodies
    ] == [stored] * 3
    assert risk_allele({"risk_allele": typed}, None) == stored  # the export


def test_formatting_variants_share_one_entity_key(db_session: Session) -> None:
    keys = {
        entity_key_of(
            db_session, {**ENTITY, "risk_allele": risk_allele({"risk_allele": a}, None)}
        )
        for a in ("RS17831251c", "rs17831251  C", "rs17831251 C")
    }
    assert keys == {"MONDO:0009633|UNDETERMINED|SUSCEPTIBILITY|RS17831251C"}


@pytest.mark.parametrize(
    ("allele", "refused"),
    [("rs17831251", True), ("rs17831251 C", False), ("APOL1 G1", False)],
)
def test_an_rsid_without_its_base_is_refused(allele: str, refused: bool) -> None:
    paths = {e.path for e in evidence_errors({"risk_allele": allele}, SUS)}
    assert ("risk_allele" in paths) is refused


@pytest.mark.parametrize(
    ("typed", "stored"),
    [
        (
            "rs\uff11\uff12\uff13 C",
            "rs\uff11\uff12\uff13 C",
        ),  # non-ASCII digits are not an rsID (as in SQL)
        ("APOL1\u00a0G1", "APOL1\u00a0G1"),  # only ASCII whitespace collapses
        ("\t rs12  a \n", "rs12 A"),
    ],
)
def test_the_normaliser_is_ascii_like_migration_091(typed: str, stored: str) -> None:
    from app.core.risk_allele import canonical_allele

    assert canonical_allele(typed) == stored
