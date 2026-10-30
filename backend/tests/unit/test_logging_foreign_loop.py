"""DB log writes must stay on the loop that owns the async engine (#segfault in save_draft)."""

import asyncio
import threading
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from app.core.logging import bind_context, clear_context, unified_logger as ul
from app.core.logging.database_logger import DatabaseLogger
from app.core.logging.unified_logger import UnifiedLogger


class RecordingDbLogger:
    """Records the loop and thread each write runs on."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, str, str, dict[str, Any]]] = []
        self.done = threading.Event()

    async def log(self, *, message: str, extra_data: dict[str, Any], **_: Any) -> None:
        loop_id = id(asyncio.get_running_loop())
        self.calls.append(
            (loop_id, threading.current_thread().name, message, extra_data)
        )
        self.done.set()


def _logger(db: RecordingDbLogger, console: MagicMock | None = None) -> UnifiedLogger:
    return UnifiedLogger(
        "test.foreign",
        console_logger=console or MagicMock(),
        database_logger=cast(DatabaseLogger, db),
    )


@pytest.mark.asyncio
async def test_write_from_temporary_loop_runs_on_main_loop() -> None:
    db = RecordingDbLogger()
    log = _logger(db)
    main_loop = asyncio.get_running_loop()
    log.info("startup")  # main thread + running loop: remembered as the engine's loop
    await asyncio.sleep(0)
    db.calls.clear()
    db.done.clear()
    foreign_tasks: list[int] = []

    async def fetch() -> None:
        bind_context(request_id="req-1")
        log.info("Publication fetched", pmid="1")
        foreign_tasks.append(len(asyncio.all_tasks()) - 1)  # minus fetch itself
        clear_context()

    # sync endpoint -> lookup_pmids -> asyncio.run in a worker thread
    await asyncio.to_thread(lambda: asyncio.run(fetch()))
    for _ in range(50):
        if db.done.is_set():
            break
        await asyncio.sleep(0.01)

    assert foreign_tasks == [0]
    assert len(db.calls) == 1
    loop_id, thread_name, message, extra = db.calls[0]
    assert loop_id == id(main_loop)
    assert thread_name == threading.main_thread().name
    assert message == "Publication fetched"
    assert extra["request_id"] == "req-1"
    assert extra["pmid"] == "1"


def test_write_from_temporary_loop_skipped_without_live_main_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ul, "_main_loop", None)
    db = RecordingDbLogger()
    console = MagicMock()
    log = _logger(db, console)
    foreign_tasks: list[int] = []

    async def fetch() -> None:
        log.info("Publication fetched")
        foreign_tasks.append(len(asyncio.all_tasks()) - 1)

    worker = threading.Thread(target=lambda: asyncio.run(fetch()))
    worker.start()
    worker.join()

    assert foreign_tasks == [0]
    assert db.calls == []
    console.info.assert_called_once()
