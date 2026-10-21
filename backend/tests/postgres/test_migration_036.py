"""Migration 036: terminal 'archived' workflow_stage, rebuilt in one transaction (#323)."""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.models import (
    CurationNew,
    CurationStatus,
    Gene,
    Scope,
    UserNew,
    WorkflowPair,
    WorkflowStage,
)

pytestmark = pytest.mark.postgres

MIGRATION = Path(__file__).parents[3] / "database/sql/036_archived_workflow_stage.sql"
LABELS = "SELECT enum_range(NULL::workflow_stage)::text"


def _downgrade_to_legacy(db: Session) -> None:
    """Recreate the pre-036 enum (no 'archived') exactly as 001 built it."""
    view = db.scalar(
        text("SELECT pg_get_viewdef('review_compliance_dashboard'::regclass, true)")
    )
    db.execute(text("DROP VIEW review_compliance_dashboard"))
    db.execute(text("DROP INDEX idx_curations_gene_public"))
    db.execute(text("ALTER TYPE workflow_stage RENAME TO workflow_stage_new"))
    db.execute(
        text(
            "CREATE TYPE workflow_stage AS ENUM ('entry','precuration','curation','review','active')"
        )
    )
    for table, default in (
        ("precurations", "precuration"),
        ("curations", "curation"),
        ("audit_log", None),
    ):
        db.execute(
            text(f"ALTER TABLE {table} ALTER COLUMN workflow_stage DROP DEFAULT")
        )
        db.execute(
            text(
                f"ALTER TABLE {table} ALTER COLUMN workflow_stage TYPE workflow_stage "
                "USING workflow_stage::text::workflow_stage"
            )
        )
        if default:
            db.execute(
                text(
                    f"ALTER TABLE {table} ALTER COLUMN workflow_stage SET DEFAULT '{default}'"
                )
            )
    db.execute(text("DROP TYPE workflow_stage_new"))
    db.execute(
        text(
            f"CREATE VIEW review_compliance_dashboard WITH (security_invoker = true) AS {view}"
        )
    )
    db.execute(
        text(
            "CREATE INDEX idx_curations_gene_public ON curations(gene_id, scope_id) "
            "INCLUDE (computed_verdict, computed_scores, workflow_stage) WHERE workflow_stage = 'active'"
        )
    )
    db.execute(
        text(
            "DELETE FROM schema_migrations WHERE filename = '036_archived_workflow_stage.sql'"
        )
    )


def test_fresh_database_has_archived_and_rerun_is_noop(owner_session: Session) -> None:
    before = owner_session.scalar(text(LABELS))
    assert before == "{entry,precuration,curation,review,active,archived}"
    owner_session.execute(text(MIGRATION.read_text()))
    assert owner_session.scalar(text(LABELS)) == before
    assert (
        owner_session.scalar(
            text(
                "SELECT count(*) FROM schema_migrations WHERE filename = '036_archived_workflow_stage.sql'"
            )
        )
        == 1
    )


def test_upgrade_backfills_archived_rows_in_one_transaction(
    owner_session: Session,
) -> None:
    scope = owner_session.scalars(select(Scope)).first()
    user = owner_session.scalars(select(UserNew)).first()
    pair = owner_session.scalars(select(WorkflowPair)).first()
    assert scope and user and pair
    gene = Gene(
        id=uuid4(),
        hgnc_id="HGNC:999036",
        approved_symbol="ARC036",
        record_hash="3" * 64,
    )
    owner_session.add(gene)
    owner_session.flush()
    _downgrade_to_legacy(owner_session)

    def new(status: str) -> str:
        cid = uuid4()
        owner_session.execute(
            text(
                "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, status, "
                "workflow_stage, evidence_data, created_by) VALUES (:i, :g, :s, :p, "
                "CAST(:st AS curation_status), 'active', CAST(:ev AS jsonb), :u)"
            ),
            {
                "i": cid,
                "g": gene.id,
                "s": scope.id,
                "p": pair.id,
                "st": status,
                "ev": f'{{"n": "{cid}"}}',
                "u": user.id,
            },
        )
        return str(cid)

    archived, live = new("archived"), new("active")
    assert (
        owner_session.scalar(text(LABELS))
        == "{entry,precuration,curation,review,active}"
    )

    owner_session.execute(text(MIGRATION.read_text()))  # same transaction as the ADD

    stages = dict(
        owner_session.execute(
            text(
                "SELECT id::text, workflow_stage::text FROM curations WHERE id::text = ANY(:ids)"
            ),
            {"ids": [archived, live]},
        ).all()
    )
    assert stages == {archived: "archived", live: "active"}
    assert (
        owner_session.scalar(text("SELECT count(*) FROM review_compliance_dashboard"))
        is not None
    )
    assert (
        owner_session.scalar(
            text(
                "SELECT count(*) FROM pg_indexes WHERE indexname = 'idx_curations_gene_public'"
            )
        )
        == 1
    )
    # Same session keeps working through the audit trigger (plpgsql plan cache refreshed).
    owner_session.execute(
        text("UPDATE curations SET updated_by = :u WHERE id = :i"),
        {"u": user.id, "i": live},
    )
    row = owner_session.get(CurationNew, archived)
    assert row is not None and row.workflow_stage == WorkflowStage.ARCHIVED
    assert row.status == CurationStatus.ARCHIVED
