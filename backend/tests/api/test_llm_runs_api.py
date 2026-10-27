"""LLM run endpoints (#489): run status, data-sharing preview, admin prompt test run."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.services import llm_runs
from app.services.llm_runs import enqueue_run
from tests.api.llm_api_support import llm_env  # noqa: F401
from tests.api.schema_api_support import auth
from tests.services.llm_run_support import World, canned, world_fixture  # noqa: F401

pytestmark = [pytest.mark.unit, pytest.mark.usefixtures("llm_env")]


def _h(w: World) -> dict[str, str]:
    return auth(create_access_token(data={"sub": str(w.scope_admin.id)}))


def test_run_status_for_scope_and_platform_admins_only(
    client: TestClient,
    db_session: Session,
    world: World,
    admin_token: str,
    curator_token: str,
) -> None:
    run = enqueue_run(db_session, world.scope_admin, world.curation.id, "skeptic")
    url = f"/api/v1/llm-runs/{run.id}"
    for headers in (_h(world), auth(admin_token)):
        r = client.get(url, headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "queued"
    assert client.get(url, headers=auth(curator_token)).status_code == 404
    assert (
        client.get(f"/api/v1/llm-runs/{uuid4()}", headers=_h(world)).status_code == 404
    )


def test_preview_shows_exactly_what_is_sent_without_user_data(
    client: TestClient, world: World, curator_token: str
) -> None:
    url = (
        f"/api/v1/scopes/{world.curation.scope_id}/curations/{world.curation.id}"
        "/llm-preview?strategy=skeptic"
    )
    r = client.get(url, headers=_h(world))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["model_id"] == "mock-model"
    assert body["system"].startswith("Review BRCA1")
    assert "HGNC:1100" in body["user"] and "segregates" in body["user"]
    sent = json.dumps(body)
    for private in ("@private.example", "Secret Person", str(world.scope_admin.id)):
        assert private not in sent
    assert client.get(url, headers=auth(curator_token)).status_code == 403
    advocate = client.get(url.replace("skeptic", "advocate"), headers=_h(world))
    assert advocate.status_code == 422
    assert advocate.json()["detail"] == "prompt_not_published"
    other = f"/api/v1/scopes/{world.curation.scope_id}/curations/{uuid4()}/llm-preview"
    assert client.get(f"{other}?strategy=skeptic", headers=_h(world)).status_code == 404


def test_admin_test_run_over_the_golden_set(
    client: TestClient,
    world: World,
    admin_token: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    url = f"/api/v1/admin/llm/prompt-versions/{world.version.id}/test-run"
    body = {"model_id": str(world.model.id)}
    canned(monkeypatch, '{"verdict": "supported"}')

    r = client.post(url, json=body, headers=auth(admin_token))

    assert r.status_code == 200, r.text
    out = r.json()
    assert out["model"] == "mock-model" and out["total"] == len(llm_runs.load_golden())
    by_case = {c["case"]: c for c in out["cases"]}
    assert by_case["strong_definitive"]["ok"] is True
    assert by_case["contradicted"]["error_code"] == "unexpected_output"
    assert out["passed"] == 1

    assert client.post(url, json=body, headers=_h(world)).status_code == 403
    missing = {"model_id": str(uuid4())}
    assert client.post(url, json=missing, headers=auth(admin_token)).status_code == 404
    monkeypatch.setattr(llm_runs, "GOLDEN_DIR", tmp_path)  # absent, as in the image
    assert client.post(url, json=body, headers=auth(admin_token)).status_code == 503
