"""One visibility rule for catalogue-style reads: a scope is visible when it is active and
public, or the caller has an accepted, active membership. Platform admins get no bypass."""

from typing import Any
from uuid import UUID

from sqlalchemy import Select, or_, select

from app.models import Scope, ScopeMembership


def member_scope_ids(user_id: UUID | None) -> Select[Any]:
    return select(ScopeMembership.scope_id).where(
        ScopeMembership.user_id == user_id,
        ScopeMembership.is_active == True,  # noqa: E712
        ScopeMembership.accepted_at.isnot(None),
    )


def visible_scope_ids(user_id: UUID | None) -> Select[Any]:
    return select(Scope.id).where(
        Scope.is_active == True,  # noqa: E712
        or_(Scope.is_public == True, Scope.id.in_(member_scope_ids(user_id))),  # noqa: E712
    )
