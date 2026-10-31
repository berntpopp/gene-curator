"""
Scope management API endpoints (RLS-based multi-tenant architecture).

This module provides scope management endpoints using PostgreSQL Row-Level Security
for secure multi-tenant data access.

Key Features:
- RLS-enforced permission checks
- Scope membership integration
- Automatic scope admin assignment on creation
- Capability checks (core.capabilities) per scope

Created: 2025-10-13
Author: Claude Code (Automated Implementation)
"""

from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core import deps
from app.core.async_bridge import run_blocking
from app.core.capabilities import (
    CREATE_GENE,
    EDIT,
    MANAGE_SCOPE,
    PLATFORM,
    VIEW,
    WORKFLOW_ASSIGN,
    audit,
    require,
    require_active_scope,
)
from app.core.database import get_db
from app.core.logging import get_logger
from app.crud.gene import gene_crud
from app.crud.gene_assignment import gene_assignment_crud
from app.crud.scope import scope_crud
from app.crud.scope_counts import get_counts_for_scopes
from app.crud.scope_membership import scope_membership_crud
from app.crud.scope_visibility import scope_id_for
from app.models import CurationSchema, Gene, Scope, User, WorkflowPair
from app.models.llm import ScopeLLMSettings
from app.schemas.gene import GeneCreate
from app.schemas.gene_assignment import (
    GeneAddStatus,
    GeneScopeAssignmentCreate,
    ScopeGeneAdded,
    ScopeGenesAdd,
    ScopeGenesAdded,
)
from app.schemas.scope import (
    Scope as ScopeResponse,
    ScopeCreate,
    ScopeListItem,
    ScopeListStats,
    ScopeStatistics,
    ScopeUpdate,
    ScopeWithStats,
    ScopeWorkflowPairs,
)
from app.services.gene_resolver import resolve_genes
from app.services.gene_verification import verify_rows

logger = get_logger(__name__)

router = APIRouter()

_DETAIL_FIELDS = (
    "description",
    "institution",
    "is_public",
    "scope_config",
    "is_active",
    "created_at",
    "updated_at",
    "created_by",
)


@router.post("/", response_model=ScopeResponse, status_code=status.HTTP_201_CREATED)
def create_scope(
    *,
    db: Session = Depends(get_db),
    scope_in: ScopeCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Scope:
    """
    Create a new scope.

    Any authenticated user can create a scope and automatically becomes an admin
    of that scope. This follows GitHub's model where anyone can create an organization.
    Without default_workflow_pair_id the scope gets the pair marked is_default=true
    in get_workflow_pairs.

    Args:
        db: Database session
        scope_in: Scope creation data
        current_user: Current authenticated user

    Returns:
        Created Scope object with creator as scope admin

    Raises:
        HTTPException 400: Scope name already exists
    """
    # Set RLS context
    deps.set_rls_context(db, current_user)

    # Check if scope name already exists
    existing = scope_crud.get_by_name(db, name=scope_in.name)
    if existing:
        logger.warning(
            "Scope creation failed: name already exists",
            scope_name=scope_in.name,
            existing_scope_id=str(existing.id),
            user_id=str(current_user.id),
            user_email=current_user.email,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scope with name '{scope_in.name}' already exists. Please choose a different name.",
        )

    if scope_in.default_workflow_pair_id is None:
        pair = db.scalar(select(WorkflowPair).where(WorkflowPair.is_default))
    else:
        pair = db.get(WorkflowPair, scope_in.default_workflow_pair_id)
    if not pair or not pair.is_active or pair.owner_scope_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow pair not found, inactive or owned by a scope",
        )

    scope_in.default_workflow_pair_id = pair.id
    scope = scope_crud.create_with_owner(db, obj_in=scope_in, owner_id=current_user.id)

    logger.debug(
        "Scope entity created, now creating admin membership",
        scope_id=str(scope.id),
        scope_name=scope.name,
        creator_id=str(current_user.id),
    )

    # Automatically create accepted scope membership with admin role.
    # On failure remove the scope again: an ownerless scope must not survive.
    try:
        membership = scope_membership_crud.create_owner_membership(
            db, scope_id=scope.id, owner_id=current_user.id
        )
    except Exception:
        db.rollback()
        db.delete(scope)
        db.commit()
        logger.error(
            "Failed to create owner membership; scope rolled back",
            scope_id=str(scope.id),
            user_id=str(current_user.id),
        )
        raise

    logger.info(
        "Scope membership created",
        membership_id=str(membership.id),
        scope_id=str(scope.id),
        user_id=str(current_user.id),
        role=membership.role,
    )

    logger.info(
        "Scope created successfully",
        scope_id=str(scope.id),
        scope_name=scope.name,
        creator_id=str(current_user.id),
        creator_username=current_user.name,
    )

    return scope


