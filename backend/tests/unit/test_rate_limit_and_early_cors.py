"""#478: early 400/414 carry CORS headers; rate limiting from config/api.yaml returns 429."""

import pytest
from fastapi.testclient import TestClient

from app.core.api_config import FeatureFlagsConfig, RateLimitConfig
from app.core.security import create_access_token, create_refresh_token
from app.main import app, cors_config

pytestmark = pytest.mark.unit

ORIGIN = cors_config.allow_origins[0]


@pytest.mark.parametrize(
    ("path", "code"),
    [("/api/v1/genes/symbol/AB%00C", 400), ("/api/v1/genes/" + "A" * 3000, 414)],
)
def test_early_rejects_carry_cors_headers(path: str, code: int) -> None:
    response = TestClient(app).get(path, headers={"Origin": ORIGIN})
    assert response.status_code == code
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "X-Request-ID" in response.headers["access-control-expose-headers"]


@pytest.fixture
def limited(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        "app.middleware.rate_limit.get_feature_flags",
        lambda: FeatureFlagsConfig(enable_rate_limiting=True),
    )
    tiers = {
        "default": RateLimitConfig(requests_per_minute=1, burst_size=2),
        "authenticated": RateLimitConfig(requests_per_minute=1, burst_size=3),
    }
    monkeypatch.setattr(
        "app.middleware.rate_limit.get_rate_limit", lambda tier: tiers[tier]
    )
    monkeypatch.setattr(app, "middleware_stack", None)  # rebuilt: fresh buckets
    return TestClient(app)


def test_anonymous_client_gets_429_after_burst(limited: TestClient) -> None:
    codes = [limited.get("/", headers={"Origin": ORIGIN}) for _ in range(3)]
    assert [r.status_code for r in codes] == [200, 200, 429]
    assert codes[-1].headers["retry-after"] == "60"
    assert codes[-1].headers["access-control-allow-origin"] == ORIGIN


def test_authenticated_user_has_own_bucket_and_tier(limited: TestClient) -> None:
    token = create_access_token({"sub": "u1", "role": "user"})
    headers = {"Authorization": f"Bearer {token}"}
    assert [limited.get("/", headers=headers).status_code for _ in range(4)] == [
        200,
        200,
        200,
        429,
    ]
    assert limited.get("/").status_code == 200  # anonymous bucket untouched


def test_invalid_token_falls_back_to_ip_bucket(limited: TestClient) -> None:
    headers = {"Authorization": "Bearer junk"}
    assert [limited.get("/", headers=headers).status_code for _ in range(3)] == [
        200,
        200,
        429,
    ]


def test_refresh_token_falls_back_to_ip_bucket(limited: TestClient) -> None:
    token = create_refresh_token({"sub": "u1", "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}
    assert [limited.get("/", headers=headers).status_code for _ in range(3)] == [
        200,
        200,
        429,
    ]


def test_rate_limiting_is_off_by_default() -> None:
    client = TestClient(app)
    assert all(client.get("/").status_code == 200 for _ in range(15))


def test_prod_env_override_turns_rate_limiting_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """docker-compose.prod.yml sets this key; it must reach features.enable_rate_limiting."""
    from app.core.api_config import get_feature_flags, load_api_config

    monkeypatch.setenv("GENE_CURATOR_API__FEATURES__ENABLE_RATE_LIMITING", "true")
    load_api_config.cache_clear()
    try:
        assert get_feature_flags().enable_rate_limiting is True
    finally:
        monkeypatch.delenv("GENE_CURATOR_API__FEATURES__ENABLE_RATE_LIMITING")
        load_api_config.cache_clear()
    assert get_feature_flags().enable_rate_limiting is False
