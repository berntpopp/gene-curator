"""LLM configuration: audit-first saves, write-only keys, call preparation and caps (#489).

Keys never leave this module in clear text except into a provider adapter, and are
never logged or written to audit_log (only the fingerprint is).
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, inspect, select, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.llm.crypto import CredentialCipher, CredentialCipherError
from app.llm.ssrf import UnsafeURLError, validate_base_url
from app.models import AuditLogNew, UserNew
from app.models.llm import (
    LLMCredential,
    LLMModel,
    LLMProvider,
    LLMRun,
    ScopeLLMSettings,
)

logger = get_logger(__name__)


def audit(
    db: Session,
    user: UserNew,
    entity_type: str,
    entity_id: UUID,
    operation: str,
    changes: dict[str, Any],
    scope_id: UUID | None = None,
) -> None:
    """Write the audit row before the change; if it cannot be written nothing is saved."""
    try:
        db.add(
            AuditLogNew(
                entity_type=entity_type,
                entity_id=entity_id,
                operation=operation,
                changes=json.loads(json.dumps(changes, default=str)),
                user_id=user.id,
                scope_id=scope_id,
            )
        )
        db.flush()
    except SQLAlchemyError:
        db.rollback()
        logger.error("LLM admin audit write failed", entity_type=entity_type)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit log unavailable; change not saved",
        ) from None


def save_revision(
    db: Session, model: Any, pk: UUID, expected: int, values: dict[str, Any]
) -> None:
    """Compare-and-increment lock_version, then commit; 409 (and rollback) when stale.

    Like crud.optimistic_lock.claim_version, but keyed on the model's primary key
    (scope_llm_settings is keyed by scope_id).
    """
    key = inspect(model).primary_key[0]
    result = db.execute(
        update(model)
        .where(key == pk, model.lock_version == expected)
        .values(**values, lock_version=model.lock_version + 1)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:  # type: ignore[attr-defined]
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Changed by someone else; reload and retry",
        )
    db.commit()


def check_base_url(url: str, kind: str) -> None:
    try:
        validate_base_url(url, kind=kind)
    except UnsafeURLError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


def _cipher() -> CredentialCipher:
    try:
        return CredentialCipher.from_settings()
    except CredentialCipherError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


def credentials_by_provider(
    db: Session, provider_ids: list[UUID]
) -> dict[UUID, LLMCredential]:
    # ciphertext is deferred, so this SELECT never names it
    rows = db.scalars(
        select(LLMCredential).where(LLMCredential.provider_id.in_(provider_ids))
    )
    return {c.provider_id: c for c in rows}


def set_provider_key(
    db: Session, provider: LLMProvider, secret: str, user: UserNew
) -> None:
    encrypted = _cipher().encrypt(secret)
    existing = credentials_by_provider(db, [provider.id]).get(provider.id)
    credential_id = existing.id if existing else uuid.uuid4()
    audit(
        db,
        user,
        "llm_credentials",
        credential_id,
        "UPDATE" if existing else "CREATE",
        {
            "provider_id": provider.id,
            "fingerprint": encrypted.fingerprint,
            "key_id": encrypted.key_id,
        },
    )
    if existing:
        db.execute(
            update(LLMCredential)
            .where(LLMCredential.provider_id == provider.id)
            .values(
                ciphertext=encrypted.ciphertext,
                key_id=encrypted.key_id,
                fingerprint=encrypted.fingerprint,
                created_by=user.id,
                rotated_at=func.now(),
            )
            .execution_options(synchronize_session=False)
        )
    else:
        db.add(
            LLMCredential(
                id=credential_id,
                provider_id=provider.id,
                ciphertext=encrypted.ciphertext,
                key_id=encrypted.key_id,
                fingerprint=encrypted.fingerprint,
                created_by=user.id,
            )
        )
    try:
        db.commit()
    except IntegrityError:  # a concurrent first save won the unique provider_id
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Key changed concurrently; retry",
        ) from None


def drop_provider_key(db: Session, provider: LLMProvider, user: UserNew) -> None:
    """Delete the provider's key (audited) in the caller's transaction; the caller commits."""
    existing = credentials_by_provider(db, [provider.id]).get(provider.id)
    if existing is None:
        return
    audit(
        db,
        user,
        "llm_credentials",
        existing.id,
        "DELETE",
        {"provider_id": provider.id, "fingerprint": existing.fingerprint},
    )
    db.execute(
        delete(LLMCredential)
        .where(LLMCredential.id == existing.id)
        .execution_options(synchronize_session=False)
    )


def read_api_key(db: Session, provider_id: UUID) -> str | None:
    """Decrypt a provider key for an outbound call. The result goes to an adapter only."""
    if db.get_bind().dialect.name == "postgresql":
        # app_user has no SELECT on the column; this SECURITY DEFINER function is the path
        ciphertext = db.scalar(
            text("SELECT llm_credential_ciphertext(:p)"), {"p": provider_id}
        )
    else:
        ciphertext = db.scalar(
            select(LLMCredential.ciphertext).where(
                LLMCredential.provider_id == provider_id
            )
        )
    if not ciphertext:
        return None
    try:
        return _cipher().decrypt(bytes(ciphertext))
    except CredentialCipherError as exc:  # e.g. its kid was removed from the key ring
        raise HTTPException(status_code=503, detail=str(exc)) from None


def call_config(db: Session, provider: LLMProvider, model: LLMModel) -> dict[str, Any]:
    """Adapter kwargs for provider_registry; blocking (DB, decrypt), so run it off the loop."""
    api_key = read_api_key(db, provider.id)
    if api_key is None and provider.kind != "mock":
        raise HTTPException(status_code=422, detail="Provider has no API key")
    return {
        "base_url": provider.base_url,
        "api_key": api_key or "",
        "model": model.model_id,
        "timeout_s": float(model.timeout_s),
        "uses_max_completion_tokens": model.uses_max_completion_tokens,
    }


def prompt_sha256(fields: dict[str, Any]) -> str:
    canonical = json.dumps(fields, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


class LLMCapError(Exception):
    """A run is not allowed; `code` is safe to store as llm_runs.error_code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def check_run_allowed(
    db: Session, scope_id: UUID, now: datetime | None = None
) -> ScopeLLMSettings:
    """Fail closed: no settings, disabled, no model or any cap reached refuses the run.

    Caps count every run including failed ones; a cap of 0 allows nothing.
    """
    now = now or datetime.now(UTC)
    settings = db.get(ScopeLLMSettings, scope_id)
    if settings is None or not settings.enabled:
        raise LLMCapError("llm_disabled")
    if settings.model_id is None:
        raise LLMCapError("no_model")
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    runs_today = db.scalar(
        select(func.count(LLMRun.id)).where(
            LLMRun.scope_id == scope_id, LLMRun.created_at >= day
        )
    )
    if (runs_today or 0) >= settings.daily_run_cap:
        raise LLMCapError("daily_run_cap")
    tokens, cost = db.execute(
        select(
            func.coalesce(func.sum(LLMRun.input_tokens + LLMRun.output_tokens), 0),
            func.coalesce(func.sum(LLMRun.cost_cents), 0),
        ).where(LLMRun.scope_id == scope_id, LLMRun.created_at >= month_start(now))
    ).one()
    if int(tokens) >= settings.monthly_token_cap:
        raise LLMCapError("monthly_token_cap")
    if Decimal(cost) >= settings.monthly_cost_cap_cents:
        raise LLMCapError("monthly_cost_cap")
    return settings
