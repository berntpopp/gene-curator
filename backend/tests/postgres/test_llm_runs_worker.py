"""LLM run worker on real PostgreSQL as app_user (060, #489).

Two workers claim each queued run once, concurrent enqueues cannot both pass a cap, the
worker finishes a run under its creator's RLS context, and non-members cannot read runs.
"""

import asyncio
import json
import os
import threading
import time
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core import database
from app.core.database import RLS_USER_KEY
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import UserNew
from app.models.llm import LLMRun
from app.services import llm_runs, llm_worker
from app.services.llm_config import LLMCapError
from app.services.llm_runs import enqueue_run
from tests.services.llm_run_support import GOOD, SCHEMA, canned

pytestmark = pytest.mark.postgres


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@dataclass
class W:
    scope_admin: UUID = field(default_factory=uuid4)
    curator: UUID = field(default_factory=uuid4)
    outsider: UUID = field(default_factory=uuid4)
    scope: UUID = field(default_factory=uuid4)
    gene: UUID = field(default_factory=uuid4)
    pair: UUID = field(default_factory=uuid4)
    curation: UUID = field(default_factory=uuid4)
    provider: UUID = field(default_factory=uuid4)
    model: UUID = field(default_factory=uuid4)
    template: UUID = field(default_factory=uuid4)
    version: UUID = field(default_factory=uuid4)


def _exec(sql: str, *args: Any) -> None:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(sql, args)


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.scope)[:8]
    with _owner() as conn, conn.cursor() as cur:
        for uid, name in (
            (x.scope_admin, "sa"),
            (x.curator, "cu"),
            (x.outsider, "out"),
        ):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, 'user')",
                (str(uid), f"{name}-{tag}@run.org", get_password_hash("pw"), name),
            )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, 'Runs', false, %s)",
            (str(x.scope), f"runs-{x.scope}", str(x.scope_admin)),
        )
        for uid, role in ((x.scope_admin, "admin"), (x.curator, "curator")):
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, %s, %s, now())",
                (str(x.scope), str(uid), role, str(x.scope_admin)),
            )
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (%s, %s, %s, %s)",
            (str(x.gene), f"HGNC:{x.gene.int % 10**9}", f"RUN{tag}", x.gene.hex * 2),
        )
        cur.execute(
            "INSERT INTO workflow_pairs (id, name, version, precuration_schema_id, "
            "curation_schema_id) SELECT %s, %s, '1', precuration_schema_id, "
            "curation_schema_id FROM workflow_pairs WHERE is_active LIMIT 1",
            (str(x.pair), f"runs-{tag}"),
        )
        cur.execute(
            "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, status, "
            "workflow_stage, created_by, evidence_data) "
            "VALUES (%s, %s, %s, %s, 'draft', 'curation', %s, %s)",
            (
                str(x.curation),
                str(x.gene),
                str(x.scope),
                str(x.pair),
                str(x.curator),
                json.dumps({"disease_name": "d", "curator_email": "x@run.org"}),
            ),
        )
        cur.execute(
            "INSERT INTO llm_providers (id, name, kind, base_url) "
            "VALUES (%s, %s, 'mock', 'mock://')",
            (str(x.provider), f"{tag}-p"),
        )
        cur.execute(
            "INSERT INTO llm_models (id, provider_id, model_id, "
            "input_price_per_mtok_cents, output_price_per_mtok_cents, max_tokens) "
            "VALUES (%s, %s, 'mock-model', 100, 300, 100)",
            (str(x.model), str(x.provider)),
        )
        cur.execute(
            "INSERT INTO prompt_templates (id, key, strategy) "
            "VALUES (%s, %s, 'skeptic')",
            (str(x.template), f"{tag}-t"),
        )
        cur.execute(
            "INSERT INTO prompt_template_versions (id, template_id, version, "
            "system_text, user_text, output_schema, sha256, published_at) "
            "VALUES (%s, %s, 1, 'Review {gene_symbol}.', '{curation_data}', %s, "
            "'abc', now())",
            (str(x.version), str(x.template), json.dumps(SCHEMA)),
        )
        cur.execute(
            "INSERT INTO scope_llm_settings (scope_id, enabled, model_id, "
            "skeptic_prompt_version_id, monthly_token_cap, monthly_cost_cap_cents, "
            "daily_run_cap) VALUES (%s, true, %s, %s, 100000, 1000, 1)",
            (str(x.scope), str(x.model), str(x.version)),
        )
    yield x
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(x.scope),))
        cur.execute("DELETE FROM prompt_templates WHERE id = %s", (str(x.template),))
        cur.execute("DELETE FROM llm_providers WHERE id = %s", (str(x.provider),))
        cur.execute("DELETE FROM audit_log WHERE workflow_pair_id = %s", (str(x.pair),))
        cur.execute("DELETE FROM workflow_pairs WHERE id = %s", (str(x.pair),))
        cur.execute("DELETE FROM genes WHERE id = %s", (str(x.gene),))
        users = (str(x.scope_admin), str(x.curator), str(x.outsider))
        cur.execute("DELETE FROM audit_log WHERE user_id IN %s", (users,))
        cur.execute("DELETE FROM users WHERE id IN %s", (users,))


def _as(uid: UUID) -> Session:
    db = Session(database.engine)
    db.info[RLS_USER_KEY] = str(uid)
    return db


