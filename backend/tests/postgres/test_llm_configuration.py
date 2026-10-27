"""LLM configuration on real PostgreSQL as app_user (057, #489).

Published prompt versions are immutable for every role, the API role cannot read key
ciphertexts, scope admins see no keys, and non-admins get 403 from the admin console.
"""

import json
import os
import socket
from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid4

import psycopg2
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.orm import Session

from app.core import database
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.main import app
from tests.postgres.conftest import set_test_user_context

pytestmark = pytest.mark.postgres

MIGRATION = Path(__file__).parents[3] / "database/sql/057_llm_configuration.sql"
SECRET = "sk-live-POSTGRES-NEVER-SHOWN"  # noqa: S105
BASE = "/api/v1/admin/llm"


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@dataclass
class W:
    admin: UUID = field(default_factory=uuid4)
    scope_admin: UUID = field(default_factory=uuid4)
    curator: UUID = field(default_factory=uuid4)
    scope: UUID = field(default_factory=uuid4)


@pytest.fixture
def w(monkeypatch: pytest.MonkeyPatch) -> Generator[W, None, None]:
    monkeypatch.setattr(
        settings,
        "LLM_CREDENTIAL_KEYS",
        json.dumps({"k1": Fernet.generate_key().decode()}),
    )
    monkeypatch.setattr(settings, "LLM_CREDENTIAL_ACTIVE_KID", "k1")
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, *a, **k: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port))
        ],
    )
    x = W()
    tag = str(x.scope)[:8]
    with _owner() as conn, conn.cursor() as cur:
        for uid, name, role in (
            (x.admin, "admin", "admin"),
            (x.scope_admin, "sadmin", "user"),
            (x.curator, "cur", "user"),
        ):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    str(uid),
                    f"{name}-{tag}@llm.org",
                    get_password_hash("pw"),
                    name,
                    role,
                ),
            )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, 'LLM', false, %s)",
            (str(x.scope), f"llm-{x.scope}", str(x.admin)),
        )
        for uid, role in ((x.scope_admin, "admin"), (x.curator, "curator")):
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, %s, %s, now())",
                (str(x.scope), str(uid), role, str(x.admin)),
            )
    yield x
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(x.scope),))
        cur.execute("DELETE FROM prompt_templates WHERE key LIKE %s", (f"{tag}%",))
        cur.execute("DELETE FROM llm_providers WHERE name LIKE %s", (f"{tag}%",))
        users = (str(x.admin), str(x.scope_admin), str(x.curator))
        cur.execute("DELETE FROM audit_log WHERE user_id IN %s", (users,))
        cur.execute("DELETE FROM users WHERE id IN %s", (users,))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _h(uid: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(uid)})}"}


