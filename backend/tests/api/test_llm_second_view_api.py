"""Second-view endpoints (#464, #465): reviewers request, read and decide; nothing else
changes, curators cannot decide on their own work, and no key reaches the browser."""

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.llm.crypto import CredentialCipher
from app.models import ScopeMembership, UserNew
from app.models.llm import LLMCredential, LLMFinding, LLMRun
from tests.api.llm_api_support import llm_env  # noqa: F401
from tests.api.schema_api_support import auth
from tests.services.llm_run_support import World, world_fixture  # noqa: F401

pytestmark = [pytest.mark.unit, pytest.mark.usefixtures("llm_env")]
SECRET = "sk-ant-secret-never-shown"  # noqa: S105 (test key)


def _reviewer(db: Session, w: World) -> dict[str, str]:
    user = UserNew(
        id=uuid4(),
        email="reviewer.sv@example.org",
        hashed_password=get_password_hash("x"),
        name="Rev",
        role="user",
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.add(
        ScopeMembership(
            scope_id=w.curation.scope_id,
            user_id=user.id,
            role="reviewer",
            accepted_at=datetime.now(UTC),
        )
    )
    db.commit()
    return auth(create_access_token(data={"sub": str(user.id)}))


def _url(w: World) -> str:
    return f"/api/v1/scopes/{w.curation.scope_id}/curations/{w.curation.id}/llm-second-view"


def test_reviewer_requests_reads_and_decides(
    client: TestClient,
    db_session: Session,
    world: World,
    curator_token: str,
    viewer_token: str,
) -> None:
    sealed = CredentialCipher.from_settings().encrypt(SECRET)
    db_session.add(
        LLMCredential(
            provider_id=world.provider.id,
            ciphertext=sealed.ciphertext,
            key_id="k1",
            fingerprint=sealed.fingerprint,
        )
    )
    db_session.commit()
    h = _reviewer(db_session, world)

    r = client.post(_url(world), headers=h)
    assert r.status_code == 202, r.text
    assert r.json()["enabled"] is True and r.json()["pending"] is True
    run = db_session.query(LLMRun).one()  # only the skeptic has a prompt configured
    assert (run.strategy, run.status) == ("skeptic", "queued")
    again = client.post(_url(world), headers=h)
    assert again.status_code == 409 and "already running" in again.json()["detail"]
    assert db_session.query(LLMRun).count() == 1

    run.status = "succeeded"
    run.proposed_verdict = "limited"
    run.proposed_scores = {"total_score": 6.5}
    run.finished_at = datetime.now(UTC)
    finding = LLMFinding(
        run_id=run.id,
        curation_id=world.curation.id,
        scope_id=world.curation.scope_id,
        category="case_level",
        message="P1 twice",
        citations=["PMID:1"],
    )
    db_session.add(finding)
    db_session.commit()

    view = client.get(_url(world), headers=h)
    assert view.status_code == 200, view.text
    body = view.json()
    assert body["runs"][0]["model_id"] == "mock-model"
    assert body["findings"][0]["citations"] == ["PMID:1"]
    assert {d["category"] for d in body["diff"]} == {"total_score", "classification"}
    assert SECRET not in view.text and SECRET not in r.text

    decide = f"/api/v1/llm-findings/{finding.id}"
    own = client.patch(
        decide, json={"decision": "accepted"}, headers=auth(curator_token)
    )
    assert own.status_code == 403  # the curator cannot be a reviewer of their own work
    assert client.patch(decide, json={"decision": "x"}, headers=h).status_code == 422
    dismissed = client.patch(decide, json={"decision": "dismissed"}, headers=h)
    assert dismissed.status_code == 200, dismissed.text
    assert dismissed.json()["decision"] == "dismissed"
    assert dismissed.json()["strategy"] == "skeptic"
    db_session.expire_all()
    stored = db_session.get(LLMFinding, finding.id)
    assert stored is not None and stored.decided_by is not None
    assert stored.decided_at is not None
    missing = f"/api/v1/llm-findings/{uuid4()}"
    assert (
        client.patch(missing, json={"decision": "accepted"}, headers=h).status_code
        == 404
    )

    for token in (curator_token, viewer_token):
        assert client.get(_url(world), headers=auth(token)).status_code == 403
        assert client.post(_url(world), headers=auth(token)).status_code == 403
    other = _url(world).replace(str(world.curation.id), str(uuid4()))
    assert client.get(other, headers=h).status_code == 404


def test_request_is_refused_when_the_scope_is_not_opted_in(
    client: TestClient, db_session: Session, world: World
) -> None:
    h = _reviewer(db_session, world)
    world.settings.enabled = False
    db_session.commit()
    r = client.post(_url(world), headers=h)
    assert r.status_code == 422 and r.json()["detail"] == "llm_disabled"
    assert client.get(_url(world), headers=h).json()["enabled"] is False
    world.settings.skeptic_prompt_version_id = None
    db_session.commit()
    assert client.post(_url(world), headers=h).json()["detail"] == "llm_disabled"
    assert json.dumps(client.get(_url(world), headers=h).json()["runs"]) == "[]"
