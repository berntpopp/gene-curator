"""Server-side HGNC verification for gene creation (#363).

Genes are shared reference data, so the stored symbol, aliases and location come from HGNC,
never from the client; the client only names the HGNC id.
"""

import asyncio

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.schemas.gene import GeneCreate, GeneUpdate
from app.services.validators import HGNCValidator

logger = get_logger(__name__)

_CONCURRENCY = 5
_BUDGET_S = (
    20.0  # total wall-clock cap so a slow HGNC cannot hold a request (and worker) open
)


async def _fetch(ids: list[str]) -> dict[str, GeneCreate | None]:
    done: dict[str, GeneCreate | None] = {}
    validator = HGNCValidator()
    sem = asyncio.Semaphore(_CONCURRENCY)

    async def one(hgnc_id: str) -> None:
        async with sem:
            rec = await validator.fetch_gene_by_id(hgnc_id)
        if rec is None or rec.hgnc_id.upper() != hgnc_id.upper() or not rec.symbol:
            done[hgnc_id] = None
            return
        done[hgnc_id] = GeneCreate(
            hgnc_id=rec.hgnc_id,
            approved_symbol=rec.symbol,
            previous_symbols=rec.previous_symbols,
            alias_symbols=rec.alias_symbols,
            chromosome=rec.chromosome,
            location=rec.location,
            details={"approved_name": rec.name} if rec.name else {},
        )

    try:
        await asyncio.wait_for(
            asyncio.gather(*(one(i) for i in ids)), timeout=_BUDGET_S
        )
    except TimeoutError:
        logger.warning("HGNC verification timed out", done=len(done), total=len(ids))
    finally:
        await validator.close()
    return done


def verify_genes(db: Session, rows: list[GeneCreate]) -> dict[str, GeneCreate | None]:
    """HGNC-sourced replacement for each row, keyed by the requested HGNC id (None: unverifiable).

    Ids missing from the result timed out.

    Called from sync endpoints (worker threads without a running loop).
    """
    db.rollback()  # no DB connection held while awaiting HGNC; RLS user re-applied on next begin
    return asyncio.run(_fetch(sorted({r.hgnc_id for r in rows})))


def verify_rows(
    db: Session,
    rows: list[GeneCreate],
) -> tuple[list[GeneCreate], list[dict[str, str]]]:
    """HGNC-sourced rows, plus an error entry for each row HGNC could not confirm."""
    checked = verify_genes(db, rows)
    ok = [c for r in rows if (c := checked.get(r.hgnc_id)) is not None]
    errors = [
        {
            "hgnc_id": r.hgnc_id,
            "error": "Could not be verified at HGNC"
            if r.hgnc_id in checked
            else "HGNC lookup timed out",
        }
        for r in rows
        if checked.get(r.hgnc_id) is None
    ]
    return ok, errors


def verified_gene(db: Session, row: GeneCreate) -> GeneCreate:
    """The HGNC-sourced gene for one row, or 422 when HGNC cannot confirm the id."""
    checked = verify_genes(db, [row])
    if row.hgnc_id not in checked:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="HGNC lookup timed out",
        )
    gene = checked[row.hgnc_id]
    if gene is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{row.hgnc_id} could not be verified at HGNC",
        )
    return gene


_REFERENCE_FIELDS = frozenset(
    {
        "hgnc_id",
        "approved_symbol",
        "previous_symbols",
        "alias_symbols",
        "chromosome",
        "location",
    }
)


def verified_update(
    db: Session, update: GeneUpdate, current_hgnc_id: str
) -> GeneUpdate:
    """`update`, with every HGNC-owned field overwritten from HGNC's record when any was sent."""
    if not update.model_fields_set & _REFERENCE_FIELDS:
        return update
    ref = verified_gene(
        db, GeneCreate(hgnc_id=update.hgnc_id or current_hgnc_id, approved_symbol="-")
    )
    return update.model_copy(update={f: getattr(ref, f) for f in _REFERENCE_FIELDS})
