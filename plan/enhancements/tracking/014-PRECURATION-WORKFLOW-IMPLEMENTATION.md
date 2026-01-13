# Enhancement #014: ClinGen-Compliant Precuration Workflow Implementation

**Date:** 2026-01-13
**Author:** Claude (Automated Analysis)
**Status:** PLANNED
**Priority:** HIGH
**Related Issues:** #116, #118, #119, #62, #61, #77
**ClinGen SOP Version:** v11 (effective June 1, 2023)

---

## Executive Summary

The Gene Curator application has **designed but not implemented** the precuration stage. While the backend models (`PrecurationNew`, `WorkflowPair`, `CurationSchema` with `SchemaType.PRECURATION`) exist, there are **no API endpoints, no CRUD operations, no Pydantic schemas, and no frontend views** for precurations.

Per ClinGen SOP v11, precuration is **mandatory** as of June 1, 2023. A precuration ID is required to start new GCI records. This enhancement provides a complete implementation plan.

---

## Current Architecture Analysis

### What EXISTS (Backend)

| Component | Status | Location |
|-----------|--------|----------|
| `PrecurationNew` model | ✅ Complete | `backend/app/models/models.py:661-763` |
| `WorkflowPair` model | ✅ Complete | `backend/app/models/models.py:436-508` |
| `SchemaType.PRECURATION` enum | ✅ Exists | `backend/app/models/models.py:85-88` |
| `WorkflowStage.PRECURATION` enum | ✅ Exists | `backend/app/models/models.py:60-65` |
| Curation model with `precuration_id` | ✅ FK exists (nullable) | `backend/app/models/models.py:794` |
| Workflow engine transitions | ✅ Partial | `backend/app/crud/workflow_engine.py` |

### What's MISSING

| Component | Impact | Priority |
|-----------|--------|----------|
| Precuration Pydantic schemas | No request/response validation | HIGH |
| Precuration CRUD module | No database operations | HIGH |
| Precuration API endpoints | No REST API | HIGH |
| Precuration schema definition (seed data) | No form fields | HIGH |
| Frontend precuration store | No state management | MEDIUM |
| Frontend precuration views | No UI | MEDIUM |
| `precuration_id` enforcement | Workflow bypass possible | MEDIUM |
| Data prefill from precuration to curation | Manual re-entry required | LOW |

---

## ClinGen SOP v11 Requirements Analysis

### Precuration Definition

Per Section 4.1 of ClinGen SOP v11:

> **Precuration** is the process of establishing the disease entity (gene-disease pair) and mode of inheritance (MOI) BEFORE collecting evidence.

### Required Precuration Fields

| Field | Source | Description | Type |
|-------|--------|-------------|------|
| `gene_symbol` | HGNC | Official gene symbol | string (auto-filled) |
| `hgnc_id` | HGNC | HGNC identifier | string (auto-filled) |
| `mondo_id` | Mondo Disease Ontology | Disease identifier | string (required) |
| `disease_name` | Mondo/User | Disease name (dyadic naming) | string (required) |
| `mode_of_inheritance` | HPO | MOI term | enum (required) |
| `hp_moi_term` | HPO | HPO term for MOI | string (required) |
| `lumping_splitting_decision` | User | Lumping/splitting rationale | enum (required if applicable) |
| `lumping_splitting_notes` | User | Justification text | text (optional) |
| `affiliation` | User | Curation group | string (required) |
| `precuration_id` | System | Auto-generated identifier | UUID (system) |
| `precuration_date` | System | When precuration was completed | datetime (system) |

### Mode of Inheritance Options (ClinGen SOP v11)

```json
{
  "options": [
    {"value": "AD", "label": "Autosomal Dominant", "hp_term": "HP:0000006"},
    {"value": "AR", "label": "Autosomal Recessive", "hp_term": "HP:0000007"},
    {"value": "XLD", "label": "X-linked Dominant", "hp_term": "HP:0001417"},
    {"value": "XLR", "label": "X-linked Recessive", "hp_term": "HP:0001419"},
    {"value": "SD", "label": "Semidominant", "hp_term": "HP:0032113"},
    {"value": "MT", "label": "Mitochondrial", "hp_term": "HP:0001427"},
    {"value": "Other", "label": "Other (specify)", "hp_term": null}
  ]
}
```

### Lumping & Splitting Guidelines

Per ClinGen Lumping and Splitting Working Group:

1. **LUMP** when: Multiple phenotypes share the same genetic mechanism
2. **SPLIT** when: Distinct molecular mechanisms or phenotypes warrant separate classifications
3. **Document rationale**: Required in evidence summary

---

## Design Patterns Applied

### 1. State Machine Pattern (Workflow)

```
ENTRY → PRECURATION → CURATION → REVIEW → ACTIVE
  │         │            │         │        │
  └─────────┴────────────┴─────────┴────────┘
            (valid transitions only)
```

**Key Principle:** Each transition is validated before execution.

### 2. CQRS Pattern (Separation of Concerns)

- **Commands**: Create, Update, Submit, Approve
- **Queries**: List, Get, Filter, Search

### 3. Saga Pattern (Multi-Step Workflow)

Precuration → Curation is a saga with:
- Precuration approval triggers curation creation
- Data prefill from precuration to curation
- Compensating action if curation fails

### 4. 4-Eyes Principle (Mandatory Review)

```
Curator ──creates──> Precuration ──submits──> Reviewer ──approves──> Curation enabled
```

---

## Implementation Plan

### Phase 1: Backend Foundation (Estimated: 8-12 hours)

#### Task 1.1: Create Precuration Pydantic Schemas

**File:** `backend/app/schemas/precuration.py`

