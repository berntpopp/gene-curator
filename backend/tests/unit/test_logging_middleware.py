"""LoggingMiddleware: path guard (#378) and request-id reuse (#373)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.unit

client = TestClient(app, raise_server_exceptions=False)


def test_nul_byte_in_path_is_rejected_with_400() -> None:
    response = client.get("/api/v1/genes/symbol/AB%00C")
    assert response.status_code == 400
    assert response.headers["x-request-id"]


def test_overlong_path_is_rejected_with_414() -> None:
    response = client.get("/api/v1/genes/symbol/" + "A" * 3000)
    assert response.status_code == 414


def test_client_request_id_is_reused() -> None:
    response = client.get("/", headers={"X-Request-ID": "abc-123_x.y"})
    assert response.headers["x-request-id"] == "abc-123_x.y"


@pytest.mark.parametrize("bad", ["", "a b", "x" * 129, "evil\nline"])
def test_unsafe_client_request_id_is_replaced(bad: str) -> None:
    response = client.get("/", headers={"X-Request-ID": bad})
    assert response.headers["x-request-id"] != bad


def test_error_response_echoes_client_request_id() -> None:
    @app.get("/__w6d_boom")
    def boom() -> None:
        raise RuntimeError("boom")

    try:
        response = client.get("/__w6d_boom", headers={"X-Request-ID": "rid-500"})
    finally:
        app.router.routes[:] = [
            r for r in app.router.routes if getattr(r, "path", "") != "/__w6d_boom"
        ]
    assert response.status_code == 500
    assert response.headers["x-request-id"] == "rid-500"
    assert response.json()["request_id"] == "rid-500"
