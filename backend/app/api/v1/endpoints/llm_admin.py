"""LLM admin console API: providers, write-only keys, models, test ping, usage, runs (#489).

Platform admins only. Every change writes audit_log first; updates carry lock_version.
No endpoint returns or logs a key: responses carry only has_key and the fingerprint.
"""

import asyncio
import time
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_admin_user
from app.llm.providers import LLMProviderError, LLMRequest, provider_registry
from app.llm.ssrf import UnsafeURLError
from app.models import UserNew
from app.models.llm import LLMModel, LLMProvider, LLMRun
from app.schemas.llm import (
    ModelCreate,
    ModelOut,
    ModelUpdate,
    PingOut,
    PingRequest,
    ProviderCreate,
    ProviderKey,
    ProviderOut,
    ProviderUpdate,
    RunOut,
    UsageRow,
)
from app.services.llm_config import (
    audit,
    call_config,
    check_base_url,
    credentials_by_provider,
    drop_provider_key,
    month_start,
    save_revision,
    set_provider_key,
)

router = APIRouter()
Admin = Depends(get_current_admin_user)


def _provider_out(db: Session, providers: Sequence[LLMProvider]) -> list[ProviderOut]:
    creds = credentials_by_provider(db, [p.id for p in providers])
    out = []
    for p in providers:
        item = ProviderOut.model_validate(p)
        if cred := creds.get(p.id):
            item.has_key, item.key_fingerprint = True, cred.fingerprint
        out.append(item)
    return out


def _get(db: Session, model: type[LLMProvider] | type[LLMModel], pk: UUID) -> Any:
    row = db.get(model, pk)
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    return row


