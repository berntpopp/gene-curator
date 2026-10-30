"""Split disease entities (#530): one open and one active curation per gene-disease-MOI."""

from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.precuration import precuration_crud
from app.crud.precuration_entity import entity_key_of
from app.crud.workflow_engine import workflow_engine
from app.models import (
    ActiveCuration,
    CurationNew,
    CurationStatus,
    Gene,
    PrecurationNew,
    Scope,
    WorkflowPair,
    WorkflowStage,
)
from app.schemas.precuration import PrecurationCreate
from tests.api.scopes.factories import (
    auth_headers,
    make_gene,
    make_member,
    make_precuration,
    make_scope,
    make_user,
)

pytestmark = pytest.mark.unit

A = {"mondo_id": "MONDO:0000001", "mode_of_inheritance": "AD"}
B = {"mondo_id": "MONDO:0000002", "mode_of_inheritance": "AD"}


@pytest.fixture(autouse=True)
def no_rls_on_sqlite():
    with (
        patch("app.api.v1.endpoints.curations.set_rls_context"),
        patch("app.api.v1.endpoints.precurations.set_rls_context"),
    ):
        yield


class World:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.author, self.reviewer = make_user(db), make_user(db)
        self.scope: Scope = make_scope(db)
        make_member(db, self.scope, self.author, "curator")
        make_member(db, self.scope, self.reviewer, "reviewer")
        self.gene: Gene = make_gene(db)
        first = make_precuration(
            db, scope=self.scope, gene=self.gene, creator=self.author
        )
        self.schema_id = first.precuration_schema_id
        db.delete(first)
        self.pair = WorkflowPair(
            name="wf-split",
            version="1.0",
            precuration_schema_id=self.schema_id,
            is_active=True,
        )
        db.add(self.pair)
        db.commit()

    def approve(self, evidence: dict[str, str]) -> tuple[PrecurationNew, UUID | None]:
        pre = PrecurationNew(
            gene_id=self.gene.id,
            scope_id=self.scope.id,
            precuration_schema_id=self.schema_id,
            status=CurationStatus.SUBMITTED,
            workflow_stage=WorkflowStage.REVIEW,
            evidence_data=evidence,
            created_by=self.author.id,
            updated_by=self.author.id,
        )
        self.db.add(pre)
        self.db.commit()
        result = precuration_crud.approve_and_create_curation(
            self.db, db_obj=pre, approver_id=self.reviewer.id
        )
        return pre, result.curation_id

    def activate(self, curation_id: UUID) -> CurationNew:
        curation = self.db.get(CurationNew, curation_id)
        assert curation is not None
        workflow_engine._transition_to_active(
            self.db, curation, self.reviewer.id, None, None
        )
        self.db.commit()
        return curation

    def actives(self) -> set[UUID]:
        return {
            a.curation_id
            for a in self.db.query(ActiveCuration).filter(
                ActiveCuration.gene_id == self.gene.id,
                ActiveCuration.archived_at.is_(None),
            )
        }

    def create(self, client: TestClient, **extra: str) -> tuple[int, dict]:
        body = {
            "gene_id": str(self.gene.id),
            "scope_id": str(self.scope.id),
            "workflow_pair_id": str(self.pair.id),
            "evidence_data": {},
            **extra,
        }
        r = client.post(
            "/api/v1/curations/", json=body, headers=auth_headers(self.author)
        )
        return r.status_code, r.json()


