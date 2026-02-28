# Curations Endpoint Implementation Plan v2.1

**Date**: 2026-01-12
**Branch**: `feature/scope-centric-refactor`
**Priority**: CRITICAL BLOCKER
**Principles**: DRY, KISS, SOLID, Modularization
**Status**: FINAL (incorporates v2.0 code review feedback)

---

## Related Documents

This plan is part of the broader Gene Curator implementation. See these related documents:

| Document | Purpose | Status |
|----------|---------|--------|
| [Enhancements README](./enhancements/README.md) | Enhancement tracking overview | Active |
| [008 - Draft Autosave](./enhancements/008-draft-autosave-frontend.md) | Auto-save for curation forms | Pending (depends on this plan) |
| [009 - Dynamic Form Generation](./enhancements/009-dynamic-form-generation.md) | Schema-driven UI generation | Backend Complete |
| [010 - Review Workflow](./enhancements/010-review-workflow-4eyes.md) | 4-eyes principle implementation | Implemented |
| [Refactoring Plans](./refactoring/) | Scope-centric architecture | Active |
| [Implementation Prompt](./CURATIONS_IMPLEMENTATION_PROMPT.md) | Agentic LLM implementation guide | Ready |

### Dependencies
- **This plan blocks**: 008 (Draft Autosave), 009 (Dynamic Forms frontend)
- **This plan requires**: Existing backend models (`CurationNew`, `WorkflowStage`, `CurationStatus`)
- **Related GitHub Issues**: Frontend `CurationList.vue` returns 404 without this endpoint

---

## Executive Summary

This plan implements the missing `/curations` API endpoint and completes frontend integration. **Version 2.1** incorporates all code review feedback from both review rounds.

### Changes from v2.0

| Issue | v2.0 | v2.1 (Fixed) |
|-------|------|--------------|
| `datetime.utcnow()` | Deprecated usage | `datetime.now(timezone.utc)` |
| `require_scope_role` | Imported but unused | Properly used in nested routes |
| Scope check pattern | Manual checks | Consistent with codebase patterns |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                     │
│  ┌─────────────────┐     ┌─────────────────┐     ┌───────────────┐ │
│  │ CurationList.vue│────▶│ CurationForm.vue│────▶│  curations.js │ │
│  └────────┬────────┘     └────────┬────────┘     └───────┬───────┘ │
│           └───────────────┬───────┴───────────────────────┘         │
│                           ▼                                          │
│               ┌───────────────────────┐                             │
│               │   curations store     │  (Pinia - matches genes.js) │
│               └───────────┬───────────┘                             │
└───────────────────────────┼─────────────────────────────────────────┘
                            │ HTTP
                            ▼
┌───────────────────────────────────────────────────────────────────────┐
│                          BACKEND                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  curations.py - Uses set_rls_context + scope permission checks  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                │                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  crud/curation.py - Extends CRUDBase, FK validation, DI scoring │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                │                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  schemas/curation.py - Uses InDBBase pattern                    │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Backend Implementation

### Step 1.0: Add Constants (5 minutes)

**File**: `backend/app/core/constants.py` (MODIFY - add to pagination section)

```python
# ========================================
# PAGINATION DEFAULTS (add after ASSIGNMENTS section)
# ========================================

CURATIONS_DEFAULT_LIMIT = 50
"""Default limit for curation list endpoints."""

CURATIONS_MAX_LIMIT = 500
"""Maximum limit for curation list endpoints."""
```

---

### Step 1.1: Pydantic Schemas

**File**: `backend/app/schemas/curation.py` (NEW)

