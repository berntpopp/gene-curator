"""070: ClinGen Precuration adds XL (HP:0001417) and Undetermined (HP:0000005) (#531).

Read through the real API as app_user; each option's CURIE is the HPO term its label
names, XLD/XLR stay, the old version is kept, and a re-run publishes nothing.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.postgres.test_methodology_versions import W, _h, client, w
from tests.postgres.test_migration_069 import _moi

pytestmark = pytest.mark.postgres
__all__ = ["client", "w"]
MIGRATION = (
    Path(__file__).parents[3]
    / "database/sql/070_clingen_precuration_moi_xl_undetermined.sql"
)
SCHEMA_ID = "e8f9a0b1-c2d3-4e5f-6a7b-8c9d0e1f2a3b"
# HPO 2026-09-01 term names for each CURIE.
HPO = {
    "HP:0000006": "Autosomal Dominant",
    "HP:0000007": "Autosomal Recessive",
    "HP:0001417": "X-linked",
    "HP:0001423": "X-linked Dominant",
    "HP:0001419": "X-linked Recessive",
    "HP:0032113": "Semidominant",
    "HP:0001427": "Mitochondrial",
    "HP:0000005": "Undetermined",
}


def test_latest_version_adds_xl_and_undetermined(client: TestClient, w: W) -> None:
    r = client.get(
        f"/api/v1/schemas/curation-schemas/{SCHEMA_ID}/versions", headers=_h(w.alice)
    )
    assert r.status_code == 200, r.text
    latest, previous = r.json()[:2]
    moi = _moi(latest)
    assert list(moi) == [
        "AD",
        "AR",
        "XL",
        "XLD",
        "XLR",
        "SD",
        "MT",
        "Undetermined",
        "Other",
    ]
    assert moi["Other"] == "Other (specify)"
    for label in (v for k, v in moi.items() if k != "Other"):
        name, curie = label.removesuffix(")").split(" (")
        assert HPO[curie] == name
    assert "XL" not in _moi(previous)  # history kept
    assert latest["derived_from_version_id"] == previous["id"]


def test_rerun_publishes_nothing_and_is_recorded(owner_session: Session) -> None:
    count = "SELECT count(*) FROM methodology_versions"
    before = owner_session.scalar(text(count))
    owner_session.execute(text(MIGRATION.read_text()))
    assert owner_session.scalar(text(count)) == before
    assert owner_session.scalar(
        text(
            "SELECT count(*) FROM schema_migrations "
            "WHERE filename = '070_clingen_precuration_moi_xl_undetermined.sql'"
        )
    )