```python
"""
Pydantic V2 schemas for precuration API operations.
Follows ClinGen SOP v11 requirements for gene-disease-MOI establishment.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import CurationStatus, WorkflowStage


# ========================================
# PRECURATION EVIDENCE DATA SCHEMA
# ========================================

class PrecurationEvidenceData(BaseModel):
    """
    ClinGen SOP v11 precuration evidence structure.
    These fields are stored in the evidence_data JSONB column.
    """
    # Disease Entity (required for ClinGen)
    mondo_id: str = Field(..., description="Mondo Disease Ontology ID")
    disease_name: str = Field(..., description="Disease name (dyadic naming)")

    # Mode of Inheritance (required)
    mode_of_inheritance: str = Field(..., description="MOI code (AD, AR, XLD, etc.)")
    hp_moi_term: str | None = Field(None, description="HPO term for MOI")

    # Lumping & Splitting (conditional)
    lumping_splitting_applicable: bool = Field(False, description="Whether L&S applies")
    lumping_splitting_decision: str | None = Field(
        None, description="LUMP, SPLIT, or NOT_APPLICABLE"
    )
    lumping_splitting_notes: str | None = Field(None, description="L&S rationale")

    # Affiliation
    affiliation: str | None = Field(None, description="Curation group/affiliation")

    # Additional notes
    curator_notes: str | None = Field(None, description="Curator notes")


# ========================================
# REQUEST SCHEMAS
# ========================================

class PrecurationCreate(BaseModel):
    """Schema for creating a new precuration."""
    gene_id: UUID = Field(..., description="Gene UUID")
    scope_id: UUID = Field(..., description="Scope UUID")
    precuration_schema_id: UUID = Field(..., description="Precuration schema UUID")
    evidence_data: dict[str, Any] = Field(
        default_factory=dict, description="Precuration evidence data"
    )


class PrecurationUpdate(BaseModel):
    """Schema for updating an existing precuration."""
    evidence_data: dict[str, Any] | None = Field(
        None, description="Updated evidence data"
    )

    model_config = ConfigDict(extra="forbid")


class PrecurationSubmit(BaseModel):
    """Schema for submitting a precuration for review."""
    notes: str | None = Field(None, max_length=1000, description="Submission notes")


# ========================================
# DATABASE SCHEMAS (InDBBase pattern)
# ========================================

class PrecurationInDBBase(BaseModel):
    """Base schema with database fields."""
    id: UUID
    gene_id: UUID
    scope_id: UUID
    precuration_schema_id: UUID

    status: CurationStatus
    workflow_stage: WorkflowStage
    is_draft: bool

    evidence_data: dict[str, Any]
    computed_scores: dict[str, Any]
    computed_fields: dict[str, Any]

    created_at: datetime
    updated_at: datetime
    auto_saved_at: datetime | None

    created_by: UUID | None
    updated_by: UUID | None

    version_number: int

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


# ========================================
# RESPONSE SCHEMAS
# ========================================

class Precuration(PrecurationInDBBase):
    """Full precuration response schema."""
    pass


class PrecurationSummary(BaseModel):
    """Lightweight precuration summary for list views."""
    id: UUID
    gene_id: UUID
    gene_symbol: str
    scope_id: UUID
    scope_name: str
    status: CurationStatus
    workflow_stage: WorkflowStage
    mondo_id: str | None
    disease_name: str | None
    mode_of_inheritance: str | None
    is_draft: bool
    created_at: datetime
    updated_at: datetime
    curator_name: str | None

    model_config = ConfigDict(use_enum_values=True)


class PrecurationListResponse(BaseModel):
    """Paginated list response."""
    precurations: list[PrecurationSummary]
    total: int
    skip: int
    limit: int


class PrecurationApprovalResult(BaseModel):
    """Result of precuration approval."""
    precuration_id: UUID
    approved: bool
    curation_created: bool
    curation_id: UUID | None
    message: str
```

#### Task 1.2: Create Precuration CRUD Module

**File:** `backend/app/crud/precuration.py`

> **IMPORTANT:** Extends `CRUDBase` to follow project patterns (see `curation.py`).

