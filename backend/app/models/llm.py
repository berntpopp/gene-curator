"""LLM configuration: providers, write-only credentials, models, prompts, scope opt-in, runs (057)."""

import uuid
from datetime import datetime as dt
from decimal import Decimal
from typing import Any
from uuid import UUID as PyUUID  # noqa: N811

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, deferred, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.db_types import compatible_jsonb, compatible_uuid


def _pk() -> Mapped[PyUUID]:
    return mapped_column(compatible_uuid(), primary_key=True, default=uuid.uuid4)


def _user_fk() -> Mapped[PyUUID | None]:
    return mapped_column(compatible_uuid(), ForeignKey("users.id"))


def _now() -> Mapped[dt]:
    return mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LLMProvider(Base):
    __tablename__ = "llm_providers"

    id: Mapped[PyUUID] = _pk()
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[PyUUID | None] = _user_fk()
    created_at: Mapped[dt] = _now()
    updated_at: Mapped[dt] = _now()


class LLMCredential(Base):
    """Encrypted API key. The API role cannot SELECT `ciphertext` (column privileges)."""

    __tablename__ = "llm_credentials"

    id: Mapped[PyUUID] = _pk()
    provider_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("llm_providers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # deferred: ORM loads never select it; read through llm_credential_ciphertext()
    ciphertext: Mapped[bytes] = deferred(mapped_column(LargeBinary, nullable=False))
    key_id: Mapped[str] = mapped_column(Text, nullable=False)
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[PyUUID | None] = _user_fk()
    created_at: Mapped[dt] = _now()
    rotated_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True))


class LLMModel(Base):
    __tablename__ = "llm_models"

    id: Mapped[PyUUID] = _pk()
    provider_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("llm_providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    input_price_per_mtok_cents: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False
    )
    output_price_per_mtok_cents: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False
    )
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    timeout_s: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    uses_max_completion_tokens: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[PyUUID | None] = _user_fk()
    created_at: Mapped[dt] = _now()

    __table_args__ = (
        UniqueConstraint(
            "provider_id", "model_id", name="uq_llm_models_provider_model"
        ),
    )


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[PyUUID] = _pk()
    key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    strategy: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[PyUUID | None] = _user_fk()
    created_at: Mapped[dt] = _now()


class PromptTemplateVersion(Base):
    """Editable while a draft; the database refuses any change once published."""

    __tablename__ = "prompt_template_versions"

    id: Mapped[PyUUID] = _pk()
    template_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("prompt_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    system_text: Mapped[str] = mapped_column(Text, nullable=False)
    user_text: Mapped[str] = mapped_column(Text, nullable=False)
    output_schema: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), nullable=False, default=dict
    )
    few_shot_examples: Mapped[list[Any]] = mapped_column(
        compatible_jsonb(), nullable=False, default=list
    )
    sha256: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True))
    derived_from: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("prompt_template_versions.id")
    )
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[PyUUID | None] = _user_fk()
    created_at: Mapped[dt] = _now()

    __table_args__ = (
        UniqueConstraint(
            "template_id", "version", name="uq_prompt_template_versions_version"
        ),
    )


class ScopeLLMSettings(Base):
    """Per-scope opt-in. Caps default to 0: a scope without caps can run nothing."""

    __tablename__ = "scope_llm_settings"

    scope_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("scopes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    model_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("llm_models.id", ondelete="SET NULL")
    )
    skeptic_prompt_version_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("prompt_template_versions.id")
    )
    advocate_prompt_version_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("prompt_template_versions.id")
    )
    monthly_token_cap: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    monthly_cost_cap_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    daily_run_cap: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_by: Mapped[PyUUID | None] = _user_fk()
    updated_at: Mapped[dt] = _now()


class LLMRun(Base):
    """One provider call. Prompt and output text are never stored here or logged."""

    __tablename__ = "llm_runs"

    id: Mapped[PyUUID] = _pk()
    curation_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("curations.id", ondelete="SET NULL")
    )
    scope_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), ForeignKey("scopes.id", ondelete="CASCADE"), nullable=False
    )
    strategy: Mapped[str] = mapped_column(Text, nullable=False)
    llm_model_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("llm_models.id", ondelete="SET NULL")
    )
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("prompt_template_versions.id")
    )
    prompt_sha256: Mapped[str | None] = mapped_column(Text)
    methodology_version_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("methodology_versions.id")
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_cents: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal(0)
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(Text)
    request_sha256: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[PyUUID | None] = _user_fk()
    created_at: Mapped[dt] = _now()
    started_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True))
