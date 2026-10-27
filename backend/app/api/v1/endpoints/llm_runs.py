"""LLM runs (#489): run status, the data-sharing preview, and the admin prompt test run.

Run status: platform admins and admins of the run's scope (the 057 RLS policy). The
preview shows a scope admin exactly what a run would send, without calling anything.
"""

import asyncio
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import (
    get_current_active_user,
    get_current_admin_user,
    require_scope_role,
)
from app.core.enums import ScopeRole
from app.llm.prompts import PromptTemplateError
from app.llm.providers import provider_registry
from app.llm.ssrf import UnsafeURLError
from app.models import CurationNew, ScopeMembership, UserNew
from app.models.llm import LLMModel, LLMProvider, LLMRun, PromptTemplateVersion
from app.schemas.llm import RunOut
from app.services.llm_config import LLMCapError, call_config
from app.services.llm_runs import load_golden, prepare_call, run_golden_case

router = APIRouter()


class LLMPreview(BaseModel):
    model_id: str
    system: str
    user: str


class TestRunRequest(BaseModel):
    model_id: UUID


class TestRunCase(BaseModel):
    case: str
    ok: bool
    error_code: str | None
    input_tokens: int
    output_tokens: int


class TestRunOut(BaseModel):
    model: str
    passed: int
    total: int
    cases: list[TestRunCase]


def _is_scope_admin(db: Session, user: UserNew, scope_id: UUID) -> bool:
    return (
        db.scalar(
            select(ScopeMembership.id).where(
                ScopeMembership.scope_id == scope_id,
                ScopeMembership.user_id == user.id,
                ScopeMembership.role == ScopeRole.ADMIN.value,
                ScopeMembership.is_active,
                ScopeMembership.accepted_at.isnot(None),
            )
        )
        is not None
    )


@router.get("/llm-runs/{run_id}", response_model=RunOut)
def get_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    user: UserNew = Depends(get_current_active_user),
) -> LLMRun:
    run = db.get(LLMRun, run_id)  # RLS hides other scopes' runs in PostgreSQL
    if run is None or not (
        user.role.value == "admin" or _is_scope_admin(db, user, run.scope_id)
    ):
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get(
    "/scopes/{scope_id}/curations/{curation_id}/llm-preview",
    response_model=LLMPreview,
)
def preview(
    scope_id: UUID,
    curation_id: UUID,
    strategy: Literal["skeptic", "advocate"],
    _: object = Depends(require_scope_role(ScopeRole.ADMIN)),
    db: Session = Depends(get_db),
) -> LLMPreview:
    """Exactly what a run would send for this curation with the scope's current choice."""
    curation = db.get(CurationNew, curation_id)
    if curation is None or curation.scope_id != scope_id:
        raise HTTPException(status_code=404, detail="Curation not found")
    try:
        prepared = prepare_call(db, curation, strategy)
    except LLMCapError as exc:
        raise HTTPException(status_code=422, detail=exc.code) from None
    return LLMPreview(
        model_id=prepared.model.model_id,
        system=prepared.request.system,
        user=prepared.request.user,
    )


@router.post(
    "/admin/llm/prompt-versions/{version_id}/test-run", response_model=TestRunOut
)
async def test_run(
    version_id: UUID,
    body: TestRunRequest,
    db: Session = Depends(get_db),
    _: UserNew = Depends(get_current_admin_user),
) -> TestRunOut:
    """Run a prompt version (draft or published) over the golden set with one model."""

    def prepare() -> tuple[PromptTemplateVersion, LLMModel, str, dict[str, Any]]:
        version = db.get(PromptTemplateVersion, version_id)
        row = db.execute(
            select(LLMModel, LLMProvider)
            .join(LLMProvider, LLMProvider.id == LLMModel.provider_id)
            .where(LLMModel.id == body.model_id)
        ).first()
        if version is None or row is None:
            raise HTTPException(status_code=404, detail="Not found")
        return version, row[0], row[1].kind, call_config(db, row[1], row[0])

    version, model, kind, config = await asyncio.to_thread(prepare)
    try:
        cases = load_golden()
    except FileNotFoundError:
        raise HTTPException(
            status_code=503, detail="Golden set not installed"
        ) from None
    try:
        adapter = await provider_registry.acreate(kind, **config)
        results = [
            await run_golden_case(adapter, version, case, model.max_tokens)
            for case in cases
        ]
    except (UnsafeURLError, PromptTemplateError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return TestRunOut(
        model=model.model_id,
        passed=sum(r["ok"] for r in results),
        total=len(results),
        cases=[TestRunCase(**r) for r in results],
    )
