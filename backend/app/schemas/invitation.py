"""
Pydantic schemas for user-facing invitation endpoints.

These schemas are used for the /me/invitations and related endpoints
that allow users to view and respond to their pending scope invitations.

Created: 2025-01-13
Author: Claude Code (Automated Implementation)
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import ScopeRole


class PendingInvitationResponse(BaseModel):
    """
    Schema for a pending invitation response.

    Contains all information needed to display an invitation to the user,
    including scope details, inviter information, and expiration status.
    """

    id: UUID = Field(..., description="Invitation/membership UUID")
    scope_id: UUID = Field(..., description="Scope UUID")
    scope_name: str = Field(..., description="Scope machine name")
    scope_display_name: str | None = Field(
        None, description="Scope human-readable name"
    )
    role: ScopeRole = Field(..., description="Role being offered")
    invited_by: UUID | None = Field(
        None, description="UUID of user who sent invitation"
    )
    inviter_name: str | None = Field(None, description="Name of inviter")
    inviter_email: str | None = Field(None, description="Email of inviter")
    invited_at: datetime = Field(..., description="When invitation was sent")
    expires_at: datetime | None = Field(None, description="When invitation expires")
    is_expired: bool = Field(..., description="Whether invitation has expired")
    notes: str | None = Field(None, description="Optional notes from inviter")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "scope_id": "550e8400-e29b-41d4-a716-446655440000",
                "scope_name": "kidney-genetics",
                "scope_display_name": "Kidney Genetics",
                "role": "curator",
                "invited_by": "770e8400-e29b-41d4-a716-446655440000",
                "inviter_name": "Dr. Jane Smith",
                "inviter_email": "jane.smith@hospital.org",
                "invited_at": "2025-01-10T10:00:00Z",
                "expires_at": "2025-01-17T10:00:00Z",
                "is_expired": False,
                "notes": "Welcome to the kidney genetics team!",
            }
        },
    }


class PendingInvitationsListResponse(BaseModel):
    """
    Schema for listing pending invitations.

    Contains the list of invitations and total count.
    """

    invitations: list[PendingInvitationResponse] = Field(
        ..., description="List of pending invitations"
    )
    total: int = Field(..., description="Total number of pending invitations", ge=0)

    model_config = {
        "json_schema_extra": {
            "example": {
                "invitations": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "scope_id": "550e8400-e29b-41d4-a716-446655440000",
                        "scope_name": "kidney-genetics",
                        "scope_display_name": "Kidney Genetics",
                        "role": "curator",
                        "invited_at": "2025-01-10T10:00:00Z",
                        "expires_at": "2025-01-17T10:00:00Z",
                        "is_expired": False,
                    }
                ],
                "total": 1,
            }
        }
    }