@router.post("/genes", response_model=ScopeGenesAdded)
def add_genes_to_scope(
    *,
    db: Session = Depends(get_db),
    body: ScopeGenesAdd,
    current_user: User = Depends(deps.get_current_active_user),
) -> ScopeGenesAdded:
    """Add genes to a scope by HGNC symbol in one call: resolves each symbol (also previous
    symbols, aliases, HGNC ids), creates genes missing locally from HGNC, assigns them to the
    scope and reports per symbol. Scope curators and admins."""
    deps.set_rls_context(db, current_user)
    scope_id = scope_id_for(db, current_user.id, body.scope_id, body.scope_name)
    if scope_id is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Send scope_id or scope_name"
        )
    require(db, current_user, scope_id, EDIT)
    require_active_scope(db.get(Scope, scope_id))
    resolved = run_blocking(resolve_genes(db, body.symbols)).items
    hits = {i.index: i.candidates[0] for i in resolved if i.status == "resolved"}
    missing = {c.hgnc_id: c.symbol for c in hits.values() if c.gene_id is None}
    problems: dict[str, str] = {}  # hgnc_id -> why no gene row was created
    if missing:
        require(db, current_user, scope_id, CREATE_GENE)
        rows, unverified = verify_rows(
            db, [GeneCreate(hgnc_id=h, approved_symbol=s) for h, s in missing.items()]
        )
        created = gene_crud.bulk_create(db, genes_data=rows, owner_id=current_user.id)
        problems = {e["hgnc_id"]: e["error"] for e in unverified + created["errors"]}
    ids = dict(
        db.execute(
            select(Gene.hgnc_id, Gene.id).where(
                Gene.hgnc_id.in_({c.hgnc_id for c in hits.values()})
            )
        ).all()
    )
    items = []
    for item in resolved:
        hit = hits.get(item.index)
        if hit is None:
            timed_out = item.reason == "lookup_timeout"
            items.append(
                ScopeGeneAdded(
                    input=item.input,
                    status="upstream_unavailable"
                    if timed_out
                    else "ambiguous"
                    if item.status == "ambiguous"
                    else "not_found",
                    candidates=item.candidates,
                    reason="HGNC lookup timed out; retry" if timed_out else item.reason,
                )
            )
            continue
        gene_id = ids.get(hit.hgnc_id)
        problem = None if gene_id else problems.get(hit.hgnc_id, "Gene not created")
        state: GeneAddStatus
        if gene_id is None:
            state = (
                "upstream_unavailable" if "timed out" in str(problem) else "not_found"
            )
        elif _assign(db, gene_id, scope_id, current_user.id):
            state = "added"
        else:
            state = "already_in_scope"
        items.append(
            ScopeGeneAdded(
                input=item.input,
                status=state,
                gene_id=gene_id,
                symbol=hit.symbol,
                hgnc_id=hit.hgnc_id,
                created=state == "added" and hit.hgnc_id in missing,
                reason=problem,
            )
        )
    db.commit()
    return ScopeGenesAdded(
        scope_id=scope_id, added=sum(i.status == "added" for i in items), items=items
    )


