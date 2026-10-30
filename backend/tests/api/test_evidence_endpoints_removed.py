"""The deprecated, unscored /curations/{id}/evidence endpoints are gone (Wave 8)."""

from app.main import app


def test_evidence_item_endpoints_are_removed() -> None:
    paths = app.openapi()["paths"]
    assert not [
        p for p in paths if p.startswith("/api/v1/curations/{curation_id}/evidence")
    ]