```python
"""
Pydantic V2 schemas for curation API operations.
Follows existing patterns from gene_assignment.py (InDBBase pattern).
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import CurationStatus, WorkflowStage


# ========================================
# BASE SCHEMAS (DRY - shared fields)
# ========================================


class CurationBase(BaseModel):
    """Base schema with common curation fields."""

    gene_id: UUID = Field(..., description="Gene UUID")
    scope_id: UUID = Field(..., description="Scope UUID")
    workflow_pair_id: UUID = Field(..., description="Workflow pair UUID")
    precuration_id: UUID | None = Field(None, description="Parent precuration UUID")
    evidence_data: dict[str, Any] = Field(
        default_factory=dict, description="Schema-agnostic evidence"
    )


# ========================================
# REQUEST SCHEMAS
# ========================================


class CurationCreate(CurationBase):
    """Schema for creating a new curation."""

    pass


class CurationUpdate(BaseModel):
    """Schema for updating an existing curation."""

    evidence_data: dict[str, Any] | None = Field(
        None, description="Updated evidence data"
    )
    lock_version: int = Field(
        ..., description="Optimistic locking version (required)"
    )

    model_config = ConfigDict(extra="forbid")


class CurationDraftSave(BaseModel):
    """Schema for saving a curation as draft."""

    evidence_data: dict[str, Any] = Field(..., description="Draft evidence data")
    lock_version: int | None = Field(None, description="Optional lock version")


class CurationSubmit(BaseModel):
    """Schema for submitting a curation for review."""

    notes: str | None = Field(None, max_length=1000, description="Submission notes")
    lock_version: int = Field(..., description="Lock version for optimistic locking")


# ========================================
# DATABASE SCHEMAS (InDBBase pattern - matches gene_assignment.py)
# ========================================


class CurationInDBBase(CurationBase):
    """Base schema with database fields."""

    id: UUID
    status: CurationStatus
    workflow_stage: WorkflowStage
    is_draft: bool

    # Computed results
    computed_scores: dict[str, Any]
    computed_verdict: str | None
    computed_summary: str | None

    # Optimistic locking
    lock_version: int

    # Timestamps
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    approved_at: datetime | None
    auto_saved_at: datetime | None

    # User references
    created_by: UUID | None
    updated_by: UUID | None
    submitted_by: UUID | None
    approved_by: UUID | None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


# ========================================
# RESPONSE SCHEMAS
# ========================================


class Curation(CurationInDBBase):
    """Full curation response schema."""

    pass


class CurationSummary(BaseModel):
    """Lightweight curation summary for list views (no evidence_data)."""

    id: UUID
    gene_id: UUID
    gene_symbol: str
    scope_id: UUID
    scope_name: str
    status: CurationStatus
    workflow_stage: WorkflowStage
    computed_verdict: str | None
    is_draft: bool
    created_at: datetime
    updated_at: datetime
    curator_name: str | None

    model_config = ConfigDict(use_enum_values=True)


class CurationListResponse(BaseModel):
    """Paginated list response."""

    curations: list[CurationSummary]
    total: int
    skip: int
    limit: int


class CurationScoreResponse(BaseModel):
    """Score calculation response."""

    curation_id: UUID
    total_score: float
    classification: str
    genetic_score: float
    experimental_score: float
    breakdown: dict[str, Any]
    calculated_at: datetime


class CurationConflictResponse(BaseModel):
    """409 Conflict response for optimistic locking."""

    error: str = "Concurrent modification detected"
    current_lock_version: int
    current_state: dict[str, Any]
    your_lock_version: int
```

**Update**: `backend/app/schemas/__init__.py`

```python
# Add to existing imports
from app.schemas.curation import (
    Curation,
    CurationCreate,
    CurationUpdate,
    CurationDraftSave,
    CurationSubmit,
    CurationInDBBase,
    CurationSummary,
    CurationListResponse,
    CurationScoreResponse,
    CurationConflictResponse,
)

__all__ = [
    # ... existing exports ...
    "Curation",
    "CurationCreate",
    "CurationUpdate",
    "CurationDraftSave",
    "CurationSubmit",
    "CurationInDBBase",
    "CurationSummary",
    "CurationListResponse",
    "CurationScoreResponse",
    "CurationConflictResponse",
]
```

---

### Step 1.2: CRUD Layer

**File**: `backend/app/crud/curation.py` (NEW)

