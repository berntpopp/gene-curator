"""Provider adapters over httpx.MockTransport: no network, no secrets in logs."""

import json
import logging
import socket
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.llm import providers
from app.llm.providers import (
    AnthropicProvider,
    LLMProviderError,
    LLMRequest,
    MockProvider,
    OpenAICompatibleProvider,
    clamp_timeout,
    provider_registry,
)
from app.llm.ssrf import UnsafeURLError

API_KEY = "sk-live-SUPERSECRET-123"
PROMPT_MARKER = "PATIENT-FREE-TEXT-xyz"
OUTPUT_MARKER = "MODEL-OUTPUT-abc"
MODEL = "claude-opus-5-5"
REQ = LLMRequest(
    system="sys", user=PROMPT_MARKER, max_tokens=256, output_schema={"type": "object"}
)

Handler = Callable[[httpx.Request], httpx.Response]


@pytest.fixture(autouse=True)
def _public_dns_no_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, *a, **k: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port))
        ],
    )
    monkeypatch.setattr(providers._HTTPProvider, "backoff_s", (0.0, 0.0))


def anthropic_body(model: str = MODEL) -> dict[str, Any]:
    return {
        "model": model,
        "content": [{"type": "text", "text": OUTPUT_MARKER}],
        "usage": {"input_tokens": 11, "output_tokens": 7},
    }


def openai_body(model: str = "gpt-x-2026-01-01") -> dict[str, Any]:
    return {
        "model": model,
        "choices": [{"message": {"content": OUTPUT_MARKER}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3},
    }


def make(cls: type[Any], handler: Handler, model: str = MODEL, **kw: Any) -> Any:
    return cls(
        base_url="https://llm.example.org/",
        api_key=API_KEY,
        model=model,
        transport=httpx.MockTransport(handler),
        **kw,
    )


@pytest.mark.asyncio
async def test_anthropic_request_shape_and_parse() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=anthropic_body())

    result = await make(AnthropicProvider, handler).complete(REQ)
    assert (result.text, result.input_tokens, result.output_tokens) == (
        OUTPUT_MARKER,
        11,
        7,
    )
    sent = seen[0]
    assert str(sent.url) == "https://llm.example.org/v1/messages"
    assert sent.headers["x-api-key"] == API_KEY
    assert sent.headers["anthropic-version"] == "2023-06-01"
    body = json.loads(sent.content)
    assert body["model"] == MODEL and body["system"] == "sys"
    assert body["output_config"]["format"]["type"] == "json_schema"


@pytest.mark.asyncio
async def test_openai_compatible_request_shape_and_parse() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=openai_body())

    provider = make(OpenAICompatibleProvider, handler, model="gpt-x-2026-01-01")
    result = await provider.complete(LLMRequest(system="s", user="u", max_tokens=10))
    assert (result.text, result.input_tokens, result.output_tokens) == (
        OUTPUT_MARKER,
        5,
        3,
    )
    assert str(seen[0].url) == "https://llm.example.org/chat/completions"
    assert seen[0].headers["authorization"] == f"Bearer {API_KEY}"
    assert "response_format" not in json.loads(seen[0].content)
    assert API_KEY not in repr(provider)


@pytest.mark.asyncio
async def test_openai_compatible_sends_native_schema() -> None:
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=openai_body())

    await make(OpenAICompatibleProvider, handler, model="gpt-x-2026-01-01").complete(
        REQ
    )
    assert bodies[0]["response_format"]["json_schema"]["schema"] == {"type": "object"}


@pytest.mark.asyncio
async def test_model_must_match_pin() -> None:
    provider = make(
        AnthropicProvider,
        lambda r: httpx.Response(200, json=anthropic_body("claude-other")),
    )
    with pytest.raises(LLMProviderError) as exc:
        await provider.complete(REQ)
    assert exc.value.code == "model_mismatch"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [429, 500, 503])
async def test_retries_twice_on_429_and_5xx_with_same_payload(status: int) -> None:
    bodies: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(request.content)
        return httpx.Response(status if len(bodies) < 3 else 200, json=anthropic_body())

    assert (await make(AnthropicProvider, handler).complete(REQ)).text == OUTPUT_MARKER
    assert len(bodies) == 3 and len(set(bodies)) == 1


@pytest.mark.asyncio
async def test_gives_up_after_two_retries() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(503)

    with pytest.raises(LLMProviderError) as exc:
        await make(AnthropicProvider, handler).complete(REQ)
    assert (exc.value.code, exc.value.status, len(calls)) == ("http_error", 503, 3)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 302])
async def test_no_retry_or_redirect_on_other_status(status: int) -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(status, headers={"location": "http://169.254.169.254/"})

    with pytest.raises(LLMProviderError):
        await make(AnthropicProvider, handler).complete(REQ)
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exc", "code"),
    [
        (httpx.ReadTimeout("t"), "timeout"),
        (httpx.ConnectError("c"), "connection_error"),
    ],
)
async def test_transport_errors_map_to_codes(exc: Exception, code: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc

    with pytest.raises(LLMProviderError) as err:
        await make(AnthropicProvider, handler).complete(REQ)
    assert err.value.code == code


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [b"not json", b'{"model": "claude-opus-5-5"}'])
async def test_malformed_response_is_bad_response(body: bytes) -> None:
    provider = make(AnthropicProvider, lambda r: httpx.Response(200, content=body))
    with pytest.raises(LLMProviderError) as exc:
        await provider.complete(REQ)
    assert exc.value.code == "bad_response"


def test_timeout_clamped_to_30_60() -> None:
    assert (clamp_timeout(1), clamp_timeout(45), clamp_timeout(600)) == (30, 45, 60)
    provider = make(AnthropicProvider, lambda r: httpx.Response(200), timeout_s=999)
    assert provider._timeout == 60


def test_constructor_applies_ssrf_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, *a, **k: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", port))
        ],
    )
    with pytest.raises(UnsafeURLError):
        make(AnthropicProvider, lambda r: httpx.Response(200))


@pytest.mark.asyncio
async def test_registry_and_mock_provider() -> None:
    assert set(provider_registry.kinds()) == {"anthropic", "openai_compatible", "mock"}
    mock = provider_registry.create(
        "mock", model="mock-1", response_text='{"ok": true}'
    )
    assert isinstance(mock, MockProvider)
    result = await mock.complete(REQ)
    assert (result.model, result.text) == ("mock-1", '{"ok": true}')
    assert mock.requests == [REQ]
    with pytest.raises(LLMProviderError):
        provider_registry.create("jinja")


@pytest.mark.asyncio
async def test_keys_prompts_and_outputs_never_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    statuses = iter([429, 200, 500, 500, 500])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(next(statuses), json=anthropic_body())

    provider = make(AnthropicProvider, handler)
    await provider.complete(REQ)
    with pytest.raises(LLMProviderError):
        await provider.complete(REQ)
    assert "LLM provider retry" in caplog.text  # the capture works
    for marker in (API_KEY, PROMPT_MARKER, OUTPUT_MARKER):
        assert marker not in caplog.text
