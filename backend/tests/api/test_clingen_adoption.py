"""Adopting ClinGen classifications (#105) through the public API."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.models import (
    ActiveCuration,
    CurationNew,
    Gene,
    ReviewItemComment,
    Scope,
    ScopeMembership,
    UserNew,
    WorkflowPair,
)
from app.services.clingen_adoption import ADOPTION_COMMENT, _moi

pytestmark = pytest.mark.unit
URL = "/api/v1/curations/clingen-adoptions"
CGGV = "CGGV:assertion_09d61dec-314b-4c5f-af2e-f22fc5992c12-2021-02-26T151356.823Z"


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _row(gene: Gene, scope: Scope, pair: WorkflowPair, **clingen: Any) -> dict:
    return {
        "gene_id": str(gene.id),
        "scope_id": str(scope.id),
        "workflow_pair_id": str(pair.id),
        "mondo_id": "MONDO:0004691",
        "mode_of_inheritance": "Autosomal dominant inheritance",
        "disease_name": "autosomal dominant polycystic kidney disease",
        "clingen": {
            "source": "clingen",
            "cggv_id": CGGV,
            "permalink": f"https://search.clinicalgenome.org/kb/gene-validity/{CGGV}",
            "classification": "Definitive",
            "moi": "AD",
            "mondo": "MONDO:0004691",
            "hgnc_id": gene.hgnc_id,
            "expert_panel": "Kidney Cystic and Ciliopathy Disorders GCEP",
            "classified_date": "2021-02-26T15:13:56.823Z",
            "retrieved_at": "2026-10-31T09:10:08.948276Z",
            "record_sha256": "35f4c231aaa38e63ee34247c4720992841b2ae92afc8be73d665b97223b5825a",
            "citation": "ClinGen Gene-Disease Validity: BRCA1 — Definitive (AD)",
            **clingen,
        },
    }


@pytest.fixture
def row(test_gene: Gene, test_scope: Scope, test_workflow_pair: WorkflowPair) -> dict:
    return _row(test_gene, test_scope, test_workflow_pair)


def _count(db: Session) -> int:
    return len(db.scalars(select(CurationNew)).all())


def test_adopt_creates_a_curation_in_review_with_the_marker_and_comment(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_user_curator: UserNew,
    row: dict,
) -> None:
    dry = client.post(
        URL, params={"dry_run": True}, json={"rows": [row]}, headers=_h(curator_token)
    )
    assert dry.status_code == 200, dry.text
    assert dry.json()["items"] == [
        {"row": 0, "cggv_id": CGGV, "action": "create", "curation_id": None}
    ]
    assert _count(db_session) == 0

    r = client.post(URL, json={"rows": [row]}, headers=_h(curator_token))
    assert r.status_code == 200, r.text
    cid = r.json()["items"][0]["curation_id"]
    c = db_session.get(CurationNew, cid)
    assert c is not None
    assert (c.status.value, c.workflow_stage.value) == ("in_review", "review")
    assert c.created_by == c.submitted_by == test_user_curator.id
    assert c.final_classification == "definitive"
    assert c.entity_key == "MONDO:0004691|AD"
    assert c.clingen_adoption == row["clingen"]
    comments = db_session.scalars(
        select(ReviewItemComment).where(ReviewItemComment.curation_id == c.id)
    ).all()
    assert [x.body for x in comments] == [ADOPTION_COMMENT]

    detail = client.get(f"/api/v1/curations/{cid}", headers=_h(curator_token)).json()
    assert detail["clingen_adoption"]["permalink"] == row["clingen"]["permalink"]
    listed = client.get(
        "/api/v1/curations/",
        params={"scope_id": row["scope_id"]},
        headers=_h(curator_token),
    ).json()["curations"]
    assert listed[0]["clingen_adoption"]["cggv_id"] == CGGV

    # re-adopting the same record for the entity is a no-op
    again = client.post(URL, json={"rows": [row]}, headers=_h(curator_token))
    assert again.status_code == 200, again.text
    assert again.json()["items"][0] == {
        "row": 0,
        "cggv_id": CGGV,
        "action": "unchanged",
        "curation_id": cid,
    }
    assert _count(db_session) == 1

    # another record for the entity is refused: it has an open curation
    other = row | {"clingen": row["clingen"] | {"cggv_id": "CGGV:assertion_other"}}
    refused = client.post(URL, json={"rows": [other]}, headers=_h(curator_token))
    assert refused.status_code == 422
    assert refused.json()["detail"]["errors"] == [
        f"rows[0].entity: already has open curation {cid}"
    ]


def test_any_invalid_row_refuses_all_and_lists_each_error(
    client: TestClient, db_session: Session, curator_token: str, row: dict
) -> None:
    bad = row | {
        "mondo_id": "MONDO:0000001",
        "mode_of_inheritance": "AR",
        "clingen": row["clingen"] | {"hgnc_id": "HGNC:1", "classification": "Bogus"},
    }
    missing = row | {"gene_id": str(uuid4())}
    no_pair = row | {
        "workflow_pair_id": str(uuid4()),
        "mondo_id": "MONDO:0009889",
        "mode_of_inheritance": "AR",
        "clingen": row["clingen"] | {"mondo": "MONDO:0009889", "moi": "AR"},
    }
    r = client.post(
        URL, json={"rows": [row, bad, missing, no_pair, row]}, headers=_h(curator_token)
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["errors"] == [
        "rows[1].clingen.hgnc_id: HGNC:1 is not HGNC:1100",
        "rows[1].clingen.mondo: MONDO:0004691 is not the entity's MONDO:0000001",
        "rows[1].clingen.moi: AD is not the entity's AR",
        "rows[1].clingen.classification: Bogus is not one of definitive, strong, "
        "moderate, limited, no_known, disputed, refuted",
        "rows[2].gene_id: gene not found",
        "rows[3].workflow_pair_id: workflow pair not found",
        "rows[4].entity: another row adopts it too",
    ]
    assert _count(db_session) == 0
    # a dry run reports the same errors with 200
    dry = client.post(
        URL, params={"dry_run": True}, json={"rows": [bad]}, headers=_h(curator_token)
    )
    assert dry.status_code == 200 and len(dry.json()["errors"]) == 4


def test_viewer_may_not_adopt(
    client: TestClient, db_session: Session, viewer_token: str, row: dict
) -> None:
    r = client.post(URL, json={"rows": [row]}, headers=_h(viewer_token))
    assert r.status_code == 403
    assert _count(db_session) == 0


def test_inactive_scope_is_refused(
    client: TestClient, db_session: Session, test_scope: Scope, row: dict
) -> None:
    test_scope.is_active = False
    db_session.commit()
    r = client.post(URL, json={"rows": [row]}, headers=_h(admin_token_for(db_session)))
    assert r.status_code == 409


def test_unknown_scope_is_a_row_error(
    client: TestClient, db_session: Session, row: dict
) -> None:
    gone = row | {"scope_id": str(uuid4())}
    r = client.post(URL, json={"rows": [gone]}, headers=_h(admin_token_for(db_session)))
    assert r.status_code == 422
    assert r.json()["detail"]["errors"] == ["rows[0].scope_id: scope not found"]


def admin_token_for(db: Session) -> str:
    user = UserNew(
        id=uuid4(),
        email=f"{uuid4().hex[:8]}@adopt.org",
        hashed_password=get_password_hash("pw"),
        name="Admin",
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    return create_access_token(data={"sub": str(user.id)})


def test_adopter_may_not_approve_another_reviewer_does_and_export_has_the_statement(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_user_curator: UserNew,
    test_scope: Scope,
    row: dict,
) -> None:
    cid = client.post(URL, json={"rows": [row]}, headers=_h(curator_token)).json()[
        "items"
    ][0]["curation_id"]
    move = f"/api/v1/workflow/curation/{cid}/transition"
    own = client.post(move, json={"target_stage": "active"}, headers=_h(curator_token))
    assert own.status_code == 403, own.text

    reviewer = UserNew(
        id=uuid4(),
        email="rev@adopt.org",
        hashed_password=get_password_hash("pw"),
        name="Rita Reviewer",
        role="user",
        is_active=True,
    )
    db_session.add(reviewer)
    db_session.flush()
    db_session.add(
        ScopeMembership(
            scope_id=test_scope.id,
            user_id=reviewer.id,
            role="reviewer",
            accepted_at=datetime.now(UTC),
        )
    )
    db_session.commit()
    rev = create_access_token(data={"sub": str(reviewer.id)})
    ok = client.post(move, json={"target_stage": "active"}, headers=_h(rev))
    assert ok.status_code == 200, ok.text
    assert ok.json()["to_stage"] == "active"
    again = client.post(move, json={"target_stage": "active"}, headers=_h(rev))
    assert again.status_code == 409, again.text
    assert db_session.scalar(select(ActiveCuration.curation_id)) is not None

    items = client.get("/api/v1/export/curations", headers=_h(rev)).json()["items"]
    adoption = items[0]["adoption"]
    assert adoption["id"] == CGGV
    assert adoption["reportedIn"] == [
        {
            "documentType": "ClinGen gene-disease validity curation",
            "title": row["clingen"]["citation"],
            "urls": [row["clingen"]["permalink"]],
        }
    ]
    roles = [
        (
            c["contributor"]["agentType"],
            c["contributor"]["name"],
            c["activityType"]["name"],
            c["activityType"]["primaryCoding"]["code"],
        )
        for c in adoption["contributions"]
    ]
    assert roles == [
        (
            "organization",
            row["clingen"]["expert_panel"],
            "interpreter",
            "SEPIO:0000331",
        ),
        ("person", "Curator User", "curator", "SEPIO:0000156"),
        ("person", "Rita Reviewer", "approver", "SEPIO:0000155"),
    ]
    assert adoption["contributions"][1]["contributor"]["id"] == str(
        test_user_curator.id
    )


@pytest.mark.parametrize(
    ("value", "abbr"),
    [
        ("AD", "AD"),
        ("Autosomal recessive inheritance", "AR"),
        ("HP:0001417", "XL"),
        ("semi-dominant", "SD"),
        ("UD", "UD"),
    ],
)
def test_moi_names_one_canonical_code(value: str, abbr: str) -> None:
    assert _moi(value) == abbr