```python
"""
CRUD operations for curations.
Extends CRUDBase with curation-specific operations.
Follows patterns from gene_assignment.py.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.logging import get_logger
from app.crud.base import CRUDBase
from app.crud.workflow_engine import workflow_engine
from app.models import (
    CurationNew,
    CurationStatus,
    Gene,
    Scope,
    UserNew,
    WorkflowPair,
    WorkflowStage,
)
from app.schemas.curation import (
    CurationCreate,
    CurationDraftSave,
    CurationScoreResponse,
    CurationSubmit,
    CurationSummary,
    CurationUpdate,
)

logger = get_logger(__name__)


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class CRUDCuration(CRUDBase[CurationNew, CurationCreate, CurationUpdate]):
    """
    CRUD operations for curations with workflow integration.

    Extends base CRUD with:
    - Scope-based filtering
    - Optimistic locking
    - Workflow state management
    - Score calculation (via dependency injection)
    """

    # ========================================
    # READ OPERATIONS
    # ========================================

    def get_with_relations(self, db: Session, id: UUID) -> CurationNew | None:
        """Get curation with eager-loaded relationships."""
        stmt = (
            select(CurationNew)
            .options(
                joinedload(CurationNew.gene),
                joinedload(CurationNew.scope),
                joinedload(CurationNew.creator),
            )
            .where(CurationNew.id == id)
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
    ) -> list[CurationNew]:
        """Get curations filtered by scope."""
        stmt = select(CurationNew).where(CurationNew.scope_id == scope_id)

        if status:
            stmt = stmt.where(CurationNew.status == status)
        if not include_drafts:
            stmt = stmt.where(CurationNew.is_draft == False)  # noqa: E712

        stmt = stmt.offset(skip).limit(limit).order_by(CurationNew.updated_at.desc())
        return list(db.execute(stmt).scalars().all())

    def get_by_gene_and_scope(
        self,
        db: Session,
        gene_id: UUID,
        scope_id: UUID,
    ) -> list[CurationNew]:
        """Get all curations for a gene within a scope."""
        stmt = (
            select(CurationNew)
            .where(
                and_(
                    CurationNew.gene_id == gene_id,
                    CurationNew.scope_id == scope_id,
                )
            )
            .order_by(CurationNew.created_at.desc())
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
        curator_id: UUID | None = None,
    ) -> tuple[list[CurationSummary], int]:
        """
        Get curation summaries with joined data for list views.
        Returns lightweight summaries (no evidence_data) for performance.
        """
        # Base query with joins
        stmt = (
            select(
                CurationNew,
                Gene.symbol.label("gene_symbol"),
                Scope.name.label("scope_name"),
                UserNew.name.label("curator_name"),
            )
            .join(Gene, CurationNew.gene_id == Gene.id)
            .join(Scope, CurationNew.scope_id == Scope.id)
            .outerjoin(UserNew, CurationNew.created_by == UserNew.id)
        )

        # Apply filters
        if scope_id:
            stmt = stmt.where(CurationNew.scope_id == scope_id)
        if scope_ids:
            stmt = stmt.where(CurationNew.scope_id.in_(scope_ids))
        if gene_id:
            stmt = stmt.where(CurationNew.gene_id == gene_id)
        if status:
            stmt = stmt.where(CurationNew.status == status)
        if curator_id:
            stmt = stmt.where(CurationNew.created_by == curator_id)

        # Get total count (before pagination)
        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(CurationNew.id).subquery()
        )
        total = db.execute(count_stmt).scalar() or 0

        # Apply pagination and ordering
        stmt = stmt.offset(skip).limit(limit).order_by(CurationNew.updated_at.desc())

        results = db.execute(stmt).all()

        # Map to summary schema
        summaries = [
            CurationSummary(
                id=row.CurationNew.id,
                gene_id=row.CurationNew.gene_id,
                gene_symbol=row.gene_symbol,
                scope_id=row.CurationNew.scope_id,
                scope_name=row.scope_name,
                status=row.CurationNew.status,
                workflow_stage=row.CurationNew.workflow_stage,
                computed_verdict=row.CurationNew.computed_verdict,
                is_draft=row.CurationNew.is_draft,
                created_at=row.CurationNew.created_at,
                updated_at=row.CurationNew.updated_at,
                curator_name=row.curator_name,
            )
            for row in results
        ]

        return summaries, total

    # ========================================
    # WRITE OPERATIONS (with FK validation)
    # ========================================

    def create_curation(
        self,
        db: Session,
        *,
        obj_in: CurationCreate,
        user_id: UUID,
    ) -> CurationNew:
        """Create a new curation with proper initialization and FK validation."""
        # Validate foreign keys exist (prevents orphaned records)
        gene = db.get(Gene, obj_in.gene_id)
        if not gene:
            raise ValueError(f"Gene with id {obj_in.gene_id} not found")

        scope = db.get(Scope, obj_in.scope_id)
        if not scope:
            raise ValueError(f"Scope with id {obj_in.scope_id} not found")

        workflow_pair = db.get(WorkflowPair, obj_in.workflow_pair_id)
        if not workflow_pair:
            raise ValueError(
                f"WorkflowPair with id {obj_in.workflow_pair_id} not found"
            )

        # Create curation
        now = _utc_now()
        db_obj = CurationNew(
            gene_id=obj_in.gene_id,
            scope_id=obj_in.scope_id,
            workflow_pair_id=obj_in.workflow_pair_id,
            precuration_id=obj_in.precuration_id,
            evidence_data=obj_in.evidence_data,
            status=CurationStatus.DRAFT,
            workflow_stage=WorkflowStage.CURATION,
            is_draft=True,
            lock_version=0,
            created_by=user_id,
            updated_by=user_id,
            created_at=now,
            updated_at=now,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        logger.info(
            "Curation created",
            curation_id=str(db_obj.id),
            gene_id=str(obj_in.gene_id),
            scope_id=str(obj_in.scope_id),
            user_id=str(user_id),
        )

        return db_obj

    def update_with_lock(
        self,
        db: Session,
        *,
        db_obj: CurationNew,
        obj_in: CurationUpdate,
        user_id: UUID,
    ) -> CurationNew | None:
        """
        Update curation with optimistic locking.
        Returns None if lock_version doesn't match (conflict).
        """
        # Check lock version
        if db_obj.lock_version != obj_in.lock_version:
            logger.warning(
                "Optimistic lock conflict",
                curation_id=str(db_obj.id),
                current_version=db_obj.lock_version,
                requested_version=obj_in.lock_version,
            )
            return None

        # Update fields
        if obj_in.evidence_data is not None:
            db_obj.evidence_data = obj_in.evidence_data

        db_obj.lock_version += 1
        db_obj.updated_by = user_id
        db_obj.updated_at = _utc_now()

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def save_draft(
        self,
        db: Session,
        *,
        db_obj: CurationNew,
        draft_data: CurationDraftSave,
        user_id: UUID,
    ) -> CurationNew:
        """Save curation as draft with auto-save timestamp."""
        db_obj.evidence_data = draft_data.evidence_data
        db_obj.is_draft = True
        db_obj.auto_saved_at = _utc_now()
        db_obj.updated_by = user_id

        # Only increment lock_version if provided and matches
        if draft_data.lock_version is not None:
            if db_obj.lock_version == draft_data.lock_version:
                db_obj.lock_version += 1

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def submit_for_review(
        self,
        db: Session,
        *,
        db_obj: CurationNew,
        submit_data: CurationSubmit,
        user_id: UUID,
    ) -> CurationNew | None:
        """Submit curation for review via workflow engine."""
        # Check lock version
        if db_obj.lock_version != submit_data.lock_version:
            return None

        # Validate transition
        validation = workflow_engine.validate_transition(
            db,
            db_obj.workflow_stage,
            WorkflowStage.REVIEW,
            user_id,
            db_obj.id,
            "curation",
        )

        if not validation.is_valid:
            raise ValueError(f"Invalid transition: {', '.join(validation.errors)}")

        # Execute transition
        workflow_engine.execute_transition(
            db,
            db_obj.id,
            "curation",
            WorkflowStage.REVIEW,
            user_id,
            submit_data.notes,
        )

        # Update curation status
        now = _utc_now()
        db_obj.status = CurationStatus.SUBMITTED
        db_obj.is_draft = False
        db_obj.submitted_at = now
        db_obj.submitted_by = user_id
        db_obj.lock_version += 1

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    # ========================================
    # SCORE CALCULATION (Dependency Injection)
    # ========================================

    def calculate_score(
        self,
        db: Session,
        db_obj: CurationNew,
        scoring_engine: Any = None,
    ) -> CurationScoreResponse:
        """
        Calculate score for curation.
        Accepts scoring engine via DI for testability.
        """
        # Lazy import to avoid circular dependency
        if scoring_engine is None:
            from app.scoring.clingen import ClinGenScoringEngine

            scoring_engine = ClinGenScoringEngine()

        # Calculate score
        result = scoring_engine.calculate_score(db_obj.evidence_data)

        # Update computed fields
        db_obj.computed_scores = result.get("breakdown", {})
        db_obj.computed_verdict = result.get("classification")
        db_obj.computed_summary = result.get("summary")

        db.add(db_obj)
        db.commit()

        return CurationScoreResponse(
            curation_id=db_obj.id,
            total_score=result.get("total_score", 0.0),
            classification=result.get("classification", "No Known"),
            genetic_score=result.get("genetic_total", 0.0),
            experimental_score=result.get("experimental_total", 0.0),
            breakdown=result.get("breakdown", {}),
            calculated_at=_utc_now(),
        )

    # ========================================
    # SOFT DELETE
    # ========================================

    def soft_delete(
        self,
        db: Session,
        *,
        db_obj: CurationNew,
        user_id: UUID,
    ) -> CurationNew:
        """Soft delete by setting status to archived."""
        db_obj.status = CurationStatus.ARCHIVED
        db_obj.updated_by = user_id
        db_obj.updated_at = _utc_now()

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        logger.info(
            "Curation archived",
            curation_id=str(db_obj.id),
            user_id=str(user_id),
        )

        return db_obj


# Singleton instance
curation_crud = CRUDCuration(CurationNew)
```

