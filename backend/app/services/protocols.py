"""Protocol interfaces for services.

Enables dependency injection and easier mocking in tests.
Following SOLID principles - Dependency Inversion Principle.

Reference: https://realpython.com/solid-principles-python/
"""

from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import UserNew


class IScopePermissionService(Protocol):
    """Protocol for scope permission checking.

    Implement this interface to create alternative permission services
    (e.g., for testing, caching, or external authorization providers).
    """

    def has_scope_access(
        self,
        db: Session,
        user: UserNew,
        scope_id: UUID,
        required_roles: list[str] | None = None,
    ) -> bool:
        """Check if user has access to scope."""
        ...

    def get_user_scope_ids(
        self,
        db: Session,
        user: UserNew,
        required_roles: list[str] | None = None,
    ) -> list[UUID]:
        """Get list of scope IDs user can access."""
        ...

    def get_user_scope_role(
        self,
        db: Session,
        user_id: UUID,
        scope_id: UUID,
    ) -> str | None:
        """Get user's role in a specific scope."""
        ...
