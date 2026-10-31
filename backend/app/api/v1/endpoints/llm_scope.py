"""Scope LLM opt-in (#489): scope admins enable or disable, pick from what platform
admins enabled, and set caps. Nothing here exposes provider keys."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.capabilities import MANAGE_SCOPE
from app.core.database import get_db
from app.core.deps import get_current_active_user, require_capability
from app.models import UserNew
from app.models.llm import (
    LLMModel,
    LLMProvider,
    PromptTemplate,
    PromptTemplateVersion,
    ScopeLLMSettings,
)
from app.schemas.llm import (
    ScopeLLMOptions,
    ScopeModelOption,
    ScopePromptOption,
    ScopeSettingsOut,
    ScopeSettingsUpdate,
)
from app.services.llm_config import audit, save_revision

router = APIRouter()
STALE = "Changed by someone else; reload and retry"
# require_capability returns the scope; the caller comes from get_current_active_user
ScopeAdmin = Depends(require_capability(MANAGE_SCOPE))


def _options(db: Session) -> ScopeLLMOptions:
    models = db.execute(
        select(LLMModel.id, LLMModel.model_id, LLMProvider.name.label("provider_name"))
        .join(LLMProvider, LLMProvider.id == LLMModel.provider_id)
        .where(LLMModel.enabled, LLMProvider.enabled)
        .order_by(LLMModel.model_id)
    ).all()
    versions = db.execute(
        select(
            PromptTemplateVersion.id,
            PromptTemplate.key.label("template_key"),
            PromptTemplate.strategy,
            PromptTemplateVersion.version,
        )
        .join(PromptTemplate, PromptTemplate.id == PromptTemplateVersion.template_id)
        .where(PromptTemplateVersion.published_at.isnot(None))
        .order_by(PromptTemplate.key, PromptTemplateVersion.version.desc())
    ).all()
    return ScopeLLMOptions(
        models=[ScopeModelOption.model_validate(dict(m._mapping)) for m in models],
        prompt_versions=[
            ScopePromptOption.model_validate(dict(v._mapping)) for v in versions
        ],
    )


@router.get("/{scope_id}/llm-options", response_model=ScopeLLMOptions)
def get_options(
    scope_id: UUID,
    _: object = ScopeAdmin,
    db: Session = Depends(get_db),
) -> ScopeLLMOptions:
    return _options(db)


@router.get("/{scope_id}/llm-settings", response_model=ScopeSettingsOut)
def get_settings(
    scope_id: UUID,
    _: object = ScopeAdmin,
    db: Session = Depends(get_db),
) -> ScopeSettingsOut:
    row = db.get(ScopeLLMSettings, scope_id)
    return (
        ScopeSettingsOut.model_validate(row)
        if row
        else ScopeSettingsOut(scope_id=scope_id)
    )


@router.put("/{scope_id}/llm-settings", response_model=ScopeSettingsOut)
def put_settings(
    scope_id: UUID,
    body: ScopeSettingsUpdate,
    _: object = ScopeAdmin,
    user: UserNew = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ScopeSettingsOut:
    """Save with a revision check: lock_version 0 creates, otherwise it must match."""
    options = _options(db)
    if body.model_id and body.model_id not in {m.id for m in options.models}:
        raise HTTPException(status_code=422, detail="Model is not enabled")
    published = {v.id: v.strategy for v in options.prompt_versions}
    for strategy in ("skeptic", "advocate"):
        chosen = getattr(body, f"{strategy}_prompt_version_id")
        if chosen and published.get(chosen) != strategy:
            raise HTTPException(
                status_code=422,
                detail=f"{strategy} prompt version must be a published {strategy} prompt",
            )
    if body.enabled and body.model_id is None:
        raise HTTPException(status_code=422, detail="Enabling requires a model")

    values = body.model_dump(exclude={"lock_version"})
    row = db.get(ScopeLLMSettings, scope_id)
    if row is None and body.lock_version != 0:
        raise HTTPException(status_code=409, detail=STALE)
    audit(
        db,
        user,
        "scope_llm_settings",
        scope_id,
        "UPDATE" if row else "CREATE",
        values,
        scope_id=scope_id,
    )
    if row is None:
        db.add(ScopeLLMSettings(scope_id=scope_id, updated_by=user.id, **values))
        try:
            db.commit()
        except IntegrityError:  # created concurrently
            db.rollback()
            raise HTTPException(status_code=409, detail=STALE) from None
    else:
        save_revision(
            db,
            ScopeLLMSettings,
            scope_id,
            body.lock_version,
            {**values, "updated_by": user.id, "updated_at": func.now()},
        )
    db.expire_all()
    return ScopeSettingsOut.model_validate(db.get(ScopeLLMSettings, scope_id))
