"""Gene summary aggregation service

Computes cross-scope statistics for a gene live from its active curations
(ActiveCuration table) plus the caller's in-progress work; nothing is cached.
"""

from collections import Counter
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
    Scope,
    ScopeMembership,
    UserNew,
)
from app.schemas.curation import disease_fields, relationship_of_key
from app.schemas.gene_summary import GeneSummaryFull, GeneSummaryPublic, ScopeSummary

logger = get_logger(__name__)


def _entry_order(entry: dict[str, Any]) -> tuple[str, bool, str]:
    """Scope name, active before in-progress, then curation id: stable across calls."""
    return (entry["scope_name"], entry["in_progress"], entry["curation_id"])


def _aggregate(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Consensus over active rows only (in-progress work is not a classification yet).

    Agreement is per gene-disease-MOI entity (#530): two entities with different verdicts
    are no conflict, and a gene with several entities has no single consensus.
    """
    counts: dict[str, int] = {}
    verdicts: dict[str, set[str]] = {}
    active = [e for e in entries if not e["in_progress"]]
    for e in active:
        key = e["classification"] or "unknown"
        counts[key] = counts.get(key, 0) + 1
        entity = verdicts.setdefault(e["entity_key"], set())
        if e["classification"]:
            entity.add(e["classification"])
    consensus = (
        max(sorted(counts), key=lambda k: counts[k])
        if counts and len(verdicts) == 1
        else None
    )
    conflicting = {k for k, v in verdicts.items() if len(v) > 1}
    conflict_counts = Counter(
        e["classification"]
        for e in active
        if e["entity_key"] in conflicting and e["classification"]
    )
    return {
        "classification_summary": counts,
        "conflict_summary": dict(conflict_counts),
        "consensus_classification": consensus,
        "consensus_confidence": counts[consensus] / sum(counts.values())
        if consensus
        else None,
        "has_conflicts": bool(conflicting),
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
        pre = curation.precuration.evidence_data if curation.precuration else None
        disease = disease_fields(curation.evidence_data, pre)
        return {
            "scope_id": str(curation.scope_id),
            "scope_name": scope.name,
            "is_public": scope.is_public,
            "curation_id": str(curation.id),
            "entity_key": curation.entity_key,
            "disease_name": disease["disease_name"],
            "mondo_id": disease["mondo_id"],
            "mode_of_inheritance": disease["mode_of_inheritance"],
            "relationship_type": relationship_of_key(curation.entity_key),
            "stage": curation.workflow_stage.value,
            "in_progress": in_progress,
            "classification": curation.final_classification,
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
        member_ids = self._member_scope_ids(user)
        entries = [
            e
            for e in self._build(gene_id)
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
        public_count = len(
            {e["scope_id"] for e in entries if e["is_public"] and not e["in_progress"]}
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
            last_updated=datetime.now(UTC),
            computation_version=1,  # SOP v11 version
            is_stale=False,
            **agg,
        )

    @timed_operation("compute_gene_summary", warning_threshold_ms=1000)
    def _build(self, gene_id: UUID) -> list[dict[str, Any]]:
        """Entries of the gene's active curations (one per scope and entity), sorted."""
        curations = (
            self.db.query(CurationNew)
            .join(ActiveCuration, ActiveCuration.curation_id == CurationNew.id)
            .filter(
                ActiveCuration.gene_id == gene_id,
                ActiveCuration.archived_at.is_(None),
            )
            .all()
        )
        scopes = {
            s.id: s
            for s in self.db.query(Scope).filter(
                Scope.id.in_({c.scope_id for c in curations})
            )
        }
        entries = [
            self._scope_entry(c, scopes[c.scope_id], in_progress=False)
            for c in curations
        ]
        entries.sort(key=_entry_order)
        logger.info("Gene summary computed", gene_id=str(gene_id), scopes=len(entries))
        return entries

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
        public_scope_summaries = [e for e in self._build(gene_id) if e["is_public"]]

        if not public_scope_summaries:
            logger.info(
                "No public scope summaries found",
                gene_id=str(gene_id),
            )
            return None

        agg = _aggregate(public_scope_summaries)
        return GeneSummaryPublic(
            gene_id=gene_id,
            public_scopes_count=len({e["scope_id"] for e in public_scope_summaries}),
            scope_summaries=[
                ScopeSummary.model_validate(e) for e in public_scope_summaries
            ],
            last_updated=datetime.now(UTC),
            classification_summary=agg["classification_summary"],
            consensus_classification=agg["consensus_classification"],
            has_conflicts=agg["has_conflicts"],
            conflict_summary=agg["conflict_summary"],
        )