```python
"""
CRUD operations for precurations.
Extends CRUDBase with precuration-specific operations.
Follows patterns from curation.py.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.logging import get_logger
from app.crud.base import CRUDBase
from app.crud.workflow_engine import workflow_engine
from app.models import (
    CurationNew,
    CurationSchema,
    CurationStatus,
    Gene,
    PrecurationNew,
    Scope,
    UserNew,
    WorkflowPair,
    WorkflowStage,
)
from app.schemas.precuration import (
    PrecurationApprovalResult,
    PrecurationCreate,
    PrecurationSubmit,
    PrecurationSummary,
    PrecurationUpdate,
)

logger = get_logger(__name__)


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class CRUDPrecuration(CRUDBase[PrecurationNew, PrecurationCreate, PrecurationUpdate]):
    """
    CRUD operations for precurations with workflow integration.

    Extends base CRUD with:
    - ClinGen SOP v11 validation
    - Scope-based filtering
    - Workflow state management
    - Precuration-to-curation data mapping
    """

    # ========================================
    # READ OPERATIONS
    # ========================================

    def get_with_relations(self, db: Session, id: UUID) -> PrecurationNew | None:
        """Get precuration with eager-loaded relationships."""
        stmt = (
            select(PrecurationNew)
            .options(
                joinedload(PrecurationNew.gene),
                joinedload(PrecurationNew.scope),
                joinedload(PrecurationNew.creator),
                joinedload(PrecurationNew.precuration_schema),
            )
            .where(PrecurationNew.id == id)
        )
        return db.execute(stmt).scalars().first()

    def get_by_scope(
        self,
        db: Session,
        scope_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
        status: CurationStatus | None = None,
        include_drafts: bool = True,
    ) -> list[PrecurationNew]:
        """Get precurations filtered by scope."""
        stmt = select(PrecurationNew).where(PrecurationNew.scope_id == scope_id)

        if status:
            stmt = stmt.where(PrecurationNew.status == status)
        if not include_drafts:
            stmt = stmt.where(PrecurationNew.is_draft == False)  # noqa: E712

        stmt = stmt.offset(skip).limit(limit).order_by(PrecurationNew.updated_at.desc())
        return list(db.execute(stmt).scalars().all())

    def get_by_gene_and_scope(
        self,
        db: Session,
        gene_id: UUID,
        scope_id: UUID,
    ) -> list[PrecurationNew]:
        """Get all precurations for a gene within a scope."""
        stmt = (
            select(PrecurationNew)
            .where(
                PrecurationNew.gene_id == gene_id,
                PrecurationNew.scope_id == scope_id,
            )
            .order_by(PrecurationNew.created_at.desc())
        )
        return list(db.execute(stmt).scalars().all())

    def get_multi_filtered(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        scope_id: UUID | None = None,
        scope_ids: list[UUID] | None = None,
        gene_id: UUID | None = None,
        status: CurationStatus | None = None,
    ) -> tuple[list[PrecurationSummary], int]:
        """
        Get precuration summaries with joined data for list views.
        Returns lightweight summaries (no evidence_data) for performance.
        """
        # Base query with joins
        stmt = (
            select(
                PrecurationNew,
                Gene.approved_symbol.label("gene_symbol"),
                Scope.name.label("scope_name"),
                UserNew.name.label("curator_name"),
            )
            .join(Gene, PrecurationNew.gene_id == Gene.id)
            .join(Scope, PrecurationNew.scope_id == Scope.id)
            .outerjoin(UserNew, PrecurationNew.created_by == UserNew.id)
        )

        # Apply filters
        if scope_id:
            stmt = stmt.where(PrecurationNew.scope_id == scope_id)
        if scope_ids:
            stmt = stmt.where(PrecurationNew.scope_id.in_(scope_ids))
        if gene_id:
            stmt = stmt.where(PrecurationNew.gene_id == gene_id)
        if status:
            stmt = stmt.where(PrecurationNew.status == status)

        # Get total count (before pagination)
        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(PrecurationNew.id).subquery()
        )
        total = db.execute(count_stmt).scalar() or 0

        # Apply pagination and ordering
        stmt = stmt.offset(skip).limit(limit).order_by(PrecurationNew.updated_at.desc())

        results = db.execute(stmt).all()

        # Map to summary schema - extract Mondo ID and MOI from evidence_data
        summaries = [
            PrecurationSummary(
                id=row.PrecurationNew.id,
                gene_id=row.PrecurationNew.gene_id,
                gene_symbol=row.gene_symbol,
                scope_id=row.PrecurationNew.scope_id,
                scope_name=row.scope_name,
                status=row.PrecurationNew.status,
                workflow_stage=row.PrecurationNew.workflow_stage,
                mondo_id=row.PrecurationNew.evidence_data.get("mondo_id"),
                disease_name=row.PrecurationNew.evidence_data.get("disease_name"),
                mode_of_inheritance=row.PrecurationNew.evidence_data.get(
                    "mode_of_inheritance"
                ),
                is_draft=row.PrecurationNew.is_draft,
                created_at=row.PrecurationNew.created_at,
                updated_at=row.PrecurationNew.updated_at,
                curator_name=row.curator_name,
            )
            for row in results
        ]

        return summaries, total

    # ========================================
    # WRITE OPERATIONS (with FK validation)
    # ========================================

    def create_precuration(
        self,
        db: Session,
        *,
        obj_in: PrecurationCreate,
        user_id: UUID,
    ) -> PrecurationNew:
        """Create a new precuration with proper initialization and FK validation."""
        # Validate foreign keys exist
        gene = db.get(Gene, obj_in.gene_id)
        if not gene:
            raise ValueError(f"Gene with id {obj_in.gene_id} not found")

        scope = db.get(Scope, obj_in.scope_id)
        if not scope:
            raise ValueError(f"Scope with id {obj_in.scope_id} not found")

        precuration_schema = db.get(CurationSchema, obj_in.precuration_schema_id)
        if not precuration_schema:
            raise ValueError(
                f"CurationSchema with id {obj_in.precuration_schema_id} not found"
            )

        # Create precuration
        now = _utc_now()
        db_obj = PrecurationNew(
            gene_id=obj_in.gene_id,
            scope_id=obj_in.scope_id,
            precuration_schema_id=obj_in.precuration_schema_id,
            evidence_data=obj_in.evidence_data,
            status=CurationStatus.DRAFT,
            workflow_stage=WorkflowStage.PRECURATION,
            is_draft=True,
            created_by=user_id,
            updated_by=user_id,
            created_at=now,
            updated_at=now,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        logger.info(
            "Precuration created",
            precuration_id=str(db_obj.id),
            gene_id=str(obj_in.gene_id),
            scope_id=str(obj_in.scope_id),
            user_id=str(user_id),
        )

        return db_obj

    def save_draft(
        self,
        db: Session,
        *,
        db_obj: PrecurationNew,
        evidence_data: dict[str, Any],
        user_id: UUID,
    ) -> PrecurationNew:
        """Save precuration as draft with auto-save timestamp."""
        db_obj.evidence_data = evidence_data
        db_obj.is_draft = True
        db_obj.auto_saved_at = _utc_now()
        db_obj.updated_by = user_id

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def submit_for_review(
        self,
        db: Session,
        *,
        db_obj: PrecurationNew,
        submit_data: PrecurationSubmit,
        user_id: UUID,
    ) -> PrecurationNew:
        """Submit precuration for review via workflow engine."""
        # Validate transition
        validation = workflow_engine.validate_transition(
            db,
            db_obj.workflow_stage,
            WorkflowStage.REVIEW,
            user_id,
            db_obj.id,
            "precuration",
        )

        if not validation.is_valid:
            raise ValueError(f"Invalid transition: {', '.join(validation.errors)}")

        # Execute transition
        workflow_engine.execute_transition(
            db,
            db_obj.id,
            "precuration",
            WorkflowStage.REVIEW,
            user_id,
            submit_data.notes,
        )

        # Update precuration status
        db_obj.status = CurationStatus.SUBMITTED
        db_obj.is_draft = False
        db_obj.updated_by = user_id
        db_obj.updated_at = _utc_now()

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def approve_and_create_curation(
        self,
        db: Session,
        *,
        db_obj: PrecurationNew,
        approver_id: UUID,
        create_curation: bool = True,
    ) -> PrecurationApprovalResult:
        """
        Approve a precuration and optionally create a linked curation.

        Implements ClinGen SOP v11 workflow:
        1. Precuration approved after review
        2. New curation auto-created with prefilled data
        3. Curation linked to precuration via precuration_id
        """
        # Validate can be approved
        if db_obj.status != CurationStatus.IN_REVIEW:
            raise ValueError("Precuration must be in review to approve")

        # Update precuration status
        db_obj.status = CurationStatus.APPROVED
        db_obj.workflow_stage = WorkflowStage.CURATION
        db_obj.updated_by = approver_id
        db_obj.updated_at = _utc_now()

        curation = None
        if create_curation:
            # Get workflow pair for data mapping
            workflow_pair = self._get_workflow_pair_for_precuration(db, db_obj)

            if workflow_pair:
                # Create curation with prefilled data
                curation = CurationNew(
                    gene_id=db_obj.gene_id,
                    scope_id=db_obj.scope_id,
                    workflow_pair_id=workflow_pair.id,
                    precuration_id=db_obj.id,  # Link to precuration
                    status=CurationStatus.DRAFT,
                    workflow_stage=WorkflowStage.CURATION,
                    is_draft=True,
                    evidence_data=self._prefill_curation_data(
                        db_obj.evidence_data, workflow_pair.data_mapping
                    ),
                    lock_version=0,
                    created_by=approver_id,
                    updated_by=approver_id,
                    created_at=_utc_now(),
                    updated_at=_utc_now(),
                )
                db.add(curation)

        db.add(db_obj)
        db.commit()
        if curation:
            db.refresh(curation)
        db.refresh(db_obj)

        logger.info(
            "Precuration approved",
            precuration_id=str(db_obj.id),
            curation_created=curation is not None,
            curation_id=str(curation.id) if curation else None,
            approver_id=str(approver_id),
        )

        return PrecurationApprovalResult(
            precuration_id=db_obj.id,
            approved=True,
            curation_created=curation is not None,
            curation_id=curation.id if curation else None,
            message="Precuration approved"
            + (f" and curation {curation.id} created" if curation else ""),
        )

    def reject(
        self,
        db: Session,
        *,
        db_obj: PrecurationNew,
        user_id: UUID,
        reason: str,
    ) -> PrecurationNew:
        """Reject precuration with reason."""
        db_obj.status = CurationStatus.REJECTED
        db_obj.workflow_stage = WorkflowStage.PRECURATION
        db_obj.updated_by = user_id
        db_obj.updated_at = _utc_now()
        # Store rejection reason in computed_fields
        db_obj.computed_fields = {
            **db_obj.computed_fields,
            "rejection_reason": reason,
            "rejected_at": _utc_now().isoformat(),
            "rejected_by": str(user_id),
        }

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        logger.info(
            "Precuration rejected",
            precuration_id=str(db_obj.id),
            user_id=str(user_id),
            reason=reason,
        )

        return db_obj

    def soft_delete(
        self,
        db: Session,
        *,
        db_obj: PrecurationNew,
        user_id: UUID,
    ) -> PrecurationNew:
        """Soft delete by setting status to archived."""
        db_obj.status = CurationStatus.ARCHIVED
        db_obj.updated_by = user_id
        db_obj.updated_at = _utc_now()

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        logger.info(
            "Precuration archived",
            precuration_id=str(db_obj.id),
            user_id=str(user_id),
        )

        return db_obj

    # ========================================
    # HELPER METHODS
    # ========================================

    def _get_workflow_pair_for_precuration(
        self, db: Session, precuration: PrecurationNew
    ) -> WorkflowPair | None:
        """Get workflow pair that uses this precuration's schema."""
        stmt = select(WorkflowPair).where(
            WorkflowPair.precuration_schema_id == precuration.precuration_schema_id,
            WorkflowPair.is_active == True,  # noqa: E712
        )
        return db.execute(stmt).scalars().first()

    def _prefill_curation_data(
        self,
        precuration_data: dict[str, Any],
        data_mapping: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply data mapping to prefill curation evidence from precuration."""
        curation_data: dict[str, Any] = {}
        mapping = data_mapping.get("precuration_to_curation", {})

        for source_field, target_path in mapping.items():
            if source_field in precuration_data:
                # Handle nested target paths (e.g., "entity_definition.mondo_id")
                parts = target_path.split(".")
                current = curation_data
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = precuration_data[source_field]

        return curation_data


# Singleton instance
precuration_crud = CRUDPrecuration(PrecurationNew)
```

