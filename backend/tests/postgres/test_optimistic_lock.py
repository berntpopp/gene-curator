"""Optimistic locking on real PostgreSQL: the 008/040 version trigger and the guarded UPDATE
agree, so every save bumps the version exactly once, and a stale save changes nothing."""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.crud.curation import curation_crud
from app.crud.precuration import precuration_crud
from app.models.models import (
    CurationNew,
    CurationSchema,
    Gene,
    PrecurationNew,
    Scope,
    UserNew,
    WorkflowPair,
)
from app.schemas.curation import CurationDraftSave

pytestmark = pytest.mark.postgres

MIGRATION = Path(__file__).parents[3] / "database/sql/040_precuration_lock_version.sql"


def _seed(s: Session) -> tuple[CurationNew, PrecurationNew]:
    user = s.scalars(select(UserNew)).first()
    scope = s.scalars(select(Scope)).first()
    pair = s.scalars(select(WorkflowPair)).first()
    schema = s.scalars(select(CurationSchema)).first()
    assert user and scope and pair and schema
    gene = Gene(
        id=uuid4(),
        hgnc_id="HGNC:998038",
        approved_symbol="LCK038",
        record_hash="1" * 64,
    )
    s.add(gene)
    s.flush()
    c = CurationNew(
        id=uuid4(),
        gene_id=gene.id,
        scope_id=scope.id,
        workflow_pair_id=pair.id,
        evidence_data={"n": uuid4().hex},
        created_by=user.id,
    )
    p = PrecurationNew(
        id=uuid4(),
        gene_id=gene.id,
        scope_id=scope.id,
        precuration_schema_id=schema.id,
        evidence_data={"n": uuid4().hex},
        created_by=user.id,
    )
    s.add_all([c, p])
    s.flush()
    return c, p


def test_each_save_bumps_the_version_once_and_a_stale_one_changes_nothing(
    owner_session: Session,
) -> None:
    c, p = _seed(owner_session)
    user = c.created_by

    first = curation_crud.save_draft(
        owner_session,
        db_obj=c,
        draft_data=CurationDraftSave(
            evidence_data={"a": 1}, lock_version=c.lock_version
        ),
        user_id=user,
    )
    assert (
        first is not None and first.lock_version == 1
    )  # trigger + explicit bump agree
    second = precuration_crud.save_draft(
        owner_session,
        db_obj=p,
        evidence_data={"a": 1},
        lock_version=p.lock_version,
        user_id=user,
    )
    assert second is not None and second.lock_version == 1
    third = precuration_crud.update_with_lock(
        owner_session, db_obj=p, evidence_data={"a": 2}, lock_version=1, user_id=user
    )
    assert third is not None and third.lock_version == 2

    stale = precuration_crud.save_draft(
        owner_session,
        db_obj=p,
        evidence_data={"a": "stale"},
        lock_version=0,
        user_id=user,
    )
    assert stale is None


def test_migration_040_is_idempotent_and_self_recording(owner_session: Session) -> None:
    sql = MIGRATION.read_text()
    owner_session.execute(text(sql))
    owner_session.execute(text(sql))
    assert (
        owner_session.execute(
            text(
                "SELECT count(*) FROM schema_migrations "
                "WHERE filename = '040_precuration_lock_version.sql'"
            )
        ).scalar_one()
        == 1
    )
    assert (
        owner_session.execute(
            text(
                "SELECT count(*) FROM pg_trigger WHERE tgrelid = 'precurations'::regclass "
                "AND tgname = 'trigger_increment_lock_version'"
            )
        ).scalar_one()
        == 1
    )
