"""ClinGen as a reference beside our own curation (KGDB 2026-10-31): the GeneFoundry
record of the same entity is stored, a class departing from it needs a rationale before
review, and the export cites it as a statement shaped like adoption."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CurationNew, Gene
from app.services.review_guards import _unexplained_departure

pytestmark = pytest.mark.unit
CGGV = "CGGV:assertion_09d61dec-314b-4c5f-af2e-f22fc5992c12-2021-02-26T151356.823Z"


def _record(gene: Gene, **over: Any) -> dict[str, Any]:
    return {
        "source": "clingen",
        "cggv_id": CGGV,
        "permalink": f"https://search.clinicalgenome.org/kb/gene-validity/{CGGV}",
        "classification": "Definitive",
        "moi": "Autosomal dominant inheritance",
        "mondo": "MONDO_0004691",
        "hgnc_id": gene.hgnc_id,
        "expert_panel": "Kidney Cystic and Ciliopathy Disorders GCEP",
        "classified_date": "2021-02-26T15:13:56.823Z",
        "retrieved_at": "2026-10-31T09:10:08.948276Z",
        "record_sha256": "3" * 64,
        "citation": "ClinGen Gene-Disease Validity: PKD1 - Definitive (AD)",
        **over,
    }


@pytest.fixture
def curation(db_session: Session, test_curation: CurationNew) -> CurationNew:
    test_curation.entity_key = "MONDO:0004691|AD"
    db_session.commit()
    return test_curation


def _put(client: TestClient, token: str, cid: object, **body: Any) -> Any:
    return client.put(
        f"/api/v1/curations/{cid}",
        json={"lock_version": 0, **body},
        headers={"Authorization": f"Bearer {token}"},
    )


def test_reference_is_stored_checked_against_the_entity_and_gates_review(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    curation: CurationNew,
    test_gene: Gene,
) -> None:
    for over, path in (
        ({"mondo": "MONDO:0000001"}, "clingen_reference.mondo"),
        ({"moi": "AR"}, "clingen_reference.moi"),
        ({"hgnc_id": "HGNC:1"}, "clingen_reference.hgnc_id"),
    ):
        r = _put(
            client,
            admin_token,
            curation.id,
            clingen_reference=_record(test_gene, **over),
        )
        assert r.status_code == 422, r.text
        assert [e["path"] for e in r.json()["detail"]["errors"]] == [path]

    record = _record(test_gene)
    r = _put(client, admin_token, curation.id, clingen_reference=record)
    assert r.status_code == 200, r.text
    assert _detail(client, admin_token, curation.id)["clingen_reference"] == record
    db_session.refresh(curation)
    assert curation.clingen_reference == record

    # computed verdict (no evidence: no_known) departs from ClinGen's Definitive
    refused = client.post(
        f"/api/v1/curations/{curation.id}/submit",
        json={"lock_version": curation.lock_version},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert refused.status_code == 422, refused.text
    [error] = refused.json()["detail"]["errors"]
    assert error["path"] == "curator_classification_rationale"
    assert error["message"].endswith("departs from ClinGen's (Definitive)")

    r = _put(
        client,
        admin_token,
        curation.id,
        lock_version=curation.lock_version,
        clingen_reference=None,
    )
    assert r.status_code == 200, r.text
    assert _detail(client, admin_token, curation.id)["clingen_reference"] is None


def _detail(client: TestClient, token: str, cid: object) -> Any:
    r = client.get(
        f"/api/v1/curations/{cid}", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize(
    ("ours", "key", "rationale", "needs"),
    [
        ("definitive", "MONDO:1|AD", None, False),
        ("Definitive", "MONDO:1|AD", None, False),
        ("strong", "MONDO:1|AD", None, True),
        ("strong", "MONDO:1|AD", "Newer evidence", False),
        ("definitive", "MONDO:1|AD|SUSCEPTIBILITY", None, True),
    ],
)
def test_a_departure_from_clingen_needs_a_rationale(
    ours: str, key: str, rationale: str | None, needs: bool
) -> None:
    c = CurationNew(
        entity_key=key,
        curator_classification_rationale=rationale,
        clingen_reference={"classification": "Definitive"},
    )
    assert bool(_unexplained_departure(c, ours)) is needs
    assert _unexplained_departure(CurationNew(entity_key=key), "strong") is None
