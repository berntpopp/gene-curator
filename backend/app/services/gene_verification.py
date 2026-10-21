"""Server-side HGNC verification for gene creation (#363).

Genes are shared reference data, so the stored symbol, aliases and location come from HGNC,
never from the client; the client only names the HGNC id.
"""

import asyncio

from fastapi import HTTPException, status

from app.core.logging import get_logger
from app.schemas.gene import GeneCreate
from app.services.validators import HGNCValidator

logger = get_logger(__name__)

_CONCURRENCY = 5


async def _fetch(ids: list[str]) -> dict[str, GeneCreate | None]:
    validator = HGNCValidator()
    sem = asyncio.Semaphore(_CONCURRENCY)

    async def one(hgnc_id: str) -> tuple[str, GeneCreate | None]:
        async with sem:
            rec = await validator.fetch_gene_by_id(hgnc_id)
        if rec is None or rec.hgnc_id.upper() != hgnc_id.upper() or not rec.symbol:
            return hgnc_id, None
        return hgnc_id, GeneCreate(
            hgnc_id=rec.hgnc_id,
            approved_symbol=rec.symbol,
            previous_symbols=rec.previous_symbols,
            alias_symbols=rec.alias_symbols,
            chromosome=rec.chromosome,
            location=rec.location,
            details={"approved_name": rec.name} if rec.name else {},
        )

    try:
        return dict(await asyncio.gather(*(one(i) for i in ids)))
    finally:
        await validator.close()


def verify_genes(rows: list[GeneCreate]) -> dict[str, GeneCreate | None]:
    """HGNC-sourced replacement for each row, keyed by the requested HGNC id (None: unverifiable).

    Called from sync endpoints (worker threads without a running loop).
    """
    return asyncio.run(_fetch(sorted({r.hgnc_id for r in rows})))


def verify_rows(
    rows: list[GeneCreate],
) -> tuple[list[GeneCreate], list[dict[str, str]]]:
    """HGNC-sourced rows, plus an error entry for each row HGNC could not confirm."""
    checked = verify_genes(rows)
    ok = [c for r in rows if (c := checked[r.hgnc_id]) is not None]
    errors = [
        {"hgnc_id": r.hgnc_id, "error": "Could not be verified at HGNC"}
        for r in rows
        if checked[r.hgnc_id] is None
    ]
    return ok, errors


def verified_gene(row: GeneCreate) -> GeneCreate:
    """The HGNC-sourced gene for one row, or 422 when HGNC cannot confirm the id."""
    gene = verify_genes([row])[row.hgnc_id]
    if gene is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{row.hgnc_id} could not be verified at HGNC",
        )
    return gene
