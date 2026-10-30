"""Export evidence, scores and summary (#558): members always, anonymous callers only for
a public scope with export_evidence_public on."""

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CurationNew, Gene, Scope, WorkflowPair
from app.scoring.point_model import score
from tests.api.test_curation_export import URL, _point, pair  # noqa: F401 (fixture)

pytestmark = pytest.mark.unit
T0 = datetime(2026, 1, 1, tzinfo=UTC)
MODEL = {
    "sections": [
        {
            "key": "genetic",
            "categories": [{"key": "case", "types": [{"path": "rows"}]}],
        }
    ],
    "bands": [{"class": "limited", "min": 0}],
}
EVIDENCE: dict[str, Any] = {
    "genetic": {"rows": [{"pmid": "12", "points": 1.5}, {"pmid": "3", "points": 2}]},
    # non-scoring clinical diagnostics section (kidney-genetics-db#439)
    "diagnostics": {
        "recommended_transcript": "NM_000546.6",
        "mane_status": "MANE Select",
        "resources": [{"url": "https://example.org/panel"}],
    },
}


def _curation(db: Session, wp: WorkflowPair, gene: Gene, scope: Scope) -> CurationNew:
    result = score(MODEL, EVIDENCE)
    return _point(
        db,
        wp,
        gene,
        scope,
        T0,
        evidence_data=EVIDENCE,
        computed_scores={"total_score": result["total"], "trace": result["trace"]},
        computed_summary="Limited: 3.5 points",
    )


def _item(client: TestClient, headers: dict[str, str] | None = None) -> dict[str, Any]:
    r = client.get(URL, headers=headers or {})
    assert r.status_code == 200, r.text
    [item] = r.json()["items"]
    return item  # type: ignore[no-any-return]


def test_member_gets_evidence_and_row_points_in_the_trace(
    client: TestClient,
    db_session: Session,
    pair: WorkflowPair,  # noqa: F811
    test_gene: Gene,
    test_scope: Scope,
    viewer_token: str,
) -> None:
    _curation(db_session, pair, test_gene, test_scope)

    item = _item(client, {"Authorization": f"Bearer {viewer_token}"})

    assert item["evidence"] == EVIDENCE  # diagnostics included, as stored
    assert item["summary"] == "Limited: 3.5 points"
    trace = item["scores"]["trace"]
    [section] = trace["sections"]
    [case] = section["categories"]
    [rows] = case["types"]
    assert (rows["path"], rows["items"]) == ("rows", 2)
    row_points = [r["points"] for r in item["evidence"]["genetic"]["rows"]]
    assert rows["score"] == sum(row_points)
    assert trace["total"] == item["total_score"] == sum(row_points)


@pytest.mark.parametrize("on", [False, True])
def test_anonymous_gets_evidence_only_when_the_scope_opts_in(
    client: TestClient,
    db_session: Session,
    pair: WorkflowPair,  # noqa: F811
    test_gene: Gene,
    test_public_scope: Scope,
    on: bool,
) -> None:
    test_public_scope.export_evidence_public = on
    _curation(db_session, pair, test_gene, test_public_scope)

    item = _item(client)

    assert item["total_score"] == 3.5  # today's fields either way
    shown = (item["evidence"], item["scores"], item["summary"])
    if on:
        assert shown[0] == EVIDENCE and shown[2] == "Limited: 3.5 points"
        assert shown[1]["trace"]["total"] == 3.5
    else:
        assert shown == (None, None, None)


@pytest.mark.parametrize("on", [False, True])
def test_signed_in_non_member_of_a_public_scope_is_treated_as_anonymous(
    client: TestClient,
    db_session: Session,
    pair: WorkflowPair,  # noqa: F811
    test_gene: Gene,
    test_public_scope: Scope,
    viewer_token: str,  # member of test_scope only
    on: bool,
) -> None:
    test_public_scope.export_evidence_public = on
    db_session.commit()
    _curation(db_session, pair, test_gene, test_public_scope)

    item = _item(client, {"Authorization": f"Bearer {viewer_token}"})

    shown = (item["evidence"], item["scores"], item["summary"])
    if on:
        assert shown[0] == EVIDENCE and shown[2] == "Limited: 3.5 points"
    else:
        assert shown == (None, None, None)


def test_scope_admin_toggles_the_setting(
    client: TestClient, test_scope: Scope, admin_token: str
) -> None:
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = client.patch(
        f"/api/v1/scopes/{test_scope.id}",
        json={"export_evidence_public": True},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["export_evidence_public"] is True