@pytest.mark.parametrize(
    ("evidence", "key"),
    [
        ({}, ""),
        ({"mode_of_inheritance": "AD"}, ""),
        (
            {
                "mondo_id": " mondo_0000001 ",
                "mode_of_inheritance": "Autosomal Dominant",
            },
            "MONDO:0000001|AD",
        ),
        (
            {
                "entity_definition": {
                    "mondo_id": "MONDO:0000002",
                    "mode_of_inheritance": "X-linked",
                }
            },
            "MONDO:0000002|XL",
        ),
        ({"mondo_id": "", "entity_definition": {"mondo_id": "MONDO:3"}}, "MONDO:3|"),
        ({"mondo_id": "MONDO:1", "mode_of_inheritance": "HP:0000007"}, "MONDO:1|AR"),
        # One canonical MOI for the HPO label, id, code and snake_case value
        *(
            ({"mondo_id": "MONDO:1", "mode_of_inheritance": moi}, "MONDO:1|AD")
            for moi in (
                "Autosomal dominant inheritance",
                "HP:0000006",
                "autosomal_dominant",
                "AD",
            )
        ),
        (
            {
                "mondo_id": "M:1",
                "mode_of_inheritance": "X-linked recessive inheritance",
            },
            "M:1|XLR",
        ),
        ({"mondo_id": "M:1", "mode_of_inheritance": "HP:0001423"}, "M:1|XLD"),
        (
            {"mondo_id": "M:1", "mode_of_inheritance": "Mitochondrial inheritance"},
            "M:1|MT",
        ),
    ],
)
def test_entity_key_normalises_mondo_and_moi(
    db_session: Session, evidence: dict, key: str
) -> None:
    """The generated column and entity_key_of share one expression."""
    world = World(db_session)
    pre = PrecurationNew(
        gene_id=world.gene.id,
        scope_id=world.scope.id,
        precuration_schema_id=world.schema_id,
        evidence_data=evidence,
        created_by=world.author.id,
    )
    db_session.add(pre)
    db_session.commit()
    db_session.refresh(pre)
    assert pre.entity_key == key
    assert entity_key_of(db_session, evidence) == key


def test_two_mondo_ids_give_two_active_curations(db_session: Session) -> None:
    world = World(db_session)
    _, a = world.approve(A)
    _, b = world.approve(B)  # a second approval creates its own draft
    assert a and b and a != b
    world.activate(a)
    world.activate(b)
    assert world.actives() == {a, b}
    assert {db_session.get(CurationNew, i).status for i in (a, b)} == {  # type: ignore[union-attr]
        CurationStatus.ACTIVE
    }


def test_same_entity_twice_is_refused(db_session: Session, client: TestClient) -> None:
    world = World(db_session)
    _, a = world.approve(A)
    again, none = world.approve({**A, "mondo_id": "mondo:0000001"})
    assert a and none is None  # the entity already has an open curation
    code, body = world.create(client, precuration_id=str(again.id))
    assert code == 409 and body["detail"]["curation_id"] == str(a)


def test_recurating_a_archives_only_a(db_session: Session, client: TestClient) -> None:
    world = World(db_session)
    pre_a, a = world.approve(A)
    _, b = world.approve(B)
    assert a and b
    world.activate(a)
    world.activate(b)

    code, body = world.create(client)  # which entity? the caller must say
    assert code == 422 and "precuration_id" in body["detail"]

    code, body = world.create(client, precuration_id=str(pre_a.id))
    assert code == 201, body
    recuration = world.activate(UUID(body["id"]))
    assert recuration.entity_key == "MONDO:0000001|AD"
    assert world.actives() == {recuration.id, b}
    assert db_session.get(CurationNew, a).status == CurationStatus.ARCHIVED  # type: ignore[union-attr]


def test_recuration_inherits_the_single_active_entity(
    db_session: Session, client: TestClient
) -> None:
    world = World(db_session)
    pre_a, a = world.approve(A)
    assert a
    world.activate(a)
    code, body = world.create(client)
    assert code == 201, body
    assert body["precuration_id"] == str(pre_a.id)
    assert (
        db_session.get(CurationNew, UUID(body["id"])).entity_key == "MONDO:0000001|AD"
    )  # type: ignore[union-attr]


def test_recuration_may_link_a_no_longer_approved_precuration(
    db_session: Session, client: TestClient
) -> None:
    world = World(db_session)
    pre_a, a = world.approve(A)
    assert a
    world.activate(a)
    pre_a.status = CurationStatus.ARCHIVED
    db_session.commit()
    code, _ = world.create(client, precuration_id=str(pre_a.id))
    assert code == 201


