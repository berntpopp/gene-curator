"""KGDB end-to-end frictions: what agents and the importer read (REST and MCP alike)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CurationNew, PrecurationNew

pytestmark = pytest.mark.unit

KEY = "MONDO:0011308|AR|SUSCEPTIBILITY|G1"
SUSCEPTIBLE = {
    "mondo_id": "MONDO:0011308",
    "mode_of_inheritance": "HP:0000007",
    "relationship_type": "susceptibility",
    "risk_allele": "G1",
}


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def susceptible(db_session: Session, test_curation: CurationNew) -> CurationNew:
    test_curation.entity_key = KEY
    test_curation.evidence_data = dict(SUSCEPTIBLE)
    db_session.commit()
    return test_curation


def test_reads_name_the_entity_key_and_risk_allele(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    susceptible: CurationNew,
    test_precuration: PrecurationNew,
) -> None:
    cid = susceptible.id
    detail = client.get(f"/api/v1/curations/{cid}", headers=_h(curator_token)).json()
    assert (detail["entity_key"], detail["risk_allele"]) == (KEY, "G1")
    review = client.get(f"/api/v1/curations/{cid}/review", headers=_h(curator_token))
    assert review.status_code == 200, review.text
    assert review.json()["curation"]["entity_key"] == KEY
    listed = client.get("/api/v1/curations/", headers=_h(curator_token)).json()
    [row] = [c for c in listed["curations"] if c["id"] == str(cid)]
    assert (row["entity_key"], row["risk_allele"]) == (KEY, "G1")

    test_precuration.evidence_data = dict(SUSCEPTIBLE)
    db_session.commit()
    pre = client.get(
        f"/api/v1/precurations/{test_precuration.id}", headers=_h(curator_token)
    ).json()
    assert pre["risk_allele"] == "G1"
    assert pre["entity_key"] == test_precuration.entity_key


def test_list_and_get_send_the_stored_verdict(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_curation: CurationNew,
) -> None:
    """One canonical form everywhere (the stored key); labels are the UI's."""
    test_curation.computed_verdict = "no_known"
    db_session.commit()
    detail = client.get(
        f"/api/v1/curations/{test_curation.id}", headers=_h(curator_token)
    ).json()
    listed = client.get("/api/v1/curations/", headers=_h(curator_token)).json()
    [row] = [c for c in listed["curations"] if c["id"] == str(test_curation.id)]
    assert row["computed_verdict"] == detail["computed_verdict"] == "no_known"


def _kgdb_susceptibility(db: Session, c: CurationNew) -> None:
    """Pin the KGDB susceptibility model; 600 cases: association 3, functional 2."""
    from tests.unit.test_kgdb_methodology import SCHEMAS
    from tests.unit.test_point_model import _version

    config = SCHEMAS["KGDB Susceptibility Curation"]["scoring_configuration"]
    c.methodology_version_id = _version(db, c, 1, config).id
    study = {"pmid": "12345678", "study_label": "A", "variant": "rs1"}
    study |= {"cases_total": 600, "controls_total": 600}
    study |= {"significant_after_correction": True}
    functional = [{"pmid": "12345678", "assay": a} for a in "ab"]
    c.evidence_data = {
        **SUSCEPTIBLE,
        "association": {"studies": [study]},
        "experimental": {"functional": functional},
    }
    db.commit()


def test_susceptibility_scores_name_the_association_points(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    susceptible: CurationNew,
) -> None:
    _kgdb_susceptibility(db_session, susceptible)
    score = client.get(
        f"/api/v1/curations/{susceptible.id}/score", headers=_h(curator_token)
    )
    assert score.status_code == 200, score.text
    assert (score.json()["association_score"], score.json()["total_score"]) == (3, 5)
    susceptible.computed_scores = {"association_total": 3, "total_score": 5}
    db_session.commit()
    listed = client.get("/api/v1/curations/", headers=_h(curator_token)).json()
    [row] = [c for c in listed["curations"] if c["id"] == str(susceptible.id)]
    assert row["computed_scores"]["association_score"] == 3


@pytest.mark.parametrize(
    ("key", "entered"),
    [
        ("MONDO:0000001|AR", "AR"),
        ("MONDO:0000001|AR", "Autosomal recessive"),
        ("MONDO:0000001|HP:0000007", "HP:0000007"),  # a key from before #614
    ],
)
def test_export_names_the_moi_by_its_hpo_id(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_curation: CurationNew,
    key: str,
    entered: str,
) -> None:
    from datetime import UTC, datetime

    from app.models import ActiveCuration, CurationStatus

    at = datetime.now(UTC)
    test_curation.entity_key = key
    test_curation.evidence_data = {
        "mondo_id": "MONDO:0000001",
        "mode_of_inheritance": entered,
    }
    test_curation.status, test_curation.approved_at = CurationStatus.ACTIVE, at
    db_session.add(
        ActiveCuration(
            gene_id=test_curation.gene_id,
            scope_id=test_curation.scope_id,
            curation_id=test_curation.id,
            entity_key=test_curation.entity_key,
            activated_at=at,
        )
    )
    db_session.commit()
    [item] = client.get("/api/v1/export/curations", headers=_h(curator_token)).json()[
        "items"
    ]
    assert (item["mode_of_inheritance"], item["moi_hpo_id"]) == ("HP:0000007",) * 2
    assert item["mode_of_inheritance_entered"] == entered
