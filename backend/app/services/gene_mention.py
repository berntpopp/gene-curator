"""Whether a paper names a gene: validate_pmids(gene_symbol) flags off-topic PMIDs."""

import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Gene
from app.schemas.validation import PublicationData


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
