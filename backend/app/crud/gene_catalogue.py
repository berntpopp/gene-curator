"""CRUD operations for the Gene Catalogue.

The Gene Catalogue is a read-only aggregation layer that provides a unified view
of genes with finished curations across all scopes. It never modifies source data.
"""

from collections import defaultdict
from typing import Any

from sqlalchemy import Select, String, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.logging import get_logger
from app.crud.curation import get_disease_fields
from app.models import ActiveCuration, CurationNew, Gene, Scope, UserNew
from app.schemas.gene_catalogue import (
    GeneCatalogueEntry,
    GeneCatalogueFilters,
    GeneCatalogueResponse,
    GeneCatalogueSummaryStats,
    ScopeCurationSummary,
)

logger = get_logger(__name__)


def get_catalogue_summary_stats(db: Session) -> GeneCatalogueSummaryStats:
    """Get overall catalogue statistics.

    Returns aggregated counts of genes, curations, scopes, and classification
    distribution across all active curations.
    """
    # Count genes with active curations
    total_genes = (
        db.execute(
            select(func.count(func.distinct(ActiveCuration.gene_id))).where(
                ActiveCuration.archived_at.is_(None)
            )
        ).scalar()
        or 0
    )

    # Count total active curations
    total_curations = (
        db.execute(
            select(func.count(ActiveCuration.id)).where(
                ActiveCuration.archived_at.is_(None)
            )
        ).scalar()
        or 0
    )

    # Count scopes with active curations
    total_scopes = (
        db.execute(
            select(func.count(func.distinct(ActiveCuration.scope_id))).where(
                ActiveCuration.archived_at.is_(None)
            )
        ).scalar()
        or 0
    )

    # Classification distribution
    classification_counts = db.execute(
        select(CurationNew.computed_verdict, func.count(CurationNew.id))
        .join(ActiveCuration, ActiveCuration.curation_id == CurationNew.id)
        .where(ActiveCuration.archived_at.is_(None))
        .group_by(CurationNew.computed_verdict)
    ).all()

    classification_summary = {
        verdict.lower() if verdict else "unknown": count
        for verdict, count in classification_counts
        if verdict
    }

    return GeneCatalogueSummaryStats(
        total_genes_curated=total_genes,
        total_curations=total_curations,
        total_scopes=total_scopes,
        classification_summary=classification_summary,
    )


def _with_sort_column(query: Select[Any], sort_by: str) -> tuple[Select[Any], Any]:
    """Sort expression for the catalogue; total_curations sorts on the aggregate."""
    if sort_by != "total_curations":
        return query, getattr(Gene, sort_by, Gene.approved_symbol)
    # DISTINCT needs the sort expression in the select list
    count = (
        select(func.count(ActiveCuration.id))
        .where(ActiveCuration.gene_id == Gene.id, ActiveCuration.archived_at.is_(None))
        .correlate(Gene)
        .scalar_subquery()
    )
    return query.add_columns(count.label("curation_count")), count


