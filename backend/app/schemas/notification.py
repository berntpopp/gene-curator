"""
Pydantic schemas for notification API operations.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.models import NotificationType

# ========================================
# RESPONSE SCHEMAS
# ========================================


class NotificationResponse(BaseModel):
    """Schema for notification API responses."""

    id: UUID = Field(..., description="Notification UUID")
    user_id: UUID = Field(..., description="Recipient user UUID")
    type: NotificationType = Field(..., description="Notification type")
    title: str = Field(..., description="Short title")
    message: str = Field(..., description="Detail message")
    link: str | None = Field(None, description="Relative URL to relevant page")
    is_read: bool = Field(..., description="Whether notification has been read")
    created_at: datetime = Field(..., description="When notification was created")

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """Schema for paginated notification list."""

    notifications: list[NotificationResponse] = Field(
        ..., description="List of notifications"
    )
    total: int = Field(..., description="Total number of notifications", ge=0)


# ========================================
# REQUEST SCHEMAS
# ========================================


class NotificationCreate(BaseModel):
    """Schema for creating a notification (internal use)."""

    user_id: UUID = Field(..., description="Recipient user UUID")
    type: NotificationType = Field(..., description="Notification type")
    title: str = Field(..., max_length=255, description="Short title")
    message: str = Field(..., description="Detail message")
    link: str | None = Field(None, max_length=500, description="Relative URL")


class NotificationMarkRead(BaseModel):
    """Schema for marking a notification as read."""

    is_read: bool = Field(True, description="Read status")
