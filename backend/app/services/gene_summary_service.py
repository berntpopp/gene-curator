"""Gene summary aggregation service

This service computes and caches aggregate statistics for genes across scopes,
enabling fast public queries without real-time aggregation overhead.

Design Principles:
- Single Responsibility: Only handles gene summary computation
- Performance: Pre-computed aggregations reduce query load
- Flexibility: Works with active curations from ActiveCuration table
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger, timed_operation
from app.models.models import ActiveCuration, CurationNew, GeneSummary, Scope
from app.schemas.gene_summary import GeneSummaryPublic

logger = get_logger(__name__)


class GeneSummaryService:
    """Service for gene summary aggregation across scopes

    This service computes cross-scope statistics for genes including:
    - Classification consensus across scopes
    - Conflict detection
    - Public/private scope counts
    - Per-scope summary data
    """

    def __init__(self, db: Session) -> None:
        """Initialize gene summary service

        Args:
            db: Database session for query operations
        """
        self.db = db

    @timed_operation("compute_gene_summary", warning_threshold_ms=1000)
    def compute_summary(self, gene_id: UUID) -> GeneSummary:
        """Compute or update gene summary

        This method aggregates data from all active curations for a gene,
        computing classification consensus, detecting conflicts, and
        generating per-scope summaries.

        Args:
            gene_id: UUID of the gene to summarize

        Returns:
            Updated GeneSummary record
        """
        # Get all ACTIVE curations for gene via ActiveCuration table
        # This ensures we only summarize the current active curation per scope
        active_curation_records = (
            self.db.query(ActiveCuration)
            .filter(
                ActiveCuration.gene_id == gene_id,
                ActiveCuration.archived_at.is_(None),  # Not archived
            )
            .all()
        )

        if not active_curation_records:
            logger.info(
                "No active curations found for gene",
                gene_id=str(gene_id),
            )
            # Return empty summary or create one
            summary = (
                self.db.query(GeneSummary)
                .filter(GeneSummary.gene_id == gene_id)
                .first()
            )
            if not summary:
                summary = GeneSummary(gene_id=gene_id)
                self.db.add(summary)
                self.db.commit()
                self.db.refresh(summary)
            return summary

        # Get curation IDs
        curation_ids = [ac.curation_id for ac in active_curation_records]

        # Fetch all curations in one query
        curations = (
            self.db.query(CurationNew)
            .filter(CurationNew.id.in_(curation_ids))
            .all()
        )

        # Get unique scopes
        scope_ids = list({c.scope_id for c in curations})
        scopes = self.db.query(Scope).filter(Scope.id.in_(scope_ids)).all()
        scope_map = {s.id: s for s in scopes}

        # Count public vs private
        public_count = sum(1 for c in curations if scope_map[c.scope_id].is_public)
        private_count = len(curations) - public_count

        # Classification counts (using computed_verdict)
        classification_summary: dict[str, int] = {}
        for c in curations:
            classification = c.computed_verdict or "unknown"
            classification_summary[classification] = (
                classification_summary.get(classification, 0) + 1
            )

        # Per-scope summaries
        scope_summaries: list[dict[str, Any]] = []
        for curation in curations:
            scope = scope_map[curation.scope_id]

            # Extract scores from computed_scores JSONB
            genetic_score = curation.computed_scores.get(
                "genetic_evidence_total", 0
            ) if curation.computed_scores else 0
            experimental_score = curation.computed_scores.get(
                "experimental_evidence_total", 0
            ) if curation.computed_scores else 0
            total_score = curation.computed_scores.get(
                "total_score", 0
            ) if curation.computed_scores else 0
            evidence_items = curation.computed_scores.get(
                "evidence_items", []
            ) if curation.computed_scores else []

            scope_summaries.append({
                "scope_id": str(curation.scope_id),
                "scope_name": scope.name,
                "is_public": scope.is_public,
                "classification": curation.computed_verdict,
                "genetic_score": genetic_score,
                "experimental_score": experimental_score,
                "total_score": total_score,
                "last_updated": curation.updated_at.isoformat(),
                "curator_count": 1,  # TODO: Get from curation history
                "evidence_count": len(evidence_items) if isinstance(evidence_items, list) else 0,
            })

        # Check for conflicts
        unique_classifications = {
            c.computed_verdict for c in curations if c.computed_verdict
        }
        has_conflicts = len(unique_classifications) > 1

        # Get or create summary
        summary = (
            self.db.query(GeneSummary)
            .filter(GeneSummary.gene_id == gene_id)
            .first()
        )

        if not summary:
            summary = GeneSummary(gene_id=gene_id)
            self.db.add(summary)

        # Update fields
        summary.total_scopes_curated = len(scope_ids)
        summary.public_scopes_count = public_count
        summary.private_scopes_count = private_count
        summary.classification_summary = classification_summary
        summary.scope_summaries = scope_summaries
        summary.has_conflicts = has_conflicts
        summary.is_stale = False
        summary.last_computed_at = datetime.now()

        # Compute consensus (simple majority for MVP)
        if classification_summary:
            summary.consensus_classification = max(
                classification_summary, key=lambda k: classification_summary[k]
            )
            summary.consensus_confidence = (
                classification_summary[summary.consensus_classification] / len(curations)
            )
        else:
            summary.consensus_classification = None
            summary.consensus_confidence = None

        self.db.commit()
        self.db.refresh(summary)

        logger.info(
            "Gene summary computed",
            gene_id=str(gene_id),
            total_scopes=len(scope_ids),
            public_scopes=public_count,
            private_scopes=private_count,
            has_conflicts=has_conflicts,
            consensus=summary.consensus_classification,
        )

        return summary

    @timed_operation("get_public_gene_summary", warning_threshold_ms=500)
    def get_public_summary(self, gene_id: UUID) -> GeneSummaryPublic | None:
        """Get public summary (only public scopes)

        This method returns a filtered summary showing only public scopes,
        suitable for unauthenticated access.

        Args:
            gene_id: UUID of the gene

        Returns:
            GeneSummaryPublic with only public scopes, or None if no public data
        """
        summary = (
            self.db.query(GeneSummary)
            .filter(GeneSummary.gene_id == gene_id)
            .first()
        )

        if not summary:
            # Compute if doesn't exist
            logger.info(
                "Summary not found, computing",
                gene_id=str(gene_id),
            )
            summary = self.compute_summary(gene_id)

        # Recompute if stale
        if summary.is_stale:
            logger.info(
                "Summary is stale, recomputing",
                gene_id=str(gene_id),
            )
            summary = self.compute_summary(gene_id)

        # Filter to only public scopes
        public_scope_summaries = [
            s for s in summary.scope_summaries if s.get("is_public", False)
        ]

        if not public_scope_summaries:
            logger.info(
                "No public scope summaries found",
                gene_id=str(gene_id),
            )
            return None

        return GeneSummaryPublic(
            gene_id=summary.gene_id,
            public_scopes_count=summary.public_scopes_count,
            classification_summary=summary.classification_summary,
            consensus_classification=summary.consensus_classification,
            has_conflicts=summary.has_conflicts,
            scope_summaries=public_scope_summaries,
            last_updated=summary.last_computed_at,
        )

    def mark_stale(self, gene_id: UUID) -> None:
        """Mark gene summary as stale (called by trigger)

        This method is designed to be called by database triggers when
        curations are modified, marking the summary for recomputation.

        Args:
            gene_id: UUID of the gene whose summary should be marked stale
        """
        updated_count = (
            self.db.query(GeneSummary)
            .filter(GeneSummary.gene_id == gene_id)
            .update({"is_stale": True})
        )

        self.db.commit()

        if updated_count > 0:
            logger.info(
                "Gene summary marked as stale",
                gene_id=str(gene_id),
            )
        else:
            logger.warning(
                "No gene summary found to mark stale",
                gene_id=str(gene_id),
            )
