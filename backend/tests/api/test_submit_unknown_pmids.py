"""Every route into review refuses unknown PMIDs (#267): the form only checked opened tables."""

import asyncio
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
from tests.api.test_evidence_point_ranges import BAD, _engine

EVIDENCE = {
    "genetic_evidence": {
        "case_level": {"autosomal_dominant": {"other": [{"pmid": "PMID: 99999999"}]}}
    },
    "experimental_evidence": {"function": {"expression": [{"pmid": "31000001"}]}},
    "contradictory_evidence": [{"pmid": "31000002"}],
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


def _transition(client: TestClient, token: str, curation: CurationNew) -> Any:
    return client.post(
        f"/api/v1/workflow/curation/{curation.id}/transition",
        json={"target_stage": "review"},
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
    assert evidence_pmids({"pmid": "not-a-pmid"}) == set()  # submit refuses its format


@pytest.mark.parametrize("route", [_submit, _transition])
def test_unknown_pmid_refuses_review_and_changes_nothing(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    stored: CurationNew,
    monkeypatch: MonkeyPatch,
    route: Any,
) -> None:
    fetched = _fake_fetch(
        monkeypatch, {"99999999": "Publication not found: 99999999", "31000001": None}
    )
    before = (stored.status, stored.workflow_stage, stored.lock_version)

    r = route(client, admin_token, stored)

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


def test_transition_route_enforces_point_ranges(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_curation: CurationNew,
    test_workflow_pair: Any,
) -> None:
    _engine(db_session, test_workflow_pair, "clingen_sop_v11")
    test_curation.evidence_data = BAD
    db_session.commit()
    before = test_curation.workflow_stage
    r = _transition(client, admin_token, test_curation)
    assert r.status_code == 422 and "between 0 and 3" in r.text
    db_session.refresh(test_curation)
    assert test_curation.workflow_stage == before


def test_lookups_are_capped_and_a_slow_europe_pmc_does_not_block(
    client: TestClient,
    admin_token: str,
    stored: CurationNew,
    monkeypatch: MonkeyPatch,
) -> None:
    running = peak = 0

    async def slow(self: PublicationService, pmid: str) -> PMIDValidationResult:
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(1)
        running -= 1
        return PMIDValidationResult(
            pmid=pmid, is_valid=False, error="Publication not found"
        )

    monkeypatch.setattr(PublicationService, "fetch_publication", slow)
    monkeypatch.setattr(publication_service, "LOOKUP_TIMEOUT_S", 0.05)
    warnings: list[str] = []
    monkeypatch.setattr(
        publication_service.logger, "warning", lambda msg, **kw: warnings.append(msg)
    )
    many = {str(31000100 + i) for i in range(12)}
    results = asyncio.run(publication_service._fetch_all(sorted(many)))
    assert [r.pmid for r in results] == sorted(many)
    assert all(not r.is_valid and "timeout" in (r.error or "").lower() for r in results)
    assert peak == publication_service.LOOKUP_CONCURRENCY
    assert _submit(client, admin_token, stored).status_code == 200
    assert warnings