def test_unkeyed_activation_supersedes_the_whole_gene(db_session: Session) -> None:
    """'' (lumped or legacy) keeps today's one-per-gene behaviour."""
    world = World(db_session)
    _, a = world.approve(A)
    assert a
    world.activate(a)
    legacy = CurationNew(
        gene_id=world.gene.id,
        scope_id=world.scope.id,
        workflow_pair_id=world.pair.id,
        status=CurationStatus.APPROVED,
        workflow_stage=WorkflowStage.REVIEW,
        evidence_data={},
        created_by=world.author.id,
    )
    db_session.add(legacy)
    db_session.commit()
    world.activate(legacy.id)
    assert world.actives() == {legacy.id}


def test_author_may_draft_several_entities(db_session: Session) -> None:
    world = World(db_session)

    def draft(evidence: dict) -> PrecurationNew:
        return precuration_crud.create_precuration(
            db_session,
            obj_in=PrecurationCreate(
                gene_id=world.gene.id,
                scope_id=world.scope.id,
                precuration_schema_id=world.schema_id,
                evidence_data=evidence,
            ),
            user_id=world.author.id,
        )

    a, b = draft(A), draft(B)
    assert a.id != b.id
    assert draft(A).id == a.id  # the same entity returns the existing draft
    found = precuration_crud.get_open_draft(
        db_session,
        gene_id=world.gene.id,
        scope_id=world.scope.id,
        user_id=world.author.id,
        entity_key=b.entity_key,
    )
    assert found and found.id == b.id


def test_entity_key_sql_is_the_one_in_067() -> None:
    from pathlib import Path

    from app.models.curation import ENTITY_KEY_SQL

    sql = Path(__file__).parents[3] / "database/sql/067_split_disease_entities.sql"
    assert ENTITY_KEY_SQL in sql.read_text()


def _draft(world: World, evidence: dict) -> PrecurationNew:
    return precuration_crud.create_precuration(
        world.db,
        obj_in=PrecurationCreate(
            gene_id=world.gene.id,
            scope_id=world.scope.id,
            precuration_schema_id=world.schema_id,
            evidence_data=evidence,
        ),
        user_id=world.author.id,
    )


@pytest.mark.parametrize("route", ["draft", "put"])
def test_saving_a_draft_onto_another_drafts_entity_is_409(
    db_session: Session, client: TestClient, route: str
) -> None:
    """Author has a draft for A, opens a blank one and fills in A: 409 naming the A draft."""
    world = World(db_session)
    a, blank = _draft(world, A), _draft(world, {})
    url = f"/api/v1/precurations/{blank.id}"
    body = {"evidence_data": A, "lock_version": blank.lock_version}
    headers = auth_headers(world.author)
    r = (
        client.patch(f"{url}/draft", json=body, headers=headers)
        if route == "draft"
        else client.put(url, json=body, headers=headers)
    )
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["precuration_id"] == str(a.id)


def test_a_racing_curation_create_is_409(
    db_session: Session, client: TestClient
) -> None:
    """The open-curation index refuses what the pre-check missed: 409, not 500."""
    from app.crud import curation as crud

    world = World(db_session)
    _, a = world.approve(A)
    real = crud.open_curation_id
    calls = iter([lambda *a: None])  # the pre-check misses it, the lookup finds it
    with patch.object(
        crud, "open_curation_id", side_effect=lambda *a: next(calls, real)(*a)
    ):
        code, body = world.create(client)
    assert code == 409 and body["detail"]["curation_id"] == str(a)


def test_a_racing_approval_is_409(db_session: Session, client: TestClient) -> None:
    from app.crud import precuration as crud

    world = World(db_session)
    _, a = world.approve(A)
    pre = PrecurationNew(
        gene_id=world.gene.id,
        scope_id=world.scope.id,
        precuration_schema_id=world.schema_id,
        status=CurationStatus.SUBMITTED,
        workflow_stage=WorkflowStage.REVIEW,
        evidence_data=A,
        created_by=world.author.id,
    )
    db_session.add(pre)
    db_session.commit()
    real = crud.open_curation_id
    calls = iter([lambda *a: None])
    with patch.object(
        crud, "open_curation_id", side_effect=lambda *a: next(calls, real)(*a)
    ):
        r = client.post(
            f"/api/v1/precurations/{pre.id}/approve",
            headers=auth_headers(world.reviewer),
        )
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["curation_id"] == str(a)
    db_session.refresh(pre)
    assert pre.status == CurationStatus.SUBMITTED  # nothing half-done