def _commit_unique(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Already exists") from None


# --- providers and keys ------------------------------------------------------


@router.get("/providers", response_model=list[ProviderOut])
def list_providers(
    db: Session = Depends(get_db), user: UserNew = Admin
) -> list[ProviderOut]:
    rows = db.scalars(select(LLMProvider).order_by(LLMProvider.name)).all()
    return _provider_out(db, rows)


@router.post("/providers", response_model=ProviderOut, status_code=201)
def create_provider(
    body: ProviderCreate, db: Session = Depends(get_db), user: UserNew = Admin
) -> ProviderOut:
    check_base_url(body.base_url, body.kind)
    provider = LLMProvider(id=uuid.uuid4(), created_by=user.id, **body.model_dump())
    audit(db, user, "llm_providers", provider.id, "CREATE", body.model_dump())
    db.add(provider)
    _commit_unique(db)
    return _provider_out(db, [provider])[0]


@router.patch("/providers/{provider_id}", response_model=ProviderOut)
def update_provider(
    provider_id: UUID,
    body: ProviderUpdate,
    db: Session = Depends(get_db),
    user: UserNew = Admin,
) -> ProviderOut:
    provider: LLMProvider = _get(db, LLMProvider, provider_id)
    values = body.model_dump(exclude_unset=True, exclude={"lock_version"})
    repointed = values.get("base_url", provider.base_url) != provider.base_url
    if repointed:
        check_base_url(values["base_url"], provider.kind)
    audit(db, user, "llm_providers", provider.id, "UPDATE", values)
    if repointed:  # a key must never follow its provider to a new host
        drop_provider_key(db, provider, user)
    save_revision(
        db,
        LLMProvider,
        provider.id,
        body.lock_version,
        {**values, "updated_at": func.now()},
    )
    db.refresh(provider)
    return _provider_out(db, [provider])[0]


@router.put("/providers/{provider_id}/key", status_code=204)
def set_key(
    provider_id: UUID,
    body: ProviderKey,
    db: Session = Depends(get_db),
    user: UserNew = Admin,
) -> Response:
    """Store or replace the provider's API key. Write-only: nothing ever reads it back."""
    provider: LLMProvider = _get(db, LLMProvider, provider_id)
    set_provider_key(db, provider, body.api_key.get_secret_value(), user)
    return Response(status_code=204)


@router.post("/providers/{provider_id}/ping", response_model=PingOut)
async def ping_provider(
    provider_id: UUID,
    body: PingRequest,
    db: Session = Depends(get_db),
    user: UserNew = Admin,
) -> PingOut:
    """One short call through the adapter; the base URL is re-validated for this call."""

    def prepare() -> tuple[str, dict[str, object]]:
        provider: LLMProvider = _get(db, LLMProvider, provider_id)
        query = select(LLMModel).where(LLMModel.provider_id == provider_id)
        if body.model_id:
            query = query.where(LLMModel.id == body.model_id)
        model = db.scalars(query.order_by(LLMModel.created_at)).first()
        if model is None:
            raise HTTPException(status_code=422, detail="Provider has no such model")
        return provider.kind, call_config(db, provider, model)

    kind, config = await asyncio.to_thread(prepare)
    try:
        adapter = await provider_registry.acreate(kind, **config)
    except UnsafeURLError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    started = time.monotonic()
    error_code = None
    try:
        await adapter.complete(
            LLMRequest(system="Reply with the word OK.", user="ping", max_tokens=16)
        )
    except LLMProviderError as exc:
        error_code = exc.code
    return PingOut(
        ok=error_code is None,
        model=str(config["model"]),
        latency_ms=int((time.monotonic() - started) * 1000),
        error_code=error_code,
    )


# --- models --------------------------------------------------------------------


@router.get("/models", response_model=list[ModelOut])
def list_models(
    db: Session = Depends(get_db), user: UserNew = Admin
) -> Sequence[LLMModel]:
    return db.scalars(select(LLMModel).order_by(LLMModel.model_id)).all()


@router.post("/models", response_model=ModelOut, status_code=201)
def create_model(
    body: ModelCreate, db: Session = Depends(get_db), user: UserNew = Admin
) -> LLMModel:
    _get(db, LLMProvider, body.provider_id)
    model = LLMModel(id=uuid.uuid4(), created_by=user.id, **body.model_dump())
    audit(db, user, "llm_models", model.id, "CREATE", body.model_dump())
    db.add(model)
    _commit_unique(db)
    return model


@router.patch("/models/{model_id}", response_model=ModelOut)
def update_model(
    model_id: UUID,
    body: ModelUpdate,
    db: Session = Depends(get_db),
    user: UserNew = Admin,
) -> LLMModel:
    model: LLMModel = _get(db, LLMModel, model_id)
    values = body.model_dump(exclude_unset=True, exclude={"lock_version"})
    audit(db, user, "llm_models", model.id, "UPDATE", values)
    save_revision(db, LLMModel, model.id, body.lock_version, values)
    db.refresh(model)
    return model


# --- usage and runs --------------------------------------------------------------


@router.get("/usage", response_model=list[UsageRow])
def usage(db: Session = Depends(get_db), user: UserNew = Admin) -> list[UsageRow]:
    """Tokens and cost per scope for the current calendar month (UTC)."""
    rows = db.execute(
        select(
            LLMRun.scope_id,
            func.count(LLMRun.id),
            func.coalesce(func.sum(LLMRun.input_tokens), 0),
            func.coalesce(func.sum(LLMRun.output_tokens), 0),
            func.coalesce(func.sum(LLMRun.cost_cents), 0),
        )
        .where(LLMRun.created_at >= month_start(datetime.now(UTC)))
        .group_by(LLMRun.scope_id)
    ).all()
    return [
        UsageRow(
            scope_id=r[0],
            runs=r[1],
            input_tokens=r[2],
            output_tokens=r[3],
            cost_cents=r[4],
        )
        for r in rows
    ]


@router.get("/runs", response_model=list[RunOut])
def list_runs(
    scope_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: UserNew = Admin,
) -> Sequence[LLMRun]:
    query = select(LLMRun).order_by(LLMRun.created_at.desc()).limit(limit)
    if scope_id:
        query = query.where(LLMRun.scope_id == scope_id)
    return db.scalars(query).all()