**Key Operations:**
- `create_precuration(db, obj_in, user_id)` - Create new precuration
- `get_multi_filtered(db, skip, limit, scope_id, gene_id, status)` - List with filters
- `get_with_relations(db, precuration_id)` - Get with gene/scope relations
- `save_draft(db, db_obj, evidence_data, user_id)` - Auto-save support
- `submit_for_review(db, db_obj, submit_data, user_id)` - Submit workflow transition
- `approve_and_create_curation(db, db_obj, user_id)` - Approve and create curation
- `reject(db, db_obj, user_id, reason)` - Reject with reason
- `soft_delete(db, db_obj, user_id)` - Archive precuration

#### Task 1.3: Create Precuration API Endpoints

**File:** `backend/app/api/v1/endpoints/precurations.py`

> **CRITICAL:** All endpoints must include RLS context via `set_rls_context(db, current_user)`.
> Follows patterns from `curations.py`.

```python
"""
Precuration API endpoints.
Full CRUD with RLS integration and scope-based access control.
Follows patterns from curations.py.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.constants import (
    DEFAULT_SKIP,
    PRECURATIONS_DEFAULT_LIMIT,
    PRECURATIONS_MAX_LIMIT,
)
from app.core.database import get_db
from app.core.deps import get_current_active_user, set_rls_context
from app.core.logging import api_endpoint, get_logger
from app.crud.precuration import precuration_crud
from app.models import CurationStatus, UserNew
from app.schemas.precuration import (
    Precuration,
    PrecurationApprovalResult,
    PrecurationCreate,
    PrecurationListResponse,
    PrecurationSubmit,
    PrecurationUpdate,
)

router = APIRouter()
logger = get_logger(__name__)


# ========================================
# HELPER FUNCTIONS
# ========================================


def _check_scope_access(
    current_user: UserNew,
    scope_id: UUID,
    action: str = "access",
) -> None:
    """
    Check if user has access to the specified scope.
    Raises HTTPException if access denied.
    """
    if current_user.role == "admin":
        return  # Admin bypasses scope checks

    user_scope_ids: list[UUID] = current_user.assigned_scopes or []
    if scope_id not in user_scope_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not authorized to {action} precurations in this scope",
        )


# ========================================
# LIST & READ ENDPOINTS
# ========================================


@router.get("/", response_model=PrecurationListResponse)
@api_endpoint()
def list_precurations(
    db: Session = Depends(get_db),
    skip: int = Query(DEFAULT_SKIP, ge=0, description="Records to skip"),
    limit: int = Query(
        PRECURATIONS_DEFAULT_LIMIT,
        ge=1,
        le=PRECURATIONS_MAX_LIMIT,
        description="Max records",
    ),
    scope_id: UUID | None = Query(None, description="Filter by scope"),
    gene_id: UUID | None = Query(None, description="Filter by gene"),
    precuration_status: CurationStatus | None = Query(
        None, description="Filter by status"
    ),
    current_user: UserNew = Depends(get_current_active_user),
) -> PrecurationListResponse:
    """
    List precurations with optional filters.
    RLS automatically filters to user's accessible scopes.
    """
    # CRITICAL: Set RLS context for current user
    set_rls_context(db, current_user)

    # Determine scope filtering
    scope_ids = None
    if current_user.role != "admin" and not scope_id:
        scope_ids = current_user.assigned_scopes or []
        if not scope_ids:
            return PrecurationListResponse(
                precurations=[], total=0, skip=skip, limit=limit
            )

    # If specific scope requested, verify access
    if scope_id and current_user.role != "admin":
        user_scope_ids: list[UUID] = current_user.assigned_scopes or []
        if scope_id not in user_scope_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )

    summaries, total = precuration_crud.get_multi_filtered(
        db,
        skip=skip,
        limit=limit,
        scope_id=scope_id,
        scope_ids=scope_ids,
        gene_id=gene_id,
        status=precuration_status,
    )

    return PrecurationListResponse(
        precurations=summaries,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{precuration_id}", response_model=Precuration)
@api_endpoint()
def get_precuration(
    precuration_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Precuration:
    """Get a single precuration by ID."""
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    precuration = precuration_crud.get_with_relations(db, precuration_id)

    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )

    # Verify scope access
    _check_scope_access(current_user, precuration.scope_id, "view")

    return Precuration.model_validate(precuration)


# ========================================
# CREATE ENDPOINT
# ========================================


@router.post("/", response_model=Precuration, status_code=status.HTTP_201_CREATED)
@api_endpoint()
def create_precuration(
    precuration_in: PrecurationCreate,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Precuration:
    """
    Create a new precuration.
    Requires access to the target scope.
    """
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    # Verify scope access
    _check_scope_access(current_user, precuration_in.scope_id, "create")

    try:
        precuration = precuration_crud.create_precuration(
            db,
            obj_in=precuration_in,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return Precuration.model_validate(precuration)


# ========================================
# UPDATE ENDPOINT
# ========================================


@router.put("/{precuration_id}", response_model=Precuration)
@api_endpoint()
def update_precuration(
    precuration_id: UUID,
    precuration_in: PrecurationUpdate,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Precuration:
    """Update a precuration's evidence data."""
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    precuration = precuration_crud.get(db, precuration_id)

    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )

    # Verify scope access
    _check_scope_access(current_user, precuration.scope_id, "update")

    # Check precuration is editable
    if precuration.status not in [CurationStatus.DRAFT, CurationStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft or rejected precurations can be edited",
        )

    # Update evidence_data
    if precuration_in.evidence_data is not None:
        precuration.evidence_data = precuration_in.evidence_data
        precuration.updated_by = current_user.id

    db.add(precuration)
    db.commit()
    db.refresh(precuration)

    return Precuration.model_validate(precuration)


# ========================================
# DRAFT & SUBMIT ENDPOINTS
# ========================================


@router.patch("/{precuration_id}/draft", response_model=Precuration)
@api_endpoint()
def save_draft(
    precuration_id: UUID,
    draft_data: dict,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Precuration:
    """Save precuration as draft (auto-save support)."""
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    precuration = precuration_crud.get(db, precuration_id)

    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )

    # Only creator or admin can save drafts
    if current_user.role != "admin" and precuration.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can save drafts",
        )

    updated = precuration_crud.save_draft(
        db,
        db_obj=precuration,
        evidence_data=draft_data.get("evidence_data", {}),
        user_id=current_user.id,
    )

    return Precuration.model_validate(updated)


@router.post("/{precuration_id}/submit", response_model=Precuration)
@api_endpoint()
def submit_precuration(
    precuration_id: UUID,
    submit_in: PrecurationSubmit,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Precuration:
    """Submit precuration for peer review."""
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    precuration = precuration_crud.get(db, precuration_id)

    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )

    # Only creator or admin can submit
    if current_user.role != "admin" and precuration.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can submit for review",
        )

    try:
        submitted = precuration_crud.submit_for_review(
            db,
            db_obj=precuration,
            submit_data=submit_in,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return Precuration.model_validate(submitted)


# ========================================
# APPROVAL & REJECTION ENDPOINTS
# ========================================


@router.post("/{precuration_id}/approve", response_model=PrecurationApprovalResult)
@api_endpoint()
def approve_precuration(
    precuration_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> PrecurationApprovalResult:
    """
    Approve precuration and optionally create linked curation.
    Requires reviewer role in scope.
    """
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    precuration = precuration_crud.get(db, precuration_id)

    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )

    # Verify scope access with reviewer role
    _check_scope_access(current_user, precuration.scope_id, "approve")

    # 4-eyes principle: creator cannot approve their own precuration
    if precuration.created_by == current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot approve your own precuration (4-eyes principle)",
        )

    try:
        result = precuration_crud.approve_and_create_curation(
            db,
            db_obj=precuration,
            approver_id=current_user.id,
            create_curation=True,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return result


@router.post("/{precuration_id}/reject", response_model=Precuration)
@api_endpoint()
def reject_precuration(
    precuration_id: UUID,
    rejection_data: dict,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Precuration:
    """Reject precuration with reason."""
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    precuration = precuration_crud.get(db, precuration_id)

    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )

    # Verify scope access
    _check_scope_access(current_user, precuration.scope_id, "reject")

    reason = rejection_data.get("reason", "No reason provided")

    rejected = precuration_crud.reject(
        db,
        db_obj=precuration,
        user_id=current_user.id,
        reason=reason,
    )

    return Precuration.model_validate(rejected)


# ========================================
# DELETE ENDPOINT
# ========================================


@router.delete("/{precuration_id}", status_code=status.HTTP_204_NO_CONTENT)
@api_endpoint()
def delete_precuration(
    precuration_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> None:
    """Soft delete a precuration (archive)."""
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    precuration = precuration_crud.get(db, precuration_id)

    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )

    # Verify scope access
    _check_scope_access(current_user, precuration.scope_id, "delete")

    # Only allow deletion of drafts (or by admin)
    if precuration.status != CurationStatus.DRAFT and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only draft precurations can be deleted",
        )

    precuration_crud.soft_delete(db, db_obj=precuration, user_id=current_user.id)
```

**Endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| GET | `/precurations/` | List precurations with filters |
| POST | `/precurations/` | Create new precuration |
| GET | `/precurations/{id}` | Get precuration by ID |
| PUT | `/precurations/{id}` | Update precuration |
| PATCH | `/precurations/{id}/draft` | Save draft (auto-save) |
| POST | `/precurations/{id}/submit` | Submit for review |
| POST | `/precurations/{id}/approve` | Approve precuration |
| POST | `/precurations/{id}/reject` | Reject precuration |
| DELETE | `/precurations/{id}` | Soft delete precuration |

#### Task 1.4: Register API Router

**File:** `backend/app/api/v1/api.py`

```python
from app.api.v1.endpoints import precurations

api_router.include_router(
    precurations.router,
    prefix="/precurations",
    tags=["precurations"]
)
```

---

### Phase 2: Schema & Seed Data (Estimated: 4-6 hours)

#### Task 2.1: Create ClinGen Precuration Schema Definition

**File:** `database/sql/08_seed_precuration_schema.sql`

> **CRITICAL:** Use `ON CONFLICT DO UPDATE` for idempotent seeding (prevents duplicate key errors on re-run).

```sql
-- ClinGen SOP v11 Precuration Schema
-- Uses ON CONFLICT DO UPDATE for idempotent seeding
INSERT INTO curation_schemas (
    id,
    name,
    version,
    schema_type,
    description,
    field_definitions,
    validation_rules,
    workflow_states,
    ui_configuration,
    scoring_configuration,
    schema_hash,
    is_active
) VALUES (
    'e8f9a0b1-c2d3-4e5f-6a7b-8c9d0e1f2a3b'::uuid,
    'ClinGen Precuration',
    'SOP v11',
    'precuration',
    'ClinGen Gene-Disease Validity Precuration Schema per SOP version 11',
    '{
        "sections": [
            {
                "id": "disease_entity",
                "label": "Disease Entity Definition",
                "description": "Establish the gene-disease pair to be curated",
                "fields": [
                    {
                        "id": "mondo_id",
                        "label": "Mondo Disease ID",
                        "type": "external_reference",
                        "required": true,
                        "external_source": "mondo",
                        "placeholder": "MONDO:0000001",
                        "help_text": "Search for disease using Mondo Disease Ontology"
                    },
                    {
                        "id": "disease_name",
                        "label": "Disease Name",
                        "type": "text",
                        "required": true,
                        "help_text": "Use dyadic naming: Gene-associated phenotype (e.g., SCN1A-related seizure disorder)"
                    },
                    {
                        "id": "disease_phenotypes",
                        "label": "Key Phenotypes",
                        "type": "array",
                        "item_type": "external_reference",
                        "external_source": "hpo",
                        "required": false,
                        "help_text": "Add relevant HPO terms describing the phenotype"
                    }
                ]
            },
            {
                "id": "inheritance",
                "label": "Mode of Inheritance",
                "description": "Specify the inheritance pattern for this gene-disease pair",
                "fields": [
                    {
                        "id": "mode_of_inheritance",
                        "label": "Mode of Inheritance",
                        "type": "select",
                        "required": true,
                        "options": [
                            {"value": "AD", "label": "Autosomal Dominant (HP:0000006)"},
                            {"value": "AR", "label": "Autosomal Recessive (HP:0000007)"},
                            {"value": "XLD", "label": "X-linked Dominant (HP:0001417)"},
                            {"value": "XLR", "label": "X-linked Recessive (HP:0001419)"},
                            {"value": "SD", "label": "Semidominant (HP:0032113)"},
                            {"value": "MT", "label": "Mitochondrial (HP:0001427)"},
                            {"value": "Other", "label": "Other (specify)"}
                        ]
                    },
                    {
                        "id": "moi_notes",
                        "label": "MOI Notes",
                        "type": "textarea",
                        "required": false,
                        "show_when": {"mode_of_inheritance": "Other"},
                        "help_text": "Provide details for Other inheritance pattern"
                    }
                ]
            },
            {
                "id": "lumping_splitting",
                "label": "Lumping & Splitting",
                "description": "Document any lumping or splitting decisions per ClinGen guidelines",
                "fields": [
                    {
                        "id": "lumping_splitting_applicable",
                        "label": "Lumping/Splitting Applicable?",
                        "type": "boolean",
                        "required": true,
                        "default": false,
                        "help_text": "Does this curation involve combining or separating disease entities?"
                    },
                    {
                        "id": "lumping_splitting_decision",
                        "label": "Decision",
                        "type": "select",
                        "required": true,
                        "show_when": {"lumping_splitting_applicable": true},
                        "options": [
                            {"value": "LUMP", "label": "Lump - Combine disease entities"},
                            {"value": "SPLIT", "label": "Split - Separate disease entities"}
                        ]
                    },
                    {
                        "id": "lumping_splitting_rationale",
                        "label": "Rationale",
                        "type": "textarea",
                        "required": true,
                        "show_when": {"lumping_splitting_applicable": true},
                        "help_text": "Explain the rationale for lumping or splitting per ClinGen guidelines"
                    }
                ]
            },
            {
                "id": "metadata",
                "label": "Precuration Metadata",
                "fields": [
                    {
                        "id": "affiliation",
                        "label": "Expert Panel / Affiliation",
                        "type": "text",
                        "required": true,
                        "help_text": "Your ClinGen Expert Panel or curation group"
                    },
                    {
                        "id": "curator_notes",
                        "label": "Curator Notes",
                        "type": "textarea",
                        "required": false,
                        "help_text": "Any additional notes for the precuration record"
                    }
                ]
            }
        ]
    }'::jsonb,
    '{
        "required_fields": ["mondo_id", "disease_name", "mode_of_inheritance", "affiliation"],
        "conditional_required": {
            "lumping_splitting_decision": {"when": {"lumping_splitting_applicable": true}},
            "lumping_splitting_rationale": {"when": {"lumping_splitting_applicable": true}}
        },
        "custom_validators": [
            {
                "type": "mondo_id_format",
                "field": "mondo_id",
                "pattern": "^MONDO:\\d{6,9}$",
                "comment": "Mondo IDs have 6-9 digits (e.g., MONDO:0000001 to MONDO:012345678)"
            }
        ]
    }'::jsonb,
    '{
        "entry": {"allowed_transitions": ["precuration"]},
        "precuration": {"allowed_transitions": ["review"]},
        "review": {"allowed_transitions": ["precuration", "approved"]},
        "approved": {"allowed_transitions": ["curation"]}
    }'::jsonb,
    '{
        "form_layout": "wizard",
        "sections_collapsible": false,
        "show_progress_bar": true,
        "auto_save_interval_seconds": 30
    }'::jsonb,
    NULL,
    'precuration_schema_v11_hash_placeholder',
    true
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    version = EXCLUDED.version,
    description = EXCLUDED.description,
    field_definitions = EXCLUDED.field_definitions,
    validation_rules = EXCLUDED.validation_rules,
    workflow_states = EXCLUDED.workflow_states,
    ui_configuration = EXCLUDED.ui_configuration,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();
```

