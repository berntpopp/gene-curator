"""API tests for /logs endpoints.

The async session dependency is replaced with a mock and the CRUD functions are
patched, since aiosqlite is not installed and the log queries are PostgreSQL SQL.
What is verified here: admin-only access, routing, response mapping and export
formats. A regression test pins the session dependency to the async one.
"""

from collections.abc import Generator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.api.v1.endpoints import logs as logs_endpoints
from app.core.database import get_async_db, get_db
from app.crud import logs as crud_logs
from app.main import app

pytestmark = pytest.mark.unit

BASE = "/api/v1/logs"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _log(
    log_id: int = 1, message: str = "boom", level: str = "ERROR"
) -> SimpleNamespace:
    return SimpleNamespace(
        id=log_id,
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        level=level,
        logger_name="app.test",
        message=message,
        request_id="req-1",
        user_id=None,
        scope_id=None,
        duration_ms=12.5,
        context={"path": "/x"},
    )


@pytest.fixture(autouse=True)
def fake_async_session() -> Generator[MagicMock, None, None]:
    session = MagicMock()
    session.execute = AsyncMock()
    app.dependency_overrides[get_async_db] = lambda: session
    yield session
    app.dependency_overrides.pop(get_async_db, None)


def test_regression_logs_use_async_session_dependency() -> None:
    # The CRUD layer is async; the routes must not depend on the sync get_db.
    for route in logs_endpoints.router.routes:
        assert isinstance(route, APIRoute)
        assert get_db not in [d.call for d in route.dependant.dependencies], route.path


def test_logs_require_authentication(client: TestClient) -> None:
    assert client.get(f"{BASE}/").status_code in (401, 403)


def test_non_admin_is_forbidden(client: TestClient, curator_token: str) -> None:
    assert client.get(f"{BASE}/", headers=_auth(curator_token)).status_code == 403
    assert (
        client.get(f"{BASE}/stats/summary", headers=_auth(curator_token)).status_code
        == 403
    )
    assert (
        client.delete(f"{BASE}/cleanup", headers=_auth(curator_token)).status_code
        == 403
    )


def test_search_logs_maps_crud_rows(
    client: TestClient, admin_token: str, monkeypatch: MonkeyPatch
) -> None:
    get_logs = AsyncMock(return_value=[_log(1), _log(2, "later", "WARNING")])
    monkeypatch.setattr(crud_logs, "get_logs", get_logs)

    response = client.get(f"{BASE}/?limit=2&level=ERROR", headers=_auth(admin_token))

    assert response.status_code == 200
    body = response.json()
    assert [row["id"] for row in body] == [1, 2]
    assert body[0]["logger_name"] == "app.test"
    assert get_logs.await_args is not None
    assert get_logs.await_args.kwargs["level"] == "ERROR"


def test_get_log_by_id_found_and_missing(
    client: TestClient, admin_token: str, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(crud_logs, "get_log_by_id", AsyncMock(return_value=_log(7)))
    found = client.get(f"{BASE}/7", headers=_auth(admin_token))
    assert found.status_code == 200
    assert found.json()["id"] == 7

    monkeypatch.setattr(crud_logs, "get_log_by_id", AsyncMock(return_value=None))
    missing = client.get(f"{BASE}/99", headers=_auth(admin_token))
    assert missing.status_code == 404
    assert "99" in missing.json()["detail"]


def test_logs_by_request_id(
    client: TestClient, admin_token: str, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        crud_logs, "get_logs_by_request_id", AsyncMock(return_value=[_log(3)])
    )
    found = client.get(f"{BASE}/request/req-1", headers=_auth(admin_token))
    assert found.status_code == 200
    assert found.json()[0]["request_id"] == "req-1"

    monkeypatch.setattr(crud_logs, "get_logs_by_request_id", AsyncMock(return_value=[]))
    missing = client.get(f"{BASE}/request/nope", headers=_auth(admin_token))
    assert missing.status_code == 404


def test_log_statistics_summary(
    client: TestClient, admin_token: str, monkeypatch: MonkeyPatch
) -> None:
    stats: dict[str, Any] = {
        "total_logs": 10,
        "logs_by_level": {"ERROR": 2, "INFO": 8},
        "logs_by_hour": {"2026-01-01T12:00:00": 10},
        "avg_duration_ms": 4.2,
        "slow_endpoints": [],
        "error_rate": 0.2,
        "top_errors": [],
    }
    monkeypatch.setattr(crud_logs, "get_log_statistics", AsyncMock(return_value=stats))

    response = client.get(f"{BASE}/stats/summary", headers=_auth(admin_token))

    assert response.status_code == 200
    assert response.json()["total_logs"] == 10
    assert response.json()["error_rate"] == 0.2


def test_recent_errors(
    client: TestClient, admin_token: str, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        crud_logs, "get_recent_errors", AsyncMock(return_value=[_log(4)])
    )

    response = client.get(f"{BASE}/recent-errors", headers=_auth(admin_token))

    assert response.status_code == 200
    assert response.json()[0]["id"] == 4


def _model_row(message: str) -> SimpleNamespace:
    """Row shaped like the SystemLog model (export reads model attribute names)."""
    return SimpleNamespace(
        id=5,
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        level="ERROR",
        logger="app.test",
        message=message,
        request_id="req-5",
        user_id=None,
        ip_address="127.0.0.1",
        user_agent="pytest",
        path="/api/v1/x",
        method="GET",
        status_code=500,
        duration_ms=3.0,
        context={},
        error_type=None,
        error_message=None,
        stack_trace=None,
    )


def test_export_json_and_csv(
    client: TestClient, admin_token: str, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        crud_logs,
        "get_logs_for_export",
        AsyncMock(return_value=[_model_row("exported")]),
    )

    as_json = client.get(f"{BASE}/export?format=json", headers=_auth(admin_token))
    assert as_json.status_code == 200
    assert "exported" in as_json.text

    as_csv = client.get(f"{BASE}/export?format=csv", headers=_auth(admin_token))
    assert as_csv.status_code == 200
    assert as_csv.headers["content-type"].startswith("text/csv")
    assert "exported" in as_csv.text


def test_export_rejects_unknown_format(client: TestClient, admin_token: str) -> None:
    response = client.get(f"{BASE}/export?format=xml", headers=_auth(admin_token))
    assert response.status_code == 400


def test_cleanup_reports_result(
    client: TestClient, admin_token: str, monkeypatch: MonkeyPatch
) -> None:
    cleanup = AsyncMock(return_value={"deleted": 3})
    monkeypatch.setattr(crud_logs, "cleanup_old_partitions", cleanup)

    response = client.delete(f"{BASE}/cleanup?days=30", headers=_auth(admin_token))

    assert response.status_code == 200
    assert response.json()["deleted"] == 3
    assert cleanup.await_args is not None
    assert cleanup.await_args.kwargs["days"] == 30


def test_search_logs_accepts_real_model_rows(
    client: TestClient, admin_token: str, monkeypatch: MonkeyPatch
) -> None:
    # SystemLog rows have `logger`/`path` and a UUID user_id, not `logger_name`/`endpoint`.
    from uuid import uuid4

    row = _model_row("real")
    row.user_id = uuid4()
    monkeypatch.setattr(crud_logs, "get_logs", AsyncMock(return_value=[row]))

    response = client.get(f"{BASE}/", headers=_auth(admin_token))

    assert response.status_code == 200, response.text
    body = response.json()[0]
    assert body["logger_name"] == "app.test"
    assert body["endpoint"] == "/api/v1/x"
    assert body["user_id"] == str(row.user_id)
