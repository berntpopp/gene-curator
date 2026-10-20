"""Behaviour tests for the HGNC validator (HTTP boundary mocked via MockTransport)."""

import httpx
import pytest

from app.services.validators.hgnc_validator import HGNC_API_BASE, HGNCValidator

BRCA1_DOC = {
    "symbol": "BRCA1",
    "hgnc_id": "HGNC:1100",
    "name": "BRCA1 DNA repair associated",
    "status": "Approved",
    "alias_symbol": ["BRCC1", "FANCS"],
    "prev_symbol": ["RNF53"],
    "locus_type": "gene with protein product",
    "location": "17q21.31",
}


def _json(payload: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=payload)


def _use(validator: HGNCValidator, handler) -> None:  # type: ignore[no-untyped-def]
    """Swap the validator's HTTP client for one that routes through handler."""
    validator.client = httpx.AsyncClient(
        base_url=HGNC_API_BASE,
        headers={"Accept": "application/json"},
        transport=httpx.MockTransport(handler),
    )


@pytest.fixture
def validator() -> HGNCValidator:
    return HGNCValidator()


@pytest.mark.asyncio
async def test_validate_returns_valid_result_for_known_symbol(
    validator: HGNCValidator,
) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return _json({"response": {"docs": [BRCA1_DOC]}})

    _use(validator, handler)
    result = await validator.validate("brca1")

    assert seen == ["/fetch/symbol/BRCA1"]  # symbol is upper-cased for the lookup
    assert result.is_valid is True
    assert result.status == "valid"
    assert result.data is not None
    assert result.data["approved_symbol"] == "BRCA1"
    assert result.data["hgnc_id"] == "HGNC:1100"
    assert result.data["alias_symbols"] == ["BRCC1", "FANCS"]
    assert result.data["previous_symbols"] == ["RNF53"]
    await validator.close()


