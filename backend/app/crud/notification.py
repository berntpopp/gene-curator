"""
CRUD operations for notifications.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.crud.base import CRUDBase
from app.models.models import NotificationNew, NotificationType
from app.schemas.notification import NotificationCreate, NotificationMarkRead


class CRUDNotification(
    CRUDBase[NotificationNew, NotificationCreate, NotificationMarkRead]
):
    """CRUD operations for notifications with user-scoped helpers."""

    def create_for_user(
        self,
        db: Session,
        *,
        user_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        link: str | None = None,
    ) -> NotificationNew:
        """Create a notification for a specific user."""
        db_obj = NotificationNew(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            link=link,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_user(
        self,
        db: Session,
        *,
        user_id: UUID,
        is_read: bool | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[NotificationNew]:
        """Get notifications for a user, optionally filtered by read status."""
        stmt = (
            select(NotificationNew)
            .where(NotificationNew.user_id == user_id)
            .order_by(NotificationNew.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if is_read is not None:
            stmt = stmt.where(NotificationNew.is_read == is_read)
        return db.execute(stmt).scalars().all()

    def count_by_user(
        self,
        db: Session,
        *,
        user_id: UUID,
        is_read: bool | None = None,
    ) -> int:
        """Count notifications for a user."""
        stmt = select(func.count()).select_from(NotificationNew).where(
            NotificationNew.user_id == user_id
        )
        if is_read is not None:
            stmt = stmt.where(NotificationNew.is_read == is_read)
        return db.execute(stmt).scalar() or 0

    def mark_as_read(
        self, db: Session, *, notification_id: UUID, user_id: UUID
    ) -> NotificationNew | None:
        """Mark a single notification as read. Returns None if not found or not owned."""
        notification = (
            db.execute(
                select(NotificationNew).where(
                    NotificationNew.id == notification_id,
                    NotificationNew.user_id == user_id,
                )
            )
            .scalars()
            .first()
        )
        if not notification:
            return None
        notification.is_read = True
        db.commit()
        db.refresh(notification)
        return notification

    def mark_all_as_read(self, db: Session, *, user_id: UUID) -> int:
        """Mark all notifications as read for a user. Returns count of updated rows."""
        result = db.execute(
            update(NotificationNew)
            .where(
                NotificationNew.user_id == user_id,
                NotificationNew.is_read == False,  # noqa: E712
            )
            .values(is_read=True)
        )
        db.commit()
        return result.rowcount


notification_crud = CRUDNotification(NotificationNew)
