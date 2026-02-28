"""Tests for notification API endpoints.

Tests listing, mark-as-read, mark-all-as-read, and user isolation.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import NotificationNew, NotificationType, UserNew

pytestmark = pytest.mark.unit


@pytest.fixture
def user_notifications(db_session: Session, test_user_admin: UserNew) -> list:
    """Create test notifications for admin user."""
    notifications = []
    for i, ntype in enumerate(
        [
            NotificationType.REVIEW_ASSIGNED,
            NotificationType.CURATION_APPROVED,
            NotificationType.REVISION_REQUESTED,
        ]
    ):
        n = NotificationNew(
            id=uuid4(),
            user_id=test_user_admin.id,
            type=ntype,
            title=f"Test notification {i}",
            message=f"Test message {i}",
            link=f"/curations/{uuid4()}",
            is_read=i == 2,  # Third one is already read
        )
        db_session.add(n)
        notifications.append(n)
    db_session.commit()
    for n in notifications:
        db_session.refresh(n)
    return notifications


@pytest.fixture
def other_user_notification(db_session: Session, test_user_curator: UserNew):
    """Create a notification for a different user."""
    n = NotificationNew(
        id=uuid4(),
        user_id=test_user_curator.id,
        type=NotificationType.REVIEW_ASSIGNED,
        title="Other user notification",
        message="Should not be visible to admin",
    )
    db_session.add(n)
    db_session.commit()
    db_session.refresh(n)
    return n


class TestListNotifications:
    """Tests for GET /notifications/"""

    def test_list_notifications(
        self,
        client: TestClient,
        admin_token: str,
        user_notifications: list,
    ):
        """Admin can list their own notifications."""
        response = client.get(
            "/api/v1/notifications/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["notifications"]) == 3

    def test_list_unread_only(
        self,
        client: TestClient,
        admin_token: str,
        user_notifications: list,
    ):
        """Can filter to unread notifications only."""
        response = client.get(
            "/api/v1/notifications/?is_read=false",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        for n in data["notifications"]:
            assert n["is_read"] is False

    def test_list_read_only(
        self,
        client: TestClient,
        admin_token: str,
        user_notifications: list,
    ):
        """Can filter to read notifications only."""
        response = client.get(
            "/api/v1/notifications/?is_read=true",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["notifications"][0]["is_read"] is True

    def test_user_isolation(
        self,
        client: TestClient,
        admin_token: str,
        user_notifications: list,
        other_user_notification,
    ):
        """Admin only sees their own notifications, not other users'."""
        response = client.get(
            "/api/v1/notifications/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        # Should only see admin's 3 notifications, not the curator's
        assert data["total"] == 3

    def test_unauthenticated_rejected(self, client: TestClient):
        """Unauthenticated requests are rejected."""
        response = client.get("/api/v1/notifications/")
        assert response.status_code in (401, 403)


class TestMarkAsRead:
    """Tests for PATCH /notifications/{id}/read"""

    def test_mark_as_read(
        self,
        client: TestClient,
        admin_token: str,
        user_notifications: list,
    ):
        """Can mark own notification as read."""
        unread = user_notifications[0]
        response = client.patch(
            f"/api/v1/notifications/{unread.id}/read",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_read"] is True
        assert data["id"] == str(unread.id)

    def test_mark_nonexistent_404(
        self,
        client: TestClient,
        admin_token: str,
    ):
        """Returns 404 for nonexistent notification."""
        response = client.patch(
            f"/api/v1/notifications/{uuid4()}/read",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    def test_cannot_mark_other_users_notification(
        self,
        client: TestClient,
        admin_token: str,
        other_user_notification,
    ):
        """Cannot mark another user's notification as read."""
        response = client.patch(
            f"/api/v1/notifications/{other_user_notification.id}/read",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404


class TestMarkAllAsRead:
    """Tests for PATCH /notifications/read-all"""

    def test_mark_all_as_read(
        self,
        client: TestClient,
        admin_token: str,
        user_notifications: list,
    ):
        """Marks all user's unread notifications as read."""
        response = client.patch(
            "/api/v1/notifications/read-all",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2  # Only 2 were unread

        # Verify all are now read
        list_response = client.get(
            "/api/v1/notifications/?is_read=false",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert list_response.json()["total"] == 0
