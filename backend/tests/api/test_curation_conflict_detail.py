"""MCP study F8: a stale save's 409 names the last editor and the evidence keys that differ."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CurationNew, UserNew

pytestmark = pytest.mark.unit


def test_stale_save_names_the_last_editor_and_the_changed_keys(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_user_admin: UserNew,
    test_curation: CurationNew,
) -> None:
    test_curation.evidence_data = {"status": "in_progress", "same": 1, "theirs": 2}
    test_curation.updated_by = test_user_admin.id
    db_session.commit()

    response = client.put(
        f"/api/v1/curations/{test_curation.id}",
        json={"evidence_data": {"status": "done", "same": 1}, "lock_version": 999},
        headers={"Authorization": f"Bearer {curator_token}"},
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["updated_by_name"] == "Admin User"
    assert detail["updated_at"]
    assert detail["changed_keys"] == ["status", "theirs"]
