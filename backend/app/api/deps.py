"""
Dependency injection for API endpoints.
Provides common dependencies like database sessions and user authentication.
"""

from collections.abc import Generator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


# Mock implementations for testing - would use real implementations in production
class DatabaseDependency:
    """Mock database dependency."""

    def __call__(self) -> Generator:
        # In real implementation, this would create and yield a database session
        yield None


class UserDependency:
    """Mock user dependency."""

    def __init__(self, role: str = "admin"):
        self.role = role
        self.id = "user-123"
        self.assigned_scopes = []


# Create dependency instances
get_db = DatabaseDependency()


def get_current_user() -> UserDependency:
    """Get current authenticated user."""
    return UserDependency()


def get_current_active_user() -> UserDependency:
    """Get current active user."""
    return UserDependency()


# Security scheme
security = HTTPBearer(auto_error=False)


def get_current_user_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str | None:
    """Extract token from authorization header."""
    if credentials:
        return credentials.credentials
    return None
