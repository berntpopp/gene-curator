"""Gene summary aggregation service

This service computes and caches aggregate statistics for genes across scopes,
enabling fast public queries without real-time aggregation overhead.

Design Principles:
- Single Responsibility: Only handles gene summary computation
- Performance: Pre-computed aggregations reduce query load
- Flexibility: Works with active curations from ActiveCuration table
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func as sa_func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, timed_operation
from app.models.models import (
    ActiveCuration,
    CurationNew,
    CurationStatus,
    GeneSummary,
    Scope,
    ScopeMembership,
    UserNew,
)
from app.schemas.curation import disease_fields
from app.schemas.gene_summary import GeneSummaryFull, GeneSummaryPublic, ScopeSummary

logger = get_logger(__name__)


def _entry_order(entry: dict[str, Any]) -> tuple[str, bool, str]:
    """Scope name, active before in-progress, then curation id: stable across calls."""
    return (entry["scope_name"], entry["in_progress"], entry["curation_id"])


def _aggregate(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Consensus over active rows only (in-progress work is not a classification yet)."""
    counts: dict[str, int] = {}
    for e in entries:
        if not e["in_progress"]:
            key = e["classification"] or "unknown"
            counts[key] = counts.get(key, 0) + 1
    consensus = max(sorted(counts), key=lambda k: counts[k]) if counts else None
    return {
        "classification_summary": counts,
        "consensus_classification": consensus,
        "consensus_confidence": counts[consensus] / sum(counts.values())
        if consensus
        else None,
        "has_conflicts": len(
            {
                e["classification"]
                for e in entries
                if not e["in_progress"] and e["classification"]
            }
        )
        > 1,
    }


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

    def _get_curator_count(self, gene_id: UUID, scope_id: UUID) -> int:
        """Count distinct users who created curations for a gene in a scope."""
        stmt = select(sa_func.count(sa_func.distinct(CurationNew.created_by))).where(
            CurationNew.gene_id == gene_id,
            CurationNew.scope_id == scope_id,
        )
        result = self.db.execute(stmt).scalar()
        return result or 0

    def _scope_entry(
        self, curation: CurationNew, scope: Scope, *, in_progress: bool
    ) -> dict[str, Any]:
        """One per-scope row: curation link, disease, stage and scores."""
        scores = curation.computed_scores or {}
        items = scores.get("evidence_items", [])
        disease = disease_fields(
            curation.evidence_data,
            curation.precuration.evidence_data if curation.precuration else None,
        )
        return {
            "scope_id": str(curation.scope_id),
            "scope_name": scope.name,
            "is_public": scope.is_public,
            "curation_id": str(curation.id),
            "disease_name": disease["disease_name"],
            "mode_of_inheritance": disease["mode_of_inheritance"],
            "stage": curation.workflow_stage.value,
            "in_progress": in_progress,
            "classification": curation.computed_verdict,
            "genetic_score": scores.get("genetic_evidence_total", 0),
            "experimental_score": scores.get("experimental_evidence_total", 0),
            "total_score": scores.get("total_score", 0),
            "last_updated": curation.updated_at.isoformat(),
            "curator_count": self._get_curator_count(
                curation.gene_id, curation.scope_id
            ),
            "evidence_count": len(items) if isinstance(items, list) else 0,
        }

    def _member_scope_ids(self, user: UserNew | None) -> set[UUID]:
        """Accepted, active memberships only. Platform admins get no extra scopes."""
        if user is None:
            return set()
        stmt = (
            select(ScopeMembership.scope_id)
            .join(Scope, Scope.id == ScopeMembership.scope_id)
            .where(
                ScopeMembership.user_id == user.id,
                ScopeMembership.is_active,
                ScopeMembership.accepted_at.isnot(None),
                Scope.is_active,
            )
        )
        return set(self.db.execute(stmt).scalars())

    def get_full_summary(self, gene_id: UUID, user: UserNew) -> GeneSummaryFull:
        """Public scopes plus the caller's own scopes, with the caller's in-progress work.

        Consensus and conflicts are recomputed from the visible active rows only,
        so a private scope never influences what a non-member sees.
        """
        summary = self.compute_summary(gene_id)
        member_ids = self._member_scope_ids(user)
        entries = [
            e
            for e in summary.scope_summaries
            if e.get("is_public") or UUID(e["scope_id"]) in member_ids
        ]
        active_ids = {e["curation_id"] for e in entries}
        if member_ids:
            stmt = (
                select(CurationNew, Scope)
                .join(Scope, Scope.id == CurationNew.scope_id)
                .where(
                    CurationNew.gene_id == gene_id,
                    CurationNew.scope_id.in_(member_ids),
                    CurationNew.status.notin_(
                        [
                            CurationStatus.ACTIVE,
                            CurationStatus.ARCHIVED,
                            CurationStatus.REJECTED,
                        ]
                    ),
                )
            )
            entries += [
                self._scope_entry(c, sc, in_progress=True)
                for c, sc in self.db.execute(stmt)
                if str(c.id) not in active_ids
            ]
        entries.sort(key=_entry_order)
        public_count = sum(
            1 for e in entries if e["is_public"] and not e["in_progress"]
        )
        agg = _aggregate(entries)
        return GeneSummaryFull(
            gene_id=gene_id,
            total_scopes_curated=len({e["scope_id"] for e in entries}),
            public_scopes_count=public_count,
            private_scopes_count=len(
                {e["scope_id"] for e in entries if not e["is_public"]}
            ),
            scope_summaries=[ScopeSummary.model_validate(e) for e in entries],
            last_updated=summary.last_computed_at,
            computation_version=1,  # SOP v11 version
            is_stale=summary.is_stale,
            **agg,
        )

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
            summary = (
                self.db.query(GeneSummary)
                .filter(GeneSummary.gene_id == gene_id)
                .first()
            )
            if not summary:
                summary = GeneSummary(gene_id=gene_id)
                self.db.add(summary)
            # Drop anything cached from curations that are no longer active.
            summary.total_scopes_curated = 0
            summary.public_scopes_count = 0
            summary.private_scopes_count = 0
            summary.classification_summary = {}
            summary.scope_summaries = []
            summary.has_conflicts = False
            summary.consensus_classification = None
            summary.consensus_confidence = None
            summary.is_stale = False
            summary.last_computed_at = datetime.now(UTC)
            self.db.commit()
            self.db.refresh(summary)
            return summary

        # Get curation IDs
        curation_ids = [ac.curation_id for ac in active_curation_records]

        # Fetch all curations in one query
        curations = (
            self.db.query(CurationNew).filter(CurationNew.id.in_(curation_ids)).all()
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

        scope_summaries = [
            self._scope_entry(c, scope_map[c.scope_id], in_progress=False)
            for c in curations
        ]
        scope_summaries.sort(key=_entry_order)

        # Check for conflicts
        unique_classifications = {
            c.computed_verdict for c in curations if c.computed_verdict
        }
        has_conflicts = len(unique_classifications) > 1

        # Get or create summary
        summary = (
            self.db.query(GeneSummary).filter(GeneSummary.gene_id == gene_id).first()
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
        summary.last_computed_at = datetime.now(UTC)

        # Compute consensus (simple majority for MVP)
        if classification_summary:
            summary.consensus_classification = max(
                classification_summary, key=lambda k: classification_summary[k]
            )
            summary.consensus_confidence = classification_summary[
                summary.consensus_classification
            ] / len(curations)
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
        # Always recompute (as the full summary does): the cached row is not marked
        # stale when a scope turns private or an activation is archived.
        summary = self.compute_summary(gene_id)
        public_scope_summaries = [
            e for e in summary.scope_summaries if e.get("is_public", False)
        ]

        if not public_scope_summaries:
            logger.info(
                "No public scope summaries found",
                gene_id=str(gene_id),
            )
            return None

        agg = _aggregate(public_scope_summaries)
        return GeneSummaryPublic(
            gene_id=summary.gene_id,
            public_scopes_count=summary.public_scopes_count,
            scope_summaries=[
                ScopeSummary.model_validate(e) for e in public_scope_summaries
            ],
            last_updated=summary.last_computed_at,
            classification_summary=agg["classification_summary"],
            consensus_classification=agg["consensus_classification"],
            has_conflicts=agg["has_conflicts"],
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
