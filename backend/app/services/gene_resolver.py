"""Resolve pasted gene identifiers: local genes table first, then HGNC (exact matches only)."""

import asyncio
import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.models import Gene
from app.schemas.gene_resolve import (
    GeneCandidate,
    GeneResolveCounts,
    GeneResolveItem,
    GeneResolveResponse,
    MatchType,
)
from app.services.validators import HGNCValidator

logger = get_logger(__name__)

_HGNC_ID = re.compile(r"^(?:HGNC:)?(\d+)$", re.IGNORECASE)
_HGNC_CONCURRENCY = 5


@dataclass
class _Gene:
    hgnc_id: str
    symbol: str
    name: str | None = None
    previous: list[str] = field(default_factory=list)
    alias: list[str] = field(default_factory=list)
    gene_id: object | None = None


def _classify(token: str, genes: list[_Gene]) -> tuple[MatchType, list[_Gene]] | None:
    """First tier (symbol, previous symbol, alias, HGNC ID) with any exact hit wins."""
    key = token.upper()
    m = _HGNC_ID.match(token)
    hgnc_id = f"HGNC:{m.group(1)}" if m else None
    tiers: list[tuple[MatchType, list[_Gene]]] = [
        ("symbol", [g for g in genes if g.symbol.upper() == key]),
        (
            "previous_symbol",
            [g for g in genes if key in (s.upper() for s in g.previous)],
        ),
        ("alias", [g for g in genes if key in (s.upper() for s in g.alias)]),
        ("hgnc_id", [g for g in genes if hgnc_id and g.hgnc_id.upper() == hgnc_id]),
    ]
    return next(((t, hits) for t, hits in tiers if hits), None)


def _local_genes(db: Session, tokens: set[str]) -> list[_Gene]:
    keys = {t.upper() for t in tokens}
    ids = {f"HGNC:{m.group(1)}" for t in tokens if (m := _HGNC_ID.match(t))}
    rows = db.execute(
        select(
            Gene.id,
            Gene.hgnc_id,
            Gene.approved_symbol,
            Gene.previous_symbols,
            Gene.alias_symbols,
        )
    ).all()
    # ponytail: scans the whole genes table (cols only); index prev/alias if it outgrows ~50k rows
    return [
        _Gene(
            r.hgnc_id,
            r.approved_symbol,
            None,
            r.previous_symbols or [],
            r.alias_symbols or [],
            r.id,
        )
        for r in rows
        if r.approved_symbol.upper() in keys
        or r.hgnc_id.upper() in ids
        or keys
        & {s.upper() for s in (r.previous_symbols or []) + (r.alias_symbols or [])}
    ]


async def _hgnc_lookup(tokens: list[str]) -> dict[str, list[_Gene]]:
    validator = HGNCValidator()
    sem = asyncio.Semaphore(_HGNC_CONCURRENCY)

    async def one(token: str) -> tuple[str, list[_Gene]]:
        async with sem:
            res = await validator.search(token, limit=10)
        return token, [
            _Gene(r.hgnc_id, r.symbol, r.name, r.previous_symbols, r.alias_symbols)
            for r in res.results
        ]

    try:
        return dict(await asyncio.gather(*(one(t) for t in tokens)))
    finally:
        await validator.close()


async def resolve_genes(db: Session, symbols: list[str]) -> GeneResolveResponse:
    unique = {s.upper(): s for s in reversed(symbols)}  # one lookup per distinct input
    local = _local_genes(db, set(unique.values()))
    found: dict[str, tuple[MatchType, list[_Gene], str]] = {}
    for key, token in unique.items():
        if hit := _classify(token, local):
            found[key] = (hit[0], hit[1], "local")

    missing = [t for k, t in unique.items() if k not in found]
    for token, genes in (await _hgnc_lookup(missing)).items() if missing else []:
        if hit := _classify(token, genes):
            found[token.upper()] = (hit[0], hit[1], "hgnc")

    first_by_gene: dict[str, int] = {}
    first_by_token: dict[str, int] = {}
    items: list[GeneResolveItem] = []
    for index, token in enumerate(symbols):
        key = token.upper()
        dup = first_by_token.setdefault(key, index)
        dup = None if dup == index else dup
        hit = found.get(key)
        if not hit:
            items.append(
                GeneResolveItem(
                    input=token, index=index, status="not_found", duplicate_of=dup
                )
            )
            continue
        match_type, genes, source = hit
        if len(genes) == 1:
            dup = dup if dup is not None else first_by_gene.get(genes[0].hgnc_id)
            first_by_gene.setdefault(genes[0].hgnc_id, index)
            dup = None if dup == index else dup
        items.append(
            GeneResolveItem(
                input=token,
                index=index,
                status="resolved" if len(genes) == 1 else "ambiguous",
                match_type=match_type,
                source=source,  # type: ignore[arg-type]
                candidates=[
                    GeneCandidate(
                        hgnc_id=g.hgnc_id,
                        symbol=g.symbol,
                        name=g.name,
                        gene_id=g.gene_id,  # type: ignore[arg-type]
                    )
                    for g in sorted(genes, key=lambda g: g.symbol)
                ],
                duplicate_of=dup,
            )
        )

    counts = GeneResolveCounts(
        resolved=sum(i.status == "resolved" for i in items),
        ambiguous=sum(i.status == "ambiguous" for i in items),
        not_found=sum(i.status == "not_found" for i in items),
    )
    logger.info("Gene resolve completed", total=len(symbols), **counts.model_dump())
    return GeneResolveResponse(items=items, counts=counts)
