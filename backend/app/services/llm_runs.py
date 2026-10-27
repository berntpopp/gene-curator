"""LLM runs: enqueue under caps, the data-sharing serializer, request building, output checks.

Prompt and output text are never logged or stored; llm_runs keeps hashes and counts only.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import RootModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.llm.output import InvalidLLMOutputError, parse_structured_output
from app.llm.prompts import render_messages
from app.llm.providers import LLMProvider as Adapter, LLMProviderError, LLMRequest
from app.models import CurationNew, CurationSchema, Gene, UserNew
from app.models.llm import (
    LLMModel,
    LLMProvider,
    LLMRun,
    PromptTemplateVersion,
    ScopeLLMSettings,
)
from app.models.methodology import MethodologyVersion
from app.services.llm_config import (
    LLMCapError,
    call_config,
    check_run_allowed,
    month_start,
)

MTOK = Decimal(1_000_000)
PENDING = ("queued", "running")
GOLDEN_DIR = Path(__file__).parents[2] / "tests" / "llm_golden"


# --- data sharing ---------------------------------------------------------------


def _is_private_key(key: str) -> bool:
    k = key.lower()
    return k.endswith("_by") or "email" in k or "user" in k


def _public(value: Any) -> Any:
    """Curation content without user references (keys like created_by, user_id, email)."""
    if isinstance(value, dict):
        return {k: _public(v) for k, v in value.items() if not _is_private_key(str(k))}
    if isinstance(value, list):
        return [_public(v) for v in value]
    return value


def curation_values(db: Session, curation: CurationNew) -> dict[str, str]:
    """Allowlist serializer: the only curation data that ever reaches a provider.

    Curation content and public IDs (HGNC, MONDO); never user names, emails or user ids.
    """
    gene = db.get(Gene, curation.gene_id)
    methodology = db.execute(
        select(CurationSchema.name, CurationSchema.version)
        .join(MethodologyVersion, MethodologyVersion.schema_id == CurationSchema.id)
        .where(MethodologyVersion.id == curation.methodology_version_id)
    ).first()
    evidence = curation.evidence_data or {}
    content = {
        "evidence_data": _public(evidence),
        "computed_scores": _public(curation.computed_scores or {}),
        "computed_verdict": curation.computed_verdict,
    }
    return {
        "gene_symbol": gene.approved_symbol if gene else "",
        "hgnc_id": gene.hgnc_id if gene else "",
        "disease_name": str(evidence.get("disease_name") or ""),
        "mondo_id": str(evidence.get("mondo_id") or ""),
        "mode_of_inheritance": str(evidence.get("mode_of_inheritance") or ""),
        "methodology": f"{methodology[0]} {methodology[1]}" if methodology else "",
        "curation_data": json.dumps(content, sort_keys=True, default=str),
        "evidence_text": curation.computed_summary or "",
    }


def build_request(
    version: PromptTemplateVersion, values: dict[str, str], max_tokens: int
) -> LLMRequest:
    system, user = render_messages(version.system_text, version.user_text, values)
    return LLMRequest(
        system=system,
        user=user,
        max_tokens=max_tokens,
        output_schema=version.output_schema or None,
    )


def request_sha256(model_id: str, request: LLMRequest) -> str:
    canonical = json.dumps(
        [
            model_id,
            request.system,
            request.user,
            request.max_tokens,
            request.output_schema,
        ],
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


# --- output ---------------------------------------------------------------------

_JSON_TYPES: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
}


class _Object(RootModel[dict[str, Any]]):
    pass


def validate_output(text: str, schema: dict[str, Any]) -> dict[str, Any]:
    """Whole output or InvalidLLMOutputError; messages carry key names, never values.

    ponytail: checks top-level required keys, property types and enums only (jsonschema
    is disabled in pyproject); upgrade to full JSON Schema when nested output matters.
    """
    data = parse_structured_output(text, _Object).root
    missing = sorted(set(schema.get("required", [])) - data.keys())
    if missing:
        raise InvalidLLMOutputError(f"LLM output failed validation at: {missing}")
    for key, spec in (schema.get("properties") or {}).items():
        if key not in data:
            continue
        expected = _JSON_TYPES.get(spec.get("type", ""))
        value = data[key]
        wrong_type = expected is not None and (
            not isinstance(value, expected)
            or (isinstance(value, bool) and spec.get("type") != "boolean")
        )
        if wrong_type or ("enum" in spec and value not in spec["enum"]):
            raise InvalidLLMOutputError(f"LLM output failed validation at: ['{key}']")
    return data


def cost_cents(model: LLMModel, input_tokens: int, output_tokens: int) -> Decimal:
    cost = (
        input_tokens * model.input_price_per_mtok_cents
        + output_tokens * model.output_price_per_mtok_cents
    ) / MTOK
    return cost.quantize(Decimal("0.0001"))


# --- enqueue --------------------------------------------------------------------


def _scope_model(db: Session, model_id: UUID | None) -> tuple[LLMModel, LLMProvider]:
    row = db.execute(
        select(LLMModel, LLMProvider)
        .join(LLMProvider, LLMProvider.id == LLMModel.provider_id)
        .where(LLMModel.id == model_id, LLMModel.enabled, LLMProvider.enabled)
    ).first()
    if row is None:
        raise LLMCapError("model_disabled")
    return row[0], row[1]


def _published_version(db: Session, version_id: UUID | None) -> PromptTemplateVersion:
    version = db.get(PromptTemplateVersion, version_id) if version_id else None
    if version is None or version.published_at is None:
        raise LLMCapError("prompt_not_published")
    return version


def _reserve(db: Session, settings: ScopeLLMSettings, model: LLMModel) -> None:
    """Count every pending run at its worst case (max_tokens output) against the caps.

    ponytail: input tokens are unknown until the call, so a run can overshoot a monthly
    cap by its prompt size; estimate input from the rendered prompt if that matters.
    """
    start = month_start(datetime.now(UTC))
    tokens, cost, pending = db.execute(
        select(
            func.coalesce(func.sum(LLMRun.input_tokens + LLMRun.output_tokens), 0),
            func.coalesce(func.sum(LLMRun.cost_cents), 0),
            func.count(LLMRun.id).filter(LLMRun.status.in_(PENDING)),
        ).where(LLMRun.scope_id == settings.scope_id, LLMRun.created_at >= start)
    ).one()
    worst = (int(pending) + 1) * model.max_tokens
    if int(tokens) + worst > settings.monthly_token_cap:
        raise LLMCapError("monthly_token_cap")
    if Decimal(cost) + cost_cents(model, 0, worst) > settings.monthly_cost_cap_cents:
        raise LLMCapError("monthly_cost_cap")


def enqueue_run(db: Session, user: UserNew, curation_id: UUID, strategy: str) -> LLMRun:
    """Check opt-in, model, prompt and caps and insert a queued run, atomically.

    The scope's settings row is locked first, so two enqueues for one scope serialize and
    the second counts the first run. Any refusal raises LLMCapError (fail closed).
    """
    curation = db.get(CurationNew, curation_id)
    if curation is None:
        raise LLMCapError("curation_not_found")
    try:
        db.execute(
            select(ScopeLLMSettings.scope_id)
            .where(ScopeLLMSettings.scope_id == curation.scope_id)
            .with_for_update()
        )
        settings = check_run_allowed(db, curation.scope_id)
        model, _ = _scope_model(db, settings.model_id)
        version = _published_version(
            db, getattr(settings, f"{strategy}_prompt_version_id")
        )
        _reserve(db, settings, model)
        run = LLMRun(
            curation_id=curation.id,
            scope_id=curation.scope_id,
            strategy=strategy,
            llm_model_id=model.id,
            model_id=model.model_id,
            prompt_version_id=version.id,
            prompt_sha256=version.sha256,
            methodology_version_id=curation.methodology_version_id,
            status="queued",
            created_by=user.id,
        )
        db.add(run)
        db.commit()
    except LLMCapError:
        db.rollback()
        raise
    return run


# --- preview and call preparation -----------------------------------------------


@dataclass(frozen=True)
class PreparedCall:
    kind: str
    config: dict[str, Any]
    request: LLMRequest
    output_schema: dict[str, Any]
    model: LLMModel


def prepare_call(
    db: Session, curation: CurationNew, strategy: str, run: LLMRun | None = None
) -> PreparedCall:
    """Everything one call sends; blocking (DB, decrypt), so run it off the event loop.

    With a run: the model and prompt version it pinned at enqueue, still enabled and
    published, in a scope still opted in. Without: the preview of the scope's current
    choice, no key, and the scope need not be enabled yet.
    """
    settings = db.get(ScopeLLMSettings, curation.scope_id)
    if settings is None or (run is not None and not settings.enabled):
        raise LLMCapError("llm_disabled")
    model, provider = _scope_model(db, run.llm_model_id if run else settings.model_id)
    version = _published_version(
        db,
        run.prompt_version_id
        if run
        else getattr(settings, f"{strategy}_prompt_version_id"),
    )
    request = build_request(version, curation_values(db, curation), model.max_tokens)
    config = call_config(db, provider, model) if run else {}
    return PreparedCall(provider.kind, config, request, version.output_schema, model)


# --- golden set -----------------------------------------------------------------


def load_golden(directory: Path | None = None) -> list[dict[str, Any]]:
    directory = directory or GOLDEN_DIR
    cases: list[dict[str, Any]] = json.loads((directory / "cases.json").read_text())
    return cases


async def run_golden_case(
    adapter: Adapter,
    version: PromptTemplateVersion,
    case: dict[str, Any],
    max_tokens: int,
) -> dict[str, Any]:
    """One golden case: ok when the output validates and matches every `expect` pair."""
    request = build_request(version, case["values"], max_tokens)
    result: dict[str, Any] = {
        "case": case["name"],
        "ok": False,
        "error_code": None,
        "input_tokens": 0,
        "output_tokens": 0,
    }
    try:
        response = await adapter.complete(request)
    except LLMProviderError as exc:
        result["error_code"] = exc.code
        return result
    result["input_tokens"] = response.input_tokens
    result["output_tokens"] = response.output_tokens
    try:
        data = validate_output(response.text, version.output_schema)
    except InvalidLLMOutputError:
        result["error_code"] = "invalid_output"
        return result
    expect = case.get("expect", {})
    result["ok"] = all(data.get(k) == v for k, v in expect.items())
    if not result["ok"]:
        result["error_code"] = "unexpected_output"
    return result
