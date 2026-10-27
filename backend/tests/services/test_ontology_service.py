"""Behaviour tests for OntologyService (MONDO / OMIM / HPO clients mocked via MockTransport)."""

from collections.abc import Callable, Generator

import httpx
import pytest

from app.services.ontology_service import (
    HPO_API_BASE,
    MONDO_API_BASE,
    OMIM_API_BASE,
    OntologyService,
)

Handler = Callable[[httpx.Request], httpx.Response]


@pytest.fixture(autouse=True)
def _reset_inheritance_cache() -> Generator[None, None, None]:
    OntologyService._inheritance_cache = None
    yield
    OntologyService._inheritance_cache = None


def _service(handler: Handler) -> OntologyService:
    svc = OntologyService()
    transport = httpx.MockTransport(handler)
    svc._mondo_client = httpx.AsyncClient(base_url=MONDO_API_BASE, transport=transport)
    svc._omim_client = httpx.AsyncClient(base_url=OMIM_API_BASE, transport=transport)
    svc._hpo_client = httpx.AsyncClient(base_url=HPO_API_BASE, transport=transport)
    return svc


def _raise(exc: Exception) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc

    return handler


MONDO_ELEMENT = {
    "curie": "MONDO:0007254",
    "label": ["breast cancer"],
    "definition": [{"value": "A cancer that starts in breast tissue."}],
    "synonym": [{"value": "mammary carcinoma"}, "BC", {"no": "value"}],
    "linkedEntities": {
        "OMIM:114480": {},
        "DOID:1612": {},
        "Orphanet:503": {},
        "UMLS:C0006142": {},
    },
    "iri": "http://purl.obolibrary.org/obo/MONDO_0007254",
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "filter_human"),
    [
        ("canine", True),
        ("MONDO:0007258", False),
        ("Marfan", True),
        ("MONDO:0009100", False),
        ("MONDO:0009100 susceptibility", True),
        ("MONDO:000910", True),
    ],
)
async def test_mondo_filters_suggestions_but_resolves_saved_ids(
    query: str, filter_human: bool
) -> None:
    calls = []
    term_id = "MONDO:0007258" if filter_human else query

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if filter_human:
            assert request.url.params["directAncestor"] == (
                "http://purl.obolibrary.org/obo/MONDO_0700096"
            )
        else:
            assert "directAncestor" not in request.url.params
        assert request.url.params["includeObsoleteEntities"] == "false"
        assert request.url.params["search"] == query
        assert request.url.params["size"] == "5"
        # A human canine-tooth disorder must not be removed by name heuristics.
        return httpx.Response(
            200,
            json={
                "elements": [
                    {
                        "curie": term_id,
                        "label": ["stored term"],
                    }
                ],
                "totalElements": 1,
            },
        )

    svc = _service(handler)
    try:
        response = await svc.search_mondo(query, limit=5)
    finally:
        await svc.close()
    assert len(calls) == 1
    assert response.total_results == 1
    assert [r.mondo_id for r in response.results] == [term_id]