#### Task 2.2: Create ClinGen Workflow Pair

**File:** `database/sql/09_seed_workflow_pair.sql`

> **CRITICAL:** Use `ON CONFLICT DO UPDATE` for idempotent seeding.

```sql
-- ClinGen SOP v11 Workflow Pair (Precuration + Curation)
-- Uses ON CONFLICT DO UPDATE for idempotent seeding
INSERT INTO workflow_pairs (
    id,
    name,
    version,
    precuration_schema_id,
    curation_schema_id,
    data_mapping,
    workflow_config,
    description,
    is_active
) VALUES (
    'f1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c'::uuid,
    'ClinGen Gene-Disease Validity',
    'SOP v11',
    'e8f9a0b1-c2d3-4e5f-6a7b-8c9d0e1f2a3b'::uuid,  -- Precuration schema
    (SELECT id FROM curation_schemas WHERE name = 'ClinGen Gene-Disease Validity' LIMIT 1),
    '{
        "precuration_to_curation": {
            "mondo_id": "entity_definition.mondo_id",
            "disease_name": "entity_definition.disease_name",
            "mode_of_inheritance": "entity_definition.mode_of_inheritance",
            "disease_phenotypes": "entity_definition.phenotypes",
            "lumping_splitting_notes": "entity_definition.lumping_splitting"
        }
    }'::jsonb,
    '{
        "require_precuration": true,
        "require_review_for_precuration": true,
        "min_precuration_reviewers": 1,
        "auto_create_curation_on_approval": true
    }'::jsonb,
    'ClinGen Gene-Disease Validity workflow combining precuration and curation per SOP v11',
    true
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    version = EXCLUDED.version,
    data_mapping = EXCLUDED.data_mapping,
    workflow_config = EXCLUDED.workflow_config,
    description = EXCLUDED.description,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();
```

---

### Phase 3: Workflow Integration (Estimated: 6-8 hours)

#### Task 3.1: Update Workflow Engine

**File:** `backend/app/crud/workflow_engine.py`

**Changes:**
1. Add precuration-specific transitions
2. Add approval flow that creates curation
3. Add data prefill from precuration to curation
4. Add precuration validation rules

```python
# Key additions to workflow_engine.py
# NOTE: Uses synchronous pattern (no async) per project standards
from sqlalchemy import select

def approve_precuration_and_create_curation(
    self,
    db: Session,
    precuration_id: UUID,
    approver_id: UUID,
    create_curation: bool = True,
) -> dict[str, Any]:
    """
    Approve a precuration and optionally create a linked curation.

    This implements the ClinGen SOP v11 workflow where:
    1. Precuration is approved after review
    2. A new curation is automatically created with prefilled data
    3. The curation is linked to the precuration via precuration_id

    Note: Uses synchronous SQLAlchemy pattern (not async).
    """
    # Get precuration using select() for SQLAlchemy 2.0 style
    stmt = select(PrecurationNew).where(PrecurationNew.id == precuration_id)
    precuration = db.execute(stmt).scalars().first()
    if not precuration:
        raise ValueError("Precuration not found")

    # Validate can be approved
    if precuration.status != CurationStatus.IN_REVIEW:
        raise ValueError("Precuration must be in review to approve")

    # Update precuration status
    precuration.status = CurationStatus.APPROVED
    precuration.workflow_stage = WorkflowStage.CURATION  # Ready for curation
    precuration.updated_by = approver_id

    curation = None
    if create_curation:
        # Get workflow pair for data mapping
        workflow_pair = self._get_workflow_pair_for_precuration(db, precuration)

        # Create curation with prefilled data
        curation = CurationNew(
            gene_id=precuration.gene_id,
            scope_id=precuration.scope_id,
            workflow_pair_id=workflow_pair.id,
            precuration_id=precuration.id,  # CRITICAL: Link to precuration
            status=CurationStatus.DRAFT,
            workflow_stage=WorkflowStage.CURATION,
            is_draft=True,
            evidence_data=self._prefill_curation_data(
                precuration.evidence_data,
                workflow_pair.data_mapping
            ),
            created_by=approver_id,
        )
        db.add(curation)

    db.commit()

    return {
        "precuration_id": precuration.id,
        "approved": True,
        "curation_created": curation is not None,
        "curation_id": curation.id if curation else None,
        "message": "Precuration approved" + (
            f" and curation {curation.id} created" if curation else ""
        ),
    }
```

#### Task 3.2: Enforce Precuration Requirement

**Option A: Strict Enforcement (Recommended for ClinGen compliance)**

```python
# In curation_crud.py create_curation()

def create_curation(
    self,
    db: Session,
    obj_in: CurationCreate,
    user_id: UUID,
) -> CurationNew:
    # Get workflow pair
    workflow_pair = db.query(WorkflowPair).get(obj_in.workflow_pair_id)
    if not workflow_pair:
        raise ValueError("Workflow pair not found")

    # Check if precuration is required
    if workflow_pair.workflow_config.get("require_precuration", False):
        if not obj_in.precuration_id:
            raise ValueError(
                "This workflow requires a precuration. "
                "Please complete precuration before creating a curation."
            )

        # Validate precuration exists and is approved
        precuration = db.query(PrecurationNew).get(obj_in.precuration_id)
        if not precuration:
            raise ValueError("Precuration not found")
        if precuration.status != CurationStatus.APPROVED:
            raise ValueError("Precuration must be approved before creating curation")

    # ... rest of creation logic
```

**Option B: Warning Mode (For backward compatibility)**

```python
# Log warning but allow creation
if workflow_pair.workflow_config.get("require_precuration", False):
    if not obj_in.precuration_id:
        logger.warning(
            "Curation created without precuration",
            gene_id=str(obj_in.gene_id),
            scope_id=str(obj_in.scope_id),
        )
```

---

### Phase 4: Frontend Implementation (Estimated: 12-16 hours)

#### Task 4.0: Create Precuration API Client Module (REQUIRED FIRST)