def get_catalogue_entries(
    db: Session, filters: GeneCatalogueFilters
) -> tuple[list[GeneCatalogueEntry], int]:
    """Query catalogue entries with filtering and pagination.

    Returns genes that have at least one non-archived active curation,
    along with aggregated curation information per scope.

    Args:
        db: Database session
        filters: Query filters (search, classification, disease, scope, pagination)

    Returns:
        Tuple of (list of GeneCatalogueEntry, total count)
    """
    # Base query: genes with active curations
    base_query = (
        select(Gene)
        .join(ActiveCuration, ActiveCuration.gene_id == Gene.id)
        .where(ActiveCuration.archived_at.is_(None))
        .distinct()
    )

    # Apply filters
    if filters.search:
        search_term = f"%{filters.search}%"
        base_query = base_query.where(
            (Gene.approved_symbol.ilike(search_term))
            | (Gene.hgnc_id.ilike(search_term))
            | (Gene.previous_symbols.cast(String).ilike(search_term))
            | (Gene.alias_symbols.cast(String).ilike(search_term))
        )

    if filters.chromosome:
        base_query = base_query.where(Gene.chromosome == filters.chromosome)

    if filters.scope_id:
        base_query = base_query.where(ActiveCuration.scope_id == filters.scope_id)

    if filters.classification:
        base_query = base_query.join(
            CurationNew, ActiveCuration.curation_id == CurationNew.id
        ).where(
            func.lower(CurationNew.computed_verdict) == filters.classification.lower()
        )

    if filters.disease:
        disease_term = f"%{filters.disease}%"
        # Need to join to curation to filter by evidence_data
        if not filters.classification:
            base_query = base_query.join(
                CurationNew, ActiveCuration.curation_id == CurationNew.id
            )
        base_query = base_query.where(
            CurationNew.evidence_data["disease_name"].astext.ilike(disease_term)
        )

    # Count total before pagination
    count_query = select(func.count()).select_from(base_query.subquery())
    total = db.execute(count_query).scalar() or 0

    base_query, sort_column = _with_sort_column(base_query, filters.sort_by)
    if filters.sort_order == "desc":
        sort_column = sort_column.desc()
    base_query = base_query.order_by(sort_column)

    # Apply pagination
    base_query = base_query.offset(filters.skip).limit(filters.limit)

    # Execute query
    genes = db.execute(base_query).scalars().all()

    # Build catalogue entries with detailed curation info
    entries = []
    for gene in genes:
        entry = _build_catalogue_entry(db, gene, filters)
        if entry:
            entries.append(entry)

    return entries, total


def _build_scope_curation_summary(
    active_curation: ActiveCuration,
    curation: CurationNew,
    scope: Scope,
    curator: UserNew | None,
) -> tuple[ScopeCurationSummary, str | None, str | None]:
    """Build a scope curation summary from database results.

    Returns:
        Tuple of (summary, classification_key, disease_name)
    """
    evidence = curation.evidence_data or {}
    disease = get_disease_fields(
        evidence, curation.precuration.evidence_data if curation.precuration else None
    )
    disease_name = disease["disease_name"]

    # Extract scores from computed_scores first
    scores = curation.computed_scores or {}
    genetic_score = scores.get("genetic_evidence_total")
    experimental_score = scores.get("experimental_evidence_total")
    total_score = scores.get("total_score")
    classification = curation.computed_verdict

    summary = ScopeCurationSummary(
        scope_id=scope.id,
        scope_name=scope.name,
        scope_display_name=scope.display_name,
        is_public=scope.is_public,
        **disease,
        classification=classification,
        genetic_score=genetic_score,
        experimental_score=experimental_score,
        total_score=total_score,
        activated_at=active_curation.activated_at,
        curator_name=curator.name if curator else None,
    )

    class_key = classification.lower() if classification else None
    return summary, class_key, disease_name