@pytest.mark.asyncio
async def test_search_mondo_parses_elements_and_filters_foreign_curies() -> None:
    payload = {
        "elements": [MONDO_ELEMENT, {"curie": "DOID:1612", "label": ["x"]}],
        "totalElements": 42,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["search"] == "breast"
        assert request.url.params["ontologyId"] == "mondo"
        return httpx.Response(200, json=payload)

    svc = _service(handler)
    response = await svc.search_mondo("breast", limit=5)
    await svc.close()

    assert response.total_results == 42
    assert len(response.results) == 1
    hit = response.results[0]
    assert hit.mondo_id == "MONDO:0007254"
    assert hit.label == "breast cancer"
    assert hit.definition == "A cancer that starts in breast tissue."
    assert hit.synonyms == ["mammary carcinoma", "BC"]
    assert hit.xrefs == ["OMIM:114480", "DOID:1612", "Orphanet:503"]


@pytest.mark.asyncio
async def test_search_mondo_failures_degrade_to_empty() -> None:
    for handler in (
        lambda request: httpx.Response(500),
        _raise(httpx.ReadTimeout("slow")),
        _raise(RuntimeError("boom")),
    ):
        svc = _service(handler)
        response = await svc.search_mondo("x")
        await svc.close()
        assert response.total_results == 0
        assert response.results == []


def test_ols4_helpers_handle_scalar_and_missing_shapes() -> None:
    assert OntologyService._extract_ols4_label({"label": "plain"}) == "plain"
    assert OntologyService._extract_ols4_label({}) == ""
    assert OntologyService._extract_ols4_definition({}) is None
    assert OntologyService._extract_ols4_definition({"definition": ["text"]}) == "text"
    assert (
        OntologyService._extract_ols4_definition({"definition": [{"value": ""}]}) == ""
    )
    assert OntologyService._extract_ols4_definition({"definition": [42]}) is None
    assert OntologyService._extract_ols4_synonyms({"synonym": "nope"}) == []
    assert OntologyService._extract_ols4_xrefs({}) == []


@pytest.mark.asyncio
async def test_get_omim_disease_builds_phenotypes_and_genes() -> None:
    payload = {
        "disease": {
            "id": "OMIM:114480",
            "name": "Breast cancer",
            "mondoId": "MONDO:0007254",
            "description": "desc",
        },
        "categories": {
            "Clinical": [
                {
                    "id": "HP:0000001",
                    "name": "Phenotype",
                    "metadata": {"frequency": "frequent", "sources": ["PMID:1"]},
                }
            ],
            "Empty": [],
            "NotAList": {"x": 1},
        },
        "genes": [{"id": "NCBIGene:672", "name": "BRCA1"}],
    }
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json=payload)

    svc = _service(handler)
    result = await svc.get_omim_disease("114480")
    await svc.close()

    assert seen == ["/api/network/annotation/OMIM:114480"]
    assert result is not None
    assert result.omim_id == "OMIM:114480"
    assert result.mondo_id == "MONDO:0007254"
    assert list(result.phenotypes) == ["Clinical"]
    phenotype = result.phenotypes["Clinical"][0]
    assert phenotype.hpo_id == "HP:0000001"
    assert phenotype.frequency == "frequent"
    assert phenotype.sources == ["PMID:1"]
    assert result.genes[0].symbol == "BRCA1"


@pytest.mark.asyncio
async def test_get_omim_disease_returns_none_on_failures() -> None:
    for handler in (
        lambda request: httpx.Response(404),
        lambda request: httpx.Response(500),
        _raise(httpx.ReadTimeout("slow")),
        _raise(RuntimeError("boom")),
    ):
        svc = _service(handler)
        assert await svc.get_omim_disease("OMIM:1") is None
        await svc.close()


@pytest.mark.asyncio
async def test_search_omim_with_id_uses_direct_fetch() -> None:
    payload = {
        "disease": {"id": "OMIM:114480", "name": "Breast cancer"},
        "genes": [{"id": "NCBIGene:672", "name": "BRCA1"}],
    }
    svc = _service(lambda request: httpx.Response(200, json=payload))
    response = await svc.search_omim("114480")
    await svc.close()

    assert response.total_results == 1
    assert response.results[0].omim_id == "OMIM:114480"
    assert response.results[0].gene_symbols == ["BRCA1"]


@pytest.mark.asyncio
async def test_search_omim_unknown_id_returns_empty() -> None:
    svc = _service(lambda request: httpx.Response(404))
    response = await svc.search_omim("OMIM:999999")
    await svc.close()

    assert response.total_results == 0
    assert response.results == []


@pytest.mark.asyncio
async def test_search_omim_text_query_filters_mondo_xrefs_and_respects_limit() -> None:
    elements = [
        {
            "curie": f"MONDO:000{i}",
            "label": [f"disease {i}"],
            "linkedEntities": {"OMIM:1000" + str(i): {}},
        }
        for i in range(4)
    ]
    elements.append(
        {
            "curie": "MONDO:0009999",
            "label": ["no omim"],
            "linkedEntities": {"DOID:1": {}},
        }
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"elements": elements, "totalElements": 5})

    svc = _service(handler)
    response = await svc.search_omim("disease", limit=2)
    await svc.close()

    assert response.total_results == 2
    assert [r.omim_id for r in response.results] == ["OMIM:10000", "OMIM:10001"]
    assert response.results[0].name == "disease 0"
    assert response.results[0].gene_symbols == []


