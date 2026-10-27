"""Scope LLM opt-in (#489): scope admins only, pick from what is enabled, caps, no keys."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.models import Scope, ScopeMembership, UserNew
from app.models.llm import (
    LLMModel,
    LLMProvider,
    PromptTemplate,
    PromptTemplateVersion,
)
from tests.api.llm_api_support import llm_env  # noqa: F401
from tests.api.schema_api_support import auth

pytestmark = [pytest.mark.unit, pytest.mark.usefixtures("llm_env")]


@pytest.fixture
def scope_admin(db_session: Session, test_scope: Scope) -> str:
    user = UserNew(
        id=uuid4(),
        email="sa@test.com",
        hashed_password=get_password_hash("x"),
        name="Scope Admin",
        role="user",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.add(
        ScopeMembership(
            scope_id=test_scope.id,
            user_id=user.id,
            role="admin",
            accepted_at=datetime.now(UTC),
        )
    )
    db_session.commit()
    return create_access_token(data={"sub": str(user.id)})


@pytest.fixture
def config(db_session: Session) -> dict[str, Any]:
    provider = LLMProvider(name="p", kind="mock", base_url="mock://")
    off = LLMProvider(name="off", kind="mock", base_url="mock://", enabled=False)
    db_session.add_all([provider, off])
    db_session.flush()
    model = LLMModel(
        provider_id=provider.id,
        model_id="m-20260101",
        input_price_per_mtok_cents=Decimal(1),
        output_price_per_mtok_cents=Decimal(1),
        max_tokens=10,
    )
    hidden = LLMModel(
        provider_id=off.id,
        model_id="h-20260101",
        input_price_per_mtok_cents=Decimal(1),
        output_price_per_mtok_cents=Decimal(1),
        max_tokens=10,
    )
    skeptic = PromptTemplate(key="s", strategy="skeptic")
    db_session.add_all([model, hidden, skeptic])
    db_session.flush()
    published = PromptTemplateVersion(
        template_id=skeptic.id,
        version=1,
        system_text="s",
        user_text="u",
        sha256="x",
        published_at=datetime.now(UTC),
    )
    draft = PromptTemplateVersion(
        template_id=skeptic.id, version=2, system_text="s", user_text="u"
    )
    db_session.add_all([published, draft])
    db_session.commit()
    return {
        "model": str(model.id),
        "hidden": str(hidden.id),
        "published": str(published.id),
        "draft": str(draft.id),
    }


def test_scope_admin_opts_in_with_caps_and_sees_no_keys(
    client: TestClient, scope_admin: str, test_scope: Scope, config: dict[str, Any]
) -> None:
    url = f"/api/v1/scopes/{test_scope.id}/llm-settings"
    h = auth(scope_admin)
    initial = client.get(url, headers=h).json()
    assert (initial["enabled"], initial["lock_version"], initial["daily_run_cap"]) == (
        False,
        0,
        0,
    )
    options = client.get(f"/api/v1/scopes/{test_scope.id}/llm-options", headers=h)
    assert [m["id"] for m in options.json()["models"]] == [config["model"]]
    assert [v["id"] for v in options.json()["prompt_versions"]] == [config["published"]]

    body = {
        "lock_version": 0,
        "enabled": True,
        "model_id": config["model"],
        "skeptic_prompt_version_id": config["published"],
        "monthly_token_cap": 100000,
        "monthly_cost_cap_cents": 500,
        "daily_run_cap": 20,
    }
    saved = client.put(url, json=body, headers=h)
    assert saved.status_code == 200, saved.text
    assert saved.json()["lock_version"] == 1 and saved.json()["daily_run_cap"] == 20
    assert client.put(url, json=body, headers=h).status_code == 409  # stale
    again = client.put(
        url, json={**body, "lock_version": 1, "enabled": False}, headers=h
    )
    assert again.status_code == 200 and again.json()["enabled"] is False
    text = initial.__repr__() + options.text + saved.text + again.text
    assert "key" not in text.replace("template_key", "")
    assert "fingerprint" not in text


def test_choices_must_be_enabled_and_published(
    client: TestClient, scope_admin: str, test_scope: Scope, config: dict[str, Any]
) -> None:
    url = f"/api/v1/scopes/{test_scope.id}/llm-settings"
    h = auth(scope_admin)
    base = {"lock_version": 0, "enabled": False}
    for extra in (
        {"model_id": config["hidden"]},
        {"skeptic_prompt_version_id": config["draft"]},
        {"advocate_prompt_version_id": config["published"]},  # wrong strategy
        {"enabled": True},  # no model
    ):
        assert client.put(url, json={**base, **extra}, headers=h).status_code == 422
    assert (
        client.put(url, json={**base, "lock_version": 3}, headers=h).status_code == 409
    )


def test_curator_and_platform_endpoints_are_forbidden(
    client: TestClient, curator_token: str, scope_admin: str, test_scope: Scope
) -> None:
    url = f"/api/v1/scopes/{test_scope.id}/llm-settings"
    assert client.get(url, headers=auth(curator_token)).status_code == 403
    assert (
        client.put(
            url, json={"lock_version": 0, "enabled": False}, headers=auth(curator_token)
        ).status_code
        == 403
    )
    # scope admins never reach the platform console (keys live there)
    assert (
        client.get("/api/v1/admin/llm/providers", headers=auth(scope_admin)).status_code
        == 403
    )


def test_scope_admin_of_another_scope_and_pending_invite_get_403(
    client: TestClient, db_session: Session, scope_admin: str, test_scope: Scope
) -> None:
    other = Scope(id=uuid4(), name="other", display_name="Other", is_active=True)
    invitee = UserNew(
        id=uuid4(),
        email="pending@test.com",
        hashed_password=get_password_hash("x"),
        name="Pending",
        role="user",
        is_active=True,
    )
    db_session.add_all([other, invitee])
    db_session.commit()
    db_session.add(
        ScopeMembership(
            scope_id=test_scope.id, user_id=invitee.id, role="admin", accepted_at=None
        )
    )
    db_session.commit()
    pending = create_access_token(data={"sub": str(invitee.id)})
    body = {"lock_version": 0, "enabled": False}
    for token, scope_id in ((scope_admin, other.id), (pending, test_scope.id)):
        for path in ("llm-settings", "llm-options"):
            url = f"/api/v1/scopes/{scope_id}/{path}"
            assert client.get(url, headers=auth(token)).status_code == 403, path
        put = client.put(
            f"/api/v1/scopes/{scope_id}/llm-settings", json=body, headers=auth(token)
        )
        assert put.status_code == 403
