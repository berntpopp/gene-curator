"""
Pydantic schemas for scope memberships (multi-tenant user-scope relationships).

This module defines schemas for the core multi-tenancy system. Scope memberships
represent user participation in scopes with specific roles (admin, curator, reviewer, viewer).

Created: 2025-10-13
Author: Claude Code (Automated Implementation)
"""

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.enums import ScopeRole


# Email validation regex (for cases where EmailStr isn't sufficient)
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class ScopeMembershipBase(BaseModel):
    """
    Base schema for scope membership.

    Contains fields common to all membership operations.
    """

    role: ScopeRole = Field(
        ...,
        description="User's role within the scope (admin, curator, reviewer, viewer)",
    )
    notes: Optional[str] = Field(
        None,
        description="Optional notes about this membership (e.g., specialty, responsibilities)",
        max_length=500,
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "role": "curator",
                "notes": "Specializes in kidney disease genes",
            }
        }
    }


class ScopeMembershipCreate(ScopeMembershipBase):
    """
    Schema for creating a scope membership invitation.

    Supports two invitation methods:
    1. Direct user invitation: Provide user_id (for existing users)
    2. Email invitation: Provide email (for external invitations - future feature)

    At least one of user_id or email must be provided.
    """

    user_id: Optional[UUID] = Field(
        None,
        description="UUID of existing user to invite (direct invitation)",
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Email address for external invitation (future feature)",
    )
    team_id: Optional[UUID] = Field(
        None,
        description="Optional team ID for group-based memberships (future feature)",
    )

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format using regex (additional validation)."""
        if v is not None and not EMAIL_REGEX.match(v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("role")
    @classmethod
    def validate_role_for_invitation(cls, v: ScopeRole) -> ScopeRole:
        """
        Validate that invited role is appropriate.

        Note: Scope admin role assignment may require additional checks
        at the service layer to prevent privilege escalation.
        """
        if v not in [ScopeRole.ADMIN, ScopeRole.CURATOR, ScopeRole.REVIEWER, ScopeRole.VIEWER]:
            raise ValueError(f"Invalid role for invitation: {v}")
        return v

    def model_post_init(self, __context) -> None:
        """Validate that at least one of user_id or email is provided."""
        if self.user_id is None and self.email is None:
            raise ValueError("Either user_id or email must be provided")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "role": "curator",
                    "notes": "Expert in kidney disease genes",
                },
                {
                    "email": "researcher@university.edu",
                    "role": "reviewer",
                    "notes": "External reviewer for cardiology cases",
                },
            ]
        }
    }


class ScopeMembershipUpdate(BaseModel):
    """
    Schema for updating an existing scope membership.

    Allows updating role, active status, and notes.
    Team ID and invitation fields cannot be updated.
    """

    role: Optional[ScopeRole] = Field(
        None,
        description="New role for the user in this scope",
    )
    is_active: Optional[bool] = Field(
        None,
        description="Whether membership is active (false = suspended)",
    )
    notes: Optional[str] = Field(
        None,
        description="Updated notes about this membership",
        max_length=500,
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "role": "admin",
                    "notes": "Promoted to scope admin after 6 months",
                },
                {
                    "is_active": False,
                    "notes": "Temporarily suspended due to leave of absence",
                },
            ]
        }
    }


class ScopeMembershipResponse(ScopeMembershipBase):
    """
    Schema for scope membership response (includes user details).

    This schema is used when returning membership information to clients.
    It includes user details joined from the users_new table.
    """

    id: UUID = Field(..., description="Unique membership ID")
    scope_id: UUID = Field(..., description="Scope UUID")
    user_id: UUID = Field(..., description="User UUID")
    invited_by: Optional[UUID] = Field(None, description="UUID of user who sent invitation")
    invited_at: datetime = Field(..., description="When invitation was sent")
    accepted_at: Optional[datetime] = Field(None, description="When invitation was accepted (NULL = pending)")
    is_active: bool = Field(..., description="Whether membership is active")
    team_id: Optional[UUID] = Field(None, description="Optional team ID")

    # User details (joined from users_new table)
    user_username: Optional[str] = Field(None, description="User's username")
    user_email: Optional[str] = Field(None, description="User's email")
    user_full_name: Optional[str] = Field(None, description="User's full name")
    user_orcid: Optional[str] = Field(None, description="User's ORCID")

    # Computed fields
    is_pending: bool = Field(..., description="Whether invitation is pending acceptance")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "scope_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "660e8400-e29b-41d4-a716-446655440000",
                "role": "curator",
                "invited_by": "770e8400-e29b-41d4-a716-446655440000",
                "invited_at": "2025-10-01T10:00:00Z",
                "accepted_at": "2025-10-01T11:30:00Z",
                "is_active": True,
                "is_pending": False,
                "notes": "Specializes in kidney disease genes",
                "user_username": "dr_smith",
                "user_email": "smith@hospital.org",
                "user_full_name": "Dr. John Smith",
                "user_orcid": "0000-0002-1825-0097",
            }
        },
    }


class ScopeMemberListResponse(BaseModel):
    """
    Schema for listing scope members (paginated response).

    Contains list of members with metadata about the query.
    """

    scope_id: UUID = Field(..., description="Scope UUID")
    total: int = Field(..., description="Total number of members in scope", ge=0)
    members: list[ScopeMembershipResponse] = Field(
        ...,
        description="List of scope members with user details",
    )

    # Statistics (useful for UI)
    active_count: int = Field(..., description="Number of active members", ge=0)
    pending_count: int = Field(..., description="Number of pending invitations", ge=0)
    role_counts: dict[str, int] = Field(
        ...,
        description="Count of members by role (admin, curator, reviewer, viewer)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "scope_id": "550e8400-e29b-41d4-a716-446655440000",
                "total": 15,
                "active_count": 12,
                "pending_count": 3,
                "role_counts": {
                    "admin": 2,
                    "curator": 6,
                    "reviewer": 4,
                    "viewer": 3,
                },
                "members": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "scope_id": "550e8400-e29b-41d4-a716-446655440000",
                        "user_id": "660e8400-e29b-41d4-a716-446655440000",
                        "role": "curator",
                        "invited_at": "2025-10-01T10:00:00Z",
                        "accepted_at": "2025-10-01T11:30:00Z",
                        "is_active": True,
                        "is_pending": False,
                        "user_username": "dr_smith",
                        "user_email": "smith@hospital.org",
                    }
                ],
            }
        }
    }


class ScopeMembershipAccept(BaseModel):
    """
    Schema for accepting a scope membership invitation.

    Simple confirmation schema - no additional data needed beyond authentication.
    """

    notes: Optional[str] = Field(
        None,
        description="Optional message when accepting invitation",
        max_length=200,
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "notes": "Excited to join the kidney genetics team!",
            }
        }
    }
