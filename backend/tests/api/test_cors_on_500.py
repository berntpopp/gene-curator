"""500 responses must carry CORS headers for allowed origins only (#237)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app, cors_config

pytestmark = pytest.mark.unit


@pytest.fixture
def boom_client():
    @app.get("/__boom")
    def boom() -> None:
        raise RuntimeError("boom")

    yield TestClient(app, raise_server_exceptions=False)
    app.router.routes[:] = [
        r for r in app.router.routes if getattr(r, "path", "") != "/__boom"
    ]


def test_500_has_cors_for_allowed_origin(boom_client):
    origin = cors_config.allow_origins[0]
    response = boom_client.get("/__boom", headers={"Origin": origin})
    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == origin
    assert "Origin" in response.headers["vary"]


def test_500_has_no_cors_for_unknown_origin(boom_client):
    response = boom_client.get("/__boom", headers={"Origin": "https://evil.example"})
    assert response.status_code == 500
    assert "access-control-allow-origin" not in response.headers


def test_500_exposes_configured_headers(boom_client):
    origin = cors_config.allow_origins[0]
    response = boom_client.get("/__boom", headers={"Origin": origin})
    assert cors_config.expose_headers  # config must list the correlation header
    assert response.headers["access-control-expose-headers"] == ", ".join(
        cors_config.expose_headers
    )


def test_lifespan_runs_startup_and_shutdown(monkeypatch):
    messages: list[str] = []
    monkeypatch.setattr(
        "app.main.logger",
        type("L", (), {"info": lambda _s, m, **_k: messages.append(m)})(),
    )
    with TestClient(app):
        assert messages == ["Starting Gene Curator API..."]
    assert messages[-1] == "Shutting down Gene Curator API..."