def _build_catalogue_entry(
    db: Session, gene: Gene, filters: GeneCatalogueFilters
) -> GeneCatalogueEntry | None:
    """Build a single catalogue entry with all scope curations.

    Args:
        db: Database session
        gene: Gene model instance
        filters: Filters to apply (may filter scopes)

    Returns:
        GeneCatalogueEntry or None if no matching curations
    """
    # Get all active curations for this gene
    curation_query = (
        select(ActiveCuration, CurationNew, Scope, UserNew)
        .options(joinedload(CurationNew.precuration))
        .join(CurationNew, ActiveCuration.curation_id == CurationNew.id)
        .join(Scope, ActiveCuration.scope_id == Scope.id)
        .outerjoin(UserNew, CurationNew.created_by == UserNew.id)
        .where(
            ActiveCuration.gene_id == gene.id,
            ActiveCuration.archived_at.is_(None),
        )
    )

    # Apply filters
    if filters.scope_id:
        curation_query = curation_query.where(
            ActiveCuration.scope_id == filters.scope_id
        )
    if filters.classification:
        curation_query = curation_query.where(
            func.lower(CurationNew.computed_verdict) == filters.classification.lower()
        )
    if filters.disease:
        disease_term = f"%{filters.disease}%"
        curation_query = curation_query.where(
            CurationNew.evidence_data["disease_name"].astext.ilike(disease_term)
        )

    results = db.execute(curation_query).all()
    if not results:
        return None

    # Build scope curation summaries
    scope_curations: list[ScopeCurationSummary] = []
    classifications: dict[str, int] = defaultdict(int)
    diseases: set[str] = set()

    for active_curation, curation, scope, curator in results:
        summary, class_key, disease_name = _build_scope_curation_summary(
            active_curation, curation, scope, curator
        )
        scope_curations.append(summary)

        if class_key:
            classifications[class_key] += 1
        if disease_name:
            diseases.add(disease_name)

    return GeneCatalogueEntry(
        gene_id=gene.id,
        hgnc_id=gene.hgnc_id,
        approved_symbol=gene.approved_symbol,
        chromosome=gene.chromosome,
        location=gene.location,
        total_curations=len(scope_curations),
        scope_count=len({sc.scope_id for sc in scope_curations}),
        classifications=dict(classifications),
        diseases=sorted(diseases),
        scope_curations=scope_curations,
    )


def get_gene_catalogue(
    db: Session,
    filters: GeneCatalogueFilters | None = None,
) -> GeneCatalogueResponse:
    """Get the complete gene catalogue response.

    Combines catalogue entries with summary statistics.

    Args:
        db: Database session
        filters: Optional query filters

    Returns:
        Complete GeneCatalogueResponse
    """
    if filters is None:
        filters = GeneCatalogueFilters()

    # Get entries and total count
    entries, total = get_catalogue_entries(db, filters)

    # Get summary statistics
    summary = get_catalogue_summary_stats(db)

    # Calculate pagination flags
    has_next = (filters.skip + filters.limit) < total
    has_prev = filters.skip > 0

    return GeneCatalogueResponse(
        entries=entries,
        total=total,
        skip=filters.skip,
        limit=filters.limit,
        has_next=has_next,
        has_prev=has_prev,
        summary=summary,
    )


def get_available_classifications(db: Session) -> list[str]:
    """Get list of available classifications in the catalogue.

    Returns classifications that have at least one active curation.
    """
    results = (
        db.execute(
            select(func.distinct(CurationNew.computed_verdict))
            .join(ActiveCuration, ActiveCuration.curation_id == CurationNew.id)
            .where(
                ActiveCuration.archived_at.is_(None),
                CurationNew.computed_verdict.isnot(None),
            )
        )
        .scalars()
        .all()
    )

    return sorted([r.lower() for r in results if r])


def get_available_diseases(db: Session, limit: int = 50) -> list[str]:
    """Get list of available diseases in the catalogue.

    Returns unique disease names from active curations.
    """
    # Query distinct disease names from evidence_data
    results = (
        db.execute(
            select(func.distinct(CurationNew.evidence_data["disease_name"].astext))
            .join(ActiveCuration, ActiveCuration.curation_id == CurationNew.id)
            .where(
                ActiveCuration.archived_at.is_(None),
                CurationNew.evidence_data["disease_name"].astext.isnot(None),
                CurationNew.evidence_data["disease_name"].astext != "",
            )
            .limit(limit)
        )
        .scalars()
        .all()
    )

    return sorted([r for r in results if r])


def get_available_scopes_for_catalogue(db: Session) -> list[dict[str, Any]]:
    """Get scopes that have active curations in the catalogue.

    Returns scope info (id, name, display_name) for filtering.
    """
    results = db.execute(
        select(Scope.id, Scope.name, Scope.display_name, Scope.is_public)
        .join(ActiveCuration, ActiveCuration.scope_id == Scope.id)
        .where(ActiveCuration.archived_at.is_(None))
        .distinct()
    ).all()

    return [
        {
            "id": str(r.id),
            "name": r.name,
            "display_name": r.display_name,
            "is_public": r.is_public,
        }
        for r in results
    ]
