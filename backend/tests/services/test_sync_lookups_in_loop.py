"""Sync lookup helpers work from inside a running event loop. External APIs are mocked."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.orm import Session

from app.core.async_bridge import run_blocking
from app.schemas.gene import GeneCreate
from app.schemas.validation import HGNCGeneSearchResult, PMIDValidationResult
from app.services import gene_verification, ontology_service, publication_service
from app.services.ontology_service import OntologyService
from app.services.publication_service import PublicationService
from app.services.validators import HGNCValidator

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def upstream(monkeypatch: pytest.MonkeyPatch) -> None:
    async def term_found(_: OntologyService, curie: str) -> bool | None:
        return curie == "HP:0000001"

    async def fetch_publication(
        _: PublicationService, pmid: str
    ) -> PMIDValidationResult:
        return PMIDValidationResult(
            pmid=pmid, is_valid=False, error=f"Publication not found: {pmid}"
        )

    async def fetch_gene(_: HGNCValidator, hgnc_id: str) -> HGNCGeneSearchResult:
        return HGNCGeneSearchResult(hgnc_id=hgnc_id, symbol="PKD1")

    monkeypatch.setattr(OntologyService, "term_found", term_found)
    monkeypatch.setattr(PublicationService, "fetch_publication", fetch_publication)
    monkeypatch.setattr(HGNCValidator, "fetch_gene_by_id", fetch_gene)
    monkeypatch.setattr(HGNCValidator, "close", AsyncMock())
    monkeypatch.setattr(ontology_service, "_known_terms", set())


@pytest.mark.asyncio
async def test_lookup_terms_inside_running_loop() -> None:
    assert ontology_service.lookup_terms({"HP:0000001", "HP:0000002"}) == (
        ["HP:0000002"],
        [],
    )


@pytest.mark.asyncio
async def test_lookup_pmids_inside_running_loop(db_session: Session) -> None:
    assert publication_service.lookup_pmids(db_session, {"424242"}) == (["424242"], [])


@pytest.mark.asyncio
async def test_verify_genes_inside_running_loop(db_session: Session) -> None:
    rows = [GeneCreate(hgnc_id="HGNC:9008", approved_symbol="x")]
    got = gene_verification.verify_genes(db_session, rows)
    assert got["HGNC:9008"] is not None
    assert got["HGNC:9008"].approved_symbol == "PKD1"


def test_lookup_errors_propagate_without_retry() -> None:
    calls: list[int] = []

    async def boom() -> None:
        calls.append(1)
        raise RuntimeError("upstream")

    with pytest.raises(RuntimeError, match="upstream"):
        run_blocking(boom())
    assert calls == [1]
