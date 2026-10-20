"""Unit tests for app.crud.logs query construction and result shaping.

The log queries are async and use PostgreSQL SQL (date_trunc, partitions), and
aiosqlite is not installed, so the session is a mock. Statements are captured and
compiled with the PostgreSQL dialect to verify the filters that reach the database.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.crud import logs as crud_logs

pytestmark = pytest.mark.unit


def _session(*results: MagicMock) -> MagicMock:
    db = MagicMock()
    db.execute = AsyncMock(side_effect=list(results) if results else None)
    db.commit = AsyncMock()
    return db


def _rows(items: list[Any]) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    result.all.return_value = items
    return result


def _scalar(value: Any) -> MagicMock:
    result = MagicMock()
    result.scalar.return_value = value
    result.scalar_one_or_none.return_value = value
    return result


def _sql(db: MagicMock, call: int = 0) -> str:
    statement = db.execute.call_args_list[call].args[0]
    return str(
        statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


@pytest.mark.asyncio
async def test_get_logs_without_filters_orders_newest_first() -> None:
    db = _session(_rows(["row"]))

    rows = await crud_logs.get_logs(db, skip=10, limit=5)

    assert rows == ["row"]
    sql = _sql(db)
    assert "WHERE" not in sql
    assert "ORDER BY system_logs.timestamp DESC" in sql
    assert "LIMIT 5" in sql
    assert "OFFSET 10" in sql


@pytest.mark.asyncio
async def test_get_logs_applies_every_filter() -> None:
    db = _session(_rows([]))
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=1)

    await crud_logs.get_logs(
        db,
        level="ERROR",
        logger_name="api",
        message="timeout",
        request_id="req-9",
        method="POST",
        endpoint="/genes",
        start_date=start,
        end_date=end,
        min_duration_ms=250.0,
    )

    sql = _sql(db)
    assert "system_logs.level = 'ERROR'" in sql
    assert "ILIKE '%%api%%'" in sql
    assert "ILIKE '%%timeout%%'" in sql
    assert "system_logs.request_id = 'req-9'" in sql
    assert "system_logs.method = 'POST'" in sql
    assert "ILIKE '%%/genes%%'" in sql
    assert "system_logs.timestamp >= '2026-01-01" in sql
    assert "system_logs.timestamp <= '2026-01-02" in sql
    assert "system_logs.duration_ms >= 250.0" in sql


@pytest.mark.asyncio
async def test_get_logs_zero_duration_is_not_a_filter() -> None:
    db = _session(_rows([]))

    await crud_logs.get_logs(db, min_duration_ms=0)

    assert "WHERE" not in _sql(db)


@pytest.mark.asyncio
async def test_get_log_by_id_returns_single_row_or_none() -> None:
    db = _session(_scalar("entry"), _scalar(None))

    assert await crud_logs.get_log_by_id(db, log_id=3) == "entry"
    assert await crud_logs.get_log_by_id(db, log_id=4) is None
    assert "system_logs.id = 3" in _sql(db, 0)


@pytest.mark.asyncio
async def test_get_logs_by_request_id_is_chronological() -> None:
    db = _session(_rows(["first", "second"]))

    rows = await crud_logs.get_logs_by_request_id(db, request_id="abc")

    assert rows == ["first", "second"]
    sql = _sql(db)
    assert "system_logs.request_id = 'abc'" in sql
    assert "ORDER BY system_logs.timestamp ASC" in sql


@pytest.mark.asyncio
async def test_get_recent_errors_uses_error_levels_and_window() -> None:
    db = _session(_rows(["err"]))

    rows = await crud_logs.get_recent_errors(db, limit=7, hours=2)

    assert rows == ["err"]
    sql = _sql(db)
    assert "system_logs.level = 'ERROR'" in sql
    assert "system_logs.level = 'CRITICAL'" in sql
    assert "system_logs.timestamp >=" in sql
    assert "LIMIT 7" in sql


@pytest.mark.asyncio
async def test_get_logs_for_export_filters_and_limit() -> None:
    db = _session(_rows(["x"]))
    start = datetime(2026, 2, 1, tzinfo=UTC)

    rows = await crud_logs.get_logs_for_export(
        db, level="WARNING", start_date=start, limit=50
    )

    assert rows == ["x"]
    sql = _sql(db)
    assert "system_logs.level = 'WARNING'" in sql
    assert "system_logs.timestamp >= '2026-02-01" in sql
    assert "LIMIT 50" in sql


@pytest.mark.asyncio
async def test_cleanup_commits_and_reports_requested_retention() -> None:
    db = _session(MagicMock())

    result = await crud_logs.cleanup_old_partitions(db, days=30)

    db.commit.assert_awaited_once()
    assert "cleanup_old_logs" in _sql(db)
    assert result["status"] == "success"
    assert result["retention_days"] == 30


@pytest.mark.asyncio
async def test_statistics_assembles_counts_and_rates() -> None:
    total = _scalar(10)
    by_level = _rows([("ERROR", 2), ("INFO", 8)])
    by_hour = _rows([(datetime(2026, 1, 1, 12, tzinfo=UTC), 10), (None, 1)])
    avg = _scalar(4.5)
    slow = _rows([("/api/v1/genes", 9.0, 3)])
    error_count = _scalar(2)
    top_errors = _rows([("boom", 2, datetime(2026, 1, 1, tzinfo=UTC))])
    db = _session(total, by_level, by_hour, avg, slow, error_count, top_errors)

    stats = await crud_logs.get_log_statistics(db)

    assert stats["total_logs"] == 10
    assert stats["logs_by_level"] == {"ERROR": 2, "INFO": 8}
    assert stats["logs_by_hour"] == {"2026-01-01T12:00:00+00:00": 10, "unknown": 1}
    assert stats["avg_duration_ms"] == 4.5
    assert stats["slow_endpoints"] == [
        {"endpoint": "/api/v1/genes", "avg_duration_ms": 9.0, "count": 3}
    ]
    assert stats["error_rate"] == 0.2
    assert stats["top_errors"][0]["message"] == "boom"
    assert stats["top_errors"][0]["last_seen"] == "2026-01-01T00:00:00+00:00"


@pytest.mark.asyncio
async def test_statistics_handles_empty_database() -> None:
    db = _session(
        _scalar(0),
        _rows([]),
        _rows([]),
        _scalar(None),
        _rows([]),
        _scalar(0),
        _rows([]),
    )

    stats = await crud_logs.get_log_statistics(db)

    assert stats["total_logs"] == 0
    assert stats["error_rate"] == 0.0
    assert stats["avg_duration_ms"] is None
    assert stats["top_errors"] == []
