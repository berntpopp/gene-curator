"""Submit refuses unknown PMIDs (#267): the form only checked tables that were opened."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy.orm import Session

from app.models import CurationNew
from app.models.models import Publication
from app.schemas.validation import PMIDValidationResult
from app.services import publication_service
from app.services.publication_service import PublicationService, evidence_pmids

EVIDENCE = {
    "genetic_evidence": {
        "case_level": {"autosomal_dominant": {"other": [{"pmid": "PMID: 99999999"}]}}
    },
    "experimental_evidence": {"function": {"expression": [{"pmid": "31000001"}]}},
    "contradictory_evidence": [{"pmid": "31000002"}, {"pmid": "not-a-pmid"}],
}


def _fake_fetch(monkeypatch: MonkeyPatch, outcome: dict[str, str | None]) -> list[str]:
    """PMID -> None (found) or the service's error text; returns the PMIDs fetched."""
    fetched: list[str] = []

    async def fetch(self: PublicationService, pmid: str) -> PMIDValidationResult:
        fetched.append(pmid)
        error = outcome.get(pmid)
        return PMIDValidationResult(pmid=pmid, is_valid=error is None, error=error)

    monkeypatch.setattr(PublicationService, "fetch_publication", fetch)
    return fetched


def _submit(client: TestClient, token: str, curation: CurationNew) -> Any:
    return client.post(
        f"/api/v1/curations/{curation.id}/submit",
        json={"lock_version": curation.lock_version},
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest.fixture
def stored(db_session: Session, test_curation: CurationNew) -> CurationNew:
    test_curation.evidence_data = EVIDENCE  # e.g. saved through /draft
    db_session.add(Publication(pmid="31000002", title="Cached", journal="J"))
    db_session.commit()
    return test_curation


def test_evidence_pmids_reads_every_table_and_the_prefix() -> None:
    assert evidence_pmids(EVIDENCE) == {"99999999", "31000001", "31000002"}
    assert evidence_pmids(None) == set()


def test_unknown_pmid_refuses_submit_and_changes_nothing(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    stored: CurationNew,
    monkeypatch: MonkeyPatch,
) -> None:
    fetched = _fake_fetch(
        monkeypatch, {"99999999": "Publication not found: 99999999", "31000001": None}
    )
    before = (stored.status, stored.workflow_stage, stored.lock_version)

    r = _submit(client, admin_token, stored)

    assert r.status_code == 422, r.text
    assert "99999999" in r.json()["detail"] and "31000001" not in r.json()["detail"]
    assert sorted(fetched) == ["31000001", "99999999"]  # the cached one is not fetched
    db_session.refresh(stored)
    assert (stored.status, stored.workflow_stage, stored.lock_version) == before


def test_known_pmids_submit(
    client: TestClient, admin_token: str, stored: CurationNew, monkeypatch: MonkeyPatch
) -> None:
    _fake_fetch(monkeypatch, {})
    r = _submit(client, admin_token, stored)
    assert r.status_code == 200, r.text
    assert r.json()["workflow_stage"] == "review"


def test_a_failed_lookup_does_not_block_submit(
    client: TestClient, admin_token: str, stored: CurationNew, monkeypatch: MonkeyPatch
) -> None:
    _fake_fetch(monkeypatch, {"99999999": "API timeout", "31000001": "HTTP 503"})
    warnings: list[dict[str, Any]] = []
    monkeypatch.setattr(
        publication_service.logger, "warning", lambda msg, **kw: warnings.append(kw)
    )
    assert _submit(client, admin_token, stored).status_code == 200
    assert warnings and sorted(warnings[0]["pmids"]) == ["31000001", "99999999"]
