"""
Notification API endpoints.

Provides endpoints for listing, reading, and managing user notifications.
Users can only access their own notifications.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.crud.notification import notification_crud
from app.models import UserNew
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
)

router = APIRouter()


@router.get("/", response_model=NotificationListResponse)
def list_notifications(
    is_read: bool | None = Query(None, description="Filter by read status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records"),
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Any:
    """List current user's notifications, optionally filtered by read status."""
    notifications = notification_crud.get_by_user(
        db, user_id=current_user.id, is_read=is_read, skip=skip, limit=limit
    )
    total = notification_crud.count_by_user(
        db, user_id=current_user.id, is_read=is_read
    )
    return NotificationListResponse(
        notifications=[
            NotificationResponse.model_validate(n) for n in notifications
        ],
        total=total,
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Any:
    """Mark a single notification as read."""
    notification = notification_crud.mark_as_read(
        db, notification_id=notification_id, user_id=current_user.id
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return NotificationResponse.model_validate(notification)


@router.patch("/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Any:
    """Mark all notifications as read for the current user."""
    count = notification_crud.mark_all_as_read(db, user_id=current_user.id)
    return {"message": "All notifications marked as read", "count": count}