@pytest.mark.asyncio
async def test_search_omim_error_path_returns_empty() -> None:
    svc = _service(_raise(RuntimeError("boom")))
    response = await svc.search_omim("disease")
    await svc.close()

    assert response.total_results == 0


@pytest.mark.asyncio
async def test_search_hpo_parses_terms() -> None:
    payload = {
        "totalCount": 7,
        "terms": [
            {
                "id": "HP:0001250",
                "name": "Seizure",
                "definition": "abnormal",
                "synonyms": ["a", "b", "c", "d", "e", "f"],
                "descendantCount": 3,
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["q"] == "seizure"
        return httpx.Response(200, json=payload)

    svc = _service(handler)
    response = await svc.search_hpo("seizure", limit=3)
    await svc.close()

    assert response.total_results == 7
    hit = response.results[0]
    assert hit.hpo_id == "HP:0001250"
    assert hit.synonyms == ["a", "b", "c", "d", "e"]  # capped at five
    assert hit.descendant_count == 3


@pytest.mark.asyncio
async def test_search_hpo_failures_degrade_to_empty() -> None:
    for handler in (
        lambda request: httpx.Response(503),
        _raise(httpx.ReadTimeout("slow")),
        _raise(RuntimeError("boom")),
    ):
        svc = _service(handler)
        response = await svc.search_hpo("seizure")
        await svc.close()
        assert response.results == []


def _inheritance_handler(mendelian: int, non_mendelian: int) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/terms/HP:0034345/descendants"):
            if mendelian != 200:
                return httpx.Response(mendelian)
            return httpx.Response(
                200,
                json=[{"id": "HP:0000007", "name": "Autosomal recessive inheritance"}],
            )
        if non_mendelian != 200:
            return httpx.Response(non_mendelian)
        return httpx.Response(
            200, json=[{"id": "HP:0001427", "name": "Mitochondrial inheritance"}]
        )

    return handler


@pytest.mark.asyncio
async def test_get_inheritance_patterns_fetches_and_caches() -> None:
    svc = _service(_inheritance_handler(200, 200))
    first = await svc.get_inheritance_patterns()
    assert first.cached is False
    assert first.total_patterns == 2
    assert first.mendelian[0].category == "mendelian"
    assert first.non_mendelian[0].category == "non_mendelian"

    second = await svc.get_inheritance_patterns()
    await svc.close()
    assert second.cached is True
    assert second.total_patterns == 2


@pytest.mark.asyncio
async def test_get_inheritance_patterns_timeout_returns_empty() -> None:
    svc = _service(_raise(httpx.ReadTimeout("slow")))
    result = await svc.get_inheritance_patterns()
    await svc.close()

    assert result.total_patterns == 0
    assert result.cached is False


@pytest.mark.asyncio
async def test_get_inheritance_patterns_unexpected_error_returns_empty() -> None:
    svc = _service(_raise(RuntimeError("boom")))
    result = await svc.get_inheritance_patterns()
    await svc.close()

    assert result.total_patterns == 0


@pytest.mark.asyncio
async def test_failed_upstream_is_not_cached_as_empty_result() -> None:
    # An outage must not pin an empty inheritance list for the process lifetime.
    failing = _service(_inheritance_handler(500, 500))
    outage = await failing.get_inheritance_patterns()
    await failing.close()
    assert outage.total_patterns == 0

    recovered = _service(_inheritance_handler(200, 200))
    result = await recovered.get_inheritance_patterns()
    await recovered.close()

    assert result.total_patterns == 2
    assert result.cached is False


@pytest.mark.asyncio
async def test_search_omim_unexpected_failure_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _service(lambda request: httpx.Response(200, json={}))

    async def broken(query: str, limit: int = 10) -> None:
        raise RuntimeError("unexpected")

    monkeypatch.setattr(svc, "search_mondo", broken)
    response = await svc.search_omim("disease")
    await svc.close()

    assert response.total_results == 0
    assert response.results == []
