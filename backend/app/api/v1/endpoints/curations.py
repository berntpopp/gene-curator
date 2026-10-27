"""
Curation API endpoints.
Full CRUD with RLS integration and scope-based access control.
Follows patterns from gene_assignments.py, workflow.py, and genes.py.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from app.core.capabilities import EDIT, require
from app.core.constants import (
    CURATIONS_DEFAULT_LIMIT,
    CURATIONS_MAX_LIMIT,
    DEFAULT_SKIP,
)
from app.core.database import get_db, raise_if_rls_denied
from app.core.deps import get_current_active_user, set_rls_context
from app.core.logging import api_endpoint, get_logger
from app.crud.curation import OpenCurationExistsError, curation_crud
from app.crud.precuration import precuration_crud
from app.crud.review_round import (
    approving_reviewers,
    holds_review_capability,
    in_current_round,
    reviewers_required,
)
from app.crud.workflow_engine import WorkflowEngine
from app.models import CurationNew, CurationStatus, Review, ReviewStatus, UserNew
from app.schemas.curation import (
    Curation,
    CurationConflictResponse,
    CurationCreate,
    CurationDetail,
    CurationDraftSave,
    CurationListResponse,
    CurationScoreResponse,
    CurationSubmit,
    CurationUpdate,
)
from app.scoring.point_limits import enforce_clingen_point_ranges
from app.services.scope_permissions import ScopePermissionService

router = APIRouter()
logger = get_logger(__name__)


# ========================================
# HELPER FUNCTIONS
# ========================================


def _conflict(curation: CurationNew, sent: int) -> HTTPException:
    """409 with the current version and state (the failed UPDATE rolled back, so this reads what
    the other tab saved)."""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "error": "Concurrent modification detected",
            "current_lock_version": curation.lock_version,
            "your_lock_version": sent,
            "current_state": curation.evidence_data,
        },
    )


def _require_active_scope(curation: CurationNew) -> None:
    """RLS (054) blocks every write to an inactive scope's curations; refuse clearly, not with a 500."""
    if not curation.scope.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This scope is inactive; its curations are read-only",
        )


def _get_user_scope_role(db: Session, user_id: UUID, scope_id: UUID) -> str | None:
    """Get user's role for a specific scope from scope_memberships."""
    from app.models import ScopeMembership

    membership = (
        db.query(ScopeMembership)
        .filter(
            ScopeMembership.user_id == user_id,
            ScopeMembership.scope_id == scope_id,
            ScopeMembership.is_active,
            ScopeMembership.accepted_at.isnot(None),
        )
        .first()
    )
    return membership.role if membership else None


def _can_user_edit_curation(
    db: Session, user: UserNew, curation: "CurationNew"
) -> bool:
    """Same rule as save-draft and submit: the creator (curator or scope admin) or a platform admin."""
    if curation.status not in [CurationStatus.DRAFT, CurationStatus.REJECTED]:
        return False
    if not curation.scope.is_active:
        return False
    if user.role == "admin":
        return True
    if curation.created_by != user.id:
        return False
    # Check scope-specific role (valid scope roles: admin, curator, reviewer, viewer)
    scope_role = _get_user_scope_role(db, user.id, curation.scope_id)
    return scope_role in ["admin", "curator"]


def _can_user_review_curation(
    db: Session, user: UserNew, curation: "CurationNew"
) -> bool:
    """
    Check if user can review (approve/reject) this curation.
    Enforces 4-eyes principle: user cannot review their own work.
    """
    # Cannot review own work (4-eyes principle)
    if curation.created_by == user.id:
        return False

    # Must be in review status/stage
    if curation.status != CurationStatus.IN_REVIEW:
        return False

    # REVIEW capability by membership; platform admins get no bypass
    return holds_review_capability(db, user.id, curation.scope_id)


def _has_approved(db: Session, user: UserNew, curation: CurationNew) -> bool:
    """The user approved in the open review round; same rule as approving_reviewers (D1)."""
    return curation.created_by != user.id and (
        db.scalar(
            select(Review.id).where(
                Review.curation_id == curation.id,
                Review.reviewer_id == user.id,
                Review.status == ReviewStatus.APPROVED,
                Review.recommendation == "approve",
                in_current_round,
            )
        )
        is not None
    )