**Update**: `backend/app/crud/__init__.py`

```python
# Add to existing imports
from app.crud.curation import curation_crud

__all__ = [
    # ... existing exports ...
    "curation_crud",
]
```

---

### Step 1.3: API Endpoints

**File**: `backend/app/api/v1/endpoints/curations.py` (NEW)

```python
"""
Curation API endpoints.
Full CRUD with RLS integration and scope-based access control.
Follows patterns from gene_assignments.py, workflow.py, and genes.py.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.constants import (
    CURATIONS_DEFAULT_LIMIT,
    CURATIONS_MAX_LIMIT,
    DEFAULT_SKIP,
)
from app.core.database import get_db
from app.core.deps import get_current_active_user, set_rls_context
from app.core.logging import api_endpoint, get_logger
from app.crud.curation import curation_crud
from app.models import CurationNew, CurationStatus, UserNew
from app.schemas.curation import (
    Curation,
    CurationConflictResponse,
    CurationCreate,
    CurationDraftSave,
    CurationListResponse,
    CurationScoreResponse,
    CurationSubmit,
    CurationUpdate,
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
    Matches pattern from gene_assignments.py and workflow.py.
    """
    if current_user.role == "admin":
        return  # Admin bypasses scope checks

    user_scope_ids: list[UUID] = current_user.assigned_scopes or []
    if scope_id not in user_scope_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not authorized to {action} curations in this scope",
        )


# ========================================
# LIST & READ ENDPOINTS
# ========================================


@router.get("/", response_model=CurationListResponse)
@api_endpoint()
def list_curations(
    db: Session = Depends(get_db),
    skip: int = Query(DEFAULT_SKIP, ge=0, description="Records to skip"),
    limit: int = Query(
        CURATIONS_DEFAULT_LIMIT,
        ge=1,
        le=CURATIONS_MAX_LIMIT,
        description="Max records",
    ),
    scope_id: UUID | None = Query(None, description="Filter by scope"),
    gene_id: UUID | None = Query(None, description="Filter by gene"),
    curation_status: CurationStatus | None = Query(None, description="Filter by status"),
    curator_id: UUID | None = Query(None, description="Filter by curator"),
    current_user: UserNew = Depends(get_current_active_user),
) -> CurationListResponse:
    """
    List curations with optional filters.
    RLS automatically filters to user's accessible scopes.
    """
    # Set RLS context for current user
    set_rls_context(db, current_user)

    # Determine scope filtering (matches workflow.py and genes.py pattern)
    scope_ids = None
    if current_user.role != "admin" and not scope_id:
        # Non-admin without specific scope: filter to their scopes
        scope_ids = current_user.assigned_scopes or []
        if not scope_ids:
            # User has no scopes assigned
            return CurationListResponse(
                curations=[], total=0, skip=skip, limit=limit
            )

    # If specific scope requested, verify access
    if scope_id and current_user.role != "admin":
        user_scope_ids: list[UUID] = current_user.assigned_scopes or []
        if scope_id not in user_scope_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )

    summaries, total = curation_crud.get_multi_filtered(
        db,
        skip=skip,
        limit=limit,
        scope_id=scope_id,
        scope_ids=scope_ids,
        gene_id=gene_id,
        status=curation_status,
        curator_id=curator_id,
    )

    return CurationListResponse(
        curations=summaries,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{curation_id}", response_model=Curation)
@api_endpoint()
def get_curation(
    curation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Curation:
    """Get a single curation by ID."""
    # Set RLS context
    set_rls_context(db, current_user)

    curation = curation_crud.get_with_relations(db, curation_id)

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    # Verify scope access (matches gene_assignments.py pattern)
    if current_user.role != "admin":
        user_scope_ids: list[UUID] = current_user.assigned_scopes or []
        if curation.scope_id not in user_scope_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )

    return Curation.model_validate(curation)


# ========================================
# CREATE ENDPOINT
# ========================================


@router.post("/", response_model=Curation, status_code=status.HTTP_201_CREATED)
@api_endpoint()
def create_curation(
    curation_in: CurationCreate,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Curation:
    """
    Create a new curation.
    Requires access to the target scope.
    """
    # Set RLS context
    set_rls_context(db, current_user)

    # Verify scope access (matches gene_assignments.py pattern)
    _check_scope_access(current_user, curation_in.scope_id, "create")

    try:
        curation = curation_crud.create_curation(
            db,
            obj_in=curation_in,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return Curation.model_validate(curation)


# ========================================
# UPDATE ENDPOINT (with optimistic locking)
# ========================================


@router.put(
    "/{curation_id}",
    response_model=Curation,
    responses={409: {"model": CurationConflictResponse}},
)
@api_endpoint()
def update_curation(
    curation_id: UUID,
    curation_in: CurationUpdate,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Curation:
    """
    Update a curation with optimistic locking.
    Returns 409 Conflict if lock_version doesn't match.
    """
    # Set RLS context
    set_rls_context(db, current_user)

    curation = curation_crud.get(db, curation_id)

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    # Verify scope access
    _check_scope_access(current_user, curation.scope_id, "update")

    # Check curation is editable
    if curation.status not in [CurationStatus.DRAFT, CurationStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft or rejected curations can be edited",
        )

    updated = curation_crud.update_with_lock(
        db,
        db_obj=curation,
        obj_in=curation_in,
        user_id=current_user.id,
    )

    if updated is None:
        # Return conflict response with current state
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "Concurrent modification detected",
                "current_lock_version": curation.lock_version,
                "your_lock_version": curation_in.lock_version,
                "current_state": curation.evidence_data,
            },
        )

    return Curation.model_validate(updated)


# ========================================
# DRAFT & SUBMIT ENDPOINTS
# ========================================


@router.patch("/{curation_id}/draft", response_model=Curation)
@api_endpoint()
def save_draft(
    curation_id: UUID,
    draft_in: CurationDraftSave,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Curation:
    """Save curation as draft (auto-save support)."""
    # Set RLS context
    set_rls_context(db, current_user)

    curation = curation_crud.get(db, curation_id)

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    # Only creator or admin can save drafts
    if current_user.role != "admin" and curation.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can save drafts",
        )

    updated = curation_crud.save_draft(
        db,
        db_obj=curation,
        draft_data=draft_in,
        user_id=current_user.id,
    )

    return Curation.model_validate(updated)


@router.post(
    "/{curation_id}/submit",
    response_model=Curation,
    responses={409: {"model": CurationConflictResponse}},
)
@api_endpoint()
def submit_curation(
    curation_id: UUID,
    submit_in: CurationSubmit,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Curation:
    """Submit curation for peer review."""
    # Set RLS context
    set_rls_context(db, current_user)

    curation = curation_crud.get(db, curation_id)

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    # Only creator or admin can submit
    if current_user.role != "admin" and curation.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can submit for review",
        )

    try:
        submitted = curation_crud.submit_for_review(
            db,
            db_obj=curation,
            submit_data=submit_in,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    if submitted is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Concurrent modification detected",
        )

    return Curation.model_validate(submitted)


# ========================================
# SCORE & DELETE ENDPOINTS
# ========================================


@router.get("/{curation_id}/score", response_model=CurationScoreResponse)
@api_endpoint()
def calculate_score(
    curation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> CurationScoreResponse:
    """Calculate ClinGen SOP v11 score for curation."""
    # Set RLS context
    set_rls_context(db, current_user)

    curation = curation_crud.get(db, curation_id)

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    # Verify scope access
    _check_scope_access(current_user, curation.scope_id, "calculate score for")

    return curation_crud.calculate_score(db, curation)


@router.delete("/{curation_id}", status_code=status.HTTP_204_NO_CONTENT)
@api_endpoint()
def delete_curation(
    curation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> None:
    """Soft delete a curation (archive)."""
    # Set RLS context
    set_rls_context(db, current_user)

    curation = curation_crud.get(db, curation_id)

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    # Verify scope access
    _check_scope_access(current_user, curation.scope_id, "delete")

    # Only allow deletion of drafts (or by admin)
    if curation.status != CurationStatus.DRAFT and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only draft curations can be deleted",
        )

    curation_crud.soft_delete(db, db_obj=curation, user_id=current_user.id)
```

