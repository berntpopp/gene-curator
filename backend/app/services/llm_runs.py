"""LLM runs: enqueue under caps, the data-sharing serializer, request building, output checks.

Prompt and output text are never logged or stored; llm_runs keeps hashes and counts only.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import RootModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.llm.output import InvalidLLMOutputError, parse_structured_output
from app.llm.prompts import render_messages, wrap_untrusted
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
from app.schemas.curation import disease_fields
from app.scoring.point_limits import scoring_configuration
from app.services.llm_config import (
    LLMCapError,
    call_config,
    check_run_allowed,
    month_start,
)
from app.services.llm_second_view import cited_findings, proposal

MTOK = Decimal(1_000_000)
PENDING = ("queued", "running")
GOLDEN_DIR = Path(__file__).parents[1] / "llm" / "golden"


# --- data sharing ---------------------------------------------------------------


# The only evidence_data keys (at any depth) sent to a provider: the evidence facts of the
# seeded schemas. Curator judgement (points, score status, rationale, impact, replication,
# summaries) is left out so the second view stays blind (#464); the postgres test
# tests/postgres/test_llm_shared_fields.py lists those keys as excluded.
# Anything else, e.g. a curator_name a custom schema adds, is dropped. ponytail: custom
# schema fields need adding here; upgrade to a per-field share flag in the schema.
SHARED_EVIDENCE_KEYS = frozenset(
    {
        "age",
        "aggregate_variant_analysis",
        "analysis_type",
        "assay_method",
        "autosomal_dominant_or_x_linked",
        "autosomal_recessive",
        "biochemical_function",
        "case_control",
        "case_control_data",
        "case_level",
        "case_level_data",
        "cases_total",
        "cases_with_variant",
        "cases_with_variants",
        "cell_culture",
        "cell_culture_model",
        "cell_line",
        "cell_type",
        "clinical_assessment",
        "confidence_interval",
        "consanguinity",
        "contradictory_evidence",
        "controls_total",
        "controls_with_variant",
        "controls_with_variants",
        "de_novo",
        "description",
        "disease_mechanism_relevance",
        "disease_name",
        "disease_relevance",
        "disease_tissue_relevance",
        "entity_definition",
        "ethnicity",
        "evidence_type",
        "experimental_category",
        "experimental_evidence",
        "expression",
        "expression_method",
        "family_label",
        "function",
        "functional_alteration",
        "functional_data",
        "functional_effect",
        "gene_function_description",
        "genetic_evidence",
        "human",
        "human_phenotype_match",
        "inheritance_pattern_match",
        "initial_assessment",
        "interacting_protein",
        "interaction_method",
        "key_references",
        "label",
        "literature_review",
        "literature_search_strategy",
        "lod_score",
        "lod_score_method",
        "lumping_splitting",
        "methods",
        "mode_of_inheritance",
        "model_type",
        "models",
        "modification",
        "mondo_id",
        "non_human_model_organism",
        "non_patient_cells",
        "odds_ratio",
        "organism",
        "other_variant_type",
        "p_value",
        "paternity_maternity_confirmed",
        "patient_cells",
        "pedigree_description",
        "phase_confirmed",
        "phenotype_observed",
        "phenotype_rescued",
        "phenotypes",
        "pmid",
        "predicted_or_proven_null",
        "previous_testing",
        "proband_label",
        "proband_with_variant",
        "protein_interaction",
        "rescue",
        "rescue_extent",
        "rescue_method",
        "sections",
        "segregation",
        "segregation_data",
        "segregations",
        "sex",
        "single_variant_analysis",
        "statistical_test",
        "study_label",
        "tissue_organ",
        "variant",
        "variant_1",
        "variant_2",
        "variant_engineered",
        "variant_tested",
        "variant_type",
        "zygosity",
    }
)


def _shared(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _shared(v) for k, v in value.items() if k in SHARED_EVIDENCE_KEYS}
    if isinstance(value, list):
        return [_shared(v) for v in value]
    return value


MONDO_ID = re.compile(r"MONDO:\d{7}")
MOI_CODES = frozenset(
    {
        "AD",
        "AR",
        "XL",
        "XLD",
        "XLR",
        "MT",
        "SD",
        "Other",
        "autosomal_dominant",
        "autosomal_recessive",
        "x_linked",
        "x_linked_dominant",
        "x_linked_recessive",
        "mitochondrial",
        "semidominant",
        "unknown",
    }
)


def _typed(name: str, value: str, trusted: bool) -> str:
    """Curator-typed values go to trusted placeholders only when they are a strict
    ID or code; anything else is wrapped as untrusted data like free text."""
    return value if trusted or not value else wrap_untrusted(name, value)


def curation_values(db: Session, curation: CurationNew) -> dict[str, str]:
    """Allowlist serializer: the only curation data that ever reaches a provider.

    Allowlisted curation content and public IDs (HGNC, MONDO); never user names,
    emails or user ids.
    """
    gene = db.get(Gene, curation.gene_id)
    methodology = db.execute(
        select(CurationSchema.name, CurationSchema.version)
        .join(MethodologyVersion, MethodologyVersion.schema_id == CurationSchema.id)
        .where(MethodologyVersion.id == curation.methodology_version_id)
    ).first()
    evidence = curation.evidence_data or {}
    # Blind (#464): no scores, class or verdict rationale; the model judges the evidence.
    content = {"evidence_data": _shared(evidence)}
    precuration = curation.precuration
    fields = disease_fields(
        evidence, precuration.evidence_data if precuration else None
    )
    disease, mondo, moi = (
        str(fields[k] or "")
        for k in ("disease_name", "mondo_id", "mode_of_inheritance")
    )
    return {
        "gene_symbol": gene.approved_symbol if gene else "",
        "hgnc_id": gene.hgnc_id if gene else "",
        "disease_name": _typed("disease_name", disease, False),
        "mondo_id": _typed("mondo_id", mondo, MONDO_ID.fullmatch(mondo) is not None),
        "mode_of_inheritance": _typed("mode_of_inheritance", moi, moi in MOI_CODES),
        "methodology": f"{methodology[0]} {methodology[1]}" if methodology else "",
        "curation_data": json.dumps(content, sort_keys=True, default=str),
        "evidence_text": "",  # was the verdict rationale; kept so older prompts render
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
    in_scope = (LLMRun.scope_id == settings.scope_id, LLMRun.created_at >= start)
    tokens, cost = db.execute(
        select(
            func.coalesce(func.sum(LLMRun.input_tokens + LLMRun.output_tokens), 0),
            func.coalesce(func.sum(LLMRun.cost_cents), 0),
        ).where(*in_scope)
    ).one()
    # each pending run at its own pinned model's worst case; the current one if deleted
    limit = func.coalesce(LLMModel.max_tokens, model.max_tokens)
    price = func.coalesce(
        LLMModel.output_price_per_mtok_cents, model.output_price_per_mtok_cents
    )
    pending_tokens, pending_cost = db.execute(
        select(
            func.coalesce(func.sum(limit), 0),
            func.coalesce(func.sum(limit * price), 0),
        )
        .select_from(LLMRun)
        .outerjoin(LLMModel, LLMModel.id == LLMRun.llm_model_id)
        .where(*in_scope, LLMRun.status.in_(PENDING))
    ).one()
    worst_tokens = int(tokens) + int(pending_tokens) + model.max_tokens
    if worst_tokens > settings.monthly_token_cap:
        raise LLMCapError("monthly_token_cap")
    worst_cost = (
        Decimal(cost)
        + Decimal(pending_cost) / MTOK
        + cost_cents(model, 0, model.max_tokens)
    )
    if worst_cost > settings.monthly_cost_cap_cents:
        raise LLMCapError("monthly_cost_cap")


def enqueue_run(
    db: Session,
    user: UserNew,
    curation_id: UUID,
    strategy: str,
    *,
    exclusive: bool = False,
) -> LLMRun:
    """Check opt-in, model, prompt and caps and insert a queued run, atomically.

    A per-scope advisory lock is taken first, so two enqueues for one scope serialize and
    the second counts the first run. `exclusive` also refuses while the curation has a
    pending run. Any refusal raises LLMCapError (fail closed).
    """
    curation = db.get(CurationNew, curation_id)
    if curation is None:
        raise LLMCapError("curation_not_found")
    try:
        if db.get_bind().dialect.name == "postgresql":
            # not FOR UPDATE on the settings row: RLS hides it from reviewers' locks
            db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"),
                {"k": f"llm_enqueue:{curation.scope_id}"},
            )
        if exclusive and db.scalar(
            select(LLMRun.id)
            .where(LLMRun.curation_id == curation.id, LLMRun.status.in_(PENDING))
            .limit(1)
        ):
            raise LLMCapError("already_pending")
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
    scoring_config: dict[str, Any]


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
    scoring = scoring_configuration(
        db,
        curation.workflow_pair_id,
        run.methodology_version_id if run else curation.methodology_version_id,
    )
    return PreparedCall(
        provider.kind, config, request, version.output_schema, model, scoring
    )


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
    strategy: str = "skeptic",
) -> dict[str, Any]:
    """One golden case: ok when the output validates and meets `expect`.

    `classification`: the engine's class (ClinGen SOP v11 defaults) for the proposed
    evidence, i.e. agreement with the expert class. `flags`: categories the skeptic must
    raise as cited findings (not checked for the advocate). Other keys: equal output keys.
    """
    # evidence_text: older prompts still name it; the blind view sends it empty
    values = {"evidence_text": "", **case["values"]}
    request = build_request(version, values, max_tokens)
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
    expect = dict(case.get("expect", {}))
    flags = set(expect.pop("flags", []))
    classification = expect.pop("classification", None)
    try:
        verdict = proposal(data, {})[1] if classification else None
    except InvalidLLMOutputError:
        result["error_code"] = "invalid_output"
        return result
    raised = {f["category"] for f in cited_findings(data)}
    result["ok"] = (
        all(data.get(k) == v for k, v in expect.items())
        and verdict == classification
        and (strategy != "skeptic" or flags <= raised)
    )
    if not result["ok"]:
        result["error_code"] = "unexpected_output"
    return result
