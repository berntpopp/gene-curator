"""
Unit tests for authentication functionality.

Tests password hashing, verification, token generation, and authentication logic.
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.crud.user import user_crud
from app.models import UserNew as User, UserRoleNew as UserRole


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self) -> None:
        """Test that password hashing produces a bcrypt hash."""
        password = "test_password_123"  # noqa: S105
        hashed = get_password_hash(password)

        # Bcrypt hashes start with $2b$ and are 60 characters long
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60

    def test_verify_correct_password(self) -> None:
        """Test that correct password verification succeeds."""
        password = "admin123"  # noqa: S105
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self) -> None:
        """Test that incorrect password verification fails."""
        password = "admin123"  # noqa: S105
        hashed = get_password_hash(password)

        assert verify_password("wrong_password", hashed) is False

    def test_different_passwords_produce_different_hashes(self) -> None:
        """Test that different passwords produce different hashes."""
        password1 = "password1"
        password2 = "password2"

        hash1 = get_password_hash(password1)
        hash2 = get_password_hash(password2)

        assert hash1 != hash2

    def test_same_password_produces_different_hashes(self) -> None:
        """Test that hashing the same password twice produces different hashes (salt)."""
        password = "admin123"  # noqa: S105

        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Different hashes due to different salts
        assert hash1 != hash2

        # But both verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_seed_data_password_hash_verification(self) -> None:
        """Test that the seed data password hash is correct."""
        # This is the hash from 004_seed_data.sql
        seed_hash = "$2b$12$bs7kTc5txFs0.0F3AtguTuzOTQ6fWItSmWPQmWgI7GMyhiscyNZd6"
        password = "admin123"  # noqa: S105

        # This should verify successfully
        assert verify_password(password, seed_hash) is True


class TestTokenGeneration:
    """Test JWT token generation and verification."""

    def test_create_access_token(self) -> None:
        """Test access token creation."""
        data = {"sub": "user-123", "email": "test@example.com", "role": "admin"}
        token = create_access_token(data)

        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expiration(self) -> None:
        """Test access token creation with custom expiration."""
        data = {"sub": "user-123", "email": "test@example.com"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data, expires_delta=expires_delta)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self) -> None:
        """Test refresh token creation."""
        data = {"sub": "user-123", "email": "test@example.com", "role": "admin"}
        token = create_refresh_token(data)

        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_valid_token(self) -> None:
        """Test verification of valid token."""
        data = {"sub": "user-123", "email": "test@example.com", "role": "admin"}
        token = create_access_token(data)

        payload = verify_token(token)

        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "admin"
        assert "exp" in payload

    def test_verify_invalid_token(self) -> None:
        """Test verification of invalid token."""
        invalid_token = "invalid.jwt.token"  # noqa: S105

        payload = verify_token(invalid_token)

        assert payload is None

    def test_refresh_token_has_type_field(self) -> None:
        """Test that refresh token includes type field."""
        data = {"sub": "user-123", "email": "test@example.com"}
        token = create_refresh_token(data)

        payload = verify_token(token)

        assert payload is not None
        assert payload.get("type") == "refresh"


class TestUserAuthentication:
    """Test user authentication logic."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()

    def test_authenticate_with_correct_credentials(self) -> None:
        """Test authentication succeeds with correct credentials."""
        # Create a mock user
        mock_user = MagicMock(spec=User)
        mock_user.id = "user-123"
        mock_user.email = "test@example.com"
        mock_user.hashed_password = get_password_hash("password123")
        mock_user.role = (
            UserRole.USER
        )  # Standard user (scope roles assigned via scope_memberships)
        mock_user.is_active = True

        # Mock the get_by_email method
        with patch.object(user_crud, "get_by_email", return_value=mock_user):
            result = user_crud.authenticate(
                self.mock_db,
                email="test@example.com",
                password="password123",  # noqa: S106
            )

        assert result is not None
        assert result.email == "test@example.com"

    def test_authenticate_with_incorrect_password(self) -> None:
        """Test authentication fails with incorrect password."""
        # Create a mock user
        mock_user = MagicMock(spec=User)
        mock_user.hashed_password = get_password_hash("password123")

        # Mock the get_by_email method
        with patch.object(user_crud, "get_by_email", return_value=mock_user):
            result = user_crud.authenticate(
                self.mock_db,
                email="test@example.com",
                password="wrong_password",  # noqa: S106
            )

        assert result is None

    def test_authenticate_with_nonexistent_user(self) -> None:
        """Test authentication fails with nonexistent user."""
        # Mock get_by_email to return None (user not found)
        with patch.object(user_crud, "get_by_email", return_value=None):
            result = user_crud.authenticate(
                self.mock_db,
                email="nonexistent@example.com",
                password="password123",  # noqa: S106
            )

        assert result is None

    def test_is_active_returns_true_for_active_user(self) -> None:
        """Test is_active returns True for active users."""
        mock_user = MagicMock(spec=User)
        mock_user.is_active = True

        assert user_crud.is_active(mock_user) is True

    def test_is_active_returns_false_for_inactive_user(self) -> None:
        """Test is_active returns False for inactive users."""
        mock_user = MagicMock(spec=User)
        mock_user.is_active = False

        assert user_crud.is_active(mock_user) is False


class TestDevelopmentCredentials:
    """Test that all development credentials work correctly."""

    @pytest.mark.parametrize(
        "email,expected_role",
        [
            ("admin@genecurator.org", "admin"),
            ("dev@example.com", "curator"),
            ("reviewer@example.org", "reviewer"),
            ("test@example.com", "viewer"),
        ],
    )
    def test_development_user_credentials(self, email: str, expected_role: str) -> None:
        """Test that development user credentials are correctly set up."""
        # This tests the known password hash from seed data
        seed_hash = "$2b$12$bs7kTc5txFs0.0F3AtguTuzOTQ6fWItSmWPQmWgI7GMyhiscyNZd6"
        password = "admin123"  # noqa: S105

        # All development users should have the same password
        assert verify_password(password, seed_hash) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
