"""LLM admin console API (#489): platform admins only, write-only keys, audit first,
revision checks, SSRF on save and on call, prompt drafts/diff/publish.

RLS, column privileges and the immutability trigger are covered in
tests/postgres/test_llm_configuration.py.
"""

import json
import logging
import socket
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLogNew
from app.models.llm import LLMCredential, LLMModel, LLMProvider
from tests.api.llm_api_support import llm_env  # noqa: F401
from tests.api.schema_api_support import auth

pytestmark = [pytest.mark.unit, pytest.mark.usefixtures("llm_env")]

BASE = "/api/v1/admin/llm"
SECRET = "sk-live-NEVER-SHOW-ME-42"  # noqa: S105


@pytest.fixture
def h(admin_token: str) -> dict[str, str]:
    return auth(admin_token)


def _provider(client: TestClient, h: dict[str, str], **kw: Any) -> dict[str, Any]:
    body = {"name": f"p-{uuid4().hex[:6]}", "kind": "mock", "base_url": "mock://"}
    r = client.post(f"{BASE}/providers", json={**body, **kw}, headers=h)
    assert r.status_code == 201, r.text
    out: dict[str, Any] = r.json()
    return out


def _model(client: TestClient, h: dict[str, str], provider_id: str) -> dict[str, Any]:
    r = client.post(
        f"{BASE}/models",
        json={
            "provider_id": provider_id,
            "model_id": "mock-model-20260101",
            "input_price_per_mtok_cents": "300",
            "output_price_per_mtok_cents": "1500",
            "max_tokens": 1024,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    out: dict[str, Any] = r.json()
    return out


def test_non_admin_gets_403_everywhere(client: TestClient, curator_token: str) -> None:
    h = auth(curator_token)
    pid = uuid4()
    for method, path in (
        ("get", "/providers"),
        ("post", "/providers"),
        ("put", f"/providers/{pid}/key"),
        ("post", f"/providers/{pid}/ping"),
        ("get", "/models"),
        ("get", "/usage"),
        ("get", "/runs"),
        ("get", "/prompt-templates"),
        ("post", f"/prompt-versions/{pid}/publish"),
    ):
        r = client.request(method, BASE + path, json={}, headers=h)
        assert r.status_code == 403, (method, path)


def test_key_is_write_only_and_never_logged(
    client: TestClient,
    h: dict[str, str],
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    provider = _provider(client, h)
    assert (provider["has_key"], provider["key_fingerprint"]) == (False, None)

    r = client.put(
        f"{BASE}/providers/{provider['id']}/key", json={"api_key": SECRET}, headers=h
    )
    assert r.status_code == 204 and r.content == b""
    listed = client.get(f"{BASE}/providers", headers=h)
    item = next(p for p in listed.json() if p["id"] == provider["id"])
    assert item["has_key"] is True
    assert item["key_fingerprint"].startswith("sha256:")

    stored = db_session.scalars(select(LLMCredential)).one()
    db_session.refresh(stored, ["ciphertext"])
    assert SECRET.encode() not in stored.ciphertext
    audits = db_session.scalars(
        select(AuditLogNew).where(AuditLogNew.entity_type == "llm_credentials")
    ).all()
    assert len(audits) == 1 and SECRET not in json.dumps(audits[0].changes)

    # replacing keeps one row and changes the fingerprint
    client.put(
        f"{BASE}/providers/{provider['id']}/key", json={"api_key": "other"}, headers=h
    )
    again = client.get(f"{BASE}/providers", headers=h).json()
    assert (
        next(p for p in again if p["id"] == provider["id"])["key_fingerprint"]
        != (item["key_fingerprint"])
    )
    everything = json.dumps([listed.json(), again]) + caplog.text
    assert SECRET not in everything


def test_ssrf_rejected_on_save_and_on_call(
    client: TestClient,
    h: dict[str, str],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def resolve_to(ip: str) -> None:
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda host, port, *a, **k: [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))
            ],
        )

    resolve_to("169.254.169.254")
    r = client.post(
        f"{BASE}/providers",
        json={"name": "meta", "kind": "anthropic", "base_url": "https://evil.example"},
        headers=h,
    )
    assert r.status_code == 422
    resolve_to("10.0.0.1")
    assert (
        client.post(
            f"{BASE}/providers",
            json={
                "name": "priv",
                "kind": "openai_compatible",
                "base_url": "https://x.example",
            },
            headers=h,
        ).status_code
        == 422
    )

    # saved while public, then DNS moves to a private address: the call re-validates
    resolve_to("8.8.8.8")
    provider = _provider(
        client, h, kind="anthropic", base_url="https://llm.example.org"
    )
    _model(client, h, provider["id"])
    client.put(
        f"{BASE}/providers/{provider['id']}/key", json={"api_key": SECRET}, headers=h
    )
    resolve_to("127.0.0.1")
    r = client.post(f"{BASE}/providers/{provider['id']}/ping", json={}, headers=h)
    assert r.status_code == 422 and "non-public" in r.text

    resolve_to("100.100.100.200")  # cloud metadata (CGNAT)
    r = client.patch(
        f"{BASE}/providers/{provider['id']}",
        json={"lock_version": 1, "base_url": "https://[::1]/"},
        headers=h,
    )
    assert r.status_code == 422


def test_ping_through_mock_adapter(client: TestClient, h: dict[str, str]) -> None:
    provider = _provider(client, h)
    r = client.post(f"{BASE}/providers/{provider['id']}/ping", json={}, headers=h)
    assert r.status_code == 422  # no model yet
    model = _model(client, h, provider["id"])
    r = client.post(
        f"{BASE}/providers/{provider['id']}/ping",
        json={"model_id": model["id"]},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True and r.json()["model"] == "mock-model-20260101"


def test_ping_reports_provider_error_code(
    client: TestClient, h: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.llm.providers import LLMProviderError, MockProvider

    async def fail(self: MockProvider, request: Any) -> Any:
        raise LLMProviderError("http_error", 500)

    monkeypatch.setattr(MockProvider, "complete", fail)
    provider = _provider(client, h)
    _model(client, h, provider["id"])
    r = client.post(f"{BASE}/providers/{provider['id']}/ping", json={}, headers=h)
    assert r.json()["ok"] is False and r.json()["error_code"] == "http_error"


def test_real_provider_without_key_cannot_ping(
    client: TestClient, h: dict[str, str]
) -> None:
    provider = _provider(
        client, h, kind="anthropic", base_url="https://llm.example.org"
    )
    _model(client, h, provider["id"])
    r = client.post(f"{BASE}/providers/{provider['id']}/ping", json={}, headers=h)
    assert r.status_code == 422 and "no API key" in r.text


def test_models_require_a_dated_pin_and_carry_the_o_series_flag(
    client: TestClient, h: dict[str, str]
) -> None:
    provider = _provider(client, h)
    anthropic = _provider(
        client, h, kind="anthropic", base_url="https://api.anthropic.com"
    )
    bad = client.post(
        f"{BASE}/models",
        json={
            "provider_id": anthropic["id"],
            "model_id": "claude-sonnet-latest",
            "input_price_per_mtok_cents": "1",
            "output_price_per_mtok_cents": "1",
            "max_tokens": 10,
        },
        headers=h,
    )
    assert bad.status_code == 422
    model = _model(client, h, provider["id"])
    assert model["uses_max_completion_tokens"] is False
    r = client.patch(
        f"{BASE}/models/{model['id']}",
        json={
            "lock_version": 1,
            "uses_max_completion_tokens": True,
            "output_price_per_mtok_cents": "2000",
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["uses_max_completion_tokens"] is True
    assert r.json()["lock_version"] == 2
    assert (
        client.get(f"{BASE}/models", headers=h).json()[0]["output_price_per_mtok_cents"]
        == "2000.0000"
    )
    # stale revision
    stale = client.patch(
        f"{BASE}/models/{model['id']}",
        json={"lock_version": 1, "enabled": False},
        headers=h,
    )
    assert stale.status_code == 409
    dup = client.post(
        f"{BASE}/models",
        json={
            "provider_id": provider["id"],
            "model_id": "mock-model-20260101",
            "input_price_per_mtok_cents": "1",
            "output_price_per_mtok_cents": "1",
            "max_tokens": 10,
        },
        headers=h,
    )
    assert dup.status_code == 409


def test_provider_update_uses_revision_and_audit(
    client: TestClient, h: dict[str, str], db_session: Session
) -> None:
    provider = _provider(client, h)
    url = f"{BASE}/providers/{provider['id']}"
    ok = client.patch(url, json={"lock_version": 1, "enabled": False}, headers=h)
    assert ok.status_code == 200 and ok.json()["enabled"] is False
    assert (
        client.patch(
            url, json={"lock_version": 1, "enabled": True}, headers=h
        ).status_code
        == 409
    )
    ops = db_session.scalars(
        select(AuditLogNew.operation).where(AuditLogNew.entity_id == provider["id"])
    ).all()
    assert sorted(ops) == [
        "CREATE",
        "UPDATE",
    ]  # the stale write's audit row rolled back with it
    assert (
        client.post(
            f"{BASE}/providers",
            json={"name": provider["name"], "kind": "mock", "base_url": "mock://"},
            headers=h,
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"{BASE}/providers/{uuid4()}", json={"lock_version": 1}, headers=h
        ).status_code
        == 404
    )


def test_change_fails_closed_when_audit_write_fails(
    client: TestClient,
    h: dict[str, str],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sqlalchemy.exc import OperationalError

    def broken(*a: Any, **k: Any) -> None:
        raise OperationalError("INSERT INTO audit_log", {}, Exception("down"))

    monkeypatch.setattr(db_session, "flush", broken)
    r = client.post(
        f"{BASE}/providers",
        json={"name": "x", "kind": "mock", "base_url": "mock://"},
        headers=h,
    )
    monkeypatch.undo()
    assert r.status_code == 503
    assert db_session.scalars(select(LLMProvider)).all() == []


@pytest.fixture
def template(client: TestClient, h: dict[str, str]) -> Iterator[dict[str, Any]]:
    r = client.post(
        f"{BASE}/prompt-templates",
        json={"key": "skeptic-main", "strategy": "skeptic"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    yield r.json()


def test_prompt_draft_publish_edit_and_diff(
    client: TestClient, h: dict[str, str], template: dict[str, Any]
) -> None:
    url = f"{BASE}/prompt-templates/{template['id']}/versions"
    draft = client.post(
        url,
        json={
            "system_text": "You review {methodology}.",
            "user_text": "Gene {gene_symbol}\n{curation_data}",
        },
        headers=h,
    ).json()
    assert draft["version"] == 1 and draft["published_at"] is None

    edited = client.patch(
        f"{BASE}/prompt-versions/{draft['id']}",
        json={"lock_version": 1, "system_text": "You strictly review {methodology}."},
        headers=h,
    ).json()
    assert edited["id"] == draft["id"] and edited["lock_version"] == 2

    pub = client.post(
        f"{BASE}/prompt-versions/{draft['id']}/publish",
        json={"lock_version": 2},
        headers=h,
    )
    assert pub.status_code == 200, pub.text
    assert pub.json()["published_at"] and len(pub.json()["sha256"]) == 64
    assert (
        client.post(
            f"{BASE}/prompt-versions/{draft['id']}/publish",
            json={"lock_version": 3},
            headers=h,
        ).status_code
        == 409
    )

    # editing a published version creates a new draft from it
    v2 = client.patch(
        f"{BASE}/prompt-versions/{draft['id']}",
        json={"lock_version": 3, "user_text": "Gene {gene_symbol}"},
        headers=h,
    ).json()
    assert v2["id"] != draft["id"] and v2["version"] == 2
    assert v2["derived_from"] == draft["id"] and v2["published_at"] is None
    assert v2["system_text"] == "You strictly review {methodology}."

    diff = client.get(
        f"{BASE}/prompt-versions/{v2['id']}/diff",
        params={"against": draft["id"]},
        headers=h,
    ).json()
    assert "-{curation_data}" in diff["user_diff"] and diff["system_diff"] == ""
    listed = client.get(url, headers=h).json()
    assert [v["version"] for v in listed] == [2, 1]
    assert (
        client.get(f"{BASE}/prompt-templates", headers=h).json()[0]["key"]
        == "skeptic-main"
    )


def test_prompt_rejects_placeholders_outside_the_allowlist(
    client: TestClient, h: dict[str, str], template: dict[str, Any]
) -> None:
    url = f"{BASE}/prompt-templates/{template['id']}/versions"
    for text in ("{user_email}", "{config}"):
        r = client.post(url, json={"system_text": "s", "user_text": text}, headers=h)
        assert r.status_code == 422, text
    assert (
        client.post(
            f"{BASE}/prompt-templates",
            json={"key": "skeptic-main", "strategy": "skeptic"},
            headers=h,
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"{BASE}/prompt-templates/{uuid4()}/versions",
            json={"system_text": "s", "user_text": "u"},
            headers=h,
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"{BASE}/prompt-versions/{uuid4()}/publish",
            json={"lock_version": 1},
            headers=h,
        ).status_code
        == 404
    )


def test_usage_and_runs(
    client: TestClient, h: dict[str, str], db_session: Session, test_scope: Any
) -> None:
    from app.models.llm import LLMRun

    for tokens in (10, 20):
        db_session.add(
            LLMRun(
                scope_id=test_scope.id,
                strategy="skeptic",
                model_id="m-20260101",
                input_tokens=tokens,
                output_tokens=1,
                cost_cents=1,
            )
        )
    db_session.commit()
    usage = client.get(f"{BASE}/usage", headers=h).json()
    assert usage == [
        {
            "scope_id": str(test_scope.id),
            "runs": 2,
            "input_tokens": 30,
            "output_tokens": 2,
            "cost_cents": "2.0000",
        }
    ]
    runs = client.get(
        f"{BASE}/runs", params={"scope_id": str(test_scope.id)}, headers=h
    )
    assert len(runs.json()) == 2 and runs.json()[0]["status"] == "queued"


def test_model_with_unknown_provider_is_404(
    client: TestClient, h: dict[str, str], db_session: Session
) -> None:
    r = client.post(
        f"{BASE}/models",
        json={
            "provider_id": str(uuid4()),
            "model_id": "m-20260101",
            "input_price_per_mtok_cents": "1",
            "output_price_per_mtok_cents": "1",
            "max_tokens": 10,
        },
        headers=h,
    )
    assert r.status_code == 404
    assert db_session.scalars(select(LLMModel)).all() == []


def test_repointing_base_url_deletes_the_key_before_any_call(
    client: TestClient,
    h: dict[str, str],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.llm.providers import provider_registry

    provider = _provider(
        client, h, kind="anthropic", base_url="https://llm.example.org"
    )
    _model(client, h, provider["id"])
    url = f"{BASE}/providers/{provider['id']}"
    client.put(f"{url}/key", json={"api_key": SECRET}, headers=h)

    # same URL or other fields: the key stays
    same = client.patch(
        url,
        json={
            "lock_version": 1,
            "base_url": "https://llm.example.org",
            "enabled": True,
        },
        headers=h,
    )
    assert same.json()["has_key"] is True

    moved = client.patch(
        url, json={"lock_version": 2, "base_url": "https://attacker.example"}, headers=h
    )
    assert moved.status_code == 200, moved.text
    assert (moved.json()["has_key"], moved.json()["key_fingerprint"]) == (False, None)
    assert db_session.scalars(select(LLMCredential)).all() == []
    ops = db_session.scalars(
        select(AuditLogNew.operation).where(
            AuditLogNew.entity_type == "llm_credentials"
        )
    ).all()
    assert sorted(ops) == ["CREATE", "DELETE"]

    calls: list[dict[str, Any]] = []

    async def spy(kind: str, **config: Any) -> Any:
        calls.append(config)
        raise AssertionError("no adapter may be built")

    monkeypatch.setattr(provider_registry, "acreate", spy)
    ping = client.post(f"{url}/ping", json={}, headers=h)
    assert ping.status_code == 422 and "no API key" in ping.text
    assert calls == []


def test_undecryptable_key_is_503_not_500(
    client: TestClient, h: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from cryptography.fernet import Fernet

    from app.core.config import settings

    provider = _provider(
        client, h, kind="anthropic", base_url="https://llm.example.org"
    )
    _model(client, h, provider["id"])
    client.put(
        f"{BASE}/providers/{provider['id']}/key", json={"api_key": SECRET}, headers=h
    )
    # the key ring lost the kid the key was stored under
    monkeypatch.setattr(
        settings,
        "LLM_CREDENTIAL_KEYS",
        json.dumps({"k1": Fernet.generate_key().decode()}),
    )
    r = client.post(f"{BASE}/providers/{provider['id']}/ping", json={}, headers=h)
    assert r.status_code == 503 and "cannot be decrypted" in r.text
    assert SECRET not in r.text


@pytest.mark.parametrize("bad", [SECRET * 200, 4242424242, "", None])
def test_invalid_key_is_not_echoed_in_422(
    client: TestClient, h: dict[str, str], bad: object
) -> None:
    provider = _provider(client, h)
    r = client.put(
        f"{BASE}/providers/{provider['id']}/key", json={"api_key": bad}, headers=h
    )
    assert r.status_code == 422
    assert SECRET not in r.text and "4242424242" not in r.text


def test_concurrent_first_key_save_is_409(
    client: TestClient,
    h: dict[str, str],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import llm_config

    provider = _provider(client, h)
    url = f"{BASE}/providers/{provider['id']}/key"
    assert client.put(url, json={"api_key": SECRET}, headers=h).status_code == 204
    # the second writer read "no key yet" before the first one committed
    monkeypatch.setattr(llm_config, "credentials_by_provider", lambda db, ids: {})
    r = client.put(url, json={"api_key": "other"}, headers=h)
    assert r.status_code == 409
    monkeypatch.undo()
    assert len(db_session.scalars(select(LLMCredential)).all()) == 1


@pytest.mark.parametrize("body", [SECRET, [SECRET], 4242424242])
def test_bare_body_key_is_not_echoed_in_422(
    client: TestClient, h: dict[str, str], body: object
) -> None:
    provider = _provider(client, h)
    r = client.put(f"{BASE}/providers/{provider['id']}/key", json=body, headers=h)
    assert r.status_code == 422
    assert SECRET not in r.text and "4242424242" not in r.text


@pytest.mark.parametrize(
    ("kind", "model_id", "code"),
    [
        ("anthropic", "claude-sonnet-5-5", 201),
        ("anthropic", "claude-sonnet-latest", 422),
        ("anthropic", "claude-x", 422),
        ("anthropic", "anthropic/claude-sonnet-5.5", 422),
        ("openai_compatible", "anthropic/claude-sonnet-5.5", 201),  # OpenRouter
        ("openai_compatible", "bad id with spaces", 422),
    ],
)
def test_only_anthropic_ids_need_a_pin(
    client: TestClient, h: dict[str, str], kind: str, model_id: str, code: int
) -> None:
    base = {"anthropic": "https://api.anthropic.com"}.get(
        kind, "https://openrouter.ai/api/v1"
    )
    provider = _provider(client, h, kind=kind, base_url=base)
    r = client.post(
        f"{BASE}/models",
        json={
            "provider_id": provider["id"],
            "model_id": model_id,
            "input_price_per_mtok_cents": "200",
            "output_price_per_mtok_cents": "1000",
            "max_tokens": 8192,
        },
        headers=h,
    )
    assert r.status_code == code, r.text
    if code == 201:
        assert r.json()["model_id"] == model_id
