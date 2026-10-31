"""SQLite-lane tests never reach a real database through the async engine.

`make` exports DATABASE_URL from .env.dev (the live dev database), so async endpoints
(logs, search) used to hit it, and asyncpg pooled a connection on one TestClient's event
loop that the next client (the MCP call in test_mcp) reused after that loop closed: a 500
on one path only. Tests now get a NullPool engine at an address nothing listens on."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import NullPool

from app.core import database, deps
from app.core.database import async_database_url
from app.core.logging.database_logger import get_database_logger
from app.main import app

pytestmark = pytest.mark.unit


def test_the_async_session_is_not_the_configured_database() -> None:
    bind = deps.AsyncSessionLocal.kw["bind"]
    assert bind.url.render_as_string(hide_password=False) != async_database_url
    assert isinstance(bind.pool, NullPool)  # nothing outlives a TestClient's loop
    # the database log handler and a re-initialised logger use the same safe factory
    assert get_database_logger().session_factory is deps.AsyncSessionLocal
    assert database.AsyncSessionLocal is deps.AsyncSessionLocal


def test_async_endpoint_answers_alike_from_two_clients(
    client: TestClient, admin_token: str
) -> None:
    # `client` overrides get_db with the SQLite session (else auth reads DATABASE_URL)
    headers = {"Authorization": f"Bearer {admin_token}"}
    codes = []
    for _ in range(2):  # each client has its own event loop, like the MCP call
        with TestClient(app, raise_server_exceptions=False) as c:
            codes.append(c.get("/api/v1/logs/", headers=headers).status_code)
    assert codes[0] == codes[1]
    assert 500 not in codes, codes
