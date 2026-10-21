"""Capability checks: endpoints ask "may this user do X in this scope", not "which role".

First slice of #284: a hard-coded role -> capability matrix. Moving it to data
(scope-owned configuration) is Wave 4.
"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ScopeRole
from app.models import Scope, ScopeMembership, UserNew

VIEW = "scope.view"
EDIT = "curation.edit"  # create/edit precuration and curation
REVIEW = "curation.review"  # approve/reject, never own work
ASSIGN_GENES = "gene.assign"
CREATE_GENE = "gene.create"  # add a global gene row (shared reference data)
MANAGE_MEMBERS = "scope.members.manage"

_VIEWER = frozenset({VIEW})
ROLE_CAPABILITIES: dict[ScopeRole, frozenset[str]] = {
    ScopeRole.VIEWER: _VIEWER,
    ScopeRole.REVIEWER: _VIEWER | {REVIEW},
    ScopeRole.CURATOR: _VIEWER | {EDIT, CREATE_GENE},
    ScopeRole.ADMIN: _VIEWER
    | {EDIT, REVIEW, ASSIGN_GENES, MANAGE_MEMBERS, CREATE_GENE},
}


def require(db: Session, user: UserNew, scope_id: UUID, capability: str) -> None:
    """Raise 403 unless the user holds `capability` in the scope (platform admins always do)."""
    if user.role == "admin":
        return
    role = db.execute(
        select(ScopeMembership.role)
        .join(Scope, Scope.id == ScopeMembership.scope_id)
        .where(
            ScopeMembership.scope_id == scope_id,
            ScopeMembership.user_id == user.id,
            ScopeMembership.is_active == True,  # noqa: E712
            ScopeMembership.accepted_at.isnot(None),
            Scope.is_active == True,  # noqa: E712
        )
    ).scalar()
    if role is None or capability not in ROLE_CAPABILITIES[ScopeRole(role)]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this scope",
        )


def require_anywhere(db: Session, user: UserNew, capability: str) -> None:
    """Raise 403 unless the user holds `capability` in at least one active scope (or is a platform admin)."""
    if user.role == "admin":
        return
    roles = db.execute(
        select(ScopeMembership.role)
        .join(Scope, Scope.id == ScopeMembership.scope_id)
        .where(
            ScopeMembership.user_id == user.id,
            ScopeMembership.is_active == True,  # noqa: E712
            ScopeMembership.accepted_at.isnot(None),
            Scope.is_active == True,  # noqa: E712
        )
    ).scalars()
    if not any(capability in ROLE_CAPABILITIES[ScopeRole(r)] for r in roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only scope curators and admins can add genes",
        )
