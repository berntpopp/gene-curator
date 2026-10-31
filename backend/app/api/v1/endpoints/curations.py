"""
Curation API endpoints.
Full CRUD with RLS integration and scope-based access control.
Follows patterns from gene_assignments.py, workflow.py, and genes.py.
"""

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import InstrumentedAttribute, Session
from sqlalchemy.orm.attributes import set_committed_value

from app.api.v1.endpoints.review_comments import curation_diff
from app.core.capabilities import EDIT, require, require_active_scope
from app.core.constants import (
    CURATIONS_DEFAULT_LIMIT,
    CURATIONS_MAX_LIMIT,
    DEFAULT_SKIP,
)
from app.core.database import get_db, raise_if_rls_denied
from app.core.deps import get_current_active_user, set_rls_context
from app.core.logging import api_endpoint, get_logger
from app.crud.curation import (
    EntityRequiredError,
    OpenCurationExistsError,
    curation_crud,
    merge_patch,
)
from app.crud.curator_classification import classification_choices
from app.crud.precuration import precuration_crud
from app.crud.review_round import (
    approving_reviewers,
    corrected_by,
    earlier_feedback,
    pending_reviews,
    reviewers_required,
)
from app.crud.scope_visibility import scope_id_for
from app.crud.workflow_engine import WorkflowEngine, workflow_engine
from app.models import (
    CurationNew,
    CurationStatus,
    Gene,
    Scope,
    ScopeMembership,
    UserNew,
)
from app.schemas.curation import (
    ClassificationChoice,
    Curation,
    CurationConflictResponse,
    CurationCreate,
    CurationDetail,
    CurationDraftResult,
    CurationDraftSave,
    CurationListResponse,
    CurationReviewRead,
    CurationScoreResponse,
    CurationSubmit,
    CurationSubmitResult,
    CurationUpdate,
    CurationWriteResult,
    capped,
    collapse_warnings,
    lean_scores,
)
from app.schemas.scope import SCOPE_NAME
from app.scoring.point_limits import enforce_clingen_point_ranges, scoring_configuration
from app.services.curation_access import (
    _can_user_delete_curation,
    _can_user_edit_curation,
    _can_user_review_curation,
    _check_scope_access,
    _has_approved,
)
from app.services.evidence_ids import InvalidEvidenceError, unprocessable
from app.services.llm_runs import queue_on_submit
from app.services.review_assignment import assigned_reviewer, submit_reviewer
from app.services.scope_permissions import ScopePermissionService

router = APIRouter()
logger = get_logger(__name__)

_FULL_WRITE = Query(
    False, description="Return the full curation, not the concise result"
)
_FULL_TRACE = Query(False, description="Include the full score trace")


# ========================================
# HELPER FUNCTIONS
# ========================================


def _conflict(
    curation: CurationNew, sent: int, mine: dict[str, Any] | None = None
) -> HTTPException:
    """409 with the current version and state (the failed UPDATE rolled back, so this reads what
    the other tab saved), who saved it, and the top-level evidence keys that differ from yours."""
    theirs = curation.evidence_data or {}
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "error": "Concurrent modification detected",
            "current_lock_version": curation.lock_version,
            "your_lock_version": sent,
            "current_state": curation.evidence_data,
            "updated_by_name": getattr(curation.updater, "name", None),
            "updated_at": curation.updated_at.isoformat(),
            "changed_keys": None
            if mine is None
            else sorted(k for k in {*theirs, *mine} if theirs.get(k) != mine.get(k)),
        },
    )


def _mine(
    curation: CurationNew, sent: CurationUpdate | CurationDraftSave
) -> dict[str, Any] | None:
    """The evidence the caller meant: a merge patch applies to the current state."""
    if sent.merge and sent.evidence_data is not None:
        return cast(
            dict[str, Any], merge_patch(curation.evidence_data, sent.evidence_data)
        )
    return sent.evidence_data


# ========================================
# LIST & READ ENDPOINTS
# ========================================


