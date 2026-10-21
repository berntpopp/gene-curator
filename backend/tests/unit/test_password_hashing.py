"""Password hashing without passlib keeps existing hashes verifiable (#334)."""

import sys

import pytest

from app.core.security import get_password_hash, verify_password

pytestmark = pytest.mark.unit

# admin123, as seeded in database/sql/004_seed_data.sql (created by passlib)
SEEDED_HASH = "$2b$12$bs7kTc5txFs0.0F3AtguTuzOTQ6fWItSmWPQmWgI7GMyhiscyNZd6"


def test_passlib_is_not_imported() -> None:
    assert "passlib" not in sys.modules


def test_seeded_hash_still_verifies() -> None:
    assert verify_password("admin123", SEEDED_HASH)
    assert not verify_password("wrong", SEEDED_HASH)


def test_round_trip_and_unique_salts() -> None:
    first, second = get_password_hash("s3cret!"), get_password_hash("s3cret!")
    assert first != second
    assert verify_password("s3cret!", first)


def test_passwords_over_72_bytes_do_not_raise() -> None:
    long = "x" * 100
    assert verify_password(long, get_password_hash(long))
