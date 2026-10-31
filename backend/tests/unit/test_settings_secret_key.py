"""Production refuses a weak or placeholder SECRET_KEY (JWT signing key)."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

BASE = {
    "DATABASE_URL": "postgresql://u:p@h/x",
    "GENE_CURATOR_PUBLIC_URL": "https://gene-curator.org",
}


@pytest.mark.parametrize(
    "key",
    [
        "short",
        "change_me_in_production",
        "dev_secret_key_change_in_production",
        "CHANGE_ME_IN_PRODUCTION_GENERATE_STRONG_SECRET",
    ],
)
def test_production_rejects_weak_or_default_secret_key(key: str) -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY must be at least 32"):
        Settings(**BASE, ENVIRONMENT="production", SECRET_KEY=key)


def test_production_accepts_a_strong_key_and_development_any_key() -> None:
    strong = "Zq3v9XkT1bWm7RpL0sYc5HnJ8eUa2GdF4iOx6KwQ"
    assert Settings(**BASE, ENVIRONMENT="production", SECRET_KEY=strong).SECRET_KEY
    assert Settings(**BASE, ENVIRONMENT="development", SECRET_KEY="dev").SECRET_KEY
