from fastapi.testclient import TestClient

from app.models import PrecurationNew


def test_list_exposes_created_by(
    client: TestClient, admin_token: str, test_precuration: PrecurationNew
):
    """The review queue hides a user's own precurations by created_by."""
    response = client.get(
        "/api/v1/precurations/", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["precurations"][0]["created_by"] == str(
        test_precuration.created_by
    )
