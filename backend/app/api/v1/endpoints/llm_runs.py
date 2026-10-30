"""LLM runs (#489): run status, the data-sharing preview, the admin prompt test run, and
the second view (#464, #465) reviewers request, read and decide on.

Run status: platform admins and admins of the run's scope. The preview shows a scope
admin exactly what a run would send, without calling anything. The second view is
advisory: no route here changes a curation, a review, a score or a workflow state.
"""

import asyncio
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.capabilities import REVIEW, require
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
from app.models.llm import (
    LLMFinding,
    LLMModel,
    LLMProvider,
    LLMRun,
    PromptTemplate,
    PromptTemplateVersion,
    ScopeLLMSettings,
)
from app.schemas.llm import FindingDecision, FindingOut, RunOut, SecondViewOut
from app.services.llm_config import LLMCapError, call_config
from app.services.llm_runs import (
    enqueue_run,
    load_golden,
    prepare_call,
    run_golden_case,
)
from app.services.llm_second_view import second_view

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

    def prepare() -> tuple[PromptTemplateVersion, str, LLMModel, str, dict[str, Any]]:
        version = db.get(PromptTemplateVersion, version_id)
        template = db.get(PromptTemplate, version.template_id) if version else None
        row = db.execute(
            select(LLMModel, LLMProvider)
            .join(LLMProvider, LLMProvider.id == LLMModel.provider_id)
            .where(LLMModel.id == body.model_id)
        ).first()
        if version is None or template is None or row is None:
            raise HTTPException(status_code=404, detail="Not found")
        config = call_config(db, row[1], row[0])
        return version, template.strategy, row[0], row[1].kind, config

    version, strategy, model, kind, config = await asyncio.to_thread(prepare)
    try:
        cases = load_golden()
    except FileNotFoundError:
        raise HTTPException(
            status_code=503, detail="Golden set not installed"
        ) from None
    try:
        adapter = await provider_registry.acreate(kind, **config)
        results = [
            await run_golden_case(adapter, version, case, model.max_tokens, strategy)
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


# --- second view (#464, #465) ----------------------------------------------------


def _reviewable(
    db: Session, user: UserNew, scope_id: UUID, curation_id: UUID
) -> CurationNew:
    require(db, user, scope_id, REVIEW)
    curation = db.get(CurationNew, curation_id)
    if curation is None or curation.scope_id != scope_id:
        raise HTTPException(status_code=404, detail="Curation not found")
    return curation


def _view(db: Session, curation: CurationNew) -> SecondViewOut:
    settings = db.get(ScopeLLMSettings, curation.scope_id)
    return SecondViewOut(
        enabled=bool(settings and settings.enabled), **second_view(db, curation)
    )


SECOND_VIEW = "/scopes/{scope_id}/curations/{curation_id}/llm-second-view"


@router.get(SECOND_VIEW, response_model=SecondViewOut)
def get_second_view(
    scope_id: UUID,
    curation_id: UUID,
    db: Session = Depends(get_db),
    user: UserNew = Depends(get_current_active_user),
) -> SecondViewOut:
    """Latest AI findings and the human vs advocate vs skeptic diff, for reviewers."""
    return _view(db, _reviewable(db, user, scope_id, curation_id))


@router.post(SECOND_VIEW, response_model=SecondViewOut, status_code=202)
def queue_second_view(
    scope_id: UUID,
    curation_id: UUID,
    db: Session = Depends(get_db),
    user: UserNew = Depends(get_current_active_user),
) -> SecondViewOut:
    """Queue a blind run per configured strategy; the worker runs them in the background."""
    curation = _reviewable(db, user, scope_id, curation_id)
    settings = db.get(ScopeLLMSettings, scope_id)
    strategies = [
        s
        for s in ("skeptic", "advocate")
        if settings and getattr(settings, f"{s}_prompt_version_id")
    ]
    refusal = "llm_disabled"
    queued = 0
    for strategy in strategies:
        try:
            # until one run is queued, refuse under the scope lock if another is pending
            enqueue_run(db, user, curation.id, strategy, exclusive=not queued)
            queued += 1
        except LLMCapError as exc:
            if exc.code == "already_pending":
                raise HTTPException(
                    status_code=409,
                    detail="A second view is already running for this curation; wait for it",
                ) from exc
            refusal = exc.code
    if not queued:
        raise HTTPException(status_code=422, detail=refusal)
    return _view(db, curation)


@router.patch("/llm-findings/{finding_id}", response_model=FindingOut)
def decide_finding(
    finding_id: UUID,
    body: FindingDecision,
    db: Session = Depends(get_db),
    user: UserNew = Depends(get_current_active_user),
) -> FindingOut:
    """Accept or dismiss one AI finding; the decision is recorded, nothing else changes."""
    finding = db.get(LLMFinding, finding_id)  # RLS hides other scopes' findings
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    curation = _reviewable(db, user, finding.scope_id, finding.curation_id)
    if curation.created_by == user.id:
        raise HTTPException(status_code=403, detail="Not on your own curation")
    finding.decision = body.decision
    finding.decided_by = user.id
    finding.decided_at = func.now()
    db.commit()
    db.refresh(finding)
    strategy = db.scalar(select(LLMRun.strategy).where(LLMRun.id == finding.run_id))
    return FindingOut.model_validate(
        {
            "id": finding.id,
            "strategy": strategy,
            "category": finding.category,
            "message": finding.message,
            "citations": list(finding.citations),
            "decision": finding.decision,
            "decided_at": finding.decided_at,
        }
    )
