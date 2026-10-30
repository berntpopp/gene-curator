"""075: Standard_Precuration offers the relationship type in a new published version.

Read through the real API as app_user (072's entity_key already reads
entity_definition.relationship_type); a re-run publishes nothing.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.postgres.test_methodology_versions import W, _h, client, w
from tests.postgres.test_migration_068 import _entity, _schema_id

pytestmark = pytest.mark.postgres
__all__ = ["client", "w"]
MIGRATION = (
    Path(__file__).parents[3]
    / "database/sql/075_standard_precuration_relationship_type.sql"
)


def test_standard_precuration_offers_relationship_type(
    client: TestClient, w: W
) -> None:
    r = client.get(
        f"/api/v1/schemas/curation-schemas/{_schema_id('Standard_Precuration')}/versions",
        headers=_h(w.alice),
    )
    assert r.status_code == 200, r.text
    latest, previous = r.json()[:2]
    field = _entity(latest)["relationship_type"]
    assert [o["value"] for o in field["options"]] == ["mendelian", "susceptibility"]
    assert "relationship_type" not in _entity(previous)  # history unchanged
    assert latest["derived_from_version_id"] == previous["id"]


def test_rerun_publishes_nothing_and_is_recorded(owner_session: Session) -> None:
    count = "SELECT count(*) FROM methodology_versions"
    before = owner_session.scalar(text(count))
    owner_session.execute(text(MIGRATION.read_text()))
    assert owner_session.scalar(text(count)) == before
    assert owner_session.scalar(
        text(
            "SELECT count(*) FROM schema_migrations WHERE filename = "
            "'075_standard_precuration_relationship_type.sql'"
        )
    )
