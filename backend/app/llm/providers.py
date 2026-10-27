"""LLM provider adapters (Anthropic Messages, OpenAI-compatible chat, mock) and registry.

Prompt text, output text and API keys are never logged here.
"""

import asyncio
from dataclasses import dataclass
from typing import Any, ClassVar, Protocol

import httpx

from app.core.logging import get_logger

from .ssrf import validate_base_url

logger = get_logger(__name__)

MIN_TIMEOUT_S = 30.0
MAX_TIMEOUT_S = 60.0
MAX_RETRIES = 2


class LLMProviderError(Exception):
    """Provider call failed. `code` is safe to store in llm_runs.error_code."""

    def __init__(self, code: str, status: int | None = None) -> None:
        super().__init__(code if status is None else f"{code} (HTTP {status})")
        self.code = code
        self.status = status


@dataclass(frozen=True)
class LLMRequest:
    system: str
    user: str
    max_tokens: int
    output_schema: dict[str, Any] | None = None


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int


class LLMProvider(Protocol):
    kind: ClassVar[str]

    async def complete(self, request: LLMRequest) -> LLMResponse: ...


def clamp_timeout(timeout_s: float) -> float:
    return min(max(timeout_s, MIN_TIMEOUT_S), MAX_TIMEOUT_S)


class _HTTPProvider:
    kind: ClassVar[str]
    path: ClassVar[str]
    backoff_s: ClassVar[tuple[float, ...]] = (1.0, 2.0)

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_s: float = MIN_TIMEOUT_S,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._url = validate_base_url(base_url, kind=self.kind).rstrip("/") + self.path
        self._api_key = api_key
        self.model = model
        self._timeout = clamp_timeout(timeout_s)
        self._transport = transport

    def __repr__(self) -> str:  # keep the key out of tracebacks and debug output
        return f"{type(self).__name__}(model={self.model!r})"

    def _headers(self) -> dict[str, str]:
        raise NotImplementedError

    def _payload(self, request: LLMRequest) -> dict[str, Any]:
        raise NotImplementedError

    def _parse(self, body: dict[str, Any]) -> LLMResponse:
        raise NotImplementedError

    async def complete(self, request: LLMRequest) -> LLMResponse:
        # One deadline for the whole call, retries and backoff included.
        try:
            async with asyncio.timeout(self._timeout):
                return await self._complete(request)
        except TimeoutError:
            raise LLMProviderError("timeout") from None

    async def _complete(self, request: LLMRequest) -> LLMResponse:
        payload = self._payload(
            request
        )  # built once: retries resend identical parameters
        async with httpx.AsyncClient(
            timeout=self._timeout, follow_redirects=False, transport=self._transport
        ) as client:
            for attempt in range(MAX_RETRIES + 1):
                try:
                    resp = await client.post(
                        self._url, json=payload, headers=self._headers()
                    )
                except httpx.TimeoutException:
                    raise LLMProviderError("timeout") from None
                except httpx.HTTPError:
                    raise LLMProviderError("connection_error") from None
                retryable = resp.status_code == 429 or resp.status_code >= 500
                if retryable and attempt < MAX_RETRIES:
                    logger.warning(
                        "LLM provider retry",
                        provider=self.kind,
                        status=resp.status_code,
                        attempt=attempt + 1,
                    )
                    await asyncio.sleep(self.backoff_s[attempt])
                    continue
                if resp.status_code != 200:
                    raise LLMProviderError("http_error", resp.status_code)
                try:
                    result = self._parse(resp.json())
                except (ValueError, KeyError, IndexError, TypeError):
                    raise LLMProviderError("bad_response") from None
                if result.model != self.model:
                    raise LLMProviderError("model_mismatch")
                return result
        raise AssertionError("unreachable")  # pragma: no cover


class AnthropicProvider(_HTTPProvider):
    kind = "anthropic"
    path = "/v1/messages"

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self._api_key, "anthropic-version": "2023-06-01"}

    def _payload(self, request: LLMRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": request.max_tokens,
            "system": request.system,
            "messages": [{"role": "user", "content": request.user}],
        }
        if request.output_schema is not None:
            payload["output_config"] = {
                "format": {"type": "json_schema", "schema": request.output_schema}
            }
        return payload

    def _parse(self, body: dict[str, Any]) -> LLMResponse:
        text = "".join(b["text"] for b in body["content"] if b.get("type") == "text")
        usage = body["usage"]
        return LLMResponse(
            text=text,
            model=body["model"],
            input_tokens=int(usage["input_tokens"]),
            output_tokens=int(usage["output_tokens"]),
        )


class OpenAICompatibleProvider(_HTTPProvider):
    kind = "openai_compatible"
    path = "/chat/completions"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    def _payload(self, request: LLMRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": request.max_tokens,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
        }
        if request.output_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "output",
                    "schema": request.output_schema,
                    "strict": True,
                },
            }
        return payload

    def _parse(self, body: dict[str, Any]) -> LLMResponse:
        usage = body["usage"]
        text = body["choices"][0]["message"]["content"]
        if not isinstance(text, str):  # refusals come back as content=null
            raise TypeError("message content is not text")
        return LLMResponse(
            text=text,
            model=body["model"],
            input_tokens=int(usage["prompt_tokens"]),
            output_tokens=int(usage["completion_tokens"]),
        )


class MockProvider:
    """Offline provider for tests and demos; returns `response_text` verbatim."""

    kind: ClassVar[str] = "mock"

    def __init__(
        self,
        *,
        base_url: str = "mock://",
        api_key: str = "",
        model: str = "mock-model",
        timeout_s: float = MIN_TIMEOUT_S,
        transport: httpx.AsyncBaseTransport | None = None,
        response_text: str = "{}",
    ) -> None:
        self.model = model
        self.response_text = response_text
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            text=self.response_text,
            model=self.model,
            input_tokens=len(request.system.split()) + len(request.user.split()),
            output_tokens=len(self.response_text.split()),
        )


class ProviderRegistry:
    """Maps llm_providers.kind to an adapter class, like scoring_registry for engines."""

    def __init__(self) -> None:
        self._providers: dict[str, type[Any]] = {}
        for cls in (AnthropicProvider, OpenAICompatibleProvider, MockProvider):
            self.register(cls)

    def register(self, cls: type[Any]) -> None:
        self._providers[cls.kind] = cls

    def kinds(self) -> list[str]:
        return list(self._providers)

    def create(self, kind: str, **config: Any) -> LLMProvider:
        cls = self._providers.get(kind)
        if cls is None:
            raise LLMProviderError("unknown_provider_kind")
        provider: LLMProvider = cls(**config)
        return provider


provider_registry = ProviderRegistry()
