"""Behaviour tests for the PubMed PMID validator (HTTP boundary mocked via MockTransport)."""

import httpx
import pytest

from app.services.validators.pubmed_validator import PUBMED_API_BASE, PubMedValidator

FULL_ARTICLE_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>31558469</PMID>
      <Article>
        <Journal>
          <Title>Nature Genetics</Title>
          <JournalIssue>
            <PubDate><Year>2019</Year><Month>Oct</Month><Day>1</Day></PubDate>
          </JournalIssue>
        </Journal>
        <ArticleTitle>Renal cysts and diabetes syndrome</ArticleTitle>
        <AuthorList>
          <Author><LastName>Smith</LastName><ForeName>Jane</ForeName></Author>
          <Author><LastName>Doe</LastName></Author>
          <Author><ForeName>NoLast</ForeName></Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">31558469</ArticleId>
        <ArticleId IdType="doi">10.1000/xyz123</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""

MINIMAL_ARTICLE_XML = """<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <Article/>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""


def _use(validator: PubMedValidator, handler) -> None:  # type: ignore[no-untyped-def]
    validator.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def validator() -> PubMedValidator:
    return PubMedValidator()


def test_defaults_and_custom_credentials() -> None:
    default = PubMedValidator()
    assert default.email == "gene-curator@example.com"
    assert default.api_key is None

    custom = PubMedValidator(email="me@example.org", api_key="k")
    assert custom.email == "me@example.org"
    assert custom.api_key == "k"


@pytest.mark.asyncio
async def test_validate_extracts_full_publication(validator: PubMedValidator) -> None:
    captured: dict[str, httpx.URL] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = request.url
        return httpx.Response(200, text=FULL_ARTICLE_XML)

    _use(validator, handler)
    result = await validator.validate("PMID: 31558469 ")

    assert captured["url"].path == "/entrez/eutils/efetch.fcgi"
    assert captured["url"].params["id"] == "31558469"
    assert captured["url"].params["retmode"] == "xml"
    assert "api_key" not in captured["url"].params

    assert result.is_valid is True
    assert result.status == "valid"
    assert result.data is not None
    assert result.data["pmid"] == "31558469"
    assert result.data["title"] == "Renal cysts and diabetes syndrome"
    assert result.data["journal"] == "Nature Genetics"
    assert result.data["pub_date"] == "2019 Oct 1"
    assert result.data["authors"] == [
        "Smith Jane",
        "Doe",
    ]  # no-forename + no-lastname skipped
    assert result.data["doi"] == "10.1000/xyz123"
    await validator.close()


@pytest.mark.asyncio
async def test_validate_sends_api_key_when_configured() -> None:
    validator = PubMedValidator(email="a@b.c", api_key="secret")
    captured: dict[str, httpx.URL] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = request.url
        return httpx.Response(200, text=FULL_ARTICLE_XML)

    _use(validator, handler)
    await validator.validate("31558469")

    assert captured["url"].params["api_key"] == "secret"
    assert captured["url"].params["email"] == "a@b.c"
    await validator.close()


@pytest.mark.asyncio
async def test_validate_rejects_non_numeric_pmid_without_request(
    validator: PubMedValidator,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no HTTP call expected for invalid PMID")

    _use(validator, handler)
    result = await validator.validate("PMID:abc")

    assert result.is_valid is False
    assert result.status == "invalid"
    await validator.close()


@pytest.mark.asyncio
async def test_validate_http_error_reports_code(validator: PubMedValidator) -> None:
    _use(validator, lambda request: httpx.Response(429))
    result = await validator.validate("31558469")

    assert result.status == "error"
    assert result.error_code == "HTTP_429"
    await validator.close()


@pytest.mark.asyncio
async def test_validate_malformed_xml_is_error(validator: PubMedValidator) -> None:
    _use(validator, lambda request: httpx.Response(200, text="<PubmedArticleSet><oops"))
    result = await validator.validate("31558469")

    assert result.status == "error"
    assert result.error_message == "Failed to parse PubMed API response"
    await validator.close()


@pytest.mark.asyncio
async def test_validate_unknown_pmid_is_not_found(validator: PubMedValidator) -> None:
    _use(validator, lambda request: httpx.Response(200, text="<PubmedArticleSet/>"))
    result = await validator.validate("99999999")

    assert result.status == "not_found"
    assert "99999999" in (result.error_message or "")
    await validator.close()


@pytest.mark.asyncio
async def test_validate_missing_medline_citation_is_error(
    validator: PubMedValidator,
) -> None:
    xml = "<PubmedArticleSet><PubmedArticle/></PubmedArticleSet>"
    _use(validator, lambda request: httpx.Response(200, text=xml))
    result = await validator.validate("1")

    assert result.status == "error"
    assert result.error_message == "Invalid PubMed response structure"
    await validator.close()


@pytest.mark.asyncio
async def test_validate_missing_article_element_is_error(
    validator: PubMedValidator,
) -> None:
    xml = (
        "<PubmedArticleSet><PubmedArticle><MedlineCitation/></PubmedArticle>"
        "</PubmedArticleSet>"
    )
    _use(validator, lambda request: httpx.Response(200, text=xml))
    result = await validator.validate("1")

    assert result.status == "error"
    assert result.error_message == "Article data missing from PubMed response"
    await validator.close()


@pytest.mark.asyncio
async def test_validate_sparse_article_uses_placeholders(
    validator: PubMedValidator,
) -> None:
    _use(validator, lambda request: httpx.Response(200, text=MINIMAL_ARTICLE_XML))
    result = await validator.validate("1")

    assert result.is_valid is True
    assert result.data is not None
    assert result.data["title"] == "Title not available"
    assert result.data["journal"] == "Journal not available"
    assert result.data["pub_date"] == "Date not available"
    assert result.data["authors"] == []
    assert result.data["doi"] is None
    await validator.close()


@pytest.mark.asyncio
async def test_validate_timeout_and_connection_errors(
    validator: PubMedValidator,
) -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    _use(validator, timeout)
    timed_out = await validator.validate("31558469")
    assert timed_out.error_code == "TIMEOUT"

    def refused(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    _use(validator, refused)
    broken = await validator.validate("31558469")
    assert broken.error_code == "EXCEPTION"
    await validator.close()


@pytest.mark.asyncio
async def test_batch_validate_returns_result_per_pmid(
    validator: PubMedValidator,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params["id"] == "31558469":
            return httpx.Response(200, text=FULL_ARTICLE_XML)
        return httpx.Response(200, text="<PubmedArticleSet/>")

    _use(validator, handler)
    results = await validator.batch_validate(["31558469", "1"])

    assert results["31558469"].is_valid is True
    assert results["1"].status == "not_found"
    await validator.close()


def test_base_url_constant() -> None:
    assert PUBMED_API_BASE.endswith("/entrez/eutils")
