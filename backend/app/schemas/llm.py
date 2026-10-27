"""LLM configuration API schemas (#489). No response model carries a key or ciphertext."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

ProviderKind = Literal["openai_compatible", "anthropic", "mock"]
Strategy = Literal["skeptic", "advocate"]
# A pinned model id ends in its release date: claude-x-20250929, gpt-4o-2024-08-06.
DATED_MODEL_ID = r"^[A-Za-z0-9][A-Za-z0-9._:/-]*(\d{8}|\d{4}-\d{2}-\d{2})$"


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Revision(BaseModel):
    lock_version: int = Field(ge=0)


class ProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: ProviderKind
    base_url: str = Field(min_length=1, max_length=2048)
    enabled: bool = True


class ProviderUpdate(Revision):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    base_url: str | None = Field(default=None, min_length=1, max_length=2048)
    enabled: bool | None = None


class ProviderKey(BaseModel):
    """Validation errors carry the field input; masking it first keeps keys out of 422s."""

    api_key: SecretStr

    @model_validator(mode="before")
    @classmethod
    def _mask(cls, data: Any) -> Any:
        if not isinstance(data, dict):  # a bare string body may itself be the key
            data = {}
        value = data.get("api_key")
        return {**data, "api_key": SecretStr(value if isinstance(value, str) else "")}

    @field_validator("api_key")
    @classmethod
    def _length(cls, value: SecretStr) -> SecretStr:
        if not 1 <= len(value.get_secret_value()) <= 4096:
            raise ValueError("api_key must be a string of 1 to 4096 characters")
        return value


class ProviderOut(_Out):
    id: UUID
    name: str
    kind: ProviderKind
    base_url: str
    enabled: bool
    lock_version: int
    has_key: bool = False
    key_fingerprint: str | None = None
    created_at: datetime


class ModelCreate(BaseModel):
    provider_id: UUID
    model_id: str = Field(pattern=DATED_MODEL_ID, max_length=200)
    input_price_per_mtok_cents: Decimal = Field(ge=0, max_digits=12, decimal_places=4)
    output_price_per_mtok_cents: Decimal = Field(ge=0, max_digits=12, decimal_places=4)
    max_tokens: int = Field(gt=0, le=200_000)
    timeout_s: int = Field(default=60, ge=30, le=60)
    uses_max_completion_tokens: bool = False
    enabled: bool = True


class ModelUpdate(Revision):
    input_price_per_mtok_cents: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=4
    )
    output_price_per_mtok_cents: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=4
    )
    max_tokens: int | None = Field(default=None, gt=0, le=200_000)
    timeout_s: int | None = Field(default=None, ge=30, le=60)
    uses_max_completion_tokens: bool | None = None
    enabled: bool | None = None


class ModelOut(_Out):
    id: UUID
    provider_id: UUID
    model_id: str
    input_price_per_mtok_cents: Decimal
    output_price_per_mtok_cents: Decimal
    max_tokens: int
    timeout_s: int
    uses_max_completion_tokens: bool
    enabled: bool
    lock_version: int


class PingRequest(BaseModel):
    model_id: UUID | None = None


class PingOut(BaseModel):
    ok: bool
    model: str
    latency_ms: int
    error_code: str | None = None


class TemplateCreate(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]{0,99}$")
    strategy: Strategy
    description: str | None = Field(default=None, max_length=2000)


class TemplateOut(_Out):
    id: UUID
    key: str
    strategy: Strategy
    description: str | None
    created_at: datetime


class VersionCreate(BaseModel):
    system_text: str = Field(min_length=1, max_length=50_000)
    user_text: str = Field(min_length=1, max_length=50_000)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    few_shot_examples: list[Any] = Field(default_factory=list)


class VersionUpdate(Revision):
    system_text: str | None = Field(default=None, min_length=1, max_length=50_000)
    user_text: str | None = Field(default=None, min_length=1, max_length=50_000)
    output_schema: dict[str, Any] | None = None
    few_shot_examples: list[Any] | None = None


class VersionOut(_Out):
    id: UUID
    template_id: UUID
    version: int
    system_text: str
    user_text: str
    output_schema: dict[str, Any]
    few_shot_examples: list[Any]
    sha256: str | None
    published_at: datetime | None
    derived_from: UUID | None
    lock_version: int
    created_at: datetime


class VersionDiff(BaseModel):
    from_id: UUID
    to_id: UUID
    system_diff: str
    user_diff: str
    output_schema_changed: bool
    few_shot_examples_changed: bool


class UsageRow(BaseModel):
    scope_id: UUID
    runs: int
    input_tokens: int
    output_tokens: int
    cost_cents: Decimal


class RunOut(_Out):
    id: UUID
    curation_id: UUID | None
    scope_id: UUID
    strategy: Strategy
    llm_model_id: UUID | None
    model_id: str
    prompt_version_id: UUID | None
    prompt_sha256: str | None
    methodology_version_id: UUID | None
    status: str
    input_tokens: int
    output_tokens: int
    cost_cents: Decimal
    duration_ms: int | None
    error_code: str | None
    request_sha256: str | None
    created_at: datetime
    finished_at: datetime | None


class ScopeSettingsUpdate(Revision):
    enabled: bool
    model_id: UUID | None = None
    skeptic_prompt_version_id: UUID | None = None
    advocate_prompt_version_id: UUID | None = None
    monthly_token_cap: int = Field(default=0, ge=0, le=10**12)
    monthly_cost_cap_cents: int = Field(default=0, ge=0, le=10**9)
    daily_run_cap: int = Field(default=0, ge=0, le=10**6)


class ScopeSettingsOut(_Out):
    scope_id: UUID
    enabled: bool = False
    model_id: UUID | None = None
    skeptic_prompt_version_id: UUID | None = None
    advocate_prompt_version_id: UUID | None = None
    monthly_token_cap: int = 0
    monthly_cost_cap_cents: int = 0
    daily_run_cap: int = 0
    lock_version: int = 0  # 0: never saved


class ScopeModelOption(BaseModel):
    id: UUID
    model_id: str
    provider_name: str


class ScopePromptOption(BaseModel):
    id: UUID
    template_key: str
    strategy: Strategy
    version: int


class ScopeLLMOptions(BaseModel):
    models: list[ScopeModelOption]
    prompt_versions: list[ScopePromptOption]
