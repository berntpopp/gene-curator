"""LLM second view on real PostgreSQL as app_user (065, #464, #465).

A reviewer requests the view through the API, the worker stores cited findings as that
reviewer, reviewers read and decide through the API; curators and outsiders see nothing,
findings cannot be forged or edited, and the curation itself never changes.
"""

import json
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core import database
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.llm import LLMFinding
from app.services import llm_worker
from app.services.llm_runs import load_golden
from tests.postgres.test_llm_runs_worker import (
    W,
    _as,
    _exec,
    _owner,
    w,  # noqa: F401  (fixture)
)
from tests.services.llm_run_support import canned

pytestmark = pytest.mark.postgres

OUTPUT = json.dumps(
    {
        "verdict": "supported",
        "findings": [
            {"category": "case_level", "message": "P1 twice", "citations": ["123"]},
            {"category": "function", "message": "uncited", "citations": []},
        ],
        "proposed_evidence": json.dumps(load_golden()[0]["expert_evidence"]),
    }
)


def _h(uid: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(uid)})}"}


def _curation_row(x: W) -> tuple[object, ...]:
    with _as(x.curator) as db:
        row = db.execute(
            text(
                "SELECT evidence_data::text, computed_scores::text, computed_verdict, "
                "status, workflow_stage, lock_version FROM curations WHERE id = :c"
            ),
            {"c": str(x.curation)},
        ).one()
    return tuple(row)


