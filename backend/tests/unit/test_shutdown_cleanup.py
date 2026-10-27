"""Shutdown waits for log writes and closes async connections (#380)."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app import main
from app.core.logging.database_logger import DatabaseLogger
from app.main import app

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_logger_flush_awaits_pending_writes() -> None:
    logger = DatabaseLogger()
    done = asyncio.Event()

    async def write() -> None:
        await asyncio.sleep(0)
        done.set()

    logger._pending_tasks.add(asyncio.create_task(write()))
    await logger.flush()
    assert done.is_set()


def test_shutdown_disposes_the_async_engine(monkeypatch: MonkeyPatch) -> None:
    engine = AsyncMock()
    monkeypatch.setattr(main, "async_engine", engine)
    with TestClient(app):
        engine.dispose.assert_not_awaited()
    engine.dispose.assert_awaited_once()
