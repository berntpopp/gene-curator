"""Capability checks: endpoints ask "may this user do X in this scope", not "which role".

The role -> capability matrix is data (table role_capabilities, migration 082, #284): require()
here and the RLS helpers (has_scope_capability) read the same rows. DEFAULT_MATRIX is the seed.
Configuration with owner scope NULL (global templates) needs a platform admin.
"""

import json
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Connection, Select, Table, event, select
from sqlalchemy.orm import Session

from app.core.enums import ScopeRole
from app.models import AuditLogNew, Scope, ScopeMembership, UserNew
from app.models.permissions import RoleCapability

VIEW = "scope.view"
EDIT = "curation.edit"  # create/edit precuration and curation
REVIEW = "curation.review"  # approve/reject, never own work
ASSIGN_GENES = "gene.assign"
CREATE_GENE = "gene.create"  # add a global gene row (shared reference data)
MANAGE_MEMBERS = "scope.members.manage"
MANAGE_SCOPE = "scope.manage"  # scope settings
METHODOLOGY_DERIVE = "methodology.derive"  # create or derive a scope-owned methodology
METHODOLOGY_EDIT = "methodology.edit"
METHODOLOGY_PUBLISH = "methodology.publish"
WORKFLOW_CREATE = "workflow.create"
WORKFLOW_ASSIGN = "workflow.assign_to_scope"
# Global templates and everything else unscoped: no scope role holds it (platform admins)
PLATFORM = "platform.manage"

_VIEWER = frozenset({VIEW})
_ADMIN = {
    EDIT,
    REVIEW,
    ASSIGN_GENES,
    CREATE_GENE,
    MANAGE_MEMBERS,
    MANAGE_SCOPE,
    METHODOLOGY_DERIVE,
    METHODOLOGY_EDIT,
    METHODOLOGY_PUBLISH,
    WORKFLOW_CREATE,
    WORKFLOW_ASSIGN,
}
# Seed of role_capabilities; 082 inserts the same rows (a Postgres test compares them)
DEFAULT_MATRIX: dict[ScopeRole, frozenset[str]] = {
    ScopeRole.VIEWER: _VIEWER,
    ScopeRole.REVIEWER: _VIEWER | {REVIEW},
    ScopeRole.CURATOR: _VIEWER | {EDIT, CREATE_GENE},
    ScopeRole.ADMIN: _VIEWER | _ADMIN,
}


@event.listens_for(RoleCapability.__table__, "after_create")
def _seed(target: Table, connection: Connection, **_: Any) -> None:
    """Seed the matrix where tables come from metadata (SQLite tests); Postgres uses 082."""
    rows = [
        {"role": role.value, "capability": cap}
        for role, caps in DEFAULT_MATRIX.items()
        for cap in caps
    ]
    connection.execute(target.insert(), rows)


def roles_holding(capability: str) -> Select[str]:
    """Scope roles that hold `capability`, as a subquery for ScopeMembership.role.in_()."""
    return select(RoleCapability.role).where(RoleCapability.capability == capability)


def _memberships(
    user_id: UUID, capability: str, active_only: bool = True
) -> Select[UUID]:
    """Scopes (active ones unless active_only=False) where the user's accepted membership
    holds `capability`."""
    query = (
        select(ScopeMembership.scope_id)
        .join(Scope, Scope.id == ScopeMembership.scope_id)
        .where(
            ScopeMembership.user_id == user_id,
            ScopeMembership.is_active == True,  # noqa: E712
            ScopeMembership.accepted_at.isnot(None),
            ScopeMembership.role.in_(roles_holding(capability)),
        )
    )
    return query.where(Scope.is_active == True) if active_only else query  # noqa: E712


def holds(
    db: Session,
    user_id: UUID,
    scope_id: UUID,
    capability: str,
    active_only: bool = True,
) -> bool:
    """The matrix grants `capability` to the user's membership in the scope (no admin
    bypass). active_only=False when managing the scope itself (RLS ignores is_active)."""
    query = _memberships(user_id, capability, active_only).where(
        ScopeMembership.scope_id == scope_id
    )
    return db.scalar(query) is not None


def require(
    db: Session,
    user: UserNew,
    scope_id: UUID | None,
    capability: str,
    active_only: bool = True,
) -> None:
    """Raise 403 unless the user holds `capability` in the scope (platform admins always do).

    scope_id None is global configuration (a template's NULL owner): platform admins only.
    """
    if user.role == "admin":
        return
    # An inactive scope is read-only, not hidden: its members keep VIEW
    active_only = active_only and capability != VIEW
    if scope_id is None or not holds(db, user.id, scope_id, capability, active_only):
        # A1: a member of an inactive scope gets the read-only reason, a stranger the 403
        if (
            scope_id is not None
            and active_only
            and holds(db, user.id, scope_id, capability, active_only=False)
        ):
            require_active_scope(db.get(Scope, scope_id))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Needs a platform admin (global configuration or data)"
            if scope_id is None
            else "Not authorized to access this scope",
        )


INACTIVE_SCOPE = "This scope is inactive; its curations are read-only"


def require_active_scope(scope: Scope | None) -> None:
    """409 for a write to an inactive scope's work: RLS (054) blocks it, which surfaced as a 500
    or a misleading 403."""
    if scope is not None and not scope.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=INACTIVE_SCOPE,
        )


def require_anywhere(db: Session, user: UserNew, capability: str) -> None:
    """Raise 403 unless the user holds `capability` in at least one active scope (or is a platform admin)."""
    if user.role == "admin":
        return
    if db.scalar(_memberships(user.id, capability)) is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only scope curators and admins can add genes",
        )


def audit(
    db: Session,
    user: UserNew,
    capability: str,
    scope_id: UUID | None,
    entity: tuple[str, UUID],
    details: dict[str, Any] | None = None,
) -> None:
    """Record a permission-relevant action: actor, capability and scope (#284). Only adds
    the row: the caller's commit writes it with the change, in one transaction."""
    entity_type, entity_id = entity
    db.add(
        AuditLogNew(
            entity_type=entity_type,
            entity_id=entity_id,
            operation=capability,
            scope_id=scope_id,
            user_id=user.id,
            changes=json.loads(
                json.dumps({"capability": capability, **(details or {})}, default=str)
            ),
        )
    )


def allowed_pair_ids(scope: Scope) -> set[UUID] | None:
    """Pairs the scope may use: its default plus its allowed list (082). None: no
    restriction configured (a legacy scope with neither)."""
    ids = set(scope.allowed_workflow_pair_ids)
    if scope.default_workflow_pair_id:
        ids.add(scope.default_workflow_pair_id)
    return ids or None


def require_allowed_pair(scope: Scope | None, *candidates: UUID | None) -> None:
    """422 unless the scope allows one of the candidate workflow pairs."""
    allowed = allowed_pair_ids(scope) if scope else None
    if allowed is not None and not allowed & set(candidates):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="This workflow is not allowed in this scope; a scope admin can add it "
            "under scope settings (allowed workflows)",
        )