def _can_user_delete_curation(
    db: Session, user: UserNew, curation: "CurationNew"
) -> bool:
    """Check if user can delete this curation."""
    if not curation.scope.is_active:
        return False
    # Admin can delete anything
    if user.role == "admin":
        return True

    # Only drafts can be deleted by non-admins
    if curation.status != CurationStatus.DRAFT:
        return False

    # Creator can delete their own drafts
    if curation.created_by == user.id:
        return True

    # Scope admin (admin role within scope) can delete drafts in their scope
    scope_role = _get_user_scope_role(db, user.id, curation.scope_id)
    return scope_role == "admin"


def _check_scope_access(
    db: Session,
    current_user: UserNew,
    scope_id: UUID,
    action: str = "access",
) -> None:
    """
    Check if user has access to the specified scope using ScopePermissionService.
    Raises HTTPException if access denied.
    Uses scope_memberships table for proper scope-specific role checking.
    """
    if current_user.role == "admin":
        return  # Admin bypasses scope checks

    # Use ScopePermissionService to check membership via scope_memberships table
    from app.models import Scope

    scope = db.query(Scope).filter(Scope.id == scope_id).first()
    if not scope:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scope not found",
        )

    if not ScopePermissionService.can_view_scope(db, current_user, scope):
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
    curation_status: CurationStatus | None = Query(
        None, description="Filter by status"
    ),
    curator_id: UUID | None = Query(None, description="Filter by curator"),
    pending_review: bool = Query(
        False,
        description="Only scopes where the caller can review, excluding their own",
    ),
    current_user: UserNew = Depends(get_current_active_user),
) -> CurationListResponse:
    """
    List curations with optional filters.
    RLS automatically filters to user's accessible scopes.
    """
    # Set RLS context for current user
    set_rls_context(db, current_user)

    # Determine scope filtering using scope_memberships
    from app.models import ScopeMembership

    scope_ids = None
    if pending_review:
        scope_ids = ScopePermissionService.get_user_scope_ids(
            db, current_user, ["admin", "reviewer"]
        )
        if scope_id:
            scope_ids = [s for s in scope_ids if s == scope_id]
            scope_id = None
        if not scope_ids:
            return CurationListResponse(curations=[], total=0, skip=skip, limit=limit)
    elif current_user.role != "admin" and not scope_id:
        # Non-admin without specific scope: filter to their scopes from memberships
        memberships = (
            db.query(ScopeMembership.scope_id)
            .filter(
                ScopeMembership.user_id == current_user.id,
                ScopeMembership.is_active,
                ScopeMembership.accepted_at.isnot(None),
            )
            .all()
        )
        scope_ids = [m.scope_id for m in memberships]
        if not scope_ids:
            # User has no scope memberships
            return CurationListResponse(curations=[], total=0, skip=skip, limit=limit)

    # If specific scope requested, verify access via membership
    if scope_id and current_user.role != "admin":
        _check_scope_access(db, current_user, scope_id, "list")

    summaries, total = curation_crud.get_multi_filtered(
        db,
        skip=skip,
        limit=limit,
        scope_id=scope_id,
        scope_ids=scope_ids,
        gene_id=gene_id,
        status=curation_status,
        curator_id=curator_id,
        exclude_creator_id=current_user.id if pending_review else None,
    )

    return CurationListResponse(
        curations=summaries,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{curation_id}", response_model=CurationDetail)
@api_endpoint()
def get_curation(
    curation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> CurationDetail:
    """Get a single curation by ID with expanded relations."""
    # Set RLS context
    set_rls_context(db, current_user)

    curation = curation_crud.get_with_relations(db, curation_id)

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    # Verify scope access using scope_memberships
    if current_user.role != "admin" and not ScopePermissionService.can_view_curation(
        db, current_user, curation
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this scope",
        )

    # If no precuration linked, show the approved one for this gene+scope. set_committed_value
    # attaches it for serialization only: a plain assignment would be flushed as an UPDATE
    # (precuration_id, and a lock_version bump by trigger) on a read.
    if not curation.precuration:
        approved_precuration = precuration_crud.get_approved_for_gene_scope(
            db, curation.gene_id, curation.scope_id
        )
        if approved_precuration:
            set_committed_value(curation, "precuration", approved_precuration)

    # Build response with permission flags
    response = CurationDetail.from_orm_with_relations(curation)

    # Compute user permissions for this curation based on scope-specific roles
    response.can_edit = _can_user_edit_curation(db, current_user, curation)
    response.can_review = _can_user_review_curation(db, current_user, curation)
    # The view hides Approve while this approval waits for others (#430)
    response.has_approved = _has_approved(db, current_user, curation)
    response.can_delete = _can_user_delete_curation(db, current_user, curation)
    if curation.status == CurationStatus.IN_REVIEW:
        required = reviewers_required(WorkflowEngine.workflow_states(db, curation))
        response.approvals_remaining = max(
            0, required - approving_reviewers(db, curation)
        )

    return response


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
    Requires curator or admin role in the target scope.
    """
    # Set RLS context
    set_rls_context(db, current_user)

    # Verify scope access using scope_memberships
    _check_scope_access(db, current_user, curation_in.scope_id, "create")
    require(db, current_user, curation_in.scope_id, EDIT)

    enforce_clingen_point_ranges(
        db, curation_in.workflow_pair_id, curation_in.evidence_data
    )
    try:
        curation = curation_crud.create_curation(
            db,
            obj_in=curation_in,
            user_id=current_user.id,
        )
    except OpenCurationExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(e), "curation_id": str(e.curation_id)},
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except DBAPIError as e:  # require() lets platform admins through; RLS does not
        db.rollback()
        raise_if_rls_denied(
            e,
            "Creating curations here needs an accepted curator membership in this scope",
        )
        raise

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

    # Verify scope access using scope_memberships
    _check_scope_access(db, current_user, curation.scope_id, "update")
    require(db, current_user, curation.scope_id, EDIT)
    _require_active_scope(curation)

    # Check curation is editable
    if curation.status not in [CurationStatus.DRAFT, CurationStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft or rejected curations can be edited",
        )

    enforce_clingen_point_ranges(
        db,
        curation.workflow_pair_id,
        curation_in.evidence_data,
        curation.methodology_version_id,
    )
    updated = curation_crud.update_with_lock(
        db,
        db_obj=curation,
        obj_in=curation_in,
        user_id=current_user.id,
    )

    if updated is None:
        raise _conflict(curation, curation_in.lock_version)

    return Curation.model_validate(updated)


# ========================================
# DRAFT & SUBMIT ENDPOINTS
# ========================================


@router.patch(
    "/{curation_id}/draft",
    response_model=Curation,
    responses={409: {"model": CurationConflictResponse}},
)
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

    require(db, current_user, curation.scope_id, EDIT)
    _require_active_scope(curation)

    # Same rule as PUT: evidence is frozen once submitted (4-eyes), for every role
    if curation.status not in [CurationStatus.DRAFT, CurationStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft or rejected curations can be edited",
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
    if updated is None:
        raise _conflict(curation, draft_in.lock_version)

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

    require(db, current_user, curation.scope_id, EDIT)
    _require_active_scope(curation)

    # Only creator or admin can submit
    if current_user.role != "admin" and curation.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can submit for review",
        )

    # Point ranges and PMIDs: review_guards, in the transition into review
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
        raise _conflict(curation, submit_in.lock_version)

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

    # Verify scope access using scope_memberships
    _check_scope_access(db, current_user, curation.scope_id, "calculate score for")

    result = curation_crud.calculate_score(db, curation)
    result.trace = result.breakdown.get("trace")
    return result


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

    # Verify scope access using scope_memberships
    _check_scope_access(db, current_user, curation.scope_id, "delete")
    require(db, current_user, curation.scope_id, EDIT)
    _require_active_scope(curation)

    # Only allow deletion of drafts (or by admin)
    if curation.status != CurationStatus.DRAFT and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only draft curations can be deleted",
        )
    if not _can_user_delete_curation(db, current_user, curation):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator or a scope admin can delete this curation",
        )

    curation_crud.soft_delete(db, db_obj=curation, user_id=current_user.id)