def _assign(db: Session, gene_id: UUID, scope_id: UUID, user_id: UUID) -> bool:
    """Assign one gene; False when it is already active in the scope."""
    try:
        gene_assignment_crud.create_assignment(
            db,
            obj_in=GeneScopeAssignmentCreate(gene_id=gene_id, scope_id=scope_id),
            assigned_by=user_id,
            commit=False,
        )
    except ValueError:
        return False
    return True


@router.get("/", response_model=list[ScopeListItem], response_model_exclude_unset=True)
def list_scopes(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        50, ge=1, le=1000, description="Maximum number of records to return"
    ),
    active_only: bool = Query(True, description="Filter for active scopes only"),
    name: str | None = Query(
        None, description="Case-insensitive part of the scope name or display name"
    ),
    detail: bool = Query(
        False, description="Full scope fields (config, description, timestamps)"
    ),
) -> list[ScopeListItem]:
    """
    List scopes the current user has access to with gene and member counts.

    Returns scopes filtered by RLS policies:
    - Application admins see all scopes
    - Regular users see scopes they are members of

    Args:
        db: Database session
        current_user: Current authenticated user
        skip: Pagination offset
        limit: Maximum results per page
        active_only: Filter for active scopes

    Returns:
        List of scopes the user has access to with counts
    """
    # Set RLS context - this will filter scopes automatically
    deps.set_rls_context(db, current_user)

    # Caller's accepted membership role per scope (admins may have none)
    user_scopes = scope_membership_crud.get_user_scopes(db, user_id=current_user.id)
    roles = {scope.id: getattr(m.role, "value", m.role) for scope, m in user_scopes}
    needle = name.lower() if name else None

    def matches(scope: Scope) -> bool:
        return (not active_only or scope.is_active) and (
            needle is None
            or needle in scope.name.lower()
            or needle in scope.display_name.lower()
        )

    if current_user.role.value == "admin":  # application admins see ALL scopes
        stmt = select(Scope).order_by(Scope.name, Scope.id)  # stable pages
        if active_only:
            stmt = stmt.where(Scope.is_active)
        if needle:
            pattern = f"%{needle}%"
            stmt = stmt.where(
                Scope.name.ilike(pattern) | Scope.display_name.ilike(pattern)
            )
        page = list(db.scalars(stmt.offset(skip).limit(limit)).all())
    else:
        scopes = [scope for scope, _ in user_scopes]
        # A non-member may open an active public scope (#484): list it too, with no role
        scopes += db.scalars(
            select(Scope)
            .where(Scope.is_public, Scope.is_active, Scope.id.notin_(list(roles)))
            .order_by(Scope.name)
        ).all()
        page = [s for s in scopes if matches(s)][skip : skip + limit]

    counts = get_counts_for_scopes(db, [sc.id for sc in page])
    # RLS (065) shows settings to the scope's reviewers only, so others read false
    ai_on = set(
        db.scalars(
            select(ScopeLLMSettings.scope_id).where(
                ScopeLLMSettings.scope_id.in_([sc.id for sc in page]),
                ScopeLLMSettings.enabled,
            )
        )
    )
    result = []
    for scope in page:
        c = counts[scope.id]
        extra = {f: getattr(scope, f) for f in _DETAIL_FIELDS} if detail else {}
        result.append(
            ScopeListItem(
                id=scope.id,
                name=scope.name,
                display_name=scope.display_name,
                default_workflow_pair_id=scope.default_workflow_pair_id,
                stats=ScopeListStats(
                    total_genes=c["total"],
                    completed_genes=c["completed"],
                    member_count=c["members"],
                ),
                user_role=roles.get(scope.id),
                llm_second_view=scope.id in ai_on,
                **extra,
            )
        )

    logger.debug(
        "Listed scopes for user",
        user_id=str(current_user.id),
        user_role=current_user.role.value,
        returned_scopes=len(result),
        skip=skip,
        limit=limit,
    )

    return result