def test_admin_flow_keys_stay_write_only_and_scope_admin_opts_in(
    client: TestClient, w: W
) -> None:
    tag = str(w.scope)[:8]
    h = _h(w.admin)
    provider = client.post(
        f"{BASE}/providers",
        json={"name": f"{tag}-mock", "kind": "mock", "base_url": "mock://"},
        headers=h,
    )
    assert provider.status_code == 201, provider.text
    pid = provider.json()["id"]
    assert (
        client.put(
            f"{BASE}/providers/{pid}/key", json={"api_key": SECRET}, headers=h
        ).status_code
        == 204
    )
    replaced = client.put(
        f"{BASE}/providers/{pid}/key", json={"api_key": SECRET + "2"}, headers=h
    )
    assert replaced.status_code == 204
    model = client.post(
        f"{BASE}/models",
        json={
            "provider_id": pid,
            "model_id": "mock-model-20260101",
            "input_price_per_mtok_cents": "300",
            "output_price_per_mtok_cents": "1500",
            "max_tokens": 512,
        },
        headers=h,
    )
    assert model.status_code == 201, model.text
    # the ping decrypts through llm_credential_ciphertext() as app_user
    ping = client.post(f"{BASE}/providers/{pid}/ping", json={}, headers=h)
    assert ping.status_code == 200 and ping.json()["ok"], ping.text

    template = client.post(
        f"{BASE}/prompt-templates",
        json={"key": f"{tag}-skeptic", "strategy": "skeptic"},
        headers=h,
    ).json()
    draft = client.post(
        f"{BASE}/prompt-templates/{template['id']}/versions",
        json={"system_text": "Review {methodology}.", "user_text": "{curation_data}"},
        headers=h,
    ).json()
    published = client.post(
        f"{BASE}/prompt-versions/{draft['id']}/publish",
        json={"lock_version": 1},
        headers=h,
    )
    assert published.status_code == 200, published.text

    listed = client.get(f"{BASE}/providers", headers=h)
    mine = next(p for p in listed.json() if p["id"] == pid)
    assert mine["has_key"] and mine["key_fingerprint"].startswith("sha256:")

    sa = _h(w.scope_admin)
    url = f"/api/v1/scopes/{w.scope}/llm-settings"
    options = client.get(f"/api/v1/scopes/{w.scope}/llm-options", headers=sa)
    assert options.status_code == 200, options.text
    saved = client.put(
        url,
        json={
            "lock_version": 0,
            "enabled": True,
            "model_id": model.json()["id"],
            "skeptic_prompt_version_id": draft["id"],
            "monthly_token_cap": 1000,
            "monthly_cost_cap_cents": 100,
            "daily_run_cap": 5,
        },
        headers=sa,
    )
    assert saved.status_code == 200, saved.text
    assert client.get(url, headers=sa).json()["daily_run_cap"] == 5

    seen = listed.text + options.text + saved.text + replaced.text + ping.text
    assert SECRET not in seen and "fingerprint" not in options.text + saved.text

    # non-admins: 403 from the console, scope admins included
    for uid in (w.scope_admin, w.curator):
        assert client.get(f"{BASE}/providers", headers=_h(uid)).status_code == 403
    assert client.get(url, headers=_h(w.curator)).status_code == 403

    # repointing the provider deletes its key as app_user (DELETE policy)
    moved = client.patch(
        f"{BASE}/providers/{pid}",
        json={"lock_version": 1, "base_url": "mock://elsewhere"},
        headers=h,
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["has_key"] is False

    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT operation FROM audit_log WHERE user_id IN (%s, %s) "
            "AND entity_type LIKE ANY (ARRAY['llm_%%', 'prompt_%%', 'scope_llm_%%'])",
            (str(w.admin), str(w.scope_admin)),
        )
        ops = sorted(r[0] for r in cur.fetchall())
        assert ops.count("CREATE") >= 5 and "PUBLISH" in ops
        cur.execute(
            "SELECT changes::text FROM audit_log WHERE user_id = %s", (str(w.admin),)
        )
        assert all(SECRET not in r[0] for r in cur.fetchall())


def test_app_user_cannot_select_ciphertext(w: W, db: Session) -> None:
    set_test_user_context(db, str(w.admin))
    with pytest.raises(ProgrammingError, match="permission denied"), db.begin_nested():
        db.execute(text("SELECT ciphertext FROM llm_credentials"))
    with pytest.raises(ProgrammingError, match="permission denied"), db.begin_nested():
        db.execute(text("SELECT * FROM llm_credentials"))
    # metadata columns stay readable for has_key / fingerprint
    db.execute(text("SELECT provider_id, fingerprint FROM llm_credentials"))


def test_credentials_invisible_to_non_admins(w: W, db: Session) -> None:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO llm_providers (name, kind, base_url) VALUES (%s, 'mock', 'mock://') "
            "RETURNING id",
            (f"{str(w.scope)[:8]}-cred",),
        )
        pid = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO llm_credentials (provider_id, ciphertext, key_id, fingerprint) "
            "VALUES (%s, 'x', 'k1', 'sha256:x')",
            (pid,),
        )
    set_test_user_context(db, str(w.scope_admin))
    assert db.scalar(text("SELECT count(*) FROM llm_credentials")) == 0
    with pytest.raises(DBAPIError), db.begin_nested():
        db.execute(
            text(
                "INSERT INTO llm_credentials (provider_id, ciphertext, key_id, fingerprint) "
                "VALUES (:p, 'y', 'k1', 'f')"
            ),
            {"p": pid},
        )


