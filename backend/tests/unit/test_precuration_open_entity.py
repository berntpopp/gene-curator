"""One open precuration per gene, scope and disease entity (#567)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CurationStatus, PrecurationNew, WorkflowStage
from tests.api.scopes.factories import auth_headers, make_member, make_user
from tests.unit.test_split_entities import A, World, _draft

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def no_rls_on_sqlite():
    with (
        patch("app.api.v1.endpoints.curations.set_rls_context"),
        patch("app.api.v1.endpoints.precurations.set_rls_context"),
    ):
        yield


def _pre(world: World, status: CurationStatus) -> PrecurationNew:
    pre = PrecurationNew(
        gene_id=world.gene.id,
        scope_id=world.scope.id,
        precuration_schema_id=world.schema_id,
        status=status,
        workflow_stage=WorkflowStage.REVIEW,
        evidence_data=A,
        created_by=world.author.id,
        updated_by=world.author.id,
    )
    world.db.add(pre)
    world.db.commit()
    return pre


def _post(client: TestClient, world: World, evidence: dict, user=None):  # type: ignore[no-untyped-def]
    return client.post(
        "/api/v1/precurations/",
        json={
            "gene_id": str(world.gene.id),
            "scope_id": str(world.scope.id),
            "precuration_schema_id": str(world.schema_id),
            "evidence_data": evidence,
        },
        headers=auth_headers(user or world.author),
    )


@pytest.mark.parametrize(
    "status",
    [
        CurationStatus.SUBMITTED,
        CurationStatus.IN_REVIEW,
        CurationStatus.REJECTED,
        CurationStatus.APPROVED,  # approved, no curation made from it yet
    ],
)
def test_second_precuration_of_an_open_entity_is_409(
    db_session: Session, client: TestClient, status: CurationStatus
) -> None:
    world = World(db_session)
    first = _pre(world, status)
    other = make_user(db_session)
    make_member(db_session, world.scope, other, "curator")
    for user in (world.author, other):
        r = _post(client, world, {**A, "mondo_id": " mondo:0000001 "}, user)
        assert r.status_code == 409, r.text
        assert r.json()["detail"]["precuration_id"] == str(first.id)
    # Another entity of the gene, incl. the susceptibility relationship, still works
    sus = {**A, "relationship_type": "susceptibility"}
    assert _post(client, world, sus).status_code == 201
    assert _post(client, world, {**A, "mode_of_inheritance": "AR"}).status_code == 201


def test_another_curators_draft_blocks_the_entity(
    db_session: Session, client: TestClient
) -> None:
    world = World(db_session)
    first = _draft(world, A)
    other = make_user(db_session)
    make_member(db_session, world.scope, other, "curator")
    r = _post(client, world, A, other)
    assert r.status_code == 409 and r.json()["detail"]["precuration_id"] == str(
        first.id
    )
    assert _post(client, world, A).status_code == 200  # the author's retry: their draft


def test_used_or_archived_precurations_do_not_block(
    db_session: Session, client: TestClient
) -> None:
    world = World(db_session)
    _, curation = world.approve(A)  # approved and curated: a re-precuration may start
    assert curation
    _pre(world, CurationStatus.ARCHIVED)
    assert _post(client, world, A).status_code == 201


@pytest.mark.parametrize("route", ["draft", "put"])
def test_saving_a_draft_onto_an_entity_in_review_is_409(
    db_session: Session, client: TestClient, route: str
) -> None:
    world = World(db_session)
    first = _pre(world, CurationStatus.SUBMITTED)
    blank = _draft(world, {})
    url = f"/api/v1/precurations/{blank.id}"
    body = {"evidence_data": A, "lock_version": blank.lock_version}
    headers = auth_headers(world.author)
    r = (
        client.patch(f"{url}/draft", json=body, headers=headers)
        if route == "draft"
        else client.put(url, json=body, headers=headers)
    )
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["precuration_id"] == str(first.id)
    db_session.refresh(blank)
    assert blank.entity_key == "" and blank.lock_version == body["lock_version"]


def test_a_save_that_keeps_a_legacy_duplicates_entity_passes(
    db_session: Session, client: TestClient
) -> None:
    """Rows duplicated before #567 stay editable while their entity is unchanged."""
    world = World(db_session)
    _pre(world, CurationStatus.SUBMITTED)
    dup = _pre(world, CurationStatus.REJECTED)
    r = client.patch(
        f"/api/v1/precurations/{dup.id}/draft",
        json={"evidence_data": {**A, "note": "x"}, "lock_version": dup.lock_version},
        headers=auth_headers(world.author),
    )
    assert r.status_code == 200, r.text


def test_a_creatorless_legacy_draft_still_blocks(
    db_session: Session, client: TestClient
) -> None:
    world = World(db_session)
    legacy = _pre(world, CurationStatus.DRAFT)
    legacy.created_by = None
    db_session.commit()
    r = _post(client, world, A)
    assert r.status_code == 409 and r.json()["detail"]["precuration_id"] == str(
        legacy.id
    )
