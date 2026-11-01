"""One visibility rule for catalogue-style reads: a scope is visible when it is active and
public, or the caller has an accepted, active membership. Platform admins get no bypass."""

from difflib import get_close_matches
from typing import Any, cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.models import Scope, ScopeMembership, UserNew


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


def scope_id_for(
    db: Session, user_id: UUID | None, scope_id: UUID | None, scope_name: str | None
) -> UUID | None:
    """scope_id, or the visible scope named scope_name (name or display name, any case);
    a platform admin resolves any scope, as list_scopes shows them (#640). Access is checked
    after. 404 lists close names when none or several match, or the name and the id disagree."""
    if not scope_name:
        return scope_id
    key = scope_name.strip().lower()
    user = db.get(UserNew, user_id) if user_id else None
    admin = user is not None and user.role.value == "admin"
    rows = db.execute(
        select(Scope.id, Scope.name, Scope.display_name).where(
            Scope.id.in_(select(Scope.id) if admin else visible_scope_ids(user_id))
        )
    ).all()
    hits = [r for r in rows if r.name.lower() == key] or [
        r for r in rows if r.display_name.lower() == key
    ]
    if len(hits) == 1 and scope_id in (None, hits[0].id):
        return cast(UUID, hits[0].id)
    names = [r.name for r in rows]
    close = [n for n in names if key in n.lower()] + get_close_matches(key, names, 5)
    suggestions = [r.name for r in hits] if len(hits) > 1 else close
    raise HTTPException(
        status.HTTP_404_NOT_FOUND,
        detail={
            "message": f"No single scope you can see is named {scope_name!r}"
            + (" with that scope_id" if len(hits) == 1 else ""),
            "suggestions": list(dict.fromkeys(suggestions))[:5],
        },
    )