def _id_for_name(
    db: Session, col: InstrumentedAttribute[str], name: str, given: UUID | None
) -> UUID | None:
    """Id whose name matches case-insensitively; None if unknown or not the given id."""
    found = db.scalar(select(col.class_.id).where(func.lower(col) == name.lower()))
    return found if given in (None, found) else None


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
    gene_symbol: str | None = Query(None, description="Filter by gene symbol"),
    scope_name: str | None = Query(None, description=SCOPE_NAME),
    pending_review: bool = Query(
        False,
        description="Only scopes where the caller can review, excluding their own",
    ),
    current_user: UserNew = Depends(get_current_active_user),
) -> CurationListResponse:
    """List curations, filtered by ids or names; RLS limits them to the caller's scopes."""
    set_rls_context(db, current_user)
    empty = CurationListResponse(curations=[], total=0, skip=skip, limit=limit)
    if gene_symbol and not (
        gene_id := _id_for_name(db, Gene.approved_symbol, gene_symbol, gene_id)
    ):
        return empty
    scope_id = scope_id_for(db, current_user.id, scope_id, scope_name)

    scope_ids = None
    if pending_review:
        scope_ids = ScopePermissionService.get_user_scope_ids(
            db, current_user, ["admin", "reviewer"]
        )
        if scope_id:
            scope_ids = [s for s in scope_ids if s == scope_id]
            scope_id = None
        if not scope_ids:
            return empty
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
        if not scope_ids:  # User has no scope memberships
            return empty

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
        curations=summaries, total=total, skip=skip, limit=limit
    )