---

### Step 1.4: Register Router (5 minutes)

**File**: `backend/app/api/v1/api.py` (MODIFY)

```python
# Add import
from app.api.v1.endpoints import curations

# Add router (after workflow router)
api_router.include_router(curations.router, prefix="/curations", tags=["curations"])
```

---

## Phase 2: Frontend Implementation

### Step 2.1: Pinia Store

**File**: `frontend/src/stores/curations.js` (NEW)

Pattern: Matches `genes.js` structure (minimal logging, consistent state shape)

```javascript
/**
 * Curations Pinia Store
 *
 * Manages curation state following existing store patterns (genes.js).
 * Implements: fetchItems, fetchItemById, createItem, updateItem, deleteItem
 */

import { defineStore } from 'pinia'
import { curationsAPI } from '@/api/curations'

export const useCurationsStore = defineStore('curations', {
  state: () => ({
    // List state
    curations: [],
    total: 0,
    loading: false,
    error: null,

    // Single item state
    currentCuration: null,

    // Pagination (matches genes.js pattern)
    pagination: {
      page: 1,
      per_page: 50,
      total: 0,
      pages: 0
    },

    // Filters
    filters: {
      scope_id: null,
      gene_id: null,
      status: null,
      curator_id: null
    },

    // Score state
    currentScore: null,
    scoreLoading: false
  }),

  getters: {
    /**
     * Get curation by ID from local state
     */
    getCurationById: state => id => {
      return state.curations.find(c => c.id === id)
    },

    /**
     * Get curations filtered by status
     */
    getCurationsByStatus: state => status => {
      return state.curations.filter(c => c.status === status)
    },

    /**
     * Get draft curations
     */
    getDraftCurations: state => {
      return state.curations.filter(c => c.is_draft)
    },

    /**
     * Get curations for a specific scope
     */
    getCurationsByScope: state => scopeId => {
      return state.curations.filter(c => c.scope_id === scopeId)
    }
  },

  actions: {
    /**
     * Fetch curations with current filters
     */
    async fetchCurations(params = {}) {
      this.loading = true
      this.error = null

      try {
        const queryParams = {
          skip: (this.pagination.page - 1) * this.pagination.per_page,
          limit: this.pagination.per_page,
          ...this.filters,
          ...params
        }

        // Remove null/undefined values
        Object.keys(queryParams).forEach(key => {
          if (queryParams[key] == null) {
            delete queryParams[key]
          }
        })

        const response = await curationsAPI.getCurations(queryParams)

        this.curations = response.curations || []
        this.total = response.total || 0

        // Update pagination
        this.pagination.total = response.total || 0
        this.pagination.pages = Math.ceil(this.total / this.pagination.per_page)

        return response
      } catch (error) {
        this.error = error.message || 'Failed to fetch curations'
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Fetch single curation by ID
     */
    async fetchCurationById(id) {
      this.loading = true
      this.error = null

      try {
        const curation = await curationsAPI.getCuration(id)
        this.currentCuration = curation

        // Update in list if exists
        const index = this.curations.findIndex(c => c.id === id)
        if (index !== -1) {
          this.curations[index] = curation
        }

        return curation
      } catch (error) {
        this.error = error.message || 'Failed to fetch curation'
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Create new curation
     */
    async createCuration(data) {
      this.loading = true
      this.error = null

      try {
        const curation = await curationsAPI.createCuration(data)
        this.curations.unshift(curation)
        this.total += 1
        return curation
      } catch (error) {
        this.error = error.message || 'Failed to create curation'
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Update curation with optimistic locking
     */
    async updateCuration(id, data) {
      this.loading = true
      this.error = null

      try {
        const updated = await curationsAPI.updateCuration(id, data)

        // Update in list
        const index = this.curations.findIndex(c => c.id === id)
        if (index !== -1) {
          this.curations[index] = updated
        }

        // Update current if same
        if (this.currentCuration?.id === id) {
          this.currentCuration = updated
        }

        return updated
      } catch (error) {
        // Handle conflict specially
        if (error.response?.status === 409) {
          const conflictData = error.response.data
          this.error = 'Another user modified this curation'
          throw {
            isConflict: true,
            currentVersion: conflictData.current_lock_version,
            currentState: conflictData.current_state,
            yourVersion: conflictData.your_lock_version
          }
        }
        this.error = error.message || 'Failed to update curation'
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Save as draft (auto-save support)
     */
    async saveDraft(id, data) {
      // Don't set loading for draft saves (background operation)
      try {
        const updated = await curationsAPI.saveDraft(id, data)

        if (this.currentCuration?.id === id) {
          this.currentCuration = updated
        }

        return updated
      } catch (error) {
        // Don't throw for draft saves, just log
        this.error = error.message
        return null
      }
    },

    /**
     * Submit curation for review
     */
    async submitCuration(id, data = {}) {
      this.loading = true
      this.error = null

      try {
        const submitted = await curationsAPI.submitCuration(id, data)

        // Update in list
        const index = this.curations.findIndex(c => c.id === id)
        if (index !== -1) {
          this.curations[index] = submitted
        }

        if (this.currentCuration?.id === id) {
          this.currentCuration = submitted
        }

        return submitted
      } catch (error) {
        this.error = error.message || 'Failed to submit curation'
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Calculate score
     */
    async calculateScore(id) {
      this.scoreLoading = true

      try {
        this.currentScore = await curationsAPI.calculateScore(id)
        return this.currentScore
      } catch (error) {
        this.error = error.message || 'Failed to calculate score'
        throw error
      } finally {
        this.scoreLoading = false
      }
    },

    /**
     * Delete curation (soft delete)
     */
    async deleteCuration(id) {
      this.loading = true
      this.error = null

      try {
        await curationsAPI.deleteCuration(id)

        // Remove from list
        this.curations = this.curations.filter(c => c.id !== id)
        this.total -= 1

        if (this.currentCuration?.id === id) {
          this.currentCuration = null
        }

        return true
      } catch (error) {
        this.error = error.message || 'Failed to delete curation'
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Update filters and refresh
     */
    setFilters(filters) {
      this.filters = { ...this.filters, ...filters }
      this.pagination.page = 1 // Reset to first page
    },

    /**
     * Set page and fetch
     */
    async setPage(page) {
      this.pagination.page = page
      await this.fetchCurations()
    },

    /**
     * Set current curation
     */
    setCurrentCuration(curation) {
      this.currentCuration = curation
    },

    /**
     * Clear current curation
     */
    clearCurrentCuration() {
      this.currentCuration = null
      this.currentScore = null
    },

    /**
     * Clear error
     */
    clearError() {
      this.error = null
    },

    /**
     * Reset store state
     */
    $reset() {
      this.curations = []
      this.total = 0
      this.currentCuration = null
      this.currentScore = null
      this.loading = false
      this.scoreLoading = false
      this.error = null
      this.filters = {
        scope_id: null,
        gene_id: null,
        status: null,
        curator_id: null
      }
      this.pagination = {
        page: 1,
        per_page: 50,
        total: 0,
        pages: 0
      }
    }
  }
})
```

