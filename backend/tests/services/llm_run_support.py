"""A configured LLM scope on SQLite for the run, worker and preview tests."""

import functools
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import get_password_hash
from app.llm.providers import MockProvider, provider_registry
from app.models import CurationNew, Gene, Scope, ScopeMembership, UserNew
from app.models.llm import (
    LLMModel,
    LLMProvider,
    PromptTemplate,
    PromptTemplateVersion,
    ScopeLLMSettings,
)

SCHEMA = {
    "type": "object",
    "required": ["verdict"],
    "properties": {
        "verdict": {"type": "string", "enum": ["supported", "refuted"]},
        "confidence": {"type": "number"},
    },
}
GOOD = json.dumps({"verdict": "supported", "confidence": 0.9})


@dataclass
class World:
    scope_admin: UserNew
    curation: CurationNew
    settings: ScopeLLMSettings
    model: LLMModel
    provider: LLMProvider
    version: PromptTemplateVersion


def canned(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    """The mock provider kind answers `text` for every call."""
    monkeypatch.setitem(
        provider_registry._providers,
        "mock",
        functools.partial(MockProvider, response_text=text),
    )


def factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine)


@pytest.fixture(name="world")
def world_fixture(
    db_session: Session, test_scope: Scope, test_gene: Gene, test_curation: CurationNew
) -> World:
    admin = UserNew(
        id=uuid4(),
        email="scope.admin@private.example",
        hashed_password=get_password_hash("x"),
        name="Secret Person",
        role="user",
        is_active=True,
    )
    db_session.add(admin)
    db_session.flush()
    db_session.add(
        ScopeMembership(
            scope_id=test_scope.id,
            user_id=admin.id,
            role="admin",
            accepted_at=datetime.now(UTC),
        )
    )
    provider = LLMProvider(name="p", kind="mock", base_url="mock://")
    db_session.add(provider)
    db_session.flush()
    model = LLMModel(
        provider_id=provider.id,
        model_id="mock-model",
        input_price_per_mtok_cents=Decimal(100),
        output_price_per_mtok_cents=Decimal(300),
        max_tokens=100,
    )
    template = PromptTemplate(key="skeptic-1", strategy="skeptic")
    db_session.add_all([model, template])
    db_session.flush()
    version = PromptTemplateVersion(
        template_id=template.id,
        version=1,
        system_text="Review {gene_symbol} under {methodology}.",
        user_text="{hgnc_id} {disease_name} {curation_data} {evidence_text}",
        output_schema=SCHEMA,
        sha256="abc",
        published_at=datetime.now(UTC),
    )
    db_session.add(version)
    db_session.flush()
    settings = ScopeLLMSettings(
        scope_id=test_scope.id,
        enabled=True,
        model_id=model.id,
        skeptic_prompt_version_id=version.id,
        monthly_token_cap=10_000,
        monthly_cost_cap_cents=1_000,
        daily_run_cap=10,
    )
    test_curation.evidence_data = {
        "disease_name": "breast cancer",
        "mondo_id": "MONDO:0007254",
        "mode_of_inheritance": "autosomal dominant",
        "curator_email": "leak@private.example",
        "notes": [{"text": "segregates", "added_by": str(admin.id)}],
    }
    test_curation.computed_summary = "Strong evidence"
    db_session.add(settings)
    db_session.commit()
    return World(admin, test_curation, settings, model, provider, version)
