"""PubMed search through Europe PMC, and whether a paper names a gene (MCP study)."""

import asyncio
import re
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.models import Gene
from app.schemas.validation import PMIDValidationResult, PublicationData
from app.services.publication_service import PublicationService, _cache_found

SEARCH_TIMEOUT_S = 8.0  # one Europe PMC search request


def search_term(*parts: str | None, exclude_reviews: bool = False) -> str:
    """Europe PMC query: every given part must match, PubMed records only."""
    term = " AND ".join(
        [f"({p.strip()})" for p in parts if p and p.strip()] + ["SRC:MED"]
    )
    # a case report that also reviews the literature is primary data: keep it
    skip = ' NOT (PUB_TYPE:"review" NOT PUB_TYPE:"case reports")'
    return term + skip if exclude_reviews else term


def in_title_or_abstract(symbol: str | None) -> str | None:
    """A gene symbol matched only in the title or abstract (not in MeSH terms or full text,
    which pull in papers that merely list the gene)."""
    clean = (symbol or "").replace('"', "").strip()
    return f'TITLE_ABS:"{clean}"' if clean else None


# Europe PMC sorts by relevance when no sort is sent
SEARCH_SORTS = {"relevance": None, "date": "P_PDATE_D desc", "cited": "CITED desc"}


async def _search(
    term: str, limit: int, sort: str | None
) -> tuple[int, list[PublicationData]]:
    service = PublicationService(cast(AsyncSession, None))
    try:
        response = await asyncio.wait_for(
            service._client.get(
                "/search",
                params={
                    "query": term,
                    "resultType": "core",
                    "pageSize": limit,
                    "format": "json",
                    **({"sort": sort} if sort else {}),
                },
            ),
            SEARCH_TIMEOUT_S,
        )
        response.raise_for_status()
        data = response.json()
    finally:
        await service.close()
    found = [
        pub
        for row in data.get("resultList", {}).get("result", [])
        if row.get("pmid")
        and (pub := service._parse_publication_response({"result": row}, row["pmid"]))
    ]
    return int(data.get("hitCount") or 0), found


def search_publications(
    db: Session, term: str, limit: int, sort: str | None = None
) -> tuple[int, list[PublicationData]]:
    """(hit count, top records) from Europe PMC; the records are cached like validated PMIDs.
    Raises httpx.HTTPError or TimeoutError when Europe PMC is unavailable."""
    total, found = asyncio.run(_search(term, limit, sort))
    _cache_found(
        db,
        [
            PMIDValidationResult(pmid=p.pmid, is_valid=True, publication=p)
            for p in found
        ],
    )
    db.commit()
    return total, found


def mentions(names: set[str], publication: PublicationData | None) -> bool | None:
    """Whether the title or abstract names any of the gene names (whole words, any case);
    None when the title does not and there is no abstract to read."""
    if publication is None:
        return None
    found = re.compile(
        r"(?<![A-Z0-9])(" + "|".join(map(re.escape, names)) + r")(?![A-Z0-9])"
    )
    text = f"{publication.title} {publication.abstract or ''}".upper()
    if found.search(text):
        return True
    return False if publication.abstract else None


async def gene_names(db: AsyncSession, symbol: str) -> set[str]:
    """The symbol plus the local gene's previous and alias symbols, upper case."""
    key = symbol.strip().upper()
    row = (
        await db.execute(
            select(Gene.previous_symbols, Gene.alias_symbols).where(
                func.upper(Gene.approved_symbol) == key
            )
        )
    ).first()
    extra = [*(row.previous_symbols or []), *(row.alias_symbols or [])] if row else []
    return {key, *(n.upper() for n in extra if n)}
