# Plan 2: Configurable Four-Eyes Principle

**Author:** Senior Developer Analysis
**Date:** January 13, 2026
**Status:** Ready for Implementation
**Phase:** 3 from Audit Report

---

## Executive Summary

This plan makes the **4-eyes principle configurable per scope and workflow**. Currently, the 4-eyes check is hardcoded in 6 locations. This solution introduces a `workflow_configurations` table allowing scopes to customize review requirements based on their risk profile.

### Best Practices Applied

- **[DZone: Four-Eyes Principle](https://dzone.com/articles/devops-guide-implementing-four-eyes-principle-with)**: Risk-based controls, configurable per context
- **[SAP SuccessFactors](https://help.sap.com/docs/successfactors-employee-central/implementing-and-managing-workflows/enabling-four-eye-principle-for-workflow-approvals)**: Enable/disable per workflow step
- **[Flagsmith](https://www.flagsmith.com/blog/what-is-the-four-eyes-principle)**: Apply based on sensitivity level
- **[Database Design 2025](https://getnerdify.com/blog/database-design-best-practices)**: Normalization, proper constraints

---

## Current Hardcoded Locations

| File | Line(s) | Description |
|------|---------|-------------|
| `workflow_engine.py` | 694-708 | `_requires_peer_review()` - hardcoded transitions |
| `workflow_engine.py` | 126-144 | Validation during transition |
| `workflow_engine.py` | 299-322 | Reviewer assignment validation |
| `scope_permissions.py` | 266-330 | `can_approve_curation()` method |
| `curations.py` | 78-99 | `_can_user_review_curation()` helper |
| `precurations.py` | 399-404 | Explicit approval check |

---

## Database Design

### New Table: `workflow_configurations`

**File:** `database/sql/004_workflow_configurations.sql`

```sql
-- =============================================================================
-- Workflow Configuration Table
-- =============================================================================
-- Allows per-scope customization of workflow behavior including 4-eyes principle
--
-- Design Principles:
-- 1. Scope-level configuration (default applies to all workflows in scope)
-- 2. Workflow-specific override (optional, for fine-grained control)
-- 3. Risk-based 4-eyes rules (based on classification result)
-- 4. Audit trail via standard columns
-- =============================================================================

-- Enum for configuration levels
CREATE TYPE workflow_config_level AS ENUM ('scope', 'workflow_pair');

-- Main configuration table
CREATE TABLE IF NOT EXISTS workflow_configurations (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Scope association (required)
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,

    -- Optional workflow pair association (for workflow-specific config)
    -- If NULL, config applies to all workflows in the scope
    workflow_pair_id UUID REFERENCES workflow_pairs(id) ON DELETE CASCADE,

    -- Configuration level indicator
    config_level workflow_config_level NOT NULL DEFAULT 'scope',

    -- ===========================================
    -- Four-Eyes Principle Configuration
    -- ===========================================

    -- Master toggle for 4-eyes requirement
    require_peer_review BOOLEAN NOT NULL DEFAULT TRUE,

    -- Allow self-review (violates 4-eyes, use with caution)
    -- When TRUE, users can approve their own work
    allow_self_review BOOLEAN NOT NULL DEFAULT FALSE,

    -- Minimum number of reviewers required
    -- 1 = standard 4-eyes, 2+ = enhanced review
    min_reviewers INTEGER NOT NULL DEFAULT 1 CHECK (min_reviewers >= 1 AND min_reviewers <= 5),

    -- ===========================================
    -- Risk-Based Review Rules (JSON)
    -- ===========================================

    -- Classifications that require peer review
    -- Empty array = all classifications require review (when require_peer_review=TRUE)
    -- Example: ["Definitive", "Strong", "Moderate"]
    require_review_for_classifications TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],

    -- Classifications that can skip peer review
    -- Example: ["Limited", "No Known Disease Relationship"]
    skip_review_for_classifications TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],

    -- Score threshold above which review is required
    -- NULL = no score-based rule
    review_required_score_threshold NUMERIC(5,2),

    -- ===========================================
    -- Workflow Stage Configuration
    -- ===========================================

    -- Which transitions require peer review
    -- Default: only REVIEW -> ACTIVE (approval)
    -- Can extend to: CURATION -> REVIEW (submission)
    peer_review_transitions JSONB NOT NULL DEFAULT '[
        {"from": "review", "to": "active"}
    ]'::JSONB,

    -- ===========================================
    -- Notification Settings
    -- ===========================================

    -- Notify on submission for review
    notify_on_submission BOOLEAN NOT NULL DEFAULT TRUE,

    -- Notify on approval/rejection
    notify_on_decision BOOLEAN NOT NULL DEFAULT TRUE,

    -- Auto-assign reviewers from pool
    auto_assign_reviewers BOOLEAN NOT NULL DEFAULT FALSE,

    -- ===========================================
    -- Audit Columns
    -- ===========================================

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,

    -- ===========================================
    -- Constraints
    -- ===========================================

    -- Unique config per scope (or scope+workflow_pair)
    CONSTRAINT uq_workflow_config_scope UNIQUE (scope_id, workflow_pair_id),

    -- If workflow_pair specified, config_level must be 'workflow_pair'
    CONSTRAINT ck_config_level_consistency CHECK (
        (workflow_pair_id IS NULL AND config_level = 'scope') OR
        (workflow_pair_id IS NOT NULL AND config_level = 'workflow_pair')
    ),

    -- Cannot skip review if allow_self_review is false and require_peer_review is true
    -- (logical consistency)
    CONSTRAINT ck_review_logic CHECK (
        NOT (require_peer_review = TRUE AND allow_self_review = TRUE AND min_reviewers > 1)
    )
);

-- Indexes for efficient lookup
CREATE INDEX idx_workflow_config_scope ON workflow_configurations(scope_id);
CREATE INDEX idx_workflow_config_workflow_pair ON workflow_configurations(workflow_pair_id)
    WHERE workflow_pair_id IS NOT NULL;

-- Trigger for updated_at
CREATE TRIGGER trg_workflow_configurations_updated_at
    BEFORE UPDATE ON workflow_configurations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Default Configuration Seed Data
-- =============================================================================

-- Insert default configuration for each existing scope
INSERT INTO workflow_configurations (scope_id, config_level, require_peer_review)
SELECT id, 'scope', TRUE
FROM scopes
WHERE NOT EXISTS (
    SELECT 1 FROM workflow_configurations wc WHERE wc.scope_id = scopes.id
);

-- =============================================================================
-- Comments
-- =============================================================================

COMMENT ON TABLE workflow_configurations IS
    'Per-scope workflow configuration including 4-eyes principle settings';

COMMENT ON COLUMN workflow_configurations.require_peer_review IS
    'Master toggle: when FALSE, users can approve their own work';

COMMENT ON COLUMN workflow_configurations.allow_self_review IS
    'When TRUE, explicitly allows self-review (use with caution)';

COMMENT ON COLUMN workflow_configurations.require_review_for_classifications IS
    'List of classifications that always require peer review';

COMMENT ON COLUMN workflow_configurations.peer_review_transitions IS
    'JSON array of workflow stage transitions requiring peer review';
```

---

## SQLAlchemy Model

**File:** `backend/app/models/models.py`

Add after `ScopeMembership` class (around line 340):

```python
class WorkflowConfiguration(Base):
    """Per-scope workflow configuration including 4-eyes principle settings.

    This model enables configurable workflow behavior per scope, supporting:
    - Enabling/disabling 4-eyes principle
    - Risk-based review requirements
    - Custom transition rules
    - Notification settings

    Best Practice Reference:
    - https://dzone.com/articles/devops-guide-implementing-four-eyes-principle-with
    - https://www.flagsmith.com/blog/what-is-the-four-eyes-principle
    """

    __tablename__ = "workflow_configurations"

    # Primary key
    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )

    # Associations
    scope_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("scopes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_pair_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(),
        ForeignKey("workflow_pairs.id", ondelete="CASCADE"),
    )

    # Configuration level
    config_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="scope"
    )  # 'scope' or 'workflow_pair'

    # Four-Eyes Configuration
    require_peer_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    allow_self_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    min_reviewers: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )

    # Risk-Based Rules
    require_review_for_classifications: Mapped[list[str]] = mapped_column(
        compatible_array_text(), default=[]
    )
    skip_review_for_classifications: Mapped[list[str]] = mapped_column(
        compatible_array_text(), default=[]
    )
    review_required_score_threshold: Mapped[float | None] = mapped_column(
        Numeric(5, 2)
    )

    # Transition Rules (JSONB)
    peer_review_transitions: Mapped[list[dict[str, str]]] = mapped_column(
        compatible_jsonb(),
        default=[{"from": "review", "to": "active"}]
    )

    # Notification Settings
    notify_on_submission: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    notify_on_decision: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    auto_assign_reviewers: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Audit Columns
    created_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )

    # Relationships
    scope: Mapped["Scope"] = relationship("Scope", foreign_keys=[scope_id])
    workflow_pair: Mapped["WorkflowPair | None"] = relationship(
        "WorkflowPair", foreign_keys=[workflow_pair_id]
    )
    creator: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[created_by]
    )
    updater: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[updated_by]
    )

    # Unique constraint
    __table_args__ = (
        UniqueConstraint("scope_id", "workflow_pair_id", name="uq_workflow_config_scope"),
    )
```

---

## Pydantic Schemas

**New File:** `backend/app/schemas/workflow_configuration.py`

```python
"""Pydantic schemas for workflow configuration API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PeerReviewTransition(BaseModel):
    """Single peer review transition rule."""
    from_stage: str = Field(..., alias="from", description="Source workflow stage")
    to_stage: str = Field(..., alias="to", description="Target workflow stage")

    model_config = ConfigDict(populate_by_name=True)


class WorkflowConfigurationBase(BaseModel):
    """Base schema with common workflow configuration fields."""

    # Four-Eyes Configuration
    require_peer_review: bool = Field(
        True,
        description="Master toggle for 4-eyes principle"
    )
    allow_self_review: bool = Field(
        False,
        description="Allow users to approve their own work (violates 4-eyes)"
    )
    min_reviewers: int = Field(
        1,
        ge=1,
        le=5,
        description="Minimum number of reviewers required"
    )

    # Risk-Based Rules
    require_review_for_classifications: list[str] = Field(
        default_factory=list,
        description="Classifications that always require peer review"
    )
    skip_review_for_classifications: list[str] = Field(
        default_factory=list,
        description="Classifications that can skip peer review"
    )
    review_required_score_threshold: float | None = Field(
        None,
        description="Score threshold above which review is required"
    )

    # Transition Rules
    peer_review_transitions: list[dict[str, str]] = Field(
        default_factory=lambda: [{"from": "review", "to": "active"}],
        description="Workflow transitions requiring peer review"
    )

    # Notification Settings
    notify_on_submission: bool = Field(True, description="Notify on submission")
    notify_on_decision: bool = Field(True, description="Notify on approval/rejection")
    auto_assign_reviewers: bool = Field(False, description="Auto-assign reviewers")

    @field_validator("peer_review_transitions")
    @classmethod
    def validate_transitions(cls, v: list[dict[str, str]]) -> list[dict[str, str]]:
        """Validate transition rules have required keys."""
        valid_stages = {"entry", "precuration", "curation", "review", "active"}
        for transition in v:
            if "from" not in transition or "to" not in transition:
                raise ValueError("Each transition must have 'from' and 'to' keys")
            if transition["from"] not in valid_stages:
                raise ValueError(f"Invalid 'from' stage: {transition['from']}")
            if transition["to"] not in valid_stages:
                raise ValueError(f"Invalid 'to' stage: {transition['to']}")
        return v


class WorkflowConfigurationCreate(WorkflowConfigurationBase):
    """Schema for creating a workflow configuration."""
    scope_id: UUID = Field(..., description="Scope UUID")
    workflow_pair_id: UUID | None = Field(
        None,
        description="Optional workflow pair UUID for workflow-specific config"
    )


class WorkflowConfigurationUpdate(BaseModel):
    """Schema for updating a workflow configuration."""
    require_peer_review: bool | None = None
    allow_self_review: bool | None = None
    min_reviewers: int | None = Field(None, ge=1, le=5)
    require_review_for_classifications: list[str] | None = None
    skip_review_for_classifications: list[str] | None = None
    review_required_score_threshold: float | None = None
    peer_review_transitions: list[dict[str, str]] | None = None
    notify_on_submission: bool | None = None
    notify_on_decision: bool | None = None
    auto_assign_reviewers: bool | None = None

    model_config = ConfigDict(extra="forbid")


class WorkflowConfiguration(WorkflowConfigurationBase):
    """Full workflow configuration response schema."""
    id: UUID
    scope_id: UUID
    workflow_pair_id: UUID | None
    config_level: str
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    # Expanded relationships
    scope_name: str | None = None
    workflow_pair_name: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_relations(cls, config: Any) -> "WorkflowConfiguration":
        """Create instance from ORM model with relationships."""
        data = {
            "id": config.id,
            "scope_id": config.scope_id,
            "workflow_pair_id": config.workflow_pair_id,
            "config_level": config.config_level,
            "require_peer_review": config.require_peer_review,
            "allow_self_review": config.allow_self_review,
            "min_reviewers": config.min_reviewers,
            "require_review_for_classifications": config.require_review_for_classifications or [],
            "skip_review_for_classifications": config.skip_review_for_classifications or [],
            "review_required_score_threshold": config.review_required_score_threshold,
            "peer_review_transitions": config.peer_review_transitions or [],
            "notify_on_submission": config.notify_on_submission,
            "notify_on_decision": config.notify_on_decision,
            "auto_assign_reviewers": config.auto_assign_reviewers,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
            "created_by": config.created_by,
            "updated_by": config.updated_by,
        }

        if hasattr(config, "scope") and config.scope:
            data["scope_name"] = config.scope.name

        if hasattr(config, "workflow_pair") and config.workflow_pair:
            data["workflow_pair_name"] = config.workflow_pair.name

        return cls(**data)


class WorkflowConfigurationListResponse(BaseModel):
    """Paginated list response."""
    configurations: list[WorkflowConfiguration]
    total: int
```

---

## Workflow Engine Updates

**File:** `backend/app/crud/workflow_engine.py`

### Add Configuration Loader Method

Add after line 60 (after `valid_transitions` dict):

```python
    def _get_workflow_config(
        self,
        db: Session,
        scope_id: UUID,
        workflow_pair_id: UUID | None = None,
    ) -> "WorkflowConfiguration | None":
        """Get workflow configuration for scope/workflow pair.

        Resolution order:
        1. Workflow-specific config (if workflow_pair_id provided)
        2. Scope-level config
        3. None (use defaults)

        Args:
            db: Database session
            scope_id: Scope UUID
            workflow_pair_id: Optional workflow pair UUID

        Returns:
            WorkflowConfiguration or None
        """
        from app.models import WorkflowConfiguration

        # Try workflow-specific config first
        if workflow_pair_id:
            config = (
                db.query(WorkflowConfiguration)
                .filter(
                    WorkflowConfiguration.scope_id == scope_id,
                    WorkflowConfiguration.workflow_pair_id == workflow_pair_id,
                )
                .first()
            )
            if config:
                return config

        # Fall back to scope-level config
        return (
            db.query(WorkflowConfiguration)
            .filter(
                WorkflowConfiguration.scope_id == scope_id,
                WorkflowConfiguration.workflow_pair_id.is_(None),
            )
            .first()
        )

    def _get_effective_peer_review_requirement(
        self,
        db: Session,
        scope_id: UUID,
        workflow_pair_id: UUID | None,
        current_stage: WorkflowStage,
        target_stage: WorkflowStage,
        classification: str | None = None,
        score: float | None = None,
    ) -> bool:
        """Determine if peer review is required for this transition.

        Implements configurable 4-eyes principle with risk-based rules.

        Args:
            db: Database session
            scope_id: Scope UUID
            workflow_pair_id: Optional workflow pair UUID
            current_stage: Current workflow stage
            target_stage: Target workflow stage
            classification: Optional classification result (for risk-based rules)
            score: Optional score (for score-based rules)

        Returns:
            True if peer review is required, False otherwise
        """
        config = self._get_workflow_config(db, scope_id, workflow_pair_id)

        # No config = use default (require peer review)
        if not config:
            return self._default_requires_peer_review(current_stage, target_stage)

        # Master toggle off = no peer review
        if not config.require_peer_review:
            logger.info(
                "Peer review disabled for scope",
                scope_id=str(scope_id),
                transition=f"{current_stage.value} -> {target_stage.value}",
            )
            return False

        # Check if this transition is in the configured list
        transition_match = any(
            t.get("from") == current_stage.value and t.get("to") == target_stage.value
            for t in (config.peer_review_transitions or [])
        )

        if not transition_match:
            return False

        # Risk-based rules: check classification
        if classification:
            # Skip review for certain classifications
            if classification in (config.skip_review_for_classifications or []):
                logger.info(
                    "Skipping peer review for classification",
                    scope_id=str(scope_id),
                    classification=classification,
                )
                return False

            # Require review for certain classifications
            if config.require_review_for_classifications:
                if classification in config.require_review_for_classifications:
                    return True
                # If list is specified but classification not in it, skip review
                return False

        # Score-based rules
        if score is not None and config.review_required_score_threshold is not None:
            if score < float(config.review_required_score_threshold):
                logger.info(
                    "Skipping peer review: score below threshold",
                    scope_id=str(scope_id),
                    score=score,
                    threshold=float(config.review_required_score_threshold),
                )
                return False

        return True

    def _default_requires_peer_review(
        self, current_stage: WorkflowStage, target_stage: WorkflowStage
    ) -> bool:
        """Default peer review requirement (fallback when no config)."""
        return (current_stage, target_stage) == (
            WorkflowStage.REVIEW,
            WorkflowStage.ACTIVE,
        )
```

### Update `_requires_peer_review` Method

Replace lines 694-708:

```python
    def _requires_peer_review(
        self,
        current_stage: WorkflowStage,
        target_stage: WorkflowStage,
        db: Session | None = None,
        scope_id: UUID | None = None,
        workflow_pair_id: UUID | None = None,
        classification: str | None = None,
        score: float | None = None,
    ) -> bool:
        """
        Check if transition requires peer review (4-eyes principle).

        Now configurable per scope via workflow_configurations table.

        Args:
            current_stage: Current workflow stage
            target_stage: Target workflow stage
            db: Database session (required for config lookup)
            scope_id: Scope UUID (required for config lookup)
            workflow_pair_id: Optional workflow pair UUID
            classification: Optional classification for risk-based rules
            score: Optional score for score-based rules

        Returns:
            True if peer review is required, False otherwise
        """
        # If no db/scope provided, use default behavior
        if db is None or scope_id is None:
            return self._default_requires_peer_review(current_stage, target_stage)

        return self._get_effective_peer_review_requirement(
            db=db,
            scope_id=scope_id,
            workflow_pair_id=workflow_pair_id,
            current_stage=current_stage,
            target_stage=target_stage,
            classification=classification,
            score=score,
        )
```

### Update `_validate_4_eyes_principle` Method

Update lines 85-106 to use configuration:

```python
    def _validate_4_eyes_principle(
        self,
        db: Session,
        user: UserNew,
        user_id: UUID,
        item: CurationNew | PrecurationNew | None,
        item_type: str,
        scope_id: UUID | None = None,
        workflow_pair_id: UUID | None = None,
    ) -> list[str]:
        """Validate 4-eyes principle and return list of errors.

        Now respects workflow configuration for allow_self_review.
        """
        errors: list[str] = []
        if not item:
            return errors

        # Get configuration to check if self-review is allowed
        config = self._get_workflow_config(db, scope_id or item.scope_id, workflow_pair_id)
        allow_self_review = config.allow_self_review if config else False

        # Check if user is reviewing their own work
        if item.created_by == user_id and not allow_self_review:
            errors.append("4-eyes principle violation: Cannot review your own work")

        # Check review permissions for curations
        if item_type == "curation" and not self._has_review_permissions(db, user, item):
            errors.append("Insufficient permissions for peer review")

        return errors
```

### Update `validate_transition` Call Site

Update line 150 to pass additional parameters:

```python
        # 4-eyes principle validation
        if self._requires_peer_review(
            current_stage,
            target_stage,
            db=db,
            scope_id=scope_id,
            workflow_pair_id=getattr(item, "workflow_pair_id", None) if item else None,
            classification=getattr(item, "computed_verdict", None) if item else None,
            score=getattr(item, "computed_scores", {}).get("total") if item else None,
        ):
            errors.extend(
                self._validate_4_eyes_principle(
                    db, user, user_id, item, item_type, scope_id
                )
            )
```

---

## API Endpoints

**New File:** `backend/app/api/v1/endpoints/workflow_configurations.py`

```python
"""Workflow Configuration API endpoints.

CRUD operations for scope-level workflow settings including 4-eyes principle.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.logging import api_endpoint, get_logger
from app.models import UserNew, WorkflowConfiguration as WorkflowConfigModel
from app.schemas.workflow_configuration import (
    WorkflowConfiguration,
    WorkflowConfigurationCreate,
    WorkflowConfigurationListResponse,
    WorkflowConfigurationUpdate,
)
from app.services.scope_permissions import ScopePermissionService

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=WorkflowConfigurationListResponse)
@api_endpoint()
def list_workflow_configurations(
    db: Session = Depends(get_db),
    scope_id: UUID | None = Query(None, description="Filter by scope"),
    current_user: UserNew = Depends(get_current_active_user),
) -> WorkflowConfigurationListResponse:
    """List workflow configurations for accessible scopes."""
    query = db.query(WorkflowConfigModel)

    # Filter by scope if specified
    if scope_id:
        query = query.filter(WorkflowConfigModel.scope_id == scope_id)

    # Non-admin users only see configs for their scopes
    if current_user.role.value != "admin":
        user_scope_ids = ScopePermissionService.get_user_scope_ids(db, current_user)
        query = query.filter(WorkflowConfigModel.scope_id.in_(user_scope_ids))

    configs = query.all()

    return WorkflowConfigurationListResponse(
        configurations=[
            WorkflowConfiguration.from_orm_with_relations(c) for c in configs
        ],
        total=len(configs),
    )


@router.get("/{config_id}", response_model=WorkflowConfiguration)
@api_endpoint()
def get_workflow_configuration(
    config_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> WorkflowConfiguration:
    """Get a workflow configuration by ID."""
    config = db.query(WorkflowConfigModel).filter(WorkflowConfigModel.id == config_id).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow configuration not found",
        )

    # Check scope access
    if not ScopePermissionService.has_scope_access(db, current_user, config.scope_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this configuration",
        )

    return WorkflowConfiguration.from_orm_with_relations(config)


@router.get("/scope/{scope_id}", response_model=WorkflowConfiguration | None)
@api_endpoint()
def get_scope_workflow_configuration(
    scope_id: UUID,
    workflow_pair_id: UUID | None = Query(None),
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> WorkflowConfiguration | None:
    """Get workflow configuration for a scope (with optional workflow pair)."""
    # Check scope access
    if not ScopePermissionService.has_scope_access(db, current_user, scope_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this scope",
        )

    query = db.query(WorkflowConfigModel).filter(WorkflowConfigModel.scope_id == scope_id)

    if workflow_pair_id:
        query = query.filter(WorkflowConfigModel.workflow_pair_id == workflow_pair_id)
    else:
        query = query.filter(WorkflowConfigModel.workflow_pair_id.is_(None))

    config = query.first()

    if not config:
        return None

    return WorkflowConfiguration.from_orm_with_relations(config)


@router.post("/", response_model=WorkflowConfiguration, status_code=status.HTTP_201_CREATED)
@api_endpoint()
def create_workflow_configuration(
    config_in: WorkflowConfigurationCreate,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> WorkflowConfiguration:
    """Create a workflow configuration (scope admin or platform admin only)."""
    # Check scope admin access
    if not ScopePermissionService.has_scope_access(
        db, current_user, config_in.scope_id, required_roles=["admin"]
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only scope admins can create workflow configurations",
        )

    # Check for existing config
    existing_query = db.query(WorkflowConfigModel).filter(
        WorkflowConfigModel.scope_id == config_in.scope_id
    )
    if config_in.workflow_pair_id:
        existing_query = existing_query.filter(
            WorkflowConfigModel.workflow_pair_id == config_in.workflow_pair_id
        )
    else:
        existing_query = existing_query.filter(
            WorkflowConfigModel.workflow_pair_id.is_(None)
        )

    if existing_query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Configuration already exists for this scope/workflow pair",
        )

    # Create configuration
    config = WorkflowConfigModel(
        scope_id=config_in.scope_id,
        workflow_pair_id=config_in.workflow_pair_id,
        config_level="workflow_pair" if config_in.workflow_pair_id else "scope",
        require_peer_review=config_in.require_peer_review,
        allow_self_review=config_in.allow_self_review,
        min_reviewers=config_in.min_reviewers,
        require_review_for_classifications=config_in.require_review_for_classifications,
        skip_review_for_classifications=config_in.skip_review_for_classifications,
        review_required_score_threshold=config_in.review_required_score_threshold,
        peer_review_transitions=config_in.peer_review_transitions,
        notify_on_submission=config_in.notify_on_submission,
        notify_on_decision=config_in.notify_on_decision,
        auto_assign_reviewers=config_in.auto_assign_reviewers,
        created_by=current_user.id,
        updated_by=current_user.id,
    )

    db.add(config)
    db.commit()
    db.refresh(config)

    logger.info(
        "Created workflow configuration",
        config_id=str(config.id),
        scope_id=str(config.scope_id),
        user_id=str(current_user.id),
    )

    return WorkflowConfiguration.from_orm_with_relations(config)


@router.patch("/{config_id}", response_model=WorkflowConfiguration)
@api_endpoint()
def update_workflow_configuration(
    config_id: UUID,
    config_in: WorkflowConfigurationUpdate,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> WorkflowConfiguration:
    """Update a workflow configuration (scope admin only)."""
    config = db.query(WorkflowConfigModel).filter(WorkflowConfigModel.id == config_id).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow configuration not found",
        )

    # Check scope admin access
    if not ScopePermissionService.has_scope_access(
        db, current_user, config.scope_id, required_roles=["admin"]
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only scope admins can update workflow configurations",
        )

    # Update fields
    update_data = config_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    config.updated_by = current_user.id
    db.commit()
    db.refresh(config)

    logger.info(
        "Updated workflow configuration",
        config_id=str(config.id),
        updated_fields=list(update_data.keys()),
        user_id=str(current_user.id),
    )

    return WorkflowConfiguration.from_orm_with_relations(config)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
@api_endpoint()
def delete_workflow_configuration(
    config_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> None:
    """Delete a workflow configuration (platform admin only)."""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only platform admins can delete workflow configurations",
        )

    config = db.query(WorkflowConfigModel).filter(WorkflowConfigModel.id == config_id).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow configuration not found",
        )

    db.delete(config)
    db.commit()

    logger.info(
        "Deleted workflow configuration",
        config_id=str(config_id),
        user_id=str(current_user.id),
    )
```

### Register Router

**File:** `backend/app/api/v1/api.py`

Add:

```python
from app.api.v1.endpoints import workflow_configurations

# Add to router includes:
api_router.include_router(
    workflow_configurations.router,
    prefix="/workflow-configurations",
    tags=["workflow-configurations"],
)
```

---

## Update ScopePermissionService

**File:** `backend/app/services/scope_permissions.py`

Update `can_approve_curation` (lines 266-330) to use configuration:

```python
    @staticmethod
    def can_approve_curation(
        db: Session,
        user: UserNew,
        curation: CurationNew,
    ) -> bool:
        """Check if user can approve/activate curation (4-eyes principle).

        Now respects workflow configuration for allow_self_review.
        """
        from app.models import WorkflowConfiguration

        # Admin can approve all
        if user.role.value == "admin":
            return True

        # Check workflow configuration for self-review setting
        config = (
            db.query(WorkflowConfiguration)
            .filter(
                WorkflowConfiguration.scope_id == curation.scope_id,
                WorkflowConfiguration.workflow_pair_id.is_(None),
            )
            .first()
        )

        allow_self_review = config.allow_self_review if config else False

        # Cannot approve own curation (unless self-review is allowed)
        if curation.created_by == user.id and not allow_self_review:
            logger.info(
                "User cannot approve own curation (4-eyes principle)",
                user_id=str(user.id),
                curation_id=str(curation.id),
            )
            return False

        # Must be scope member with reviewer+ role
        scope_member = (
            db.query(ScopeMembership)
            .filter(
                ScopeMembership.scope_id == curation.scope_id,
                ScopeMembership.user_id == user.id,
                ScopeMembership.is_active,
            )
            .first()
        )

        if not scope_member:
            return False

        return scope_member.role in ["reviewer", "admin", "curator"]
```

---

## Frontend Integration (Optional)

**File:** `frontend/src/stores/workflowConfiguration.js`

```javascript
// Pinia store for workflow configuration management
import { defineStore } from 'pinia'
import { workflowConfigurationApi } from '@/api/workflowConfiguration'

export const useWorkflowConfigurationStore = defineStore('workflowConfiguration', {
  state: () => ({
    configurations: [],
    currentConfig: null,
    loading: false,
    error: null,
  }),

  getters: {
    getScopeConfig: (state) => (scopeId) => {
      return state.configurations.find(c => c.scope_id === scopeId && !c.workflow_pair_id)
    },
    isPeerReviewRequired: (state) => (scopeId) => {
      const config = state.configurations.find(c => c.scope_id === scopeId)
      return config?.require_peer_review ?? true // Default to true
    },
  },

  actions: {
    async fetchConfigurations(scopeId = null) {
      this.loading = true
      try {
        const params = scopeId ? { scope_id: scopeId } : {}
        const response = await workflowConfigurationApi.list(params)
        this.configurations = response.data.configurations
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async createConfiguration(data) {
      this.loading = true
      try {
        const response = await workflowConfigurationApi.create(data)
        this.configurations.push(response.data)
        return response.data
      } finally {
        this.loading = false
      }
    },

    async updateConfiguration(id, data) {
      this.loading = true
      try {
        const response = await workflowConfigurationApi.update(id, data)
        const index = this.configurations.findIndex(c => c.id === id)
        if (index !== -1) {
          this.configurations[index] = response.data
        }
        return response.data
      } finally {
        this.loading = false
      }
    },
  },
})
```

---

## Testing Strategy

### Unit Tests

```python
# backend/tests/crud/test_workflow_engine_config.py

import pytest
from app.crud.workflow_engine import WorkflowEngine
from app.models import WorkflowConfiguration, WorkflowStage


class TestWorkflowEngineConfiguration:
    def test_default_peer_review_required(self, db, workflow_engine):
        """Without config, peer review should be required for REVIEW->ACTIVE."""
        assert workflow_engine._default_requires_peer_review(
            WorkflowStage.REVIEW, WorkflowStage.ACTIVE
        )

    def test_peer_review_disabled_by_config(self, db, scope, workflow_engine):
        """Config can disable peer review."""
        config = WorkflowConfiguration(
            scope_id=scope.id,
            require_peer_review=False,
        )
        db.add(config)
        db.commit()

        assert not workflow_engine._requires_peer_review(
            WorkflowStage.REVIEW,
            WorkflowStage.ACTIVE,
            db=db,
            scope_id=scope.id,
        )

    def test_self_review_allowed_by_config(self, db, scope, user, curation, workflow_engine):
        """Config can allow self-review."""
        curation.created_by = user.id
        config = WorkflowConfiguration(
            scope_id=scope.id,
            require_peer_review=True,
            allow_self_review=True,
        )
        db.add(config)
        db.commit()

        errors = workflow_engine._validate_4_eyes_principle(
            db, user, user.id, curation, "curation", scope.id
        )
        assert len(errors) == 0  # No 4-eyes violation

    def test_risk_based_skip_classification(self, db, scope, workflow_engine):
        """Classifications in skip list should not require review."""
        config = WorkflowConfiguration(
            scope_id=scope.id,
            require_peer_review=True,
            skip_review_for_classifications=["Limited", "No Known Disease Relationship"],
        )
        db.add(config)
        db.commit()

        assert not workflow_engine._get_effective_peer_review_requirement(
            db, scope.id, None,
            WorkflowStage.REVIEW, WorkflowStage.ACTIVE,
            classification="Limited",
        )

    def test_score_threshold_skip(self, db, scope, workflow_engine):
        """Low scores can skip review when threshold is set."""
        config = WorkflowConfiguration(
            scope_id=scope.id,
            require_peer_review=True,
            review_required_score_threshold=5.0,
        )
        db.add(config)
        db.commit()

        assert not workflow_engine._get_effective_peer_review_requirement(
            db, scope.id, None,
            WorkflowStage.REVIEW, WorkflowStage.ACTIVE,
            score=3.5,
        )
```

### Integration Tests

```python
# backend/tests/api/test_workflow_configurations.py

def test_create_config_requires_scope_admin(client, db, curator_token, scope):
    """Only scope admins can create configurations."""
    response = client.post(
        "/api/v1/workflow-configurations/",
        json={"scope_id": str(scope.id), "require_peer_review": False},
        headers={"Authorization": f"Bearer {curator_token}"},
    )
    assert response.status_code == 403

def test_curation_approval_respects_config(client, db, reviewer_token, scope, curation):
    """Approval should respect 4-eyes config."""
    # Create config allowing self-review
    config = WorkflowConfiguration(
        scope_id=scope.id,
        allow_self_review=True,
    )
    db.add(config)
    db.commit()

    # Creator should be able to approve own work
    response = client.post(
        f"/api/v1/workflow/{curation.id}/approve",
        headers={"Authorization": f"Bearer {curation_creator_token}"},
    )
    assert response.status_code == 200
```

---

## Implementation Order

### Week 1: Database & Model
1. Create SQL migration file
2. Run migration on dev database
3. Add SQLAlchemy model
4. Create Pydantic schemas

### Week 2: Backend Logic
5. Add configuration loader to WorkflowEngine
6. Update `_requires_peer_review` method
7. Update `_validate_4_eyes_principle` method
8. Update `ScopePermissionService.can_approve_curation`

### Week 3: API & Integration
9. Create API endpoints
10. Register router
11. Write tests
12. Integration testing

### Week 4: Frontend (Optional)
13. Create Pinia store
14. Add configuration UI to scope settings
15. End-to-end testing

---

## Rollback Plan

If issues arise:

1. **Code rollback**: Revert workflow engine changes (old behavior is default)
2. **Config cleanup**: Delete problematic workflow_configurations rows
3. **Table removal** (if needed):
   ```sql
   DROP TABLE IF EXISTS workflow_configurations CASCADE;
   DROP TYPE IF EXISTS workflow_config_level;
   ```

---

## Security Considerations

1. **Only scope admins** can modify workflow configurations
2. **Audit logging** for all configuration changes
3. **Validation** prevents illogical combinations (e.g., allow_self_review + min_reviewers > 1)
4. **Default secure**: require_peer_review=TRUE by default

---

## References

- [DZone: Implementing Four-Eyes Principle](https://dzone.com/articles/devops-guide-implementing-four-eyes-principle-with)
- [SAP: Enabling Four-Eye Principle](https://help.sap.com/docs/successfactors-employee-central/implementing-and-managing-workflows/enabling-four-eye-principle-for-workflow-approvals)
- [Flagsmith: Four Eyes Principle](https://www.flagsmith.com/blog/what-is-the-four-eyes-principle)
- [Database Design Best Practices 2025](https://getnerdify.com/blog/database-design-best-practices)
- [Graph AI: Four-eyes Principle](https://www.graphapp.ai/engineering-glossary/devops/four-eyes-principle)

---

*Plan generated by senior developer analysis. Manual review recommended before implementation.*
