"""The real app_user API persists an untouched form's declared false answer for both stages."""

import pytest

from app.core.security import create_access_token
from tests.postgres.test_submit_required_when import (
    W,
    _enter_review,
    _item_state,
    _owner,
    client,
    w,
)

pytestmark = pytest.mark.postgres
__all__ = ["client", "w"]


@pytest.mark.parametrize("item_type", ["precuration", "curation"])
def test_default_false_payload_saves_reloads_and_enters_review(client, w: W, item_type):
    headers = {
        "Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"
    }
    if item_type == "curation":
        with _owner() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO precurations (gene_id, scope_id, precuration_schema_id, "
                "status, workflow_stage, is_draft, created_by) VALUES "
                "(%s, %s, %s, 'approved', 'curation', false, %s)",
                (str(w.gene), str(w.scope), w.schema, str(w.alice)),
            )
    evidence = {"kind": "AD", "parent": {"child": "yes"}}
    made = client.post(
        f"/api/v1/{item_type}s/",
        headers=headers,
        json={
            "gene_id": str(w.gene),
            "scope_id": str(w.scope),
            **(
                {"workflow_pair_id": w.pair}
                if item_type == "curation"
                else {"precuration_schema_id": w.schema}
            ),
            "evidence_data": evidence,
        },
    )
    assert made.status_code == 201, made.text
    item = made.json()
    before = _item_state(item_type, item["id"])
    refused = _enter_review(
        client, headers, item_type, item["id"], "submit", item["lock_version"]
    )
    assert refused.status_code in (400, 422), refused.text
    assert "answered" in refused.text
    assert _item_state(item_type, item["id"]) == before
    # This is the untouched editable form's payload; a declared default is an answer.
    evidence["answered"] = False
    url = f"/api/v1/{item_type}s/{item['id']}"
    saved = client.patch(
        f"{url}/draft?detail=true",
        headers=headers,
        json={"evidence_data": evidence, "lock_version": item["lock_version"]},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["evidence_data"] == evidence
    loaded = client.get(url, headers=headers)
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["evidence_data"] == evidence
    accepted = _enter_review(
        client, headers, item_type, item["id"], "submit", saved.json()["lock_version"]
    )
    assert accepted.status_code == 200, accepted.text
    assert _item_state(item_type, item["id"])[1] == "review"
    assert _item_state(item_type, item["id"])[3] == evidence
