"""#613: an adoption carries no points of ours, keeps its agent credit and takes
diagnostics while in review; final_classification exists only once approved."""

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import (
    ActiveCuration,
    CurationNew,
    CurationStatus,
    Gene,
    ReviewStatus,
    Scope,
    UserNew,
    WorkflowPair,
)
from tests.api.test_clingen_adoption import URL, _h, _member, _row
from tests.api.test_mcp import call, pat, status_of
from tests.api.test_provenance_mcp import AGENT

pytestmark = pytest.mark.unit

DIAGNOSTICS = {"diagnostics": {"recommended_transcript": {"refseq": "NM_000296.4"}}}


@pytest.fixture
def row(test_gene: Gene, test_scope: Scope, test_workflow_pair: WorkflowPair) -> dict:
    return _row(test_gene, test_scope, test_workflow_pair)


def _adopt(client: TestClient, token: str, row: dict) -> str:
    r = client.post(URL, json={"rows": [row]}, headers=_h(token))
    assert r.status_code == 200, r.text
    return str(r.json()["items"][0]["curation_id"])


def _approve(client: TestClient, db: Session, scope: Scope, cid: str) -> None:
    rev = _member(db, scope, "reviewer", "Rita Reviewer")
    token = create_access_token(data={"sub": str(rev.id)})
    move = f"/api/v1/workflow/curation/{cid}/transition"
    ok = client.post(move, json={"target_stage": "active"}, headers=_h(token))
    assert ok.status_code == 200, ok.text


def _put(client: TestClient, token: str, cid: str, **body: Any) -> Any:
    lock = client.get(f"/api/v1/curations/{cid}", headers=_h(token)).json()
    return client.put(
        f"/api/v1/curations/{cid}",
        json={"lock_version": lock["lock_version"], **body},
        headers=_h(token),
    )


def test_adoption_exports_no_points_and_final_class_only_once_approved(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_scope: Scope,
    row: dict,
) -> None:
    cid = _adopt(client, curator_token, row)
    c = db_session.get(CurationNew, cid)
    assert c is not None
    # not scored at all: no verdict, no points, so no band-margin or other flag
    assert (c.computed_verdict, c.computed_scores) == (None, {})
    detail = client.get(f"/api/v1/curations/{cid}", headers=_h(curator_token)).json()
    assert detail["final_classification"] is None  # nobody approved it yet
    assert detail["curator_classification"] == "definitive"

    _approve(client, db_session, test_scope, cid)
    [item] = client.get("/api/v1/export/curations", headers=_h(curator_token)).json()[
        "items"
    ]
    assert item["final_classification"] == "definitive"
    assert item["computed_verdict"] is None
    assert [item[k] for k in ("genetic_score", "experimental_score")] == [None, None]
    assert (item["total_score"], item["scores"]) == (None, None)
    # what KGDB reads off an adoption
    assert item["adoption"]["classification"] == "Definitive"
    assert item["adoption"]["reportedIn"][0]["urls"] == [row["clingen"]["permalink"]]


def test_diagnostics_stay_editable_in_review_but_not_the_entity_or_class(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_scope: Scope,
    row: dict,
) -> None:
    cid = _adopt(client, curator_token, row)
    r = _put(client, curator_token, cid, evidence_data=DIAGNOSTICS, merge=True)
    assert r.status_code == 200, r.text
    c = db_session.get(CurationNew, cid)
    assert c is not None
    db_session.refresh(c)
    assert c.evidence_data["diagnostics"] == DIAGNOSTICS["diagnostics"]
    assert c.evidence_data["entity_definition"]["mondo_id"] == "MONDO:0004691"
    assert (c.status.value, c.computed_scores) == ("in_review", {})

    entity = {"entity_definition": {"mondo_id": "MONDO:0000001"}}
    for body in (
        {"evidence_data": entity, "merge": True},
        {"evidence_data": DIAGNOSTICS},  # a replace would drop the entity
        {"curator_classification": "limited"},
    ):
        refused = _put(client, curator_token, cid, **body)
        assert refused.status_code == 409, (body, refused.text)

    # another scope member may not edit it, as for any curation
    other = _member(db_session, test_scope, "curator", "Other Curator")
    token = create_access_token(data={"sub": str(other.id)})
    assert (
        _put(client, token, cid, evidence_data=DIAGNOSTICS, merge=True).status_code
        == 403
    )


def test_an_ordinary_curation_in_review_stays_frozen(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_curation: CurationNew,
) -> None:
    test_curation.status = test_curation.status.IN_REVIEW
    db_session.commit()
    r = _put(client, curator_token, str(test_curation.id), evidence_data=DIAGNOSTICS)
    assert r.status_code == 400, r.text


def test_an_agent_adopting_over_mcp_keeps_its_software_credit(
    client: TestClient,
    db_session: Session,
    test_user_curator: UserNew,
    test_scope: Scope,
    row: dict,
) -> None:
    token = pat(db_session, test_user_curator)
    result = call(
        client, token, "adopt_clingen_classifications", rows=[row], agent=AGENT
    )
    assert status_of(result) == 200, result
    cid = json.loads(result["content"][0]["text"])["items"][0]["curation_id"]
    _approve(client, db_session, test_scope, cid)
    jwt = create_access_token(data={"sub": str(test_user_curator.id)})
    [item] = client.get("/api/v1/export/curations", headers=_h(jwt)).json()["items"]
    roles = [
        (
            c["contributor"]["agentType"],
            c["contributor"]["name"],
            c["activityType"]["name"],
        )
        for c in item["contributions"]
    ]
    assert roles == [
        ("person", "Curator User", "curator"),
        ("software", AGENT["model"], "curator"),
        ("person", "Rita Reviewer", "assessor"),
        ("person", "Rita Reviewer", "approver"),
    ]
    software = item["contributions"][1]
    assert software["actedOnBehalfOf"]["name"] == "Curator User"
    assert item["adoption"]["contributions"][0]["contributor"]["agentType"] == (
        "organization"
    )