**File:** `frontend/src/api/precurations.js`

> **Note:** This API module MUST be created before the store. Follows project pattern from `curations.js`.

```javascript
import apiClient from './client.js'

export const precurationsAPI = {
  /**
   * Get precurations with optional filters
   */
  async getPrecurations(params = {}) {
    const response = await apiClient.get('/precurations/', { params })
    return response.data
  },

  /**
   * Get single precuration by ID
   */
  async getPrecuration(id) {
    const response = await apiClient.get(`/precurations/${id}`)
    return response.data
  },

  /**
   * Create new precuration
   */
  async createPrecuration(data) {
    const response = await apiClient.post('/precurations/', data)
    return response.data
  },

  /**
   * Update precuration
   */
  async updatePrecuration(id, data) {
    const response = await apiClient.put(`/precurations/${id}`, data)
    return response.data
  },

  /**
   * Save precuration as draft (auto-save)
   */
  async saveDraft(id, data) {
    const response = await apiClient.patch(`/precurations/${id}/draft`, data)
    return response.data
  },

  /**
   * Submit precuration for review
   */
  async submitPrecuration(id, data = {}) {
    const response = await apiClient.post(`/precurations/${id}/submit`, data)
    return response.data
  },

  /**
   * Approve precuration (creates curation if configured)
   */
  async approvePrecuration(id) {
    const response = await apiClient.post(`/precurations/${id}/approve`)
    return response.data
  },

  /**
   * Reject precuration
   */
  async rejectPrecuration(id, data) {
    const response = await apiClient.post(`/precurations/${id}/reject`, data)
    return response.data
  },

  /**
   * Delete (archive) precuration
   */
  async deletePrecuration(id) {
    await apiClient.delete(`/precurations/${id}`)
  }
}
```

#### Task 4.1: Create Precuration Pinia Store

**File:** `frontend/src/stores/precurations.js`

> **IMPORTANT:** Uses Options API pattern to match existing stores (curations.js, genes.js, etc.)
> Do NOT use Setup/Composition API syntax for stores in this project.

```javascript
/**
 * Precurations Pinia Store
 *
 * Manages precuration state following the curations.js pattern.
 * Handles CRUD operations, draft auto-save, and workflow transitions.
 */
import { defineStore } from 'pinia'
import { precurationsAPI } from '@/api/precurations'
import { logService } from '@/services/logService'

export const usePrecurationsStore = defineStore('precurations', {
  state: () => ({
    precurations: [],
    currentPrecuration: null,
    loading: false,
    error: null,
    pagination: {
      page: 1,
      per_page: 50,
      total: 0,
      pages: 0
    },
    filters: {
      scope_id: null,
      gene_id: null,
      status: null
    }
  }),

  getters: {
    getPrecurationById: state => id => {
      return state.precurations.find(precuration => precuration.id === id)
    },

    getPrecurationsByScope: state => scopeId => {
      return state.precurations.filter(precuration => precuration.scope_id === scopeId)
    },

    getPrecurationsByGene: state => geneId => {
      return state.precurations.filter(precuration => precuration.gene_id === geneId)
    },

    draftPrecurations: state => {
      return state.precurations.filter(precuration => precuration.status === 'draft')
    },

    submittedPrecurations: state => {
      return state.precurations.filter(precuration => precuration.status === 'submitted')
    },

    approvedPrecurations: state => {
      return state.precurations.filter(precuration => precuration.status === 'approved')
    },

    hasError: state => state.error !== null
  },

  actions: {
    /**
     * Fetch precurations with optional filters
     */
    async fetchPrecurations(params = {}) {
      this.loading = true
      this.error = null
      try {
        const response = await precurationsAPI.getPrecurations({
          ...this.filters,
          ...params,
          skip: (this.pagination.page - 1) * this.pagination.per_page,
          limit: this.pagination.per_page
        })

        this.precurations = response.precurations || []
        this.pagination.total = response.total || 0
        this.pagination.pages = Math.ceil(this.pagination.total / this.pagination.per_page)

        return response
      } catch (error) {
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Fetch single precuration by ID
     */
    async fetchPrecurationById(id) {
      this.loading = true
      this.error = null
      try {
        const precuration = await precurationsAPI.getPrecuration(id)
        this.currentPrecuration = precuration

        // Update in list if exists
        const index = this.precurations.findIndex(p => p.id === id)
        if (index !== -1) {
          this.precurations[index] = precuration
        }

        return precuration
      } catch (error) {
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Create new precuration
     */
    async createPrecuration(data) {
      this.loading = true
      this.error = null
      try {
        const newPrecuration = await precurationsAPI.createPrecuration(data)
        this.precurations.unshift(newPrecuration)
        this.pagination.total += 1
        return newPrecuration
      } catch (error) {
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Update precuration
     */
    async updatePrecuration(id, data) {
      this.loading = true
      this.error = null
      try {
        const updated = await precurationsAPI.updatePrecuration(id, data)

        // Update in list
        const index = this.precurations.findIndex(p => p.id === id)
        if (index !== -1) {
          this.precurations[index] = updated
        }

        // Update current if same
        if (this.currentPrecuration?.id === id) {
          this.currentPrecuration = updated
        }

        return updated
      } catch (error) {
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Save precuration as draft (auto-save)
     * Does NOT set loading state for background operation
     */
    async saveDraft(id, evidenceData) {
      this.error = null
      try {
        const updated = await precurationsAPI.saveDraft(id, {
          evidence_data: evidenceData
        })

        // Update in list
        const index = this.precurations.findIndex(p => p.id === id)
        if (index !== -1) {
          this.precurations[index] = updated
        }

        // Update current if same
        if (this.currentPrecuration?.id === id) {
          this.currentPrecuration = updated
        }

        return updated
      } catch (error) {
        // Use logService instead of console.error (per CLAUDE.md)
        logService.error('Auto-save failed', {
          precuration_id: id,
          error: error.message
        })
        this.error = { message: error.message, isAutoSave: true }
        return null
      }
    },

    /**
     * Submit precuration for review
     */
    async submitForReview(id, notes = null) {
      this.loading = true
      this.error = null
      try {
        const submitted = await precurationsAPI.submitPrecuration(id, { notes })

        // Update in list
        const index = this.precurations.findIndex(p => p.id === id)
        if (index !== -1) {
          this.precurations[index] = submitted
        }

        // Update current if same
        if (this.currentPrecuration?.id === id) {
          this.currentPrecuration = submitted
        }

        return submitted
      } catch (error) {
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Approve precuration (may auto-create curation)
     */
    async approvePrecuration(id) {
      this.loading = true
      this.error = null
      try {
        const result = await precurationsAPI.approvePrecuration(id)

        // Update in list
        const index = this.precurations.findIndex(p => p.id === id)
        if (index !== -1) {
          this.precurations[index] = {
            ...this.precurations[index],
            status: 'approved'
          }
        }

        return result // Contains curation_id if auto-created
      } catch (error) {
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Reject precuration
     */
    async rejectPrecuration(id, reason) {
      this.loading = true
      this.error = null
      try {
        const rejected = await precurationsAPI.rejectPrecuration(id, { reason })

        // Update in list
        const index = this.precurations.findIndex(p => p.id === id)
        if (index !== -1) {
          this.precurations[index] = rejected
        }

        return rejected
      } catch (error) {
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Delete (archive) precuration
     */
    async deletePrecuration(id) {
      this.loading = true
      this.error = null
      try {
        await precurationsAPI.deletePrecuration(id)

        // Remove from list
        this.precurations = this.precurations.filter(p => p.id !== id)
        this.pagination.total = Math.max(0, this.pagination.total - 1)

        // Clear current if same
        if (this.currentPrecuration?.id === id) {
          this.currentPrecuration = null
        }

        return true
      } catch (error) {
        this.error = { message: error.message }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Update filters and reset to first page
     */
    updateFilters(newFilters) {
      this.filters = { ...this.filters, ...newFilters }
      this.pagination.page = 1
    },

    /**
     * Set current page
     */
    setPage(page) {
      this.pagination.page = page
    },

    /**
     * Set current precuration
     */
    setCurrentPrecuration(precuration) {
      this.currentPrecuration = precuration
    },

    /**
     * Clear current precuration
     */
    clearCurrentPrecuration() {
      this.currentPrecuration = null
    },

    /**
     * Clear error
     */
    clearError() {
      this.error = null
    },

    /**
     * Reset store to initial state
     */
    $reset() {
      this.precurations = []
      this.currentPrecuration = null
      this.loading = false
      this.error = null
      this.pagination = {
        page: 1,
        per_page: 50,
        total: 0,
        pages: 0
      }
      this.filters = {
        scope_id: null,
        gene_id: null,
        status: null
      }
    }
  }
})
```

