"""GET /curations/{id} shows the gene's approved precuration without linking it (no write on read)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CurationNew, PrecurationNew

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def mock_rls_context():
    with patch("app.api.v1.endpoints.curations.set_rls_context"):
        yield


def test_get_shows_the_approved_precuration_but_never_links_it(
    client: TestClient,
    db_session: Session,
    test_curation: CurationNew,
    test_precuration: PrecurationNew,
    curator_token: str,
):
    test_precuration.status = "approved"
    db_session.commit()

    response = client.get(
        f"/api/v1/curations/{test_curation.id}",
        headers={"Authorization": f"Bearer {curator_token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["disease_name"] == "Test Disease"
    db_session.commit()  # anything the read left pending would be written now
    db_session.expire_all()
    stored = db_session.get(CurationNew, test_curation.id)
    assert stored is not None
    assert stored.precuration_id is None
    assert stored.lock_version == test_curation.lock_version
