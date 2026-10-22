"""Bounded network work preserves completed results without concurrent cache sessions."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.schemas.validation import PMIDValidationResult
from app.services import publication_service as service
from tests.services.test_publication_service import _db


@pytest.mark.asyncio
async def test_deadline_preserves_not_found_and_reports_unfinished(monkeypatch):
    async def fetch(self, pmid):
        if pmid == "1":
            return PMIDValidationResult(
                pmid=pmid, is_valid=False, error="Publication not found: 1"
            )
        await asyncio.Event().wait()

    monkeypatch.setattr(service.PublicationService, "fetch_publication", fetch)
    monkeypatch.setattr(service, "LOOKUP_TIMEOUT_S", 0.02)
    results = await service._fetch_all(["1", "2"])
    assert [r.pmid for r in results] == ["1", "2"]
    assert results[0].error == "Publication not found: 1"
    assert "timeout" in results[1].error.lower()


@pytest.mark.asyncio
async def test_validation_parallelizes_network_only_and_deduplicates(monkeypatch):
    svc = service.PublicationService(_db())
    svc._get_cached_publication = AsyncMock(return_value=None)
    svc._cache_publication = AsyncMock()
    active = peak = 0
    fetched = []

    async def fetch(pmid):
        nonlocal active, peak
        active += 1
        peak = max(active, peak)
        fetched.append(pmid)
        await asyncio.sleep(0.01)
        active -= 1
        return PMIDValidationResult(
            pmid=pmid, is_valid=False, error="Publication not found"
        )

    monkeypatch.setattr(svc, "fetch_publication", fetch)
    try:
        response = await svc.validate_pmids(["1", "2", "PMID:1", "3", "4", "5", "6"])
    finally:
        await svc.close()
    assert peak == service.LOOKUP_CONCURRENCY
    assert fetched.count("1") == 1
    assert [r.pmid for r in response.results] == ["1", "2", "1", "3", "4", "5", "6"]
    assert response.invalid_count == 7
    assert svc._get_cached_publication.await_count == 6
