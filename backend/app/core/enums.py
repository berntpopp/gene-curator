"""
Enums for scope-centric architecture.

This module provides centralized enum definitions for application-level and
scope-level roles, following DRY principles.

Created: 2025-10-13
Author: Claude Code (Automated Implementation)
"""

from enum import Enum


class ApplicationRole(str, Enum):
    """
    Application-level roles (simplified from original 5-role system).

    The scope-centric architecture simplifies application-level permissions to
    just two roles:
    - ADMIN: Full system access, can manage all scopes
    - USER: Normal user, access controlled by scope membership
    """

    ADMIN = "admin"
    USER = "user"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    @classmethod
    def from_string(cls, role: str) -> "ApplicationRole":
        """Create ApplicationRole from string (case-insensitive)."""
        role_upper = role.upper()
        try:
            return cls[role_upper]
        except KeyError as e:
            raise ValueError(
                f"Invalid application role: {role}. Must be one of: {', '.join([r.value for r in cls])}"
            ) from e


class ScopeRole(str, Enum):
    """
    Scope-level roles (detailed permissions within scopes).

    These roles define what users can do within a specific scope:
    - ADMIN: Manage scope settings, invite/remove members, full access
    - CURATOR: Create and edit curations, assign genes
    - REVIEWER: Review curations (4-eyes principle)
    - VIEWER: Read-only access to scope data
    """

    ADMIN = "admin"
    CURATOR = "curator"
    REVIEWER = "reviewer"
    VIEWER = "viewer"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    @classmethod
    def from_string(cls, role: str) -> "ScopeRole":
        """Create ScopeRole from string (case-insensitive)."""
        role_upper = role.upper()
        try:
            return cls[role_upper]
        except KeyError as e:
            raise ValueError(
                f"Invalid scope role: {role}. Must be one of: {', '.join([r.value for r in cls])}"
            ) from e

    @property
    def display_name(self) -> str:
        """Get user-friendly display name for the role."""
        return self.value.capitalize()

    @property
    def description(self) -> str:
        """Get detailed description of role permissions."""
        descriptions = {
            ScopeRole.ADMIN: "Full access: manage scope, invite members, curate, and review",
            ScopeRole.CURATOR: "Can create and edit curations, assign genes",
            ScopeRole.REVIEWER: "Can review curations (4-eyes principle)",
            ScopeRole.VIEWER: "Read-only access to scope data",
        }
        return descriptions[self]


# Type aliases for convenience
ApplicationRoleType = ApplicationRole
ScopeRoleType = ScopeRole