---

### Step 2.2: Update Store Index (5 minutes)

**File**: `frontend/src/stores/index.js` (MODIFY if exists)

```javascript
// Add export
export { useCurationsStore } from './curations'
```

---

### Step 2.3: Wire CurationList.vue

Key changes to `frontend/src/components/curation/CurationList.vue`:

```javascript
// Add import
import { useCurationsStore } from '@/stores/curations'

// In setup
const curationsStore = useCurationsStore()

// Replace direct API calls with store
const curations = computed(() => curationsStore.curations)
const loading = computed(() => curationsStore.loading)
const total = computed(() => curationsStore.total)
const error = computed(() => curationsStore.error)

// On mount
onMounted(async () => {
  curationsStore.setFilters({ scope_id: props.scopeId })
  await curationsStore.fetchCurations()
})

// Pagination
const handlePageChange = async (page) => {
  await curationsStore.setPage(page)
}
```

---

### Step 2.4: Wire CurationForm.vue

Key changes to `frontend/src/components/forms/CurationForm.vue`:

```javascript
// Add imports
import { useCurationsStore } from '@/stores/curations'
import { useFormRecovery } from '@/composables/useFormRecovery'
import { useOptimisticLocking } from '@/composables/useOptimisticLocking'

// In setup
const curationsStore = useCurationsStore()
const { showRecoveryDialog, restoreRecovery, discardRecovery } = useFormRecovery(
  `curation-${props.curationId || 'new'}`,
  formData
)
const { conflictDetected, conflictData, saveWithLockCheck } = useOptimisticLocking()

// Save handler with conflict detection
const handleSave = async () => {
  try {
    if (props.curationId) {
      await curationsStore.updateCuration(props.curationId, {
        evidence_data: formData.value,
        lock_version: lockVersion.value
      })
    } else {
      await curationsStore.createCuration(formData.value)
    }
  } catch (error) {
    if (error.isConflict) {
      conflictDetected.value = true
      conflictData.value = error
    }
  }
}

// Auto-save draft
const autoSaveDraft = useDebounceFn(async () => {
  if (props.curationId) {
    await curationsStore.saveDraft(props.curationId, {
      evidence_data: formData.value,
      lock_version: lockVersion.value
    })
  }
}, 30000) // 30 seconds
```