def test_export_keeps_every_field_kgdb_reads(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_scope: Scope,
    test_curation: CurationNew,
    row: dict,
) -> None:
    """The KGDB importer's contract: never rename or drop these (coordinator, #613)."""
    at = datetime.now(UTC)
    test_curation.entity_key = "MONDO:0011308|AR|SUSCEPTIBILITY"
    test_curation.evidence_data = {
        **DIAGNOSTICS,
        "diagnostics_notes": {"transcript_verified_via": "MANE"},
    }
    test_curation.computed_scores = {"association_total": 6, "total_score": 6}
    test_curation.computed_verdict = "established"
    test_curation.curator_classification = "likely"
    test_curation.curator_classification_rationale = "One replication only"
    test_curation.status, test_curation.approved_at = CurationStatus.ACTIVE, at
    db_session.add(
        ActiveCuration(
            gene_id=test_curation.gene_id,
            scope_id=test_curation.scope_id,
            curation_id=test_curation.id,
            entity_key=test_curation.entity_key,
            activated_at=at,
        )
    )
    db_session.commit()
    cid = _adopt(client, curator_token, row | {"mode_of_inheritance": "AD"})
    _approve(client, db_session, test_scope, cid)

    items = client.get("/api/v1/export/curations", headers=_h(curator_token)).json()
    by_id = {i["curation_id"]: i for i in items["items"]}
    own, adopted = by_id[str(test_curation.id)], by_id[cid]
    assert own["scores"]["association_total"] == 6
    assert (own["computed_verdict"], own["final_classification"]) == (
        "established",
        "likely",
    )
    assert own["curator_classification_rationale"] == "One replication only"
    assert own["evidence"]["diagnostics"] == DIAGNOSTICS["diagnostics"]
    assert own["evidence"]["diagnostics_notes"] == {"transcript_verified_via": "MANE"}
    adoption = adopted["adoption"]
    assert adoption["id"] == row["clingen"]["cggv_id"]
    assert adoption["classification"] == "Definitive"
    assert adoption["reportedIn"][0]["urls"][0] == row["clingen"]["permalink"]
    [panel] = [
        c
        for c in adoption["contributions"]
        if c["activityType"]["name"] == "interpreter"
    ]
    assert panel["contributor"]["name"] == row["clingen"]["expert_panel"]
    assert panel["date"].startswith("2021-02-26")
    assert "computed_verdict" in adopted and "scores" in adopted


def test_an_adoption_scored_before_613_exports_no_points(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_scope: Scope,
    row: dict,
) -> None:
    """Rows adopted before the fix kept no_known and 0 points in the database."""
    cid = _adopt(client, curator_token, row)
    c = db_session.get(CurationNew, cid)
    assert c is not None
    c.computed_verdict = "no_known"
    c.computed_scores = {"genetic_total": 0, "experimental_total": 0, "total_score": 0}
    db_session.commit()
    _approve(client, db_session, test_scope, cid)
    [item] = client.get("/api/v1/export/curations", headers=_h(curator_token)).json()[
        "items"
    ]
    assert item["computed_verdict"] is None
    assert [
        item[k] for k in ("genetic_score", "experimental_score", "total_score")
    ] == [None] * 3
    assert (item["scores"], item["final_classification"]) == (None, "definitive")


def test_a_diagnostics_edit_in_review_starts_a_new_review_round(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_scope: Scope,
    row: dict,
) -> None:
    """Every required approval sees the edited content: earlier ones are asked again."""
    from app.models import Review
    from tests.unit.scope.test_workflow_config import _pin

    cid = _adopt(client, curator_token, row)
    c = db_session.get(CurationNew, cid)
    assert c is not None
    _pin(db_session, c, {"review": {"reviewers_required": 2}})
    first, second = (
        _member(db_session, test_scope, "reviewer", n) for n in ("R One", "R Two")
    )

    def approve(user: UserNew) -> None:
        r = client.post(
            f"/api/v1/workflow/curation/{cid}/assign-reviewer",
            json={"reviewer_id": str(user.id)},
            headers=_h(curator_token),
        )
        assert r.status_code in (200, 409), r.text  # 409: already asked (new round)
        review = db_session.scalars(
            select(Review).where(
                Review.curation_id == c.id,
                Review.reviewer_id == user.id,
                Review.status == ReviewStatus.PENDING,
            )
        ).one()
        token = create_access_token(data={"sub": str(user.id)})
        r = client.post(
            f"/api/v1/workflow/reviews/{review.id}/submit",
            json={"decision": "approve"},
            headers=_h(token),
        )
        assert r.status_code == 200, r.text

    approve(first)
    r = _put(client, curator_token, cid, evidence_data=DIAGNOSTICS, merge=True)
    assert r.status_code == 200, r.text
    approve(second)  # the first approval was of the content before the edit
    db_session.refresh(c)
    assert c.status == CurationStatus.IN_REVIEW
    # asked again in the new round, with the notification a resubmit sends
    from app.models import NotificationNew
    from app.models.model_enums import NotificationType

    note = db_session.scalars(
        select(NotificationNew).where(
            NotificationNew.user_id == first.id,
            NotificationNew.type == NotificationType.REVIEW_ASSIGNED,
            NotificationNew.link == f"/scopes/{c.scope_id}/curations/{cid}",
        )
    ).all()
    assert len(note) == 2  # the first ask and the new round
    approve(first)
    db_session.refresh(c)
    assert c.status == CurationStatus.ACTIVE
