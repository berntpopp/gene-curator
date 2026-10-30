"""Concurrent enqueues by a REVIEWER serialize on real PostgreSQL as app_user (#530 B2).

Reviewers may not UPDATE scope_llm_settings, so RLS filtered their FOR UPDATE lock to no
rows: two second views both queued and both passed the cost caps.
"""

import threading
import time
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.models.llm import LLMRun
from app.services import llm_runs
from app.services.llm_config import LLMCapError
from app.services.llm_runs import enqueue_run
from tests.postgres.test_llm_runs_worker import (
    W,
    _as,
    _exec,
    _user,
    w,  # noqa: F401  (fixture)
)

pytestmark = pytest.mark.postgres


@pytest.fixture
def reviewer(w: W) -> Generator[UUID, None, None]:  # noqa: F811
    uid = uuid4()
    _exec(
        "INSERT INTO users (id, email, hashed_password, name, role) "
        "VALUES (%s, %s, 'x', 'rv', 'user')",
        str(uid),
        f"rvl-{str(w.scope)[:8]}@run.org",
    )
    _exec(
        "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
        "accepted_at) VALUES (%s, %s, 'reviewer', %s, now())",
        str(w.scope),
        str(uid),
        str(w.scope_admin),
    )
    yield uid
    _exec("DELETE FROM llm_runs WHERE scope_id = %s", str(w.scope))
    _exec("DELETE FROM audit_log WHERE user_id = %s", str(uid))
    _exec("DELETE FROM scope_memberships WHERE user_id = %s", str(uid))
    _exec("DELETE FROM users WHERE id = %s", str(uid))


def _race(
    w: W,  # noqa: F811
    uid: UUID,
    monkeypatch: pytest.MonkeyPatch,
    exclusive: bool,
) -> list[Any]:
    first_checked = threading.Event()
    reserve = llm_runs._reserve

    def slow_reserve(*args: Any) -> None:
        reserve(*args)
        if not first_checked.is_set():
            first_checked.set()
            time.sleep(1.0)  # the second enqueue starts while the first holds the lock

    monkeypatch.setattr(llm_runs, "_reserve", slow_reserve)

    def view() -> UUID:
        with _as(uid) as db:
            return enqueue_run(
                db, _user(db, uid), w.curation, "skeptic", exclusive=exclusive
            ).id

    def second() -> UUID:
        assert first_checked.wait(15)
        return view()

    outcomes: list[Any] = []
    with ThreadPoolExecutor(2) as pool:
        for f in [pool.submit(view), pool.submit(second)]:
            try:
                outcomes.append(f.result())
            except LLMCapError as exc:
                outcomes.append(exc.code)
    with _as(uid) as db:
        runs = db.scalars(select(LLMRun).where(LLMRun.scope_id == w.scope)).all()
        assert len(runs) == 1, outcomes
    return outcomes


def test_reviewer_second_views_queue_once(
    w: W,  # noqa: F811
    reviewer: UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _exec(
        "UPDATE scope_llm_settings SET daily_run_cap = 10 WHERE scope_id = %s",
        str(w.scope),
    )
    assert _race(w, reviewer, monkeypatch, True).count("already_pending") == 1


def test_reviewer_enqueues_cannot_both_pass_a_cap(
    w: W,  # noqa: F811
    reviewer: UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # room for one worst-case run (max_tokens 100), not two
    _exec(
        "UPDATE scope_llm_settings SET daily_run_cap = 10, monthly_token_cap = 150 "
        "WHERE scope_id = %s",
        str(w.scope),
    )
    outcomes = _race(w, reviewer, monkeypatch, False)
    assert outcomes.count("monthly_token_cap") == 1, outcomes
