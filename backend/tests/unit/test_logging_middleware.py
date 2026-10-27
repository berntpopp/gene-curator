"""LoggingMiddleware: path guard (#378)."""

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