@router.get("/{curation_id}", response_model=CurationDetail)
@api_endpoint()
def get_curation(
    curation_id: UUID,
    detail: bool = _FULL_TRACE,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> CurationDetail:
    """Get a single curation by ID with expanded relations."""
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
    if not detail:  # totals, excluded rows and warnings; the trace on request
        response.computed_scores = {
            k: v for k, v in response.computed_scores.items() if k != "trace"
        }

    # Compute user permissions for this curation based on scope-specific roles
    response.can_edit = _can_user_edit_curation(db, current_user, curation)
    response.can_review = _can_user_review_curation(db, current_user, curation)
    response.classification_choices = [
        ClassificationChoice(**c)
        for c in classification_choices(
            scoring_configuration(
                db, curation.workflow_pair_id, curation.methodology_version_id
            )
        )
    ]
    # The view hides Approve while this approval waits for others (#430)
    response.has_approved = _has_approved(db, current_user, curation)
    response.corrected_disease = corrected_by(db, curation.id, current_user.id)
    response.can_delete = _can_user_delete_curation(db, current_user, curation)
    if curation.status == CurationStatus.IN_REVIEW:
        required = reviewers_required(WorkflowEngine.workflow_states(db, curation))
        response.approvals_remaining = max(
            0, required - approving_reviewers(db, curation)
        )
        response.assigned_reviewers = [
            r
            for p in pending_reviews(db, curation.id)
            if (r := assigned_reviewer(db, p["reviewer_id"]))
        ]

    return response


@router.get("/{curation_id}/review", response_model=CurationReviewRead)
@api_endpoint()
def read_curation_for_review(
    curation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> CurationReviewRead:
    """Reviewer read in one call: the curation with evidence and score trace (excluded
    rows with reasons), warnings, workflow state with blocked moves, the evidence diff (none
    on a first submission) and, on a resubmission, the earlier round's feedback."""
    curation = get_curation(curation_id, True, db, current_user)
    scores = lean_scores(curation.computed_scores)
    warnings = scores.pop("warnings", None) or []  # listed once, at the top level
    curation.computed_scores = scores
    diff = curation_diff(curation_id, None, db, current_user)
    reviews, comments = earlier_feedback(
        db, cast(CurationNew, db.get(CurationNew, curation_id))
    )
    first = diff.baseline is None and not reviews  # nothing earlier to compare
    return CurationReviewRead(
        curation=curation,
        warnings=[*warnings, *capped(scores.get("trace"))],
        workflow=workflow_engine.get_workflow_state(
            db, curation_id, "curation", current_user.id
        ),
        first_submission=first,
        diff=None if first else diff,
        previous_reviews=reviews,
        open_item_comments=comments,
    )


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
    """Create a curation (curator or admin of the scope) for one gene-disease-MOI entity.
    Needs an approved precuration for the gene and scope unless one is active; the approval
    already opens a draft curation (list_curations), and this fails (409) while the entity
    has an open one. precuration_id picks the entity; without it a re-curation inherits
    the active curation's entity, and a gene with several entities in the scope is a 422."""
    set_rls_context(db, current_user)

    # Verify scope access using scope_memberships
    _check_scope_access(db, current_user, curation_in.scope_id, "create")
    require(db, current_user, curation_in.scope_id, EDIT)
    require_active_scope(db.get(Scope, curation_in.scope_id))

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
    except EntityRequiredError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
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
    response_model=Curation | CurationWriteResult,
    responses={409: {"model": CurationConflictResponse}},
)
@api_endpoint()
def update_curation(
    curation_id: UUID,
    curation_in: CurationUpdate,
    detail: bool = _FULL_WRITE,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Curation | CurationWriteResult:
    """Update a draft or rejected curation. evidence_data replaces the stored evidence
    entirely unless merge=true (RFC 7396 merge patch). 409 if lock_version is stale."""
    set_rls_context(db, current_user)

    curation = curation_crud.get(db, curation_id)

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    _check_scope_access(db, current_user, curation.scope_id, "update")
    require(db, current_user, curation.scope_id, EDIT)
    require_active_scope(curation.scope)

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
        raise _conflict(
            curation, curation_in.lock_version, _mine(curation, curation_in)
        )

    return (
        Curation.model_validate(updated) if detail else CurationWriteResult.of(updated)
    )


# ========================================
# DRAFT & SUBMIT ENDPOINTS
# ========================================


@router.patch(
    "/{curation_id}/draft",
    response_model=CurationDraftResult | CurationWriteResult,
    responses={409: {"model": CurationConflictResponse}},
)
@api_endpoint()
def save_draft(
    curation_id: UUID,
    draft_in: CurationDraftSave,
    detail: bool = _FULL_WRITE,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> CurationDraftResult | CurationWriteResult:
    """Save a draft (autosave): never refused for its content. evidence_data replaces the
    stored evidence entirely unless merge=true (RFC 7396 merge patch: objects merge, null
    deletes a key, arrays replace whole). `warnings` names each field path whose PMID,
    MONDO, OMIM or HPO ID is malformed, unknown or unverified; rows with a malformed or
    unknown PMID score 0 points. 409 if lock_version is stale, merge or not."""
    set_rls_context(db, current_user)

    curation = curation_crud.get(db, curation_id)

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    require(db, current_user, curation.scope_id, EDIT)
    require_active_scope(curation.scope)

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

    saved = curation_crud.save_draft(
        db, db_obj=curation, draft_data=draft_in, user_id=current_user.id
    )
    if saved is None:
        raise _conflict(curation, draft_in.lock_version, _mine(curation, draft_in))
    if not detail:
        return CurationWriteResult.of(saved[0])
    result = CurationDraftResult.model_validate(saved[0])
    result.warnings = collapse_warnings(saved[1])
    return result


@router.post(
    "/{curation_id}/submit",
    response_model=Curation | CurationSubmitResult,
    responses={409: {"model": CurationConflictResponse}},
)
@api_endpoint()
def submit_curation(
    curation_id: UUID,
    submit_in: CurationSubmit,
    detail: bool = _FULL_WRITE,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Curation | CurationSubmitResult:
    """Submit for peer review. 422 names each field path that fails the schema or holds a
    malformed PMID, MONDO, OMIM or HPO ID, or an ID PubMed or the ontology does not know."""
    set_rls_context(db, current_user)

    curation = curation_crud.get(db, curation_id)

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    require(db, current_user, curation.scope_id, EDIT)
    require_active_scope(curation.scope)

    # Only creator or admin can submit
    if current_user.role != "admin" and curation.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can submit for review",
        )

    # Point ranges and PMIDs: review_guards, in the transition into review
    try:
        reviewer_id = submit_reviewer(db, curation.scope_id, submit_in)
        submitted = curation_crud.submit_for_review(
            db,
            db_obj=curation,
            submit_data=submit_in.model_copy(update={"reviewer_id": reviewer_id}),
            user_id=current_user.id,
        )
    except InvalidEvidenceError as e:
        raise unprocessable(e) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    if submitted is None:
        raise _conflict(curation, submit_in.lock_version)
    queue_on_submit(db, submitted)  # #464: opt-in LLM second view; never fails submit

    if detail:
        return Curation.model_validate(submitted)
    return CurationSubmitResult(
        **CurationWriteResult.of(submitted).model_dump(),
        assigned_reviewer=assigned_reviewer(db, reviewer_id),
    )


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
    """Preview the score. Rows with points but no PMID, an unknown PMID or (case-level) no
    real variant or a score_status other than score score 0 points and are listed in
    breakdown.excluded with the reason."""
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
    result.trace = result.breakdown.pop("trace", None)  # sent once, at the top
    return result


@router.delete("/{curation_id}", status_code=status.HTTP_204_NO_CONTENT)
@api_endpoint()
def delete_curation(
    curation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> None:
    """Soft delete a curation (archive)."""
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
    require_active_scope(curation.scope)

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
