"""LLM runs (#489): enqueue fails closed, data sharing allowlist, output validation, golden."""

import json
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm.output import InvalidLLMOutputError
from app.llm.providers import LLMProviderError, LLMRequest, LLMResponse, MockProvider
from app.models.llm import LLMRun
from app.services.llm_config import LLMCapError
from app.services.llm_runs import (
    curation_values,
    enqueue_run,
    load_golden,
    prepare_call,
    run_golden_case,
    validate_output,
)
from tests.api.llm_api_support import llm_env  # noqa: F401
from tests.llm_golden.eval import golden_version
from tests.services.llm_run_support import GOOD, SCHEMA, World, world_fixture  # noqa: F401

pytestmark = [pytest.mark.unit, pytest.mark.usefixtures("llm_env")]


def _refused(db: Session, w: World) -> str:
    with pytest.raises(LLMCapError) as exc:
        enqueue_run(db, w.scope_admin, w.curation.id, "skeptic")
    return exc.value.code


def test_enqueue_pins_model_prompt_and_methodology(
    db_session: Session, world: World
) -> None:
    run = enqueue_run(db_session, world.scope_admin, world.curation.id, "skeptic")
    assert run.status == "queued"
    assert (run.llm_model_id, run.model_id) == (world.model.id, "mock-model")
    assert (run.prompt_version_id, run.prompt_sha256) == (world.version.id, "abc")
    assert run.created_by == world.scope_admin.id
    assert run.methodology_version_id == world.curation.methodology_version_id


@pytest.mark.parametrize(
    ("change", "code"),
    [
        (lambda w: setattr(w.settings, "enabled", False), "llm_disabled"),
        (lambda w: setattr(w.model, "enabled", False), "model_disabled"),
        (lambda w: setattr(w.provider, "enabled", False), "model_disabled"),
        (lambda w: setattr(w.version, "published_at", None), "prompt_not_published"),
        (lambda w: setattr(w.settings, "daily_run_cap", 0), "daily_run_cap"),
        # worst case is max_tokens (100) of output per pending run
        (lambda w: setattr(w.settings, "monthly_token_cap", 99), "monthly_token_cap"),
    ],
)
def test_enqueue_fails_closed(
    db_session: Session, world: World, change: object, code: str
) -> None:
    change(world)  # type: ignore[operator]
    db_session.commit()
    assert _refused(db_session, world) == code
    assert db_session.scalars(select(LLMRun)).all() == []


def test_cost_cap_counts_pending_worst_case(db_session: Session, world: World) -> None:
    # one worst-case run costs 100 tokens x 300 cents/MTok = 0.03 cents
    world.settings.monthly_cost_cap_cents = 0
    db_session.commit()
    assert _refused(db_session, world) == "monthly_cost_cap"


def test_pending_runs_reserve_the_token_cap(db_session: Session, world: World) -> None:
    world.settings.monthly_token_cap = 150  # room for one worst-case run, not two
    db_session.commit()
    enqueue_run(db_session, world.scope_admin, world.curation.id, "skeptic")
    assert _refused(db_session, world) == "monthly_token_cap"


def test_unknown_curation_and_strategy_refused(
    db_session: Session, world: World
) -> None:
    with pytest.raises(LLMCapError, match="curation_not_found"):
        enqueue_run(db_session, world.scope_admin, uuid4(), "skeptic")
    with pytest.raises(LLMCapError, match="prompt_not_published"):
        enqueue_run(db_session, world.scope_admin, world.curation.id, "advocate")


def test_serializer_sends_content_and_public_ids_only(
    db_session: Session, world: World
) -> None:
    values = curation_values(db_session, world.curation)
    sent = json.dumps(values)
    assert values["gene_symbol"] == "BRCA1" and values["hgnc_id"] == "HGNC:1100"
    assert values["mondo_id"] == "MONDO:0007254"
    assert "segregates" in values["curation_data"]
    for private in ("leak@private.example", "scope.admin@private.example"):
        assert private not in sent
    assert "Secret Person" not in sent and str(world.scope_admin.id) not in sent
    assert "added_by" not in sent and "curator_email" not in sent


def test_preview_needs_no_key_or_opt_in(db_session: Session, world: World) -> None:
    world.settings.enabled = False
    db_session.commit()
    prepared = prepare_call(db_session, world.curation, "skeptic")
    assert prepared.config == {}
    assert prepared.request.system.startswith("Review BRCA1")
    assert "<untrusted_data" in prepared.request.user


@pytest.mark.parametrize(
    "text",
    [
        "[]",
        "not json",
        '{"confidence": 1}',
        '{"verdict": "maybe"}',
        '{"verdict": 1}',
        '{"verdict": "supported", "confidence": true}',
    ],
)
def test_invalid_output_is_rejected_without_values(text: str) -> None:
    with pytest.raises(InvalidLLMOutputError) as exc:
        validate_output(text, SCHEMA)
    assert "maybe" not in str(exc.value)


def test_valid_output_including_fenced() -> None:
    assert validate_output(f"```json\n{GOOD}\n```", SCHEMA)["verdict"] == "supported"
    assert validate_output('{"verdict": "refuted", "x": 1}', SCHEMA)["x"] == 1


class _Failing(MockProvider):
    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise LLMProviderError("http_error", 500)


@pytest.mark.asyncio
async def test_golden_cases_report_ok_unexpected_invalid_and_errors() -> None:
    version = golden_version()
    case = load_golden()[0]
    ok = MockProvider(response_text='{"verdict": "supported", "rationale": "r"}')
    result = await run_golden_case(ok, version, case, 100)
    assert result["ok"] and result["input_tokens"] > 0
    wrong = MockProvider(response_text='{"verdict": "refuted", "rationale": "r"}')
    assert (await run_golden_case(wrong, version, case, 100))["error_code"] == (
        "unexpected_output"
    )
    bad = MockProvider(response_text='{"verdict": "refuted"}')
    assert (await run_golden_case(bad, version, case, 100))["error_code"] == (
        "invalid_output"
    )
    assert (await run_golden_case(_Failing(), version, case, 100))["error_code"] == (
        "http_error"
    )


@pytest.mark.asyncio
async def test_every_golden_case_renders_through_the_golden_prompt() -> None:
    adapter = MockProvider(response_text="{}")
    for case in load_golden():
        await run_golden_case(adapter, golden_version(), case, 10)
    assert len(adapter.requests) == len(load_golden()) >= 3
    assert all("<untrusted_data" in r.user for r in adapter.requests)


def test_cost_uses_database_prices(db_session: Session, world: World) -> None:
    from app.services.llm_runs import cost_cents

    assert cost_cents(world.model, 1_000_000, 1_000_000) == Decimal(400)
