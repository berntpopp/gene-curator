"""
CRUD operations for the new Gene model in schema-agnostic system.
"""

import hashlib
import json
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import Session

from app.core.logging import batch_operation, database_query, timed_operation
from app.crud.base import CRUDBase
from app.models import (
    CurationNew,
    GeneNew,
    GeneScopeAssignment,
    PrecurationNew,
)
from app.schemas.gene_new import (
    GeneNewCreate,
    GeneNewUpdate,
    GeneSearchQuery,
)


class CRUDGeneNew(CRUDBase[GeneNew, GeneNewCreate, GeneNewUpdate]):
    """CRUD operations for the new Gene model."""

    def generate_record_hash(self, gene_data: dict[str, Any], user_id: UUID) -> str:
        """Generate SHA-256 hash for record integrity."""
        content_string = (
            str(gene_data.get("hgnc_id", ""))
            + str(gene_data.get("approved_symbol", ""))
            + str(gene_data.get("chromosome", ""))
            + json.dumps(gene_data.get("details", {}), sort_keys=True)
            + str(user_id)
        )
        return hashlib.sha256(content_string.encode()).hexdigest()

    @database_query(query_type="SELECT")
    def get_by_hgnc_id(self, db: Session, *, hgnc_id: str) -> GeneNew | None:
        """Get gene by HGNC ID."""
        return db.execute(select(GeneNew).where(GeneNew.hgnc_id == hgnc_id)).scalars().first()

    def get_by_symbol(self, db: Session, *, symbol: str) -> GeneNew | None:
        """Get gene by approved symbol."""
        return db.execute(
            select(GeneNew).where(GeneNew.approved_symbol.ilike(f"%{symbol}%"))
        ).scalars().first()

    @database_query(query_type="SELECT")
    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "approved_symbol",
        sort_order: str = "asc",
    ) -> Sequence[GeneNew]:
        """Get multiple genes with pagination and sorting."""
        stmt = select(GeneNew)

        # Apply sorting
        if hasattr(GeneNew, sort_by):
            order_column = getattr(GeneNew, sort_by)
            if sort_order.lower() == "desc":
                stmt = stmt.order_by(order_column.desc())
            else:
                stmt = stmt.order_by(order_column.asc())

        return db.execute(stmt.offset(skip).limit(limit)).scalars().all()

    @timed_operation("gene_search", warning_threshold_ms=500)
    def search(self, db: Session, *, search_params: GeneSearchQuery) -> Sequence[GeneNew]:
        """Advanced gene search with multiple filters."""
        stmt = select(GeneNew)

        # Text search across multiple fields
        if search_params.query:
            search_term = f"%{search_params.query}%"
            stmt = stmt.where(
                or_(
                    GeneNew.approved_symbol.ilike(search_term),
                    GeneNew.hgnc_id.ilike(search_term),
                    GeneNew.details.op("->>")("gene_description").ilike(search_term),
                    text(f"'{search_params.query}' = ANY(genes_new.previous_symbols)"),
                    text(f"'{search_params.query}' = ANY(genes_new.alias_symbols)"),
                )
            )

        # Filter by chromosome
        if search_params.chromosome:
            stmt = stmt.where(GeneNew.chromosome == search_params.chromosome)

        # Filter by HGNC ID
        if search_params.hgnc_id:
            stmt = stmt.where(GeneNew.hgnc_id == search_params.hgnc_id)

        # Apply sorting
        if hasattr(GeneNew, search_params.sort_by):
            order_column = getattr(GeneNew, search_params.sort_by)
            if search_params.sort_order.lower() == "desc":
                stmt = stmt.order_by(order_column.desc())
            else:
                stmt = stmt.order_by(order_column.asc())

        return db.execute(stmt.offset(search_params.skip).limit(search_params.limit)).scalars().all()

    @database_query(query_type="INSERT")
    def create_with_owner(
        self, db: Session, *, obj_in: GeneNewCreate, owner_id: UUID
    ) -> GeneNew:
        """Create a new gene with owner."""
        # Check if gene with HGNC ID already exists
        existing_gene = self.get_by_hgnc_id(db, hgnc_id=obj_in.hgnc_id)
        if existing_gene:
            raise ValueError(f"Gene with HGNC ID {obj_in.hgnc_id} already exists")

        # Prepare gene data
        gene_data = obj_in.model_dump()
        record_hash = self.generate_record_hash(gene_data, owner_id)

        obj_in_data = obj_in.model_dump()
        obj_in_data.update(
            {
                "record_hash": record_hash,
                "created_by": owner_id,
                "updated_by": owner_id,
            }
        )

        db_obj = GeneNew(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_with_owner(
        self, db: Session, *, db_obj: GeneNew, obj_in: GeneNewUpdate, owner_id: UUID
    ) -> GeneNew:
        """Update gene with owner tracking."""
        # Store previous hash
        previous_hash = db_obj.record_hash

        # Update fields
        update_data = obj_in.model_dump(exclude_unset=True)

        # Check for HGNC ID conflicts if being updated
        if "hgnc_id" in update_data and update_data["hgnc_id"] != db_obj.hgnc_id:
            existing_gene = self.get_by_hgnc_id(db, hgnc_id=update_data["hgnc_id"])
            if existing_gene and existing_gene.id != db_obj.id:
                raise ValueError(
                    f"Gene with HGNC ID {update_data['hgnc_id']} already exists"
                )

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # Update metadata
        db_obj.updated_by = owner_id
        db_obj.previous_hash = previous_hash

        # Generate new hash
        current_data = {
            "hgnc_id": db_obj.hgnc_id,
            "approved_symbol": db_obj.approved_symbol,
            "chromosome": db_obj.chromosome,
            "details": db_obj.details,
        }
        db_obj.record_hash = self.generate_record_hash(current_data, owner_id)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    @batch_operation(
        "gene_bulk_create",
        batch_size_getter=lambda genes_data, **kwargs: len(genes_data),
    )
    def bulk_create(
        self,
        db: Session,
        *,
        genes_data: list[GeneNewCreate],
        owner_id: UUID,
        skip_duplicates: bool = True,
    ) -> dict[str, Any]:
        """Bulk create multiple genes."""
        created_genes = []
        skipped_genes = []
        errors = []

        for gene_data in genes_data:
            try:
                # Check for existing gene
                existing_gene = self.get_by_hgnc_id(db, hgnc_id=gene_data.hgnc_id)
                if existing_gene:
                    if skip_duplicates:
                        skipped_genes.append(
                            {
                                "hgnc_id": gene_data.hgnc_id,
                                "reason": "Gene with this HGNC ID already exists",
                            }
                        )
                        continue
                    else:
                        errors.append(
                            {
                                "hgnc_id": gene_data.hgnc_id,
                                "error": "Gene with this HGNC ID already exists",
                            }
                        )
                        continue

                # Create gene
                created_gene = self.create_with_owner(
                    db, obj_in=gene_data, owner_id=owner_id
                )
                created_genes.append(created_gene)

            except Exception as e:
                errors.append({"hgnc_id": gene_data.hgnc_id, "error": str(e)})

        return {
            "created_genes": created_genes,
            "skipped_genes": skipped_genes,
            "errors": errors,
            "total_processed": len(genes_data),
            "total_created": len(created_genes),
            "total_skipped": len(skipped_genes),
            "total_errors": len(errors),
        }

    def get_genes_for_scope(
        self,
        db: Session,
        *,
        scope_id: UUID,
        skip: int = 0,
        limit: int = 100,
        assigned_only: bool = False,
    ) -> Sequence[GeneNew]:
        """Get genes available or assigned to a specific scope."""
        if assigned_only:
            # Get only genes assigned to this scope
            stmt = select(GeneNew).join(
                GeneScopeAssignment,
                and_(
                    GeneScopeAssignment.gene_id == GeneNew.id,
                    GeneScopeAssignment.scope_id == scope_id,
                    GeneScopeAssignment.is_active,  # Fixed: use == instead of is,
                ),
            )
        else:
            # Get all genes (could be filtered by scope preferences in the future)
            stmt = select(GeneNew)

        return db.execute(stmt.offset(skip).limit(limit)).scalars().all()

    def get_gene_assignment_status(
        self, db: Session, *, gene_id: UUID, scope_id: UUID | None = None
    ) -> dict[str, Any]:
        """Get assignment status for a gene across scopes."""
        stmt = select(GeneScopeAssignment).where(
            and_(
                GeneScopeAssignment.gene_id == gene_id,
                GeneScopeAssignment.is_active,  # Fixed: use == instead of is,
            )
        )

        if scope_id:
            stmt = stmt.where(GeneScopeAssignment.scope_id == scope_id)

        assignments = db.execute(stmt).scalars().all()

        # Group by scope
        scope_assignments: dict[str, dict[str, Any]] = {}
        for assignment in assignments:
            scope_assignments[str(assignment.scope_id)] = {
                "assignment_id": assignment.id,
                "assigned_curator_id": assignment.assigned_curator_id,
                "assigned_at": assignment.assigned_at,
            }

        return {
            "gene_id": gene_id,
            "total_scope_assignments": len(assignments),
            "scope_assignments": scope_assignments,
            "is_assigned_to_any_scope": len(assignments) > 0,
        }

    def get_gene_curation_progress(
        self, db: Session, *, gene_id: UUID, scope_id: UUID | None = None
    ) -> dict[str, Any]:
        """Get curation progress for a gene."""
        precuration_stmt = select(PrecurationNew).where(
            PrecurationNew.gene_id == gene_id
        )
        curation_stmt = select(CurationNew).where(CurationNew.gene_id == gene_id)

        if scope_id:
            precuration_stmt = precuration_stmt.where(
                PrecurationNew.scope_id == scope_id
            )
            curation_stmt = curation_stmt.where(CurationNew.scope_id == scope_id)

        precurations = db.execute(precuration_stmt).scalars().all()
        curations = db.execute(curation_stmt).scalars().all()

        # Count by status
        precuration_status_counts: dict[str, int] = {}
        for precuration in precurations:
            status = (
                precuration.status.value
                if hasattr(precuration.status, "value")
                else str(precuration.status)
            )
            precuration_status_counts[status] = (
                precuration_status_counts.get(status, 0) + 1
            )

        curation_status_counts: dict[str, int] = {}
        for curation in curations:
            status = (
                curation.status.value
                if hasattr(curation.status, "value")
                else str(curation.status)
            )
            curation_status_counts[status] = curation_status_counts.get(status, 0) + 1

        return {
            "gene_id": gene_id,
            "scope_id": scope_id,
            "total_precurations": len(precurations),
            "total_curations": len(curations),
            "precuration_status_counts": precuration_status_counts,
            "curation_status_counts": curation_status_counts,
            "has_active_work": len(precurations) > 0 or len(curations) > 0,
        }

    @timed_operation("gene_statistics", warning_threshold_ms=1000)
    def get_statistics(
        self, db: Session, *, scope_id: UUID | None = None
    ) -> dict[str, Any]:
        """Get gene database statistics."""
        from datetime import datetime, timedelta

        base_stmt = select(GeneNew)

        # If scope specified, filter to genes assigned to that scope
        if scope_id:
            base_stmt = base_stmt.join(
                GeneScopeAssignment,
                and_(
                    GeneScopeAssignment.gene_id == GeneNew.id,
                    GeneScopeAssignment.scope_id == scope_id,
                    GeneScopeAssignment.is_active,  # Fixed: use == instead of is,
                ),
            )

        # Total genes
        total_genes = db.execute(select(func.count()).select_from(base_stmt.subquery())).scalar() or 0

        # Recent additions (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_additions = db.execute(
            select(func.count()).select_from(
                base_stmt.where(GeneNew.created_at >= thirty_days_ago).subquery()
            )
        ).scalar() or 0

        # Updated last week
        week_ago = datetime.utcnow() - timedelta(days=7)
        updated_last_week = db.execute(
            select(func.count()).select_from(
                base_stmt.where(GeneNew.updated_at >= week_ago).subquery()
            )
        ).scalar() or 0

        # Genes with detailed information
        genes_with_details = db.execute(
            select(func.count()).select_from(
                base_stmt.where(
                    GeneNew.details.isnot(None),
                    func.jsonb_typeof(GeneNew.details) == "object"
                ).subquery()
            )
        ).scalar() or 0

        # Assignment statistics (if scope not specified)
        assignment_stats: dict[str, int] = {}
        if not scope_id:
            total_assignments = db.execute(
                select(func.count(GeneScopeAssignment.id))
                .where(GeneScopeAssignment.is_active)  # Fixed: use == instead of is
            ).scalar() or 0

            assigned_genes = db.execute(
                select(func.count(func.distinct(GeneScopeAssignment.gene_id)))
                .where(GeneScopeAssignment.is_active)  # Fixed: use == instead of is
            ).scalar() or 0

            unassigned_genes = total_genes - assigned_genes

            assignment_stats = {
                "total_assignments": total_assignments or 0,
                "assigned_genes": assigned_genes or 0,
                "unassigned_genes": max(0, unassigned_genes),
            }

        result = {
            "scope_id": scope_id,
            "total_genes": total_genes,
            "recent_additions": recent_additions,
            "updated_last_week": updated_last_week,
            "genes_with_details": genes_with_details,
            **assignment_stats,
        }

        return result


# Create instance
gene_new_crud = CRUDGeneNew(GeneNew)