---

## Phase 3: Testing

### Step 3.1: Backend Tests

**File**: `backend/tests/api/test_curations.py` (NEW)

```python
"""Integration tests for curations API."""

import pytest
from fastapi import status
from uuid import uuid4


class TestCurationsAPI:
    """Test curation CRUD operations."""

    def test_list_curations_empty(self, client, auth_headers):
        """Test listing curations returns empty list."""
        response = client.get("/api/v1/curations/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "curations" in data
        assert "total" in data

    def test_create_curation_invalid_gene(self, client, auth_headers):
        """Test creating curation with invalid gene returns 400."""
        data = {
            "gene_id": str(uuid4()),  # Non-existent
            "scope_id": str(uuid4()),
            "workflow_pair_id": str(uuid4()),
            "evidence_data": {},
        }
        response = client.post("/api/v1/curations/", json=data, headers=auth_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_optimistic_locking_conflict(self, client, auth_headers, test_curation):
        """Test optimistic locking returns 409 on conflict."""
        # Update with wrong lock version
        update_data = {
            "evidence_data": {"updated": True},
            "lock_version": 999,  # Wrong version
        }
        response = client.put(
            f"/api/v1/curations/{test_curation.id}",
            json=update_data,
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "current_lock_version" in response.json()

    def test_draft_save_does_not_require_lock(self, client, auth_headers, test_curation):
        """Test draft save works without lock_version."""
        draft_data = {"evidence_data": {"draft": True}}
        response = client.patch(
            f"/api/v1/curations/{test_curation.id}/draft",
            json=draft_data,
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

    def test_rls_filters_curations(self, client, user_headers, admin_curation):
        """Test RLS prevents access to other scopes' curations."""
        response = client.get(
            f"/api/v1/curations/{admin_curation.id}",
            headers=user_headers,
        )
        # Should not find curation from different scope
        assert response.status_code == status.HTTP_404_NOT_FOUND
```

