"""#464 on real PostgreSQL as app_user: a curator's submit queues the opt-in second view
(073) for the admin who opted in, once; off by default; the worker then runs it."""

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.core import database
from app.core.security import create_access_token, get_password_hash
from app.schemas.validation import PMIDValidationResult
from app.services import llm_worker
from app.services.publication_service import PublicationService
from tests.postgres.test_submit_unknown_pmids import (
    W,
    _owner,
    _stage,
    client as client,
    w as w,
)
from tests.services.llm_run_support import GOOD, SCHEMA, canned

pytestmark = pytest.mark.postgres


def _configure(w: W, auto: bool) -> str:
    """A scope admin who saved LLM settings with auto_second_view_on_submit = auto."""
    admin, provider, model, template, version = (str(uuid4()) for _ in range(5))
    tag = str(w.scope)[:8]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (id, email, hashed_password, name, role) "
            "VALUES (%s, %s, %s, 'sa', 'user')",
            (admin, f"sa-{tag}@auto.org", get_password_hash("pw")),
        )
        cur.execute(
            "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
            "accepted_at) VALUES (%s, %s, 'admin', %s, now())",
            (str(w.scope), admin, admin),
        )
        cur.execute(
            "INSERT INTO llm_providers (id, name, kind, base_url) "
            "VALUES (%s, %s, 'mock', 'mock://')",
            (provider, f"{tag}-auto"),
        )
        cur.execute(
            "INSERT INTO llm_models (id, provider_id, model_id, "
            "input_price_per_mtok_cents, output_price_per_mtok_cents, max_tokens) "
            "VALUES (%s, %s, 'mock-model', 100, 300, 100)",
            (model, provider),
        )
        cur.execute(
            "INSERT INTO prompt_templates (id, key, strategy) VALUES (%s, %s, 'skeptic')",
            (template, f"{tag}-auto"),
        )
        cur.execute(
            "INSERT INTO prompt_template_versions (id, template_id, version, "
            "system_text, user_text, output_schema, sha256, published_at) "
            "VALUES (%s, %s, 1, 'Review {gene_symbol}.', '{curation_data}', %s, "
            "'abc', now())",
            (version, template, json.dumps(SCHEMA)),
        )
        cur.execute(
            "INSERT INTO scope_llm_settings (scope_id, enabled, model_id, "
            "skeptic_prompt_version_id, monthly_token_cap, monthly_cost_cap_cents, "
            "daily_run_cap, auto_second_view_on_submit, updated_by) "
            "VALUES (%s, true, %s, %s, 100000, 1000, 5, %s, %s)",
            (str(w.scope), model, version, auto, admin),
        )
    return admin


def _cleanup(w: W, admin: str) -> None:
    tag = f"{str(w.scope)[:8]}-auto"
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM llm_runs WHERE created_by = %s", (admin,))
        cur.execute(
            "DELETE FROM scope_llm_settings WHERE scope_id = %s", (str(w.scope),)
        )
        cur.execute("DELETE FROM prompt_templates WHERE key = %s", (tag,))
        cur.execute("DELETE FROM llm_providers WHERE name = %s", (tag,))
        cur.execute("DELETE FROM audit_log WHERE user_id = %s", (admin,))
        cur.execute("DELETE FROM scope_memberships WHERE user_id = %s", (admin,))
        cur.execute("DELETE FROM users WHERE id = %s", (admin,))


def _runs(cid: str) -> list[tuple[str, str, str]]:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT strategy, status, created_by::text FROM llm_runs "
            "WHERE curation_id = %s ORDER BY created_at",
            (cid,),
        )
        return [tuple(r) for r in cur.fetchall()]


@pytest.mark.asyncio
@pytest.mark.parametrize("auto", [False, True])
async def test_curator_submit_queues_the_second_view_only_when_opted_in(
    client: TestClient, w: W, monkeypatch: MonkeyPatch, auto: bool
) -> None:
    async def fetch(self: PublicationService, pmid: str) -> PMIDValidationResult:
        return PMIDValidationResult(pmid=pmid, is_valid=True)

    monkeypatch.setattr(PublicationService, "fetch_publication", fetch)
    admin = _configure(w, auto)
    try:
        h = {
            "Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"
        }
        entity = {"mondo_id": "MONDO:0000001", "disease_name": "d"}
        r = client.post(
            "/api/v1/curations/",
            json={
                "gene_id": str(w.gene),
                "scope_id": str(w.scope),
                "workflow_pair_id": w.pair,
                "evidence_data": {
                    "entity_definition": {**entity, "mode_of_inheritance": "AD"}
                },
            },
            headers=h,
        )
        assert r.status_code == 201, r.text
        cid = r.json()["id"]
        ok = client.post(
            f"/api/v1/curations/{cid}/submit",
            json={"lock_version": _stage(cid)[2]},
            headers=h,
        )
        assert ok.status_code == 200, ok.text
        assert _stage(cid)[1] == "review"
        if not auto:
            assert _runs(cid) == []
            return
        assert _runs(cid) == [("skeptic", "queued", admin)]

        # only this run is queued while the worker runs (others belong to other tests)
        with _owner() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE llm_runs SET status = 'failed' WHERE status = 'queued' "
                "AND curation_id <> %s",
                (cid,),
            )
        canned(monkeypatch, GOOD)
        database.engine.dispose()
        assert await llm_worker.process_next() is True
        assert _runs(cid) == [("skeptic", "succeeded", admin)]
    finally:
        _cleanup(w, admin)
