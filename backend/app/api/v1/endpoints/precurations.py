"""
Precuration API endpoints.
Full CRUD with RLS integration and scope-based access control.
Follows patterns from curations.py.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.core.capabilities import EDIT, REVIEW, require
from app.core.constants import (
    DEFAULT_SKIP,
    PRECURATIONS_DEFAULT_LIMIT,
    PRECURATIONS_MAX_LIMIT,
)
from app.core.database import get_db, raise_if_rls_denied
from app.core.deps import get_current_active_user, set_rls_context
from app.core.logging import api_endpoint, get_logger
from app.crud.precuration import precuration_crud
from app.crud.precuration_required import (
    MissingRequiredFieldsError,
    field_contract,
    missing_required_fields,
)
from app.crud.scope_visibility import scope_id_for
from app.models import CurationStatus, PrecurationNew, Scope, UserNew
from app.schemas.curation import collapse_warnings
from app.schemas.precuration import (
    Precuration,
    PrecurationApprovalResult,
    PrecurationConflictResponse,
    PrecurationCreate,
    PrecurationCreated,
    PrecurationDraftResult,
    PrecurationDraftSave,
    PrecurationListResponse,
    PrecurationReject,
    PrecurationSubmit,
    PrecurationSubmitted,
    PrecurationUpdate,
)
from app.schemas.scope import SCOPE_NAME
from app.services.evidence_ids import InvalidEvidenceError, unprocessable
from app.services.review_assignment import assigned_reviewer, submit_reviewer
from app.services.review_guards import item_definition
from app.services.scope_permissions import ScopePermissionService

router = APIRouter()
logger = get_logger(__name__)


# ========================================
# HELPER FUNCTIONS
# ========================================


def _check_scope_access(
    db: Session,
    current_user: UserNew,
    scope_id: UUID,
) -> None:
    """
    Check if user has access to the specified scope.
    Uses ScopePermissionService for centralized permission logic.
    """
    if not ScopePermissionService.has_scope_access(db, current_user, scope_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this scope",
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
    scope_name: str | None = Query(None, description=SCOPE_NAME),
    gene_id: UUID | None = Query(None, description="Filter by gene"),
    precuration_status: CurationStatus | None = Query(
        None, description="Filter by status"
    ),
    pending_review: bool = Query(
        False,
        description="Only scopes where the caller can review, excluding their own",
    ),
    current_user: UserNew = Depends(get_current_active_user),
) -> PrecurationListResponse:
    """
    List precurations with optional filters.
    RLS automatically filters to user's accessible scopes.
    """
    # CRITICAL: Set RLS context for current user
    set_rls_context(db, current_user)
    scope_id = scope_id_for(db, current_user.id, scope_id, scope_name)

    # Determine scope filtering
    scope_ids = None
    if pending_review:
        scope_ids = ScopePermissionService.get_user_scope_ids(
            db, current_user, ["admin", "reviewer"]
        )
        if scope_id:
            scope_ids = [s for s in scope_ids if s == scope_id]
            scope_id = None
        if not scope_ids:
            return PrecurationListResponse(
                precurations=[], total=0, skip=skip, limit=limit
            )
    elif not scope_id:
        scope_ids = ScopePermissionService.get_user_scope_ids(db, current_user)
        if not scope_ids:
            return PrecurationListResponse(
                precurations=[], total=0, skip=skip, limit=limit
            )

    # If specific scope requested, verify access
    if scope_id:
        _check_scope_access(db, current_user, scope_id)

    summaries, total = precuration_crud.get_multi_filtered(
        db,
        skip=skip,
        limit=limit,
        scope_id=scope_id,
        scope_ids=scope_ids,
        gene_id=gene_id,
        status=precuration_status,
        exclude_creator_id=current_user.id if pending_review else None,
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
    _check_scope_access(db, current_user, precuration.scope_id)

    # Enrich with curation count
    curation_count = precuration_crud.has_associated_curations(db, precuration.id)
    result = Precuration.model_validate(precuration)
    result.curation_count = curation_count
    rejected_by = (precuration.computed_fields or {}).get("rejected_by")
    reviewer = db.get(UserNew, UUID(rejected_by)) if rejected_by else None
    if reviewer:
        result.rejected_by_name = reviewer.name or reviewer.email
    return result


# ========================================
# CREATE ENDPOINT
# ========================================


@router.post(
    "/", response_model=PrecurationCreated, status_code=status.HTTP_201_CREATED
)
@api_endpoint()
def create_precuration(
    precuration_in: PrecurationCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> PrecurationCreated:
    """
    Create a new precuration. The result lists the schema's required fields with their
    allowed values (required_fields), so the draft can be filled without guessing.
    Requires curator or admin access to the target scope.
    Idempotent per creator: an open draft for the same gene and scope is returned
    (200) instead of inserting another, so a retry after a lost response is safe.
    """
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    scope_id = scope_id_for(
        db, current_user.id, precuration_in.scope_id, precuration_in.scope_name
    )
    if scope_id is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Send scope_id or scope_name"
        )
    precuration_in = precuration_in.model_copy(update={"scope_id": scope_id})
    require(db, current_user, scope_id, EDIT)

    if precuration_in.precuration_schema_id is None:
        scope = db.get(Scope, scope_id)
        pair = scope.default_workflow_pair if scope else None
        if pair is None or pair.precuration_schema_id is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "precuration_schema_id is required: the scope's workflow pair has none",
            )
        precuration_in = precuration_in.model_copy(
            update={"precuration_schema_id": pair.precuration_schema_id}
        )

    existing = precuration_crud.get_open_draft(
        db,
        gene_id=precuration_in.gene_id,
        scope_id=scope_id,
        user_id=current_user.id,
    )
    if existing:
        response.status_code = status.HTTP_200_OK
        return _created(db, existing)

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
    except DBAPIError as e:  # require() lets platform admins through; RLS does not
        db.rollback()
        raise_if_rls_denied(
            e,
            "Creating precurations here needs an accepted curator membership in this scope",
        )
        raise

    return _created(db, precuration)


def _created(db: Session, precuration: PrecurationNew) -> PrecurationCreated:
    definition = item_definition(db, precuration)
    fields = definition.get("field_definitions")
    evidence = precuration.evidence_data or {}
    missing = missing_required_fields(
        fields, evidence, definition.get("validation_rules")
    )
    return PrecurationCreated(
        **Precuration.model_validate(precuration).model_dump(),
        required_fields=field_contract(fields, evidence, missing),
    )


def _conflict(precuration: PrecurationNew, sent: int) -> HTTPException:
    """409 carrying the current version and state (the failed UPDATE rolled back, so this reads
    what the other tab saved)."""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "error": "Concurrent modification detected",
            "current_lock_version": precuration.lock_version,
            "your_lock_version": sent,
            "current_state": precuration.evidence_data,
        },
    )


# ========================================
# UPDATE ENDPOINT
# ========================================


@router.put(
    "/{precuration_id}",
    response_model=PrecurationDraftResult,
    responses={409: {"model": PrecurationConflictResponse}},
)
@api_endpoint()
def update_precuration(
    precuration_id: UUID,
    precuration_in: PrecurationUpdate,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> PrecurationDraftResult:
    """Update a draft or rejected precuration. evidence_data replaces the stored evidence
    entirely unless merge=true (RFC 7396 merge patch; arrays are replaced whole).
    `warnings` names bad or unknown IDs and arrays a merge shortened. 409 if
    lock_version is stale."""
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    precuration = precuration_crud.get(db, precuration_id)

    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )

    # Verify scope access
    require(db, current_user, precuration.scope_id, EDIT)

    # Check precuration is editable
    if precuration.status not in [CurationStatus.DRAFT, CurationStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft or rejected precurations can be edited",
        )

    saved = precuration_crud.update_with_lock(
        db,
        db_obj=precuration,
        evidence_data=precuration_in.evidence_data,
        lock_version=precuration_in.lock_version,
        user_id=current_user.id,
        merge=bool(precuration_in.merge),
    )
    if saved is None:
        raise _conflict(precuration, precuration_in.lock_version)
    result = PrecurationDraftResult.model_validate(saved[0])
    result.warnings = collapse_warnings(saved[1])
    return result


# ========================================
# DRAFT & SUBMIT ENDPOINTS
# ========================================


@router.patch(
    "/{precuration_id}/draft",
    response_model=PrecurationDraftResult,
    responses={409: {"model": PrecurationConflictResponse}},
)
@api_endpoint()
def save_draft(
    precuration_id: UUID,
    draft_data: PrecurationDraftSave,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> PrecurationDraftResult:
    """Save a draft (autosave): never refused for its content. evidence_data replaces the
    stored evidence entirely unless merge=true (RFC 7396 merge patch: objects merge, null
    deletes a key, arrays replace whole). `warnings` names each field path whose PMID,
    MONDO, OMIM or HPO ID is malformed, unknown or unverified. 409 if lock_version is
    stale, merge or not."""
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    precuration = precuration_crud.get(db, precuration_id)

    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )

    require(db, current_user, precuration.scope_id, EDIT)

    # Only creator or admin can save drafts
    if current_user.role != "admin" and precuration.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can save drafts",
        )

    saved = precuration_crud.save_draft(
        db,
        db_obj=precuration,
        evidence_data=draft_data.evidence_data,
        lock_version=draft_data.lock_version,
        user_id=current_user.id,
        merge=bool(draft_data.merge),
    )
    if saved is None:
        raise _conflict(precuration, draft_data.lock_version)
    result = PrecurationDraftResult.model_validate(saved[0])
    result.warnings = collapse_warnings(saved[1])
    return result


@router.post(
    "/{precuration_id}/submit",
    response_model=PrecurationSubmitted,
    responses={409: {"model": PrecurationConflictResponse}},
)
@api_endpoint()
def submit_precuration(
    precuration_id: UUID,
    submit_in: PrecurationSubmit,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> PrecurationSubmitted:
    """Submit for peer review. 422 names each field path that fails the schema or holds a
    malformed PMID, MONDO, OMIM or HPO ID."""
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    precuration = precuration_crud.get(db, precuration_id)

    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )

    require(db, current_user, precuration.scope_id, EDIT)

    # Only creator or admin can submit
    if current_user.role != "admin" and precuration.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can submit for review",
        )

    try:
        reviewer_id = submit_reviewer(db, precuration.scope_id, submit_in)
        submitted = precuration_crud.submit_for_review(
            db,
            db_obj=precuration,
            submit_data=submit_in.model_copy(update={"reviewer_id": reviewer_id}),
            user_id=current_user.id,
        )
    except MissingRequiredFieldsError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": str(e),
                "fields": e.fields,
                "required": e.contract,
                "schema": f"get_curation_schema(schema_id="
                f"{precuration.precuration_schema_id}, compact=true)",
            },
        ) from e
    except InvalidEvidenceError as e:
        raise unprocessable(e) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    if submitted is None:
        raise _conflict(precuration, submit_in.lock_version)

    return PrecurationSubmitted(
        **Precuration.model_validate(submitted).model_dump(),
        assigned_reviewer=assigned_reviewer(db, reviewer_id),
    )


# ========================================
# COMPLETE ENDPOINT (submits for review)
# ========================================


@router.post(
    "/{precuration_id}/complete",
    response_model=Precuration,
    responses={409: {"model": PrecurationConflictResponse}},
)
@api_endpoint()
def complete_precuration(
    precuration_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Precuration:
    """Submit the precuration for review at its current version, like /submit.

    D1: nobody approves their own work (admins included), so there is no shortcut past review.
    """
    set_rls_context(db, current_user)
    precuration = precuration_crud.get(db, precuration_id)
    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )
    return submit_precuration(
        precuration_id,
        PrecurationSubmit(lock_version=precuration.lock_version),
        db,
        current_user,
    )


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

    # 4-eyes first, so the creator learns why even without a reviewer role (#393)
    if precuration.created_by == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot approve your own precuration (4-eyes principle)",
        )

    # Verify scope access with reviewer role
    require(db, current_user, precuration.scope_id, REVIEW)

    try:
        result = precuration_crud.approve_and_create_curation(
            db,
            db_obj=precuration,
            approver_id=current_user.id,
            create_curation=True,
        )
    except (StaleDataError, DBAPIError) as e:
        db.rollback()
        raise_if_rls_denied(e, "Not authorized to approve this precuration")
        raise
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
    rejection_data: PrecurationReject,
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
    require(db, current_user, precuration.scope_id, REVIEW)

    try:
        rejected = precuration_crud.reject(
            db,
            db_obj=precuration,
            user_id=current_user.id,
            reason=rejection_data.reason,
        )
    except (StaleDataError, DBAPIError) as e:
        db.rollback()
        raise_if_rls_denied(e, "Not authorized to reject this precuration")
        raise

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
    """Archive a precuration. Linked curations prevent deletion with HTTP 409."""
    # CRITICAL: Set RLS context
    set_rls_context(db, current_user)

    precuration = precuration_crud.get(db, precuration_id)

    if not precuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Precuration not found",
        )

    # Verify scope access
    require(db, current_user, precuration.scope_id, EDIT)

    # Only allow deletion of drafts (or by admin)
    if precuration.status != CurationStatus.DRAFT and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only draft precurations can be deleted",
        )

    try:
        precuration_crud.soft_delete(db, db_obj=precuration, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