@router.get("/{scope_id}", response_model=ScopeWithStats)
def get_scope_details(
    *,
    db: Session = Depends(get_db),
    scope_id: UUID,
    current_user: User = Depends(deps.get_current_active_user),
) -> ScopeWithStats:
    """
    Get scope details with statistics.

    User must be a member of the scope or it must be public.
    RLS policies automatically enforce access control.

    Args:
        db: Database session
        scope_id: Scope UUID
        current_user: Current authenticated user

    Returns:
        Scope with statistics

    Raises:
        HTTPException 404: Scope not found or access denied
    """
    # This will use RLS and return scope only if user has access
    scope = deps.get_scope(scope_id, db, current_user)

    # Get statistics
    scope_with_stats = scope_crud.get_with_statistics(db, scope_id=scope_id)

    if not scope_with_stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scope not found or access denied",
        )

    logger.info(
        "Retrieved scope details",
        scope_id=str(scope_id),
        scope_name=scope.name,
        user_id=str(current_user.id),
    )

    role = scope_membership_crud.get_user_role_in_scope(
        db, user_id=current_user.id, scope_id=scope_id
    )
    pair = scope.default_workflow_pair
    return ScopeWithStats(
        **scope_with_stats,
        user_role=role.value if role else None,
        curation_schema_id=pair.curation_schema_id if pair else None,
        precuration_schema_id=pair.precuration_schema_id if pair else None,
    )


def _usable_pairs(
    db: Session, scope: Scope, pair_ids: Sequence[UUID | None]
) -> list[WorkflowPair]:
    """Active pairs that are global or this scope's own; 422 names any other."""
    pairs = {pid: db.get(WorkflowPair, pid) for pid in pair_ids if pid}
    bad = [
        str(pid)
        for pid, pair in pairs.items()
        if pair is None
        or not pair.is_active
        or pair.owner_scope_id not in (None, scope.id)
    ]
    if bad:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Workflow pairs not found, inactive or owned by another scope: "
            f"{', '.join(bad)}",
        )
    return [p for p in pairs.values() if p is not None]


@router.patch("/{scope_id}", response_model=ScopeResponse)
def update_scope(
    *,
    db: Session = Depends(get_db),
    scope_id: UUID,
    scope_in: ScopeUpdate,
    request: Request,
    scope: Scope = Depends(deps.require_capability(MANAGE_SCOPE, active_only=False)),
    current_user: User = Depends(deps.get_current_active_user),
) -> Scope:
    """
    Update scope details.

    Requires scope admin role or application admin.
    Uses RLS and role-based access control.

    Args:
        db: Database session
        scope_id: Scope UUID
        scope_in: Update data
        scope: Scope object (dependency ensures admin access)

    Returns:
        Updated scope object
    """
    gate = scope_in.approvals_require_session
    # an agent may not lift its own approval gate
    if (
        gate is not None
        and gate != scope.approvals_require_session
        and not deps.is_session_request(request)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Changing approvals_require_session needs a signed-in person",
        )
    # publishing evidence to anonymous callers is a person's call (#558), also when a
    # scope with it on becomes public
    exported = scope_in.export_evidence_public and not scope.export_evidence_public
    published = (
        scope_in.is_public and not scope.is_public and scope.export_evidence_public
    )
    if (exported or published) and not deps.is_session_request(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Turning on export_evidence_public or making a scope with it on "
            "public needs a signed-in person",
        )
    _usable_pairs(db, scope, [scope_in.default_workflow_pair_id])
    old_default = scope.default_workflow_pair_id
    updated_scope = scope_crud.update(db, db_obj=scope, obj_in=scope_in)
    if updated_scope.default_workflow_pair_id != old_default:
        audit(
            db,
            current_user,
            MANAGE_SCOPE,
            scope_id,
            ("scopes", scope_id),
            {
                "default_workflow_pair_id": [
                    old_default,
                    scope_in.default_workflow_pair_id,
                ]
            },
        )

    logger.info(
        "Scope updated",
        scope_id=str(scope_id),
        scope_name=updated_scope.name,
        user_id=str(current_user.id),
        approvals_require_session=updated_scope.approvals_require_session,
    )

    return updated_scope