@pytest.mark.asyncio
async def test_reviewer_flow_as_app_user(w: W, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: F811
    reviewer = uuid4()
    _exec(
        "INSERT INTO users (id, email, hashed_password, name, role) "
        "VALUES (%s, %s, %s, 'rv', 'user')",
        str(reviewer),
        f"rv-{str(w.scope)[:8]}@run.org",
        get_password_hash("pw"),
    )
    _exec(
        "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
        "accepted_at) VALUES (%s, %s, 'reviewer', %s, now())",
        str(w.scope),
        str(reviewer),
        str(w.scope_admin),
    )
    before = _curation_row(w)
    canned(monkeypatch, OUTPUT)
    url = f"/api/v1/scopes/{w.scope}/curations/{w.curation}/llm-second-view"
    try:
        database.engine.dispose()
        with TestClient(app) as client:
            r = client.post(url, headers=_h(reviewer))
            assert r.status_code == 202, r.text
            assert client.post(url, headers=_h(w.curator)).status_code == 403
        # only our run is queued while the worker runs
        _exec(
            "UPDATE llm_runs SET status = 'failed' WHERE status = 'queued' "
            "AND curation_id <> %s",
            str(w.curation),
        )
        database.engine.dispose()
        assert await llm_worker.process_next() is True

        with _as(reviewer) as db:
            findings = db.scalars(
                select(LLMFinding).where(LLMFinding.curation_id == w.curation)
            ).all()
            assert [(f.category, f.citations) for f in findings] == [
                ("case_level", ["PMID:123"])
            ]
            finding_id, run_id = findings[0].id, findings[0].run_id
            with pytest.raises(DBAPIError, match="row-level security"):
                db.execute(
                    text(
                        "INSERT INTO llm_findings (run_id, curation_id, scope_id, "
                        "category, message, citations) VALUES "
                        "(:r, :c, :s, 'x', 'forged', ARRAY['PMID:1'])"
                    ),
                    {"r": str(run_id), "c": str(w.curation), "s": str(w.scope)},
                )
        with _as(reviewer) as db, pytest.raises(DBAPIError, match="permission denied"):
            db.execute(
                text("UPDATE llm_findings SET message = 'edited' WHERE id = :f"),
                {"f": str(finding_id)},
            )
        for uid in (w.curator, w.outsider):
            with _as(uid) as db:
                assert (
                    db.scalars(
                        select(LLMFinding).where(LLMFinding.curation_id == w.curation)
                    ).all()
                    == []
                )
                result = db.execute(
                    text(
                        "UPDATE llm_findings SET decision = 'accepted', "
                        "decided_by = :u WHERE id = :f"
                    ),
                    {"u": str(uid), "f": str(finding_id)},
                )
                assert result.rowcount == 0  # type: ignore[attr-defined]

        database.engine.dispose()
        with TestClient(app) as client:
            view = client.get(url, headers=_h(reviewer))
            assert view.status_code == 200, view.text
            body = view.json()
            assert body["enabled"] is True and body["runs"][0]["strategy"] == "skeptic"
            classification = [
                d for d in body["diff"] if d["category"] == "classification"
            ]
            assert classification[0]["skeptic"] == "limited"
            assert client.get(url, headers=_h(w.curator)).status_code == 403
            decide = f"/api/v1/llm-findings/{finding_id}"
            r = client.patch(
                decide, json={"decision": "dismissed"}, headers=_h(reviewer)
            )
            assert r.status_code == 200, r.text
            assert r.json()["decision"] == "dismissed"
            r = client.patch(
                decide, json={"decision": "accepted"}, headers=_h(w.curator)
            )
            assert r.status_code in (403, 404)
        assert _curation_row(w) == before  # advisory only
    finally:
        database.engine.dispose()
        _exec("DELETE FROM llm_runs WHERE curation_id = %s", str(w.curation))
        _exec("DELETE FROM audit_log WHERE user_id = %s", str(reviewer))
        _exec("DELETE FROM scope_memberships WHERE user_id = %s", str(reviewer))
        _exec("DELETE FROM users WHERE id = %s", str(reviewer))


def test_a_reviewer_cannot_decide_findings_on_their_own_curation(w: W) -> None:  # noqa: F811
    """The 065 NOT EXISTS rule alone: same scope role, only authorship differs."""
    own, other, mine, run, finding = uuid4(), uuid4(), uuid4(), uuid4(), uuid4()
    tag = str(w.scope)[:8]
    try:
        for uid, name in ((own, "own"), (other, "oth")):
            _exec(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, 'x', %s, 'user')",
                str(uid),
                f"{name}-{tag}@run.org",
                name,
            )
            _exec(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, 'reviewer', %s, now())",
                str(w.scope),
                str(uid),
                str(w.scope_admin),
            )
        _exec(
            "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, status, "
            "workflow_stage, created_by, evidence_data, entity_key) "
            "VALUES (%s, %s, %s, %s, 'draft', 'curation', %s, '{}', 'MONDO:2|AD')",
            str(mine),
            str(w.gene),
            str(w.scope),
            str(w.pair),
            str(own),
        )
        _exec(
            "INSERT INTO llm_runs (id, curation_id, scope_id, strategy, model_id, "
            "created_by, status) VALUES (%s, %s, %s, 'skeptic', 'm', %s, 'succeeded')",
            str(run),
            str(mine),
            str(w.scope),
            str(other),
        )
        _exec(
            "INSERT INTO llm_findings (id, run_id, curation_id, scope_id, category, "
            "message, citations) VALUES (%s, %s, %s, %s, 'c', 'm', ARRAY['PMID:1'])",
            str(finding),
            str(run),
            str(mine),
            str(w.scope),
        )
        decide = text(
            "UPDATE llm_findings SET decision = 'accepted', decided_by = :u, "
            "decided_at = now() WHERE id = :f"
        )
        for uid, rows in ((own, 0), (other, 1)):
            with _as(uid) as db:
                result = db.execute(decide, {"u": str(uid), "f": str(finding)})
                assert result.rowcount == rows  # type: ignore[attr-defined]
                db.commit()
    finally:
        _exec("DELETE FROM llm_runs WHERE id = %s", str(run))  # cascades the finding
        _exec("DELETE FROM curations WHERE id = %s", str(mine))
        users = (str(own), str(other))
        _exec("DELETE FROM scope_memberships WHERE user_id IN %s", users)
        _exec("DELETE FROM users WHERE id IN %s", users)


def test_migration_065_is_recorded() -> None:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM schema_migrations "
            "WHERE filename = '065_llm_second_view.sql'"
        )
        assert cur.fetchone()[0] == 1
