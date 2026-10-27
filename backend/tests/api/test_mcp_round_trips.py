"""MCP study round trips agents named (token-efficiency plan item 2)."""

from fastapi.testclient import TestClient

from app.models import CurationNew, PrecurationNew


def test_list_rows_carry_lock_version(
    client: TestClient,
    curator_token: str,
    test_curation: CurationNew,
    test_precuration: PrecurationNew,
) -> None:
    """A save needs lock_version; the list row has it, so no GET just for it."""
    h = {"Authorization": f"Bearer {curator_token}"}
    (c,) = client.get("/api/v1/curations/", headers=h).json()["curations"]
    (p,) = client.get("/api/v1/precurations/", headers=h).json()["precurations"]
    assert c["lock_version"] == test_curation.lock_version
    assert p["lock_version"] == test_precuration.lock_version
