"""069: ClinGen Precuration labels XLD with HP:0001423 in a new published version.

Read through the real API as app_user; the old version keeps its label, the stored
value stays XLD, and a re-run publishes nothing.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.postgres.test_methodology_versions import W, _h, client, w

pytestmark = pytest.mark.postgres
__all__ = ["client", "w"]
MIGRATION = (
    Path(__file__).parents[3] / "database/sql/069_clingen_precuration_xld_hpo.sql"
)
SCHEMA_ID = "e8f9a0b1-c2d3-4e5f-6a7b-8c9d0e1f2a3b"


def _moi(version: dict) -> dict[str, str]:
    for section in version["snapshot"]["field_definitions"]["sections"]:
        for f in section["fields"]:
            if f["id"] == "mode_of_inheritance":
                return {o["value"]: o["label"] for o in f["options"]}
    raise AssertionError("no mode_of_inheritance field")


def test_latest_version_labels_xld_with_hp_0001423(client: TestClient, w: W) -> None:
    r = client.get(
        f"/api/v1/schemas/curation-schemas/{SCHEMA_ID}/versions", headers=_h(w.alice)
    )
    assert r.status_code == 200, r.text
    latest, previous = r.json()[2:4]  # 070 and 072 publish on top of 069
    assert _moi(latest) == {
        "AD": "Autosomal Dominant (HP:0000006)",
        "AR": "Autosomal Recessive (HP:0000007)",
        "XLD": "X-linked Dominant (HP:0001423)",
        "XLR": "X-linked Recessive (HP:0001419)",
        "SD": "Semidominant (HP:0032113)",
        "MT": "Mitochondrial (HP:0001427)",
        "Other": "Other (specify)",
    }
    assert _moi(previous)["XLD"] == "X-linked Dominant (HP:0001417)"  # history kept
    assert latest["derived_from_version_id"] == previous["id"]


def test_rerun_publishes_nothing_and_is_recorded(owner_session: Session) -> None:
    count = "SELECT count(*) FROM methodology_versions"
    before = owner_session.scalar(text(count))
    owner_session.execute(text(MIGRATION.read_text()))
    assert owner_session.scalar(text(count)) == before
    assert owner_session.scalar(
        text(
            "SELECT count(*) FROM schema_migrations "
            "WHERE filename = '069_clingen_precuration_xld_hpo.sql'"
        )
    )
