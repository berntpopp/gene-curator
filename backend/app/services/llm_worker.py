"""Background LLM run worker, started in the app lifespan (#489).

Claims queued runs with FOR UPDATE SKIP LOCKED (llm_claim_run(), 060), then works as the
run's creator: app.current_user_id is that user for every read and the final update, so
the run sees exactly what its requester may see. DB work runs in threads; requests never
wait on it. Prompt and output text are never logged.
"""

import asyncio
import os
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.core import database
from app.core.database import RLS_USER_KEY
from app.core.logging import get_logger
from app.llm.output import InvalidLLMOutputError
from app.llm.prompts import PromptTemplateError
from app.llm.providers import LLMProviderError, provider_registry
from app.llm.ssrf import UnsafeURLError
from app.models import CurationNew, UserNew
from app.models.llm import LLMRun
from app.services.llm_config import LLMCapError
from app.services.llm_runs import (
    PreparedCall,
    cost_cents,
    prepare_call,
    request_sha256,
    validate_output,
)

logger = get_logger(__name__)

POLL_S = 2.0
SHUTDOWN_S = 10.0
SessionFactory = Callable[[], Session]


def _session() -> Session:
    return Session(database.engine)


def claim(db: Session) -> tuple[UUID, UUID] | None:
    """Move one queued run to running; returns (run id, creator) or None."""
    if db.get_bind().dialect.name == "postgresql":
        row = db.execute(text("SELECT run_id, run_by FROM llm_claim_run()")).first()
        db.commit()
        return (row[0], row[1]) if row else None
    run = db.scalars(  # SQLite (tests): a single process, no row locks needed
        select(LLMRun)
        .where(LLMRun.status == "queued", LLMRun.created_by.isnot(None))
        .order_by(LLMRun.created_at)
        .limit(1)
    ).first()
    if run is None or run.created_by is None:
        return None
    run.status = "running"
    db.commit()
    return run.id, run.created_by


@dataclass
class Outcome:
    status: str = "failed"
    error_code: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost: Decimal = field(default_factory=lambda: Decimal(0))
    request_sha256: str | None = None


def _claim(factory: SessionFactory) -> tuple[UUID, UUID] | None:
    with factory() as db:
        return claim(db)


def _as_user(db: Session, user_id: UUID) -> Session:
    db.info[RLS_USER_KEY] = str(
        user_id
    )  # re-applied on every transaction (core.database)
    return db


def _prepare(factory: SessionFactory, run_id: UUID, user_id: UUID) -> PreparedCall:
    with factory() as db:
        _as_user(db, user_id)
        creator = db.get(UserNew, user_id)
        if creator is None or not creator.is_active:  # RLS helpers ignore is_active
            raise LLMCapError("user_inactive")
        run = db.get(LLMRun, run_id)
        curation = (
            db.get(CurationNew, run.curation_id) if run and run.curation_id else None
        )
        if run is None or curation is None:
            raise LLMCapError("curation_not_found")
        return prepare_call(db, curation, run.strategy, run)


def _finish(
    factory: SessionFactory, run_id: UUID, user_id: UUID, outcome: Outcome, ms: int
) -> None:
    with factory() as db:
        _as_user(db, user_id)
        db.execute(
            update(LLMRun)
            .where(LLMRun.id == run_id, LLMRun.status == "running")
            .values(
                status=outcome.status,
                error_code=outcome.error_code,
                input_tokens=outcome.input_tokens,
                output_tokens=outcome.output_tokens,
                cost_cents=outcome.cost,
                request_sha256=outcome.request_sha256,
                duration_ms=ms,
                finished_at=func.now(),
            )
            .execution_options(synchronize_session=False)
        )
        db.commit()


async def _call(prepared: PreparedCall, outcome: Outcome) -> None:
    outcome.request_sha256 = request_sha256(prepared.model.model_id, prepared.request)
    adapter = await provider_registry.acreate(prepared.kind, **prepared.config)
    response = await adapter.complete(prepared.request)
    outcome.input_tokens = response.input_tokens
    outcome.output_tokens = response.output_tokens
    outcome.cost = cost_cents(
        prepared.model, response.input_tokens, response.output_tokens
    )
    # Validated output is handed to the consumer (#464, #465); nothing partial is kept.
    validate_output(response.text, prepared.output_schema)
    outcome.status = "succeeded"


async def process_next(factory: SessionFactory = _session) -> bool:
    """Claim and run one queued run; False when nothing was queued."""
    claimed = await asyncio.to_thread(_claim, factory)
    if claimed is None:
        return False
    run_id, user_id = claimed
    started = time.monotonic()
    outcome = Outcome()
    try:
        prepared = await asyncio.to_thread(_prepare, factory, run_id, user_id)
        await _call(prepared, outcome)
    except (LLMProviderError, LLMCapError) as exc:
        outcome.error_code = exc.code
    except InvalidLLMOutputError:
        outcome.error_code = "invalid_output"
    except (HTTPException, UnsafeURLError, PromptTemplateError) as exc:
        outcome.error_code = "config_error"
        logger.warning(
            "LLM run misconfigured", run_id=str(run_id), error_type=type(exc).__name__
        )
    except asyncio.CancelledError:
        outcome.error_code = "interrupted"
        _finish(factory, run_id, user_id, outcome, _ms(started))
        raise
    except Exception as exc:  # never let one run stop the worker
        outcome.error_code = "internal_error"
        logger.error(
            "LLM run crashed", run_id=str(run_id), error_type=type(exc).__name__
        )
    await asyncio.to_thread(_finish, factory, run_id, user_id, outcome, _ms(started))
    logger.info(
        "LLM run finished",
        run_id=str(run_id),
        status=outcome.status,
        error_code=outcome.error_code,
    )
    return True


def _ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


async def run_worker(stop: asyncio.Event, factory: SessionFactory = _session) -> None:
    while not stop.is_set():
        try:
            busy = await process_next(factory)
        except Exception as exc:  # e.g. database unreachable: back off and retry
            logger.warning("LLM worker poll failed", error_type=type(exc).__name__)
            busy = False
        if not busy:
            with suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), POLL_S)


@asynccontextmanager
async def worker_running() -> AsyncIterator[None]:
    """Run the worker for the app's lifetime; shutdown waits at most SHUTDOWN_S.

    ponytail: off under pytest (PYTEST_CURRENT_TEST) so test clients never claim runs;
    replace with a settings flag in core/config.py.
    """
    if "PYTEST_CURRENT_TEST" in os.environ:
        yield
        return
    stop = asyncio.Event()
    task = asyncio.create_task(run_worker(stop))
    try:
        yield
    finally:
        stop.set()
        with suppress(TimeoutError):
            await asyncio.wait_for(task, SHUTDOWN_S)  # cancels the task on timeout