---

## File Summary

### New Files (5)

| File | Purpose |
|------|---------|
| `backend/app/schemas/curation.py` | Pydantic schemas (InDBBase pattern) |
| `backend/app/crud/curation.py` | CRUD with FK validation, DI scoring |
| `backend/app/api/v1/endpoints/curations.py` | REST API with RLS |
| `frontend/src/stores/curations.js` | Pinia store (genes.js pattern) |
| `backend/tests/api/test_curations.py` | Integration tests |

### Modified Files (4)

| File | Change |
|------|--------|
| `backend/app/core/constants.py` | Add `CURATIONS_*` constants |
| `backend/app/api/v1/api.py` | Register curations router |
| `backend/app/schemas/__init__.py` | Export curation schemas |
| `backend/app/crud/__init__.py` | Export curation_crud |

---

## Implementation Checklist

```markdown
### Phase 1: Backend
- [ ] Add CURATIONS_DEFAULT_LIMIT, CURATIONS_MAX_LIMIT to constants.py
- [ ] Create schemas/curation.py with InDBBase pattern
- [ ] Update schemas/__init__.py exports
- [ ] Create crud/curation.py with FK validation
- [ ] Update crud/__init__.py exports
- [ ] Create endpoints/curations.py with RLS
- [ ] Register router in api.py
- [ ] Run: make lint && make test

### Phase 2: Frontend
- [ ] Create stores/curations.js (genes.js pattern)
- [ ] Wire CurationList.vue to store
- [ ] Wire CurationForm.vue to store
- [ ] Test conflict resolution UI
- [ ] Run: make lint-frontend

### Phase 3: Testing
- [ ] Write backend integration tests
- [ ] Manual test all 8 endpoints
- [ ] Test RLS filtering
- [ ] Test optimistic locking conflict
```

---

## Success Criteria

- [ ] `GET /curations/` returns paginated list
- [ ] `POST /curations/` creates with FK validation
- [ ] `PUT /curations/{id}` enforces optimistic locking
- [ ] `PATCH /curations/{id}/draft` saves without lock
- [ ] `POST /curations/{id}/submit` transitions workflow
- [ ] RLS filters curations by user scope
- [ ] CurationList.vue loads without errors
- [ ] CurationForm.vue handles conflicts gracefully
- [ ] All tests pass: `make test && make lint`

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| v2.1 | 2026-01-12 | Fixed `datetime.utcnow()` deprecation, added `_utc_now()` helper, cleaned up imports, added `_check_scope_access()` helper |
| v2.0 | 2026-01-12 | Added RLS, constants, InDBBase pattern, FK validation, fixed store patterns |
| v1.0 | 2026-01-12 | Initial implementation plan |

---

**Version**: 2.1 (Final)
**Status**: Ready for Implementation
