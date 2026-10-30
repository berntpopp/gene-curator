"""add_genes_to_scope works when called from inside a running event loop. HGNC is mocked."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.orm import Session

from app.api.v1.endpoints.scopes import add_genes_to_scope
from app.models import Scope, UserNew
from app.schemas.gene_assignment import ScopeGenesAdd
from app.schemas.validation import HGNCGeneSearchResult, HGNCSearchResponse
from app.services.validators import HGNCValidator

pytestmark = pytest.mark.unit

PKD1 = HGNCGeneSearchResult(hgnc_id="HGNC:9008", symbol="PKD1")


@pytest.mark.asyncio
async def test_add_genes_inside_running_loop(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    curator: UserNew,
    scope_with_admin: Scope,
) -> None:
    async def search(_: HGNCValidator, q: str, limit: int = 10) -> HGNCSearchResponse:
        return HGNCSearchResponse(query=q, total_results=1, results=[PKD1])

    async def fetch(_: HGNCValidator, hgnc_id: str) -> HGNCGeneSearchResult:
        return PKD1

    monkeypatch.setattr(HGNCValidator, "search", search)
    monkeypatch.setattr(HGNCValidator, "fetch_gene_by_id", fetch)
    monkeypatch.setattr(HGNCValidator, "close", AsyncMock())
    body = ScopeGenesAdd(scope_id=scope_with_admin.id, symbols=["PKD1"])
    out = add_genes_to_scope(db=db_session, body=body, current_user=curator)
    assert out.added == 1
