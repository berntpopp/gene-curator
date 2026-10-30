"""Migration 034 + activation keep exactly one active curation per gene+scope."""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.crud.workflow_engine import workflow_engine
from app.models.models import (
    CurationNew,
    CurationStatus,
    Gene,
    Scope,
    UserNew,
    WorkflowPair,
)

pytestmark = pytest.mark.postgres

MIGRATION = Path(__file__).parents[3] / "database/sql/034_single_active_curation.sql"


def test_activation_and_repair(owner_session: Session) -> None:
    scope = owner_session.scalars(select(Scope)).first()
    user = owner_session.scalars(select(UserNew)).first()
    pair = owner_session.scalars(select(WorkflowPair)).first()
    assert scope and user and pair
    gene = Gene(
        id=uuid4(),
        hgnc_id="HGNC:999034",
        approved_symbol="ACT034",
        record_hash="0" * 64,
    )
    owner_session.add(gene)
    owner_session.flush()

    def new() -> CurationNew:
        c = CurationNew(
            id=uuid4(),
            gene_id=gene.id,
            scope_id=scope.id,
            workflow_pair_id=pair.id,
            workflow_stage="review",
            status=CurationStatus.APPROVED,
            evidence_data={"n": uuid4().hex},
            created_by=user.id,
        )
        owner_session.add(c)
        owner_session.flush()
        return c

    # One open curation per entity (067): the second opens after the first
    first = new()
    workflow_engine._transition_to_active(owner_session, first, user.id, None, None)
    second = new()
    workflow_engine._transition_to_active(owner_session, second, user.id, None, None)
    owner_session.refresh(first)
    assert first.status == CurationStatus.ARCHIVED
    assert second.status == CurationStatus.ACTIVE and second.approved_at is not None

    # Legacy damage: an older curation left at 'active' next to the live one.
    owner_session.execute(text("DROP INDEX IF EXISTS uq_curations_one_active"))
    first.status = CurationStatus.ACTIVE
    owner_session.flush()
    for _ in range(2):
        owner_session.execute(text(MIGRATION.read_text()))
    owner_session.refresh(first)
    owner_session.refresh(second)
    assert first.status == CurationStatus.ARCHIVED
    assert second.status == CurationStatus.ACTIVE
    assert owner_session.scalar(
        text(
            "SELECT count(*) FROM pg_indexes WHERE indexname='uq_curations_one_active'"
        )
    )


MIGRATION_067 = MIGRATION.with_name("067_split_disease_entities.sql")


def _index(session: Session, name: str) -> str | None:
    return session.scalar(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = :n"), {"n": name}
    )


def test_067_on_fresh_and_legacy_data(owner_session: Session) -> None:
    """Fresh: every index is keyed on the entity. Legacy (pre-067 schema, one curation per
    gene): existing rows keep '' and satisfy the re-keyed indexes; reruns are no-ops."""
    for name in (
        "uq_curations_one_active",
        "uq_curations_one_open",
        "uq_active_curation_gene_scope_current",
        "uq_precurations_open_draft",
    ):
        assert "entity_key" in (_index(owner_session, name) or ""), name

    # Back to the pre-067 schema
    owner_session.execute(
        text(
            "DROP INDEX uq_curations_one_open; "
            "DROP INDEX uq_precurations_open_draft; "
            "ALTER TABLE precurations DROP COLUMN entity_key; "
            "ALTER TABLE curations DROP COLUMN entity_key; "
            "ALTER TABLE active_curations DROP COLUMN entity_key; "
            "CREATE UNIQUE INDEX uq_precurations_open_draft "
            "ON precurations (gene_id, scope_id, created_by) WHERE status = 'draft'"
        )
    )
    scope = owner_session.scalars(select(Scope)).first()
    user = owner_session.scalars(select(UserNew)).first()
    pair = owner_session.scalars(select(WorkflowPair)).first()
    assert scope and user and pair and pair.precuration_schema_id
    gene = uuid4()
    owner_session.execute(
        text(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (:g, 'HGNC:999067', 'LEG067', :h)"
        ),
        {"g": gene, "h": "1" * 64},
    )
    pre = owner_session.scalar(
        text(
            "INSERT INTO precurations (gene_id, scope_id, precuration_schema_id, "
            "status, evidence_data, created_by) VALUES (:g, :s, :ps, 'approved', :e, :u) "
            "RETURNING id"
        ),
        {
            "g": gene,
            "s": scope.id,
            "ps": pair.precuration_schema_id,
            "e": '{"entity_definition": {"mondo_id": "mondo:0000009", '
            '"mode_of_inheritance": "Autosomal recessive inheritance"}}',
            "u": user.id,
        },
    )
    # The active curation links the precuration; the open draft links none
    ids = {}
    for status, link in (("active", pre), ("draft", None)):
        ids[status] = owner_session.scalar(
            text(
                "INSERT INTO curations (gene_id, scope_id, workflow_pair_id, status, "
                "workflow_stage, evidence_data, created_by, precuration_id) VALUES "
                "(:g, :s, :p, CAST(:st AS curation_status), 'curation', :e, :u, :pre) "
                "RETURNING id"
            ),
            {
                "g": gene,
                "s": scope.id,
                "p": pair.id,
                "st": status,
                "e": f'{{"n": "{status}"}}',
                "u": user.id,
                "pre": link,
            },
        )
    owner_session.execute(
        text(
            "INSERT INTO active_curations (gene_id, scope_id, curation_id) "
            "VALUES (:g, :s, :c)"
        ),
        {"g": gene, "s": scope.id, "c": ids["active"]},
    )

    for _ in range(2):
        owner_session.execute(text(MIGRATION_067.read_text()))

    def key(sql: str, row: object) -> object:
        return owner_session.scalar(text(sql), {"i": row})

    entity = "MONDO:0000009|AR"
    assert key("SELECT entity_key FROM precurations WHERE id = :i", pre) == entity
    # Backfilled from the linked precuration; '' only without one
    assert (
        key("SELECT entity_key FROM curations WHERE id = :i", ids["active"]) == entity
    )
    assert key("SELECT entity_key FROM curations WHERE id = :i", ids["draft"]) == ""
    assert (
        key(
            "SELECT entity_key FROM active_curations WHERE curation_id = :i",
            ids["active"],
        )
        == entity
    )
    assert "entity_key" in (_index(owner_session, "uq_curations_one_open") or "")
