"""Free-text search parameters: wildcards are literal, NUL and long input give 422 (#367)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_async_db
from app.crud import logs as crud_logs
from app.main import app
from tests.api.scopes.factories import auth_headers, make_member, make_scope, make_user

pytestmark = pytest.mark.unit


def _escaped(stmt) -> bool:
    compiled = stmt.compile()
    return "ESCAPE" in str(compiled) and any(
        v == "%\\%%" for v in compiled.params.values()
    )


BAD = ["a\x00b", "x" * 101]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("path", ["/api/v1/genes/search", "/api/v1/genes/search/count"])
def test_gene_search_params(client: TestClient, curator_token: str, test_gene, path):
    for bad in BAD:
        r = client.get(path, params={"query": bad}, headers=_h(curator_token))
        assert r.status_code == 422, (path, bad)


def test_gene_search_escapes_wildcards():
    from app.crud.gene import gene_crud
    from app.schemas.gene import GeneSearchQuery

    stmt = gene_crud._search_stmt(GeneSearchQuery(query="%"))
    assert _escaped(stmt)


def test_user_search_params(client: TestClient, admin_token: str):
    for bad in BAD:
        r = client.get(
            "/api/v1/users/search", params={"q": bad}, headers=_h(admin_token)
        )
        assert r.status_code == 422
    r = client.get("/api/v1/users/search", params={"q": "%"}, headers=_h(admin_token))
    assert r.status_code == 200 and r.json() == []


def test_scope_invitation_search_params(client: TestClient, db_session: Session):
    scope, admin = make_scope(db_session), make_user(db_session)
    make_member(db_session, scope, admin, "admin")
    url = f"/api/v1/scopes/{scope.id}/users/search"
    for bad in BAD:
        r = client.get(url, params={"q": bad}, headers=auth_headers(admin))
        assert r.status_code == 422
    r = client.get(url, params={"q": "%"}, headers=auth_headers(admin))
    assert r.status_code == 200 and r.json() == []


@pytest.fixture
def fake_db():
    session = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    app.dependency_overrides[get_async_db] = lambda: session
    yield session
    app.dependency_overrides.pop(get_async_db, None)


def test_publication_search_params(client: TestClient, curator_token: str, fake_db):
    for bad in BAD:
        r = client.get(
            "/api/v1/publications", params={"search": bad}, headers=_h(curator_token)
        )
        assert r.status_code == 422
    r = client.get(
        "/api/v1/publications", params={"search": "%"}, headers=_h(curator_token)
    )
    assert r.status_code == 200
    assert _escaped(fake_db.execute.call_args.args[0])


@pytest.mark.parametrize("param", ["logger_name", "message", "endpoint"])
def test_log_search_params(client: TestClient, admin_token: str, param, monkeypatch):
    for bad in BAD:
        r = client.get("/api/v1/logs/", params={param: bad}, headers=_h(admin_token))
        assert r.status_code == 422, (param, bad)


@pytest.mark.parametrize("param", ["logger_name", "message", "endpoint"])
@pytest.mark.asyncio
async def test_log_crud_escapes_wildcards(param):
    session = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    await crud_logs.get_logs(session, **{param: "%"})
    assert _escaped(session.execute.call_args.args[0])