def _user(db: Session, uid: UUID) -> UserNew:
    user = db.get(UserNew, uid)
    assert user is not None
    return user


def _enqueue(uid: UUID, curation: UUID) -> UUID:
    with _as(uid) as db:
        return enqueue_run(db, _user(db, uid), curation, "skeptic").id


def test_two_workers_claim_each_run_once(w: W) -> None:
    ids = [uuid4() for _ in range(8)]
    for rid in ids:
        _exec(
            "INSERT INTO llm_runs (id, curation_id, scope_id, strategy, model_id, "
            "created_by) VALUES (%s, %s, %s, 'skeptic', 'mock-model', %s)",
            str(rid),
            str(w.curation),
            str(w.scope),
            str(w.scope_admin),
        )
    barrier = threading.Barrier(2, timeout=15)

    def drain() -> list[UUID]:
        got = []
        with Session(database.engine) as db:  # the worker has no user of its own
            barrier.wait()
            while (claimed := llm_worker.claim(db)) is not None:
                got.append(claimed[0])
                assert claimed[1] == w.scope_admin
        return got

    with ThreadPoolExecutor(2) as pool:
        claimed = [
            rid for f in [pool.submit(drain), pool.submit(drain)] for rid in f.result()
        ]

    mine = [rid for rid in claimed if rid in ids]
    assert sorted(mine) == sorted(ids)  # every run claimed, none twice
    with _as(w.scope_admin) as db:
        statuses = db.scalars(select(LLMRun.status).where(LLMRun.scope_id == w.scope))
        assert set(statuses) == {"running"}


def test_concurrent_enqueues_cannot_both_pass_the_daily_cap(
    w: W, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_checked = threading.Event()
    reserve = llm_runs._reserve

    def slow_reserve(*args: Any) -> None:
        reserve(*args)
        if not first_checked.is_set():
            first_checked.set()
            time.sleep(
                1.0
            )  # the second enqueue starts while the first still holds the lock

    monkeypatch.setattr(llm_runs, "_reserve", slow_reserve)

    def second() -> UUID:
        assert first_checked.wait(15)
        return _enqueue(w.scope_admin, w.curation)

    with ThreadPoolExecutor(2) as pool:
        futures = [
            pool.submit(_enqueue, w.scope_admin, w.curation),
            pool.submit(second),
        ]
        outcomes: list[Any] = []
        for f in futures:
            try:
                outcomes.append(f.result())
            except LLMCapError as exc:
                outcomes.append(exc.code)

    assert outcomes.count("daily_run_cap") == 1, outcomes
    with _as(w.scope_admin) as db:
        assert (
            len(db.scalars(select(LLMRun).where(LLMRun.scope_id == w.scope)).all()) == 1
        )


@pytest.mark.asyncio
async def test_worker_finishes_as_creator_and_non_members_cannot_read(
    w: W, monkeypatch: pytest.MonkeyPatch
) -> None:
    canned(monkeypatch, GOOD)
    run_id = await asyncio.to_thread(_enqueue, w.scope_admin, w.curation)
    # leave other tests' queued runs alone: only ours is queued while the worker runs
    _exec(
        "UPDATE llm_runs SET status = 'failed' WHERE status = 'queued' AND id <> %s",
        str(run_id),
    )

    assert await llm_worker.process_next() is True

    with _as(w.scope_admin) as db:
        done = db.get(LLMRun, run_id)
        assert done is not None
        assert (done.status, done.error_code) == ("succeeded", None)
        assert done.input_tokens > 0 and done.request_sha256
        # finished runs are final, even for their creator
        result = db.execute(
            update(LLMRun).where(LLMRun.id == run_id).values(status="failed")
        )
        assert result.rowcount == 0  # type: ignore[attr-defined]
    for uid in (w.curator, w.outsider):
        with _as(uid) as db:
            assert (
                db.scalars(select(LLMRun).where(LLMRun.scope_id == w.scope)).all() == []
            )

    database.engine.dispose()
    with TestClient(app) as client:
        for uid, code in ((w.scope_admin, 200), (w.curator, 404), (w.outsider, 404)):
            token = create_access_token(data={"sub": str(uid)})
            r = client.get(
                f"/api/v1/llm-runs/{run_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == code, r.text
    database.engine.dispose()


def test_only_scope_admins_enqueue_and_only_queued(w: W) -> None:
    with _as(w.curator) as db, pytest.raises(DBAPIError, match="row-level security"):
        db.execute(
            text(
                "INSERT INTO llm_runs (scope_id, strategy, model_id, created_by) "
                "VALUES (:s, 'skeptic', 'm', :u)"
            ),
            {"s": str(w.scope), "u": str(w.curator)},
        )
    with (
        _as(w.scope_admin) as db,
        pytest.raises(DBAPIError, match="row-level security"),
    ):
        db.execute(
            text(
                "INSERT INTO llm_runs (scope_id, strategy, model_id, created_by, status) "
                "VALUES (:s, 'skeptic', 'm', :u, 'succeeded')"
            ),
            {"s": str(w.scope), "u": str(w.scope_admin)},
        )


def test_migration_060_is_recorded() -> None:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM schema_migrations WHERE filename = '060_llm_runs_worker.sql'"
        )
        assert cur.fetchone()[0] == 1
