"""068: the seeded MONDO fields get the MONDO lookup in a new published version.

Read through the real API as app_user (the form renders the pinned version's snapshot);
new precurations pin the new version, old versions stay unchanged, and a re-run adds
nothing.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.postgres.test_methodology_versions import W, _h, _owner, client, w

pytestmark = pytest.mark.postgres
__all__ = ["client", "w"]
MIGRATION = Path(__file__).parents[3] / "database/sql/068_seeded_mondo_lookup.sql"
ENTITY = ("field_definitions", "entity_definition", "properties")


def _schema_id(name: str) -> str:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM curation_schemas WHERE name = %s AND version = '1.0.0'",
            (name,),
        )
        return str(cur.fetchone()[0])


def _entity(version: dict) -> dict:
    out = version["snapshot"]
    for key in ENTITY:
        out = out[key]
    return out


@pytest.mark.parametrize("name", ["Standard_Precuration", "ClinGen_SOP_v11"])
def test_latest_seeded_version_uses_the_mondo_lookup(
    client: TestClient, w: W, name: str
) -> None:
    r = client.get(
        f"/api/v1/schemas/curation-schemas/{_schema_id(name)}/versions",
        headers=_h(w.alice),
    )
    assert r.status_code == 200, r.text
    latest, previous = r.json()[:2]
    assert _entity(latest)["mondo_id"]["component"] == "MONDOAutocomplete"
    assert "component" not in _entity(previous)["mondo_id"]  # history unchanged
    assert _entity(latest).keys() == _entity(previous).keys()  # same field keys
    assert latest["derived_from_version_id"] == previous["id"]


def test_new_precurations_pin_the_new_version(w: W) -> None:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT mv.snapshot #>> "
            "'{field_definitions,entity_definition,properties,mondo_id,component}' "
            "FROM precurations p JOIN methodology_versions mv "
            "ON mv.id = p.methodology_version_id WHERE p.scope_id = %s",
            (str(w.scope),),
        )
        assert cur.fetchall() == [("MONDOAutocomplete",)]


def test_rerun_publishes_nothing_and_is_recorded(owner_session: Session) -> None:
    count = "SELECT count(*) FROM methodology_versions"
    before = owner_session.scalar(text(count))
    owner_session.execute(text(MIGRATION.read_text()))
    assert owner_session.scalar(text(count)) == before
    assert owner_session.scalar(
        text(
            "SELECT count(*) FROM schema_migrations "
            "WHERE filename = '068_seeded_mondo_lookup.sql'"
        )
    )
