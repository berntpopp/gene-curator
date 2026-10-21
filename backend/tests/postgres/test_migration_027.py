"""Migration 027: partial unique index, log retention function, default log partition."""

from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.crud.schema_repository import schema_crud

pytestmark = pytest.mark.postgres


def _partitions(session: Session) -> set[str]:
    return set(
        session.execute(
            text("SELECT tablename FROM pg_tables WHERE tablename LIKE 'system_logs_%'")
        )
        .scalars()
        .all()
    )


def test_active_curations_unique_only_among_non_archived(
    owner_session: Session,
) -> None:
    indexdef = owner_session.execute(
        text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE indexname = 'uq_active_curation_gene_scope_current'"
        )
    ).scalar_one()
    assert "UNIQUE" in indexdef
    assert "archived_at IS NULL" in indexdef
    unique_constraints = owner_session.execute(
        text(
            "SELECT count(*) FROM pg_constraint "
            "WHERE conrelid = 'active_curations'::regclass AND contype = 'u'"
        )
    ).scalar_one()
    assert unique_constraints == 0


def test_cleanup_old_logs_signature_and_drops_only_expired_months(
    owner_session: Session,
) -> None:
    args = (
        owner_session.execute(
            text(
                "SELECT pg_get_function_arguments(oid) FROM pg_proc "
                "WHERE proname = 'cleanup_old_logs'"
            )
        )
        .scalars()
        .all()
    )
    assert args == ["retention_days integer DEFAULT 90"]

    # A month that ended ~45 days ago is inside a 90-day window, outside a 30-day one.
    recent_start = (date.today() - timedelta(days=45)).replace(day=1)
    recent_end = (recent_start + timedelta(days=32)).replace(day=1)
    recent = recent_start.strftime("system_logs_%Y_%m")
    if recent not in _partitions(owner_session):
        owner_session.execute(
            text(
                f"CREATE TABLE {recent} PARTITION OF system_logs "
                f"FOR VALUES FROM ('{recent_start}') TO ('{recent_end}')"
            )
        )
    owner_session.execute(
        text(
            "CREATE TABLE system_logs_2020_01 PARTITION OF system_logs "
            "FOR VALUES FROM ('2020-01-01') TO ('2020-02-01')"
        )
    )

    owner_session.execute(text("SELECT cleanup_old_logs(365)"))
    assert "system_logs_2020_01" not in _partitions(owner_session)
    assert recent in _partitions(owner_session)
    assert "system_logs_default" in _partitions(owner_session)

    owner_session.execute(text("SELECT cleanup_old_logs(1)"))
    assert recent not in _partitions(owner_session)
    assert "system_logs_default" in _partitions(owner_session)


def test_log_row_for_date_without_monthly_partition_is_accepted(
    owner_session: Session,
) -> None:
    owner_session.execute(
        text(
            "INSERT INTO system_logs (timestamp, level, logger, message) "
            "VALUES (NOW() + INTERVAL '30 years', 'INFO', 't', 'm')"
        )
    )


def test_curation_schema_listing_works_on_fresh_database(
    owner_session: Session,
) -> None:
    schema_crud.get_multi(owner_session, active_only=False)