#### Task 4.2: Create Precuration Form Component

**File:** `frontend/src/components/precuration/PrecurationForm.vue`

Key features:
- Wizard-style multi-step form
- Mondo disease search integration
- HPO term search for phenotypes
- Mode of inheritance selector
- Lumping/splitting decision section
- Auto-save every 30 seconds
- Real-time validation

#### Task 4.3: Create Precuration Views

**Files:**
- `frontend/src/views/PrecurationList.vue` - List with filters
- `frontend/src/views/PrecurationDetail.vue` - View/edit precuration
- `frontend/src/views/PrecurationCreate.vue` - Create new precuration

#### Task 4.4: Update Router

**File:** `frontend/src/router/index.js`

```javascript
// Add precuration routes
{
  path: '/scopes/:scopeId/precurations',
  name: 'PrecurationList',
  component: () => import('@/views/PrecurationList.vue'),
  meta: { requiresAuth: true },
},
{
  path: '/scopes/:scopeId/precurations/create',
  name: 'PrecurationCreate',
  component: () => import('@/views/PrecurationCreate.vue'),
  meta: { requiresAuth: true },
},
{
  path: '/scopes/:scopeId/precurations/:id',
  name: 'PrecurationDetail',
  component: () => import('@/views/PrecurationDetail.vue'),
  meta: { requiresAuth: true },
},
```

#### Task 4.5: Update Scope Dashboard

**File:** `frontend/src/views/ScopeDashboard.vue`

Add "Precurations" tab between Overview and Genes.

---

### Phase 5: Testing & Documentation (Estimated: 6-8 hours)

#### Task 5.1: Backend Tests

**File:** `backend/tests/test_precurations.py`

Test cases:
- Create precuration with valid data
- Create precuration with missing required fields (should fail)
- Update precuration evidence data
- Submit precuration for review
- Approve precuration creates curation
- Reject precuration workflow
- Precuration-curation data prefill

#### Task 5.2: Frontend Tests

**File:** `frontend/src/__tests__/PrecurationForm.test.js`

Test cases:
- Form renders all required fields
- Validation prevents submission without required fields
- Auto-save triggers correctly
- Mondo ID search integration
- MOI selector options

#### Task 5.3: API Documentation

Update OpenAPI documentation with precuration endpoints.

---

## Migration Strategy

### Option A: Strict Migration (Recommended)

1. Deploy backend changes (API, schemas, database)
2. Run migration to create precuration schema seed data
3. Deploy frontend changes
4. Enable `require_precuration: true` in workflow config
5. All new curations require precuration

### Option B: Gradual Migration

1. Deploy with `require_precuration: false`
2. Add precuration for new curations optionally
3. Monitor adoption
4. Enable requirement after 2-4 weeks

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Mondo API rate limits | Medium | Low | Cache results in ValidationCache table |
| User confusion with two-stage workflow | Medium | Medium | Clear UI messaging, help text |
| Data loss during precuration | Low | High | Auto-save every 30s, draft recovery |
| Breaking existing workflows | Low | High | Backward-compatible API, gradual rollout |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Precuration completion rate | >80% | Precurations approved / created |
| Time to precuration approval | <2 days | Avg time from submit to approve |
| Data prefill accuracy | >95% | Fields correctly transferred |
| User satisfaction | >4/5 | Survey after implementation |

---

## Timeline Summary

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Backend Foundation | 8-12 hours | None |
| Phase 2: Schema & Seed Data | 4-6 hours | Phase 1 |
| Phase 3: Workflow Integration | 6-8 hours | Phase 1, 2 |
| Phase 4: Frontend Implementation | 12-16 hours | Phase 1, 2, 3 |
| Phase 5: Testing & Documentation | 6-8 hours | All phases |
| **Total** | **36-50 hours** | |

---

## Appendix A: ClinGen SOP v11 Reference Excerpts

### Section 4.1 - Precuration

> The first step in the curation process is precuration, which establishes the disease entity to be curated. This includes identifying the HGNC gene symbol, the Mondo Disease Ontology identifier, and the mode of inheritance.

### Section 4.2 - Precuration ID Requirement

> As of June 1, 2023, a precuration identifier (precuration ID) issued from the GeneTracker is required to start all new GCI records. This ensures proper tracking and prevents duplicate curations.

### Section 5.3 - Lumping and Splitting

> The Lumping and Splitting Working Group has developed guidelines for when to combine (lump) or separate (split) disease entities. Curators should document their lumping/splitting decisions in the precuration record.

---

## Appendix B: Related Enhancement Plans

- **Enhancement #008**: Draft Auto-Save - Integrates with precuration form
- **Enhancement #009**: Dynamic Form Generation - Precuration schema uses same system
- **Enhancement #010**: 4-Eyes Review Workflow - Applies to precuration approval
- **Enhancement #011**: UI Gap Analysis - Identified precuration as missing

---

---

## Appendix C: Implementation Checklist

### Critical Pre-Implementation Items

- [ ] Add pagination constants to `backend/app/core/constants.py`:
  ```python
  # Precuration pagination limits
  PRECURATIONS_DEFAULT_LIMIT = 50
  PRECURATIONS_MAX_LIMIT = 200
  ```

- [ ] Add CSS custom properties to global styles (if not already present):
  ```css
  :root {
    --app-header-height: 64px;
    --app-footer-height: 77px;
  }
  ```

- [ ] Verify `set_rls_context` is available in `app/core/deps.py`

- [ ] Verify `workflow_engine` is properly imported from `app/crud/workflow_engine.py`

### Code Review Requirements

Before merging each phase:

1. Run `make lint` and `make lint-frontend` - must pass with zero errors
2. Run `make test` - all tests must pass
3. Run `make format-all` - code must be properly formatted
4. Verify no `console.log` / `console.error` in frontend code
5. Verify no hardcoded magic numbers (use constants)
6. Verify all endpoints have RLS context via `set_rls_context(db, current_user)`

---

**Document Version:** 1.1
**Last Updated:** 2026-01-13
**Revision Notes:** Added critical implementation fixes from code review (015-IMPLEMENTATION-PLAN-REVIEW.md)
**Next Review:** After Phase 1 completion