@router.put("/{scope_id}/workflow-pairs", response_model=ScopeResponse)
def set_allowed_workflow_pairs(
    *,
    db: Session = Depends(get_db),
    scope_id: UUID,
    body: ScopeWorkflowPairs,
    scope: Scope = Depends(deps.require_capability(WORKFLOW_ASSIGN)),
    current_user: User = Depends(deps.get_current_active_user),
) -> Scope:
    """Replace the workflow pairs the scope may use besides its default (global or this
    scope's own pairs); an empty list allows the default pair only."""
    scope.allowed_workflow_pairs = _usable_pairs(db, scope, body.workflow_pair_ids)
    db.commit()
    audit(
        db,
        current_user,
        WORKFLOW_ASSIGN,
        scope_id,
        ("scopes", scope_id),
        {"allowed_workflow_pair_ids": body.workflow_pair_ids},
    )
    db.refresh(scope)
    return scope


@router.delete("/{scope_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scope(
    *,
    db: Session = Depends(get_db),
    scope_id: UUID,
    force: bool = Query(
        False,
        description="Force deletion even if scope has active gene assignments",
    ),
    current_user: User = Depends(deps.get_current_active_user),
) -> None:
    """
    Delete a scope (platform admins only; RLS allows nothing else).

    This is a destructive operation that should be used with caution. The scope's own
    templates and workflows are deactivated first, so they never become global ones.

    Args:
        db: Database session
        scope_id: Scope UUID
        force: If True, delete even with active gene assignments (cascade delete)
        current_user: Current user (must be a platform admin)

    Raises:
        HTTPException 404: Scope not found
        HTTPException 403: Not authorized to delete
        HTTPException 400: Scope has active assignments (unless force=True)
    """
    # Set RLS context
    deps.set_rls_context(db, current_user)

    # Get scope
    scope = scope_crud.get(db, id=scope_id)
    if not scope:
        logger.warning(
            "Delete scope failed: not found",
            scope_id=str(scope_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scope not found",
        )

    require(db, current_user, None, PLATFORM)  # as RLS: platform admins only

    # Check if scope has active assignments (prevent accidental deletion)
    has_assignments = scope_crud.has_active_assignments(db, scope_id=scope_id)
    if has_assignments and not force:
        logger.warning(
            "Delete scope failed: has active assignments (use force=true to override)",
            scope_id=str(scope_id),
            scope_name=scope.name,
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete scope with active gene assignments. Use force=true to delete anyway.",
        )

    if has_assignments and force:
        logger.warning(
            "Force deleting scope with active assignments",
            scope_id=str(scope_id),
            scope_name=scope.name,
            user_id=str(current_user.id),
        )

    # ON DELETE SET NULL would make the scope's own items global: deactivate them first
    for model in (CurationSchema, WorkflowPair):
        db.execute(
            update(model)
            .where(model.owner_scope_id == scope_id)
            .values(is_active=False)
        )
    # Delete scope (CASCADE will delete memberships and assignments)
    scope_crud.remove(db, id=scope_id)

    logger.warning(
        "Scope deleted",
        scope_id=str(scope_id),
        scope_name=scope.name,
        deleted_by=str(current_user.id),
        deleted_by_username=current_user.name,
    )


@router.get("/{scope_id}/statistics", response_model=ScopeStatistics)
def get_scope_statistics(
    *,
    db: Session = Depends(get_db),
    scope_id: UUID,
    scope: Scope = Depends(deps.require_capability(VIEW)),
) -> ScopeStatistics:
    """
    Get detailed statistics for a scope.

    Requires viewer role or higher (any scope member can view statistics).

    Args:
        db: Database session
        scope_id: Scope UUID
        scope: Scope object (dependency ensures member access)

    Returns:
        Scope statistics including gene counts, curation progress, etc.
    """
    statistics = scope_crud.get_detailed_statistics(db, scope_id=scope_id)

    logger.debug(
        "Retrieved scope statistics",
        scope_id=str(scope_id),
        total_genes=statistics.get("total_genes", 0),
        active_curations=statistics.get("active_curations", 0),
    )

    return ScopeStatistics(**statistics)