def _published_version(cur: psycopg2.extensions.cursor, key: str) -> str:
    cur.execute(
        "INSERT INTO prompt_templates (key, strategy) VALUES (%s, 'skeptic') RETURNING id",
        (key,),
    )
    tid = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO prompt_template_versions (template_id, version, system_text, "
        "user_text, sha256, published_at) VALUES (%s, 1, 's', 'u', 'h', now()) RETURNING id",
        (tid,),
    )
    vid: str = cur.fetchone()[0]
    return vid


def test_published_prompt_version_immutable_as_owner_and_app_user(
    w: W, db: Session, owner_session: Session
) -> None:
    with _owner() as conn, conn.cursor() as cur:
        vid = _published_version(cur, f"{str(w.scope)[:8]}-imm")
    for session in (owner_session, db):
        if session is db:
            set_test_user_context(db, str(w.admin))
        for sql in (
            "UPDATE prompt_template_versions SET user_text = 'x' WHERE id = :v",
            "UPDATE prompt_template_versions SET published_at = NULL WHERE id = :v",
            "DELETE FROM prompt_template_versions WHERE id = :v",
        ):
            with pytest.raises(DBAPIError, match="immutable"), session.begin_nested():
                session.execute(text(sql), {"v": vid})


def test_truncate_is_refused_as_owner(w: W, owner_session: Session) -> None:
    with _owner() as conn, conn.cursor() as cur:
        _published_version(cur, f"{str(w.scope)[:8]}-trunc")
    count = "SELECT count(*) FROM prompt_template_versions"
    before = owner_session.scalar(text(count))
    for sql in (
        "TRUNCATE prompt_template_versions CASCADE",
        "TRUNCATE prompt_templates CASCADE",
    ):
        with pytest.raises(DBAPIError, match="immutable"), owner_session.begin_nested():
            owner_session.execute(text(sql))
    assert before and owner_session.scalar(text(count)) == before


def test_drafts_are_editable_and_publishable(w: W, db: Session) -> None:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO prompt_templates (key, strategy) VALUES (%s, 'advocate') RETURNING id",
            (f"{str(w.scope)[:8]}-draft",),
        )
        tid = cur.fetchone()[0]
    set_test_user_context(db, str(w.admin))
    vid = db.scalar(
        text(
            "INSERT INTO prompt_template_versions (template_id, version, system_text, "
            "user_text) VALUES (:t, 1, 's', 'u') RETURNING id"
        ),
        {"t": tid},
    )
    db.execute(
        text("UPDATE prompt_template_versions SET user_text = 'v' WHERE id = :v"),
        {"v": vid},
    )
    db.execute(
        text(
            "UPDATE prompt_template_versions SET published_at = now(), sha256 = 'h' "
            "WHERE id = :v"
        ),
        {"v": vid},
    )
    with pytest.raises(DBAPIError, match="immutable"), db.begin_nested():
        db.execute(
            text("UPDATE prompt_template_versions SET user_text = 'w' WHERE id = :v"),
            {"v": vid},
        )


def test_migration_runs_twice(owner_session: Session) -> None:
    sql = MIGRATION.read_text()
    # raw DBAPI cursor: no parameter interpolation of the %I in format(); rolled back after
    cursor = owner_session.connection().connection.cursor()
    cursor.execute(sql)
    cursor.execute(sql)
    assert (
        owner_session.scalar(
            text(
                "SELECT count(*) FROM schema_migrations WHERE filename = '057_llm_configuration.sql'"
            )
        )
        == 1
    )
