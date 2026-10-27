"""LLM run worker (#489): records usage, fails closed, never logs prompt or output text."""

import asyncio
import logging
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.llm.providers import LLMProviderError, LLMRequest, LLMResponse, MockProvider
from app.models.llm import LLMRun
from app.services import llm_worker
from app.services.llm_runs import enqueue_run
from tests.api.llm_api_support import llm_env  # noqa: F401
from tests.services.llm_run_support import (
    GOOD,
    World,
    canned,
    factory,
    world_fixture,  # noqa: F401
)

pytestmark = [pytest.mark.unit, pytest.mark.usefixtures("llm_env")]


def _queued(db: Session, w: World) -> LLMRun:
    return enqueue_run(db, w.scope_admin, w.curation.id, "skeptic")


async def _process(db: Session) -> bool:
    return await llm_worker.process_next(factory(db.get_bind()))  # type: ignore[arg-type]


def _reloaded(db: Session, run: LLMRun) -> LLMRun:
    db.expire_all()
    found = db.get(LLMRun, run.id)
    assert found is not None
    return found


@pytest.mark.asyncio
async def test_success_records_usage_cost_hash_and_duration(
    db_session: Session,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    canned(monkeypatch, GOOD)
    run = _queued(db_session, world)

    assert await _process(db_session) is True

    done = _reloaded(db_session, run)
    assert (done.status, done.error_code) == ("succeeded", None)
    assert done.input_tokens > 0 and done.output_tokens == len(GOOD.split())
    expected = (
        done.input_tokens * world.model.input_price_per_mtok_cents
        + done.output_tokens * world.model.output_price_per_mtok_cents
    ) / 1_000_000
    assert done.cost_cents == expected.quantize(done.cost_cents)
    assert done.request_sha256 and len(done.request_sha256) == 64
    assert done.duration_ms is not None and done.finished_at is not None
    assert "LLM run finished" in caplog.text  # the capture works
    for text in ("Review BRCA1", "segregates", "Strong evidence", "supported"):
        assert text not in caplog.text
    assert await _process(db_session) is False  # nothing queued


@pytest.mark.asyncio
async def test_invalid_output_fails_but_counts_tokens(
    db_session: Session, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    canned(monkeypatch, '{"verdict": "maybe"}')
    run = _queued(db_session, world)
    await _process(db_session)
    done = _reloaded(db_session, run)
    assert (done.status, done.error_code) == ("failed", "invalid_output")
    assert done.output_tokens > 0 and done.cost_cents > 0


class _Down(MockProvider):
    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise LLMProviderError("http_error", 503)


class _Broken(MockProvider):
    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise RuntimeError("boom")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("setup", "code"),
    [
        ("provider_down", "http_error"),
        ("crash", "internal_error"),
        ("opted_out", "llm_disabled"),
        ("unpublished", "prompt_not_published"),
        ("no_key", "config_error"),
        ("creator_deactivated", "user_inactive"),
    ],
)
async def test_failures_are_recorded_with_a_code(
    db_session: Session,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    setup: str,
    code: str,
) -> None:
    from app.llm.providers import provider_registry

    run = _queued(db_session, world)
    if setup == "provider_down":
        monkeypatch.setitem(provider_registry._providers, "mock", _Down)
    elif setup == "crash":
        monkeypatch.setitem(provider_registry._providers, "mock", _Broken)
    elif setup == "opted_out":
        world.settings.enabled = False
    elif setup == "unpublished":
        world.version.published_at = None
    elif setup == "creator_deactivated":
        world.scope_admin.is_active = False
    else:
        world.provider.kind = "anthropic"  # needs a key; none stored
    db_session.commit()

    await _process(db_session)

    done = _reloaded(db_session, run)
    assert (done.status, done.error_code) == ("failed", code)


@pytest.mark.asyncio
async def test_cancelled_run_is_marked_interrupted(
    db_session: Session, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Hang(MockProvider):
        async def complete(self, request: LLMRequest) -> LLMResponse:
            await asyncio.sleep(60)
            raise AssertionError("unreachable")

    from app.llm.providers import provider_registry

    monkeypatch.setitem(provider_registry._providers, "mock", _Hang)
    run = _queued(db_session, world)
    task = asyncio.create_task(_process(db_session))
    for _ in range(200):
        await asyncio.sleep(0.01)
        if _reloaded(db_session, run).status == "running":
            break
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert _reloaded(db_session, run).error_code == "interrupted"


@pytest.mark.asyncio
async def test_loop_survives_errors_and_stops(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    stop = asyncio.Event()

    async def flaky(_: Any = None) -> bool:
        calls.append(1)
        if len(calls) == 1:
            raise OSError("db down")
        stop.set()
        return False

    monkeypatch.setattr(llm_worker, "process_next", flaky)
    monkeypatch.setattr(llm_worker, "POLL_S", 0.01)
    await asyncio.wait_for(llm_worker.run_worker(stop), 5)
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_lifespan_starts_and_stops_the_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = asyncio.Event()

    async def fake(stop: asyncio.Event) -> None:
        started.set()
        await stop.wait()

    monkeypatch.setattr(llm_worker, "run_worker", fake)
    async with llm_worker.worker_running():
        assert not started.is_set()  # off under pytest
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    async with llm_worker.worker_running():
        await asyncio.wait_for(started.wait(), 5)
