"""Shared preflight applies to bulk and refuses changed authorization/snapshot state."""

from uuid import uuid4

import pytest
from sqlalchemy import update

from app.models import CurationNew, UserNew
from app.models.methodology import MethodologyVersion
from app.services import review_entry
from tests.api.test_submit_unknown_pmids import _fake_fetch, stored as stored


def test_bulk_preflights_only_existing_eligible_items(
    client, admin_token, stored, monkeypatch
):
    fetched = _fake_fetch(monkeypatch, {})
    missing = str(uuid4())
    response = client.post(
        "/api/v1/workflow/bulk-transition",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "item_ids": [str(stored.id), missing],
            "item_type": "curation",
            "target_stage": "review",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["successful_transitions"] == [str(stored.id)]
    assert response.json()["failed_transitions"][0]["item_id"] == missing
    assert sorted(fetched) == ["31000001", "99999999"]


@pytest.mark.parametrize("change", ["pin", "user", "creator"])
def test_revalidation_uses_fresh_orm_state(
    client,
    curator_token,
    db_session,
    test_curation,
    test_user_curator,
    test_user_viewer,
    test_precuration_schema,
    monkeypatch,
    change,
):
    item_id = test_curation.id
    version = test_curation.lock_version

    def remote(db, entries):
        if change == "pin":
            # SQLite lacks PG's immutable-pin trigger; still bind results to the exact pin.
            version = MethodologyVersion(
                schema_id=test_precuration_schema.id, version=1, snapshot={}
            )
            db.add(version)
            db.flush()
            db.execute(
                update(CurationNew)
                .where(CurationNew.id == item_id)
                .values(methodology_version_id=version.id)
            )
        elif change == "creator":
            db.execute(
                update(CurationNew)
                .where(CurationNew.id == item_id)
                .values(created_by=test_user_viewer.id)
            )
        else:
            db.execute(
                update(UserNew)
                .where(UserNew.id == test_user_curator.id)
                .values(is_active=False)
            )
        db.commit()
        return entries

    monkeypatch.setattr(review_entry, "lookup_reviews", remote)
    response = client.post(
        f"/api/v1/curations/{item_id}/submit",
        headers={"Authorization": f"Bearer {curator_token}"},
        json={"lock_version": version},
    )
    assert response.status_code == (409 if change == "pin" else 403), response.text
    db_session.expire_all()
    assert db_session.get(CurationNew, item_id).workflow_stage.value == "curation"