@pytest.mark.asyncio
async def test_validate_404_returns_not_found_with_suggestions(
    validator: HGNCValidator,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/fetch/symbol/"):
            return httpx.Response(404)
        return _json({"response": {"docs": [{"symbol": "BRCA2"}, {"symbol": "BRCA1"}]}})

    _use(validator, handler)
    result = await validator.validate("BRCA3")

    assert result.is_valid is False
    assert result.status == "not_found"
    assert result.suggestions == {"did_you_mean": ["BRCA2", "BRCA1"]}
    assert "BRCA3" in (result.error_message or "")
    await validator.close()


@pytest.mark.asyncio
async def test_validate_404_without_usable_suggestions(
    validator: HGNCValidator,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/fetch/symbol/"):
            return httpx.Response(404)
        # Search endpoint fails -> no suggestions, still a clean not_found
        return httpx.Response(503)

    _use(validator, handler)
    result = await validator.validate("NOPE")

    assert result.status == "not_found"
    assert result.suggestions is None
    await validator.close()


@pytest.mark.asyncio
async def test_validate_404_with_malformed_search_body(
    validator: HGNCValidator,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/fetch/symbol/"):
            return httpx.Response(404)
        return _json({"unexpected": True})

    _use(validator, handler)
    result = await validator.validate("NOPE")

    assert result.status == "not_found"
    assert result.suggestions is None
    await validator.close()


@pytest.mark.asyncio
async def test_validate_server_error_is_reported_with_http_code(
    validator: HGNCValidator,
) -> None:
    _use(validator, lambda request: httpx.Response(500))
    result = await validator.validate("BRCA1")

    assert result.is_valid is False
    assert result.status == "error"
    assert result.error_code == "HTTP_500"
    await validator.close()


@pytest.mark.asyncio
async def test_validate_unexpected_body_shape_is_error(
    validator: HGNCValidator,
) -> None:
    _use(validator, lambda request: _json({"no_response_key": {}}))
    result = await validator.validate("BRCA1")

    assert result.status == "error"
    assert result.error_message == "Unexpected HGNC API response format"
    await validator.close()


@pytest.mark.asyncio
async def test_validate_empty_docs_is_not_found(validator: HGNCValidator) -> None:
    _use(validator, lambda request: _json({"response": {"docs": []}}))
    result = await validator.validate("BRCA1")

    assert result.status == "not_found"
    assert result.is_valid is False
    await validator.close()


@pytest.mark.asyncio
async def test_validate_timeout_is_reported_as_timeout(
    validator: HGNCValidator,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    _use(validator, handler)
    result = await validator.validate("BRCA1")

    assert result.status == "error"
    assert result.error_code == "TIMEOUT"
    await validator.close()


@pytest.mark.asyncio
async def test_validate_connection_error_is_reported_as_exception(
    validator: HGNCValidator,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    _use(validator, handler)
    result = await validator.validate("BRCA1")

    assert result.status == "error"
    assert result.error_code == "EXCEPTION"
    assert "refused" in (result.error_message or "")
    await validator.close()


@pytest.mark.asyncio
async def test_validate_non_json_body_is_reported_as_exception(
    validator: HGNCValidator,
) -> None:
    _use(validator, lambda request: httpx.Response(200, text="<html>oops</html>"))
    result = await validator.validate("BRCA1")

    assert result.status == "error"
    assert result.error_code == "EXCEPTION"
    await validator.close()


@pytest.mark.asyncio
async def test_batch_validate_maps_each_symbol(validator: HGNCValidator) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/fetch/symbol/BRCA1":
            return _json({"response": {"docs": [BRCA1_DOC]}})
        return httpx.Response(404)

    _use(validator, handler)
    results = await validator.batch_validate(["BRCA1", "ZZZ9"])

    assert set(results) == {"BRCA1", "ZZZ9"}
    assert results["BRCA1"].is_valid is True
    assert results["ZZZ9"].status == "not_found"
    await validator.close()


@pytest.mark.asyncio
async def test_search_blank_query_returns_empty_without_request(
    validator: HGNCValidator,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no HTTP call expected for blank query")

    _use(validator, handler)
    response = await validator.search("   ")

    assert response.total_results == 0
    assert response.results == []
    await validator.close()


@pytest.mark.asyncio
async def test_search_by_hgnc_id_uses_fetch_endpoint(validator: HGNCValidator) -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return _json({"response": {"docs": [BRCA1_DOC]}})

    _use(validator, handler)
    with_prefix = await validator.search("hgnc:1100")
    digits_only = await validator.search("1100")

    assert paths == ["/fetch/hgnc_id/HGNC:1100", "/fetch/hgnc_id/HGNC:1100"]
    assert with_prefix.total_results == 1
    assert digits_only.results[0].symbol == "BRCA1"
    await validator.close()


@pytest.mark.asyncio
async def test_search_by_symbol_uses_wildcards_for_multi_char_queries(
    validator: HGNCValidator,
) -> None:
    urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        urls.append(str(request.url))
        return _json({"response": {"docs": []}})

    _use(validator, handler)
    await validator.search("brc")
    await validator.search("b")

    assert "symbol:BRC*" in urls[0]  # multi-char query gets a wildcard suffix
    assert "symbol:B+OR" in urls[1]  # single char: no wildcard suffix
    assert "symbol:B*" not in urls[1]
    await validator.close()


@pytest.mark.asyncio
async def test_search_parses_results_and_derives_chromosome(
    validator: HGNCValidator,
) -> None:
    docs = [
        BRCA1_DOC,
        {"symbol": "TP53", "hgnc_id": "HGNC:11998", "location": "17p13.1"},
        {"symbol": "NOLOC", "hgnc_id": "HGNC:1"},
    ]
    _use(validator, lambda request: _json({"response": {"docs": docs}}))
    response = await validator.search("BRCA", limit=10)

    assert response.total_results == 3
    by_symbol = {r.symbol: r for r in response.results}
    assert by_symbol["BRCA1"].chromosome == "17"
    assert by_symbol["TP53"].chromosome == "17"
    assert by_symbol["NOLOC"].chromosome is None
    await validator.close()


@pytest.mark.asyncio
async def test_search_respects_limit(validator: HGNCValidator) -> None:
    docs = [{"symbol": f"G{i}", "hgnc_id": f"HGNC:{i}"} for i in range(5)]
    _use(validator, lambda request: _json({"response": {"docs": docs}}))
    response = await validator.search("G", limit=2)

    assert response.total_results == 2
    assert [r.symbol for r in response.results] == ["G0", "G1"]
    await validator.close()


@pytest.mark.asyncio
async def test_search_non_200_returns_empty(validator: HGNCValidator) -> None:
    _use(validator, lambda request: httpx.Response(502))
    response = await validator.search("BRCA1")

    assert response.total_results == 0
    assert response.results == []
    await validator.close()


@pytest.mark.asyncio
async def test_search_timeout_and_errors_degrade_to_empty(
    validator: HGNCValidator,
) -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    _use(validator, timeout)
    assert (await validator.search("BRCA1")).results == []

    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    _use(validator, broken)
    assert (await validator.search("BRCA1")).results == []
    await validator.close()


@pytest.mark.asyncio
async def test_search_with_invalid_json_degrades_to_empty(
    validator: HGNCValidator,
) -> None:
    _use(validator, lambda request: httpx.Response(200, text="not json"))
    response = await validator.search("BRCA1")

    assert response.total_results == 0
    await validator.close()


def test_parse_search_response_handles_missing_docs(validator: HGNCValidator) -> None:
    assert validator._parse_search_response({"foo": 1}, limit=5) == []


def test_parse_search_response_handles_null_lists(validator: HGNCValidator) -> None:
    results = validator._parse_search_response(
        {
            "response": {
                "docs": [{"symbol": "X", "hgnc_id": "HGNC:9", "alias_symbol": None}]
            }
        },
        limit=5,
    )
    assert results[0].alias_symbols == []
    assert results[0].previous_symbols == []


@pytest.mark.asyncio
async def test_fetch_gene_by_id_normalises_prefix(validator: HGNCValidator) -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return _json({"response": {"docs": [BRCA1_DOC]}})

    _use(validator, handler)
    gene = await validator.fetch_gene_by_id("1100")

    assert paths == ["/fetch/hgnc_id/HGNC:1100"]
    assert gene is not None
    assert gene.symbol == "BRCA1"
    assert gene.chromosome == "17"
    await validator.close()


@pytest.mark.asyncio
async def test_fetch_gene_by_id_returns_none_on_failure_shapes(
    validator: HGNCValidator,
) -> None:
    responses = [
        httpx.Response(404),
        _json({"nope": 1}),
        _json({"response": {"docs": []}}),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    _use(validator, handler)
    assert await validator.fetch_gene_by_id("HGNC:1") is None
    assert await validator.fetch_gene_by_id("HGNC:1") is None
    assert await validator.fetch_gene_by_id("HGNC:1") is None
    await validator.close()


@pytest.mark.asyncio
async def test_fetch_gene_by_id_swallows_transport_errors(
    validator: HGNCValidator,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    _use(validator, handler)
    assert await validator.fetch_gene_by_id("HGNC:1100") is None
    await validator.close()


def test_base_url_constant_is_https() -> None:
    assert HGNC_API_BASE.startswith("https://")


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [1, 7])
async def test_search_ranks_exact_symbols_before_limit(
    validator: HGNCValidator, limit: int
) -> None:
    docs = [
        {"symbol": "OTHER", "alias_symbol": None},
        {"symbol": "PKD1-AS1"},
        {"symbol": "OLD", "prev_symbol": ["pkd1"]},
        {"symbol": "ALIAS", "alias_symbol": ["PKD1"]},
        {"symbol": "PKD1L1-AS1"},
        {"symbol": "PKD1"},
        {"symbol": "LAST"},
    ]
    _use(validator, lambda request: _json({"response": {"docs": docs}}))
    response = await validator.search(" pkd1 ", limit=limit)
    assert [r.symbol for r in response.results] == [
        "PKD1",
        "OLD",
        "ALIAS",
        "PKD1-AS1",
        "PKD1L1-AS1",
        "OTHER",
        "LAST",
    ][:limit]
    await validator.close()
