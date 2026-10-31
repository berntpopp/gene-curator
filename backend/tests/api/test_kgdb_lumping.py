"""#610: the KGDB bundle's lumping/splitting options (lowercase `lump`/`split`) pass
review entry; values outside both the bundle and the legacy set are still refused."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models import CurationSchema, Gene, PrecurationNew, Scope, UserNew
from app.services.review_guards import check_review_content

BUNDLE = json.loads(
    (
        Path(__file__).parents[3] / "docs/schemas/kidney-genetics/kgdb-methodology.json"
    ).read_text()
)
SCHEMA = next(s for s in BUNDLE["schemas"] if s["name"] == "KGDB Mendelian Precuration")
EVIDENCE = {
    "clingen_curated": False,
    "mondo_id": "MONDO:0011234",
    "disease_name": "Nephrotic syndrome",
    "mode_of_inheritance": "HP:0000007",
    "relationship_type": "mendelian",
    "binning": "isolated",
    "mechanism": "lof",
    "lumping_splitting_applicable": True,
    "lumping_splitting_rationale": "Same mechanism, same phenotype spectrum",
}


@pytest.fixture
def make_precuration(
    db_session: Session, test_scope: Scope, test_gene: Gene, test_user_admin: UserNew
):
    schema = CurationSchema(
        id=uuid4(),
        **{k: SCHEMA[k] for k in SCHEMA if k != "scoring_configuration"},
        is_active=True,
        schema_hash=uuid4().hex,
    )
    db_session.add(schema)
    db_session.commit()

    def make(decision: str) -> PrecurationNew:
        item = PrecurationNew(
            id=uuid4(),
            scope_id=test_scope.id,
            gene_id=test_gene.id,
            precuration_schema_id=schema.id,
            workflow_stage="precuration",
            evidence_data={**EVIDENCE, "lumping_splitting_decision": decision},
            created_by=test_user_admin.id,
            updated_by=test_user_admin.id,
        )
        db_session.add(item)
        db_session.commit()
        return item

    return make


@pytest.mark.parametrize("decision", ["lump", "split"])
def test_kgdb_bundle_decisions_enter_review(
    db_session: Session, make_precuration, decision: str
) -> None:
    check_review_content(db_session, make_precuration(decision))


def test_unknown_decision_is_refused(db_session: Session, make_precuration) -> None:
    with pytest.raises(ValueError):
        check_review_content(db_session, make_precuration("merge"))
