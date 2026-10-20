"""Behaviour tests for the HPO (OLS) validator (HTTP boundary mocked via MockTransport)."""

import httpx
import pytest

from app.services.validators.hpo_validator import HPO_API_BASE, HPOValidator

SEIZURE = {
    "label": "Seizure",
    "obo_id": "HP:0001250",
    "description": ["A seizure is an abnormal..."],
    "synonyms": ["Epileptic seizure", "Fits"],
}


def _use(validator: HPOValidator, handler) -> None:  # type: ignore[no-untyped-def]
    validator.client = httpx.AsyncClient(
        base_url=HPO_API_BASE, transport=httpx.MockTransport(handler)
    )


@pytest.fixture
def validator() -> HPOValidator:
    return HPOValidator()


@pytest.mark.asyncio
async def test_validate_returns_term_details(validator: HPOValidator) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json=SEIZURE)

    _use(validator, handler)
    result = await validator.validate("hp:0001250")

    assert len(seen) == 1
    assert "/ontologies/hp/terms/" in seen[0]
    assert seen[0].endswith("HP_0001250")
    assert result.is_valid is True
    assert result.data is not None
    assert result.data["term_id"] == "HP:0001250"
    assert result.data["term_name"] == "Seizure"
    assert result.data["definition"] == "A seizure is an abnormal..."
    assert result.data["synonyms"] == ["Epileptic seizure", "Fits"]
    await validator.close()


@pytest.mark.asyncio
async def test_validate_accepts_bare_numeric_id(validator: HPOValidator) -> None:
    _use(validator, lambda request: httpx.Response(200, json=SEIZURE))
    result = await validator.validate("0001250")

    assert result.is_valid is True
    assert result.data is not None
    assert result.data["term_id"] == "HP:0001250"
    await validator.close()


@pytest.mark.asyncio
async def test_validate_handles_scalar_description_and_synonym(
    validator: HPOValidator,
) -> None:
    payload = {"label": "X", "description": "plain text", "synonyms": "single"}
    _use(validator, lambda request: httpx.Response(200, json=payload))
    result = await validator.validate("HP:0000001")

    assert result.data is not None
    assert result.data["definition"] == "plain text"
    assert result.data["synonyms"] == ["single"]
    await validator.close()


@pytest.mark.asyncio
async def test_validate_missing_optional_fields(validator: HPOValidator) -> None:
    _use(validator, lambda request: httpx.Response(200, json={"label": "Bare"}))
    result = await validator.validate("HP:0000002")

    assert result.data is not None
    assert result.data["definition"] == ""
    assert result.data["synonyms"] == []
    await validator.close()


@pytest.mark.asyncio
async def test_validate_rejects_bad_format_without_request(
    validator: HPOValidator,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no HTTP call expected for malformed term")

    _use(validator, handler)
    result = await validator.validate("HP:12")

    assert result.status == "invalid"
    assert result.is_valid is False
    await validator.close()


@pytest.mark.asyncio
async def test_validate_404_searches_for_suggestions(validator: HPOValidator) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/ontologies/hp/terms/" in request.url.path:
            return httpx.Response(404)
        return httpx.Response(
            200,
            json={
                "response": {"docs": [{"obo_id": "HP:0001250"}, {"label": "no obo id"}]}
            },
        )

    _use(validator, handler)
    result = await validator.validate("HP:0009999")

    assert result.status == "not_found"
    assert result.suggestions == {"did_you_mean": ["HP:0001250"]}
    await validator.close()


@pytest.mark.asyncio
async def test_validate_404_with_failing_search_has_no_suggestions(
    validator: HPOValidator,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/ontologies/hp/terms/" in request.url.path:
            return httpx.Response(404)
        return httpx.Response(500)

    _use(validator, handler)
    result = await validator.validate("HP:0009999")

    assert result.status == "not_found"
    assert result.suggestions is None
    await validator.close()


@pytest.mark.asyncio
async def test_validate_server_error_reports_http_code(validator: HPOValidator) -> None:
    _use(validator, lambda request: httpx.Response(503))
    result = await validator.validate("HP:0001250")

    assert result.status == "error"
    assert result.error_code == "HTTP_503"
    await validator.close()


@pytest.mark.asyncio
async def test_validate_non_json_body_is_exception(validator: HPOValidator) -> None:
    _use(validator, lambda request: httpx.Response(200, text="<html>"))
    result = await validator.validate("HP:0001250")

    assert result.status == "error"
    assert result.error_code == "EXCEPTION"
    await validator.close()


@pytest.mark.asyncio
async def test_validate_timeout_and_connection_errors(validator: HPOValidator) -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    _use(validator, timeout)
    assert (await validator.validate("HP:0001250")).error_code == "TIMEOUT"

    def refused(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    _use(validator, refused)
    assert (await validator.validate("HP:0001250")).error_code == "EXCEPTION"
    await validator.close()


@pytest.mark.asyncio
async def test_batch_validate_maps_each_term(validator: HPOValidator) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("HP_0001250"):
            return httpx.Response(200, json=SEIZURE)
        return httpx.Response(404)

    _use(validator, handler)
    results = await validator.batch_validate(["HP:0001250", "HP:0000999"])

    assert results["HP:0001250"].is_valid is True
    assert results["HP:0000999"].status == "not_found"
    await validator.close()


def test_base_url_constant() -> None:
    assert HPO_API_BASE.startswith("https://")
