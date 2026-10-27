"""Caps fail closed and key rotation (#489)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm.crypto import CredentialCipher
from app.llm.rotate import rotate_all
from app.models import AuditLogNew, Scope
from app.models.llm import (
    LLMCredential,
    LLMModel,
    LLMProvider,
    LLMRun,
    ScopeLLMSettings,
)
from app.services.llm_config import LLMCapError, check_run_allowed
from tests.api.llm_api_support import llm_env  # noqa: F401

pytestmark = pytest.mark.unit
NOW = datetime(2026, 10, 15, 12, tzinfo=UTC)


def _setup(db: Session, scope: Scope, **caps: int) -> ScopeLLMSettings:
    provider = LLMProvider(name="p", kind="mock", base_url="mock://")
    db.add(provider)
    db.flush()
    model = LLMModel(
        provider_id=provider.id,
        model_id="m-20260101",
        input_price_per_mtok_cents=Decimal(1),
        output_price_per_mtok_cents=Decimal(1),
        max_tokens=10,
    )
    db.add(model)
    db.flush()
    settings = ScopeLLMSettings(
        scope_id=scope.id, enabled=True, model_id=model.id, **caps
    )
    db.add(settings)
    db.commit()
    return settings


def _run(
    db: Session, scope: Scope, when: datetime, tokens: int = 0, cost: int = 0
) -> None:
    db.add(
        LLMRun(
            scope_id=scope.id,
            strategy="skeptic",
            model_id="m",
            status="failed",
            input_tokens=tokens,
            cost_cents=Decimal(cost),
            created_at=when,
        )
    )
    db.commit()


def _code(db: Session, scope: Scope) -> str:
    with pytest.raises(LLMCapError) as exc:
        check_run_allowed(db, scope.id, NOW)
    return exc.value.code


def test_no_settings_disabled_or_no_model_refuse(
    db_session: Session, test_scope: Scope
) -> None:
    assert _code(db_session, test_scope) == "llm_disabled"
    settings = _setup(db_session, test_scope)
    settings.model_id = None
    db_session.commit()
    assert _code(db_session, test_scope) == "no_model"
    settings.enabled = False
    db_session.commit()
    assert _code(db_session, test_scope) == "llm_disabled"


def test_default_caps_are_zero_and_refuse(
    db_session: Session, test_scope: Scope
) -> None:
    _setup(db_session, test_scope)
    assert _code(db_session, test_scope) == "daily_run_cap"


def test_each_cap_fails_closed(db_session: Session, test_scope: Scope) -> None:
    settings = _setup(
        db_session,
        test_scope,
        daily_run_cap=1,
        monthly_token_cap=100,
        monthly_cost_cap_cents=10,
    )
    assert check_run_allowed(db_session, test_scope.id, NOW) is settings
    _run(db_session, test_scope, NOW - timedelta(hours=1))  # failed runs count too
    assert _code(db_session, test_scope) == "daily_run_cap"

    settings.daily_run_cap = 10
    db_session.commit()
    _run(db_session, test_scope, NOW - timedelta(days=3), tokens=100)
    assert _code(db_session, test_scope) == "monthly_token_cap"

    settings.monthly_token_cap = 1000
    db_session.commit()
    _run(db_session, test_scope, NOW - timedelta(days=4), cost=10)
    assert _code(db_session, test_scope) == "monthly_cost_cap"

    # last month's usage does not count
    settings.monthly_cost_cap_cents = 11
    db_session.commit()
    _run(db_session, test_scope, NOW - timedelta(days=40), tokens=10**6, cost=10**4)
    assert check_run_allowed(db_session, test_scope.id, NOW) is settings


@pytest.mark.usefixtures("llm_env")
def test_rotate_reencrypts_to_active_kid(db_session: Session) -> None:
    old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    before = CredentialCipher({"old": old}, "old").encrypt("sk-secret")
    provider = LLMProvider(name="p", kind="mock", base_url="mock://")
    db_session.add(provider)
    db_session.flush()
    db_session.add(
        LLMCredential(
            provider_id=provider.id,
            ciphertext=before.ciphertext,
            key_id="old",
            fingerprint=before.fingerprint,
        )
    )
    db_session.commit()

    ring = CredentialCipher({"old": old, "new": new}, "new")
    assert rotate_all(db_session, ring, "new") == 1
    assert rotate_all(db_session, ring, "new") == 0
    audit = db_session.scalars(select(AuditLogNew)).one()
    assert audit.operation == "ROTATE"
    assert audit.changes == {
        "provider_id": str(provider.id),
        "from_key_id": "old",
        "to_key_id": "new",
    }
    kid, ciphertext, rotated = db_session.execute(
        select(LLMCredential.key_id, LLMCredential.ciphertext, LLMCredential.rotated_at)
    ).one()
    assert kid == "new" and rotated is not None
    assert CredentialCipher({"new": new}, "new").decrypt(ciphertext) == "sk-secret"


@pytest.mark.usefixtures("llm_env")
def test_rotate_fails_closed_when_audit_fails(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy.exc import OperationalError

    old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    before = CredentialCipher({"old": old}, "old").encrypt("sk-secret")
    provider = LLMProvider(name="p", kind="mock", base_url="mock://")
    db_session.add(provider)
    db_session.flush()
    db_session.add(
        LLMCredential(
            provider_id=provider.id,
            ciphertext=before.ciphertext,
            key_id="old",
            fingerprint=before.fingerprint,
        )
    )
    db_session.commit()

    def broken(*a: object, **k: object) -> None:
        raise OperationalError("INSERT INTO audit_log", {}, Exception("down"))

    monkeypatch.setattr(db_session, "flush", broken)
    with pytest.raises(OperationalError):
        rotate_all(db_session, CredentialCipher({"old": old, "new": new}, "new"), "new")
    monkeypatch.undo()
    db_session.rollback()
    assert db_session.scalar(select(LLMCredential.key_id)) == "old"
    assert db_session.scalars(select(AuditLogNew)).all() == []
