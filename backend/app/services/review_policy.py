"""Who may approve in a scope (#639): scopes.review_policy and agent accounts.

human (default, as before 093): an agent account curates but never reviews or approves.
ai: an agent account may review and approve; 4-eyes still needs another identity.
ai_then_human: an agent may approve too, but a curation activates only once a person
approved it in the open round; until then the agent's approval is provisional.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.workflow_errors import ReviewForbiddenError, http_error
from app.mcp.audit import request_agent
from app.models import CurationNew, Review, ReviewStatus, Scope, UserNew

POLICIES = ("human", "ai", "ai_then_human")
HUMAN_ONLY = (
    "Agent accounts cannot review or approve in this scope (review_policy human); "
    "a person must"
)
NEEDS_PERSON = (
    "This scope's review_policy is ai_then_human: the agent approval is provisional "
    "until a person approves"
)


def check_agent_review(user: UserNew | None, scope: Scope | None) -> None:
    """403 for an agent account's review or approval in a human scope."""
    if user is not None and user.is_agent and _policy(scope) == "human":
        raise ReviewForbiddenError(HUMAN_ONLY)


def require_agent_may_review(user: UserNew, scope: Scope | None) -> None:
    """check_agent_review as an HTTP 403, for endpoints outside the engine's error map."""
    try:
        check_agent_review(user, scope)
    except ReviewForbiddenError as e:
        raise http_error(e) from e


def _policy(scope: Scope | None) -> str:
    return scope.review_policy if scope is not None else "human"


def person_approved(db: Session, curation: CurationNew) -> bool:
    """A non-agent reviewer approved it in the open round."""
    from app.crud.review_round import in_current_round  # import cycle

    approved = db.scalar(
        select(func.count())
        .select_from(Review)
        .join(UserNew, Review.reviewer_id == UserNew.id)
        .where(
            Review.curation_id == curation.id,
            in_current_round,
            Review.status == ReviewStatus.APPROVED,
            UserNew.is_agent == False,  # noqa: E712
        )
    )
    return bool(approved)


def waits_for_person(db: Session, curation: CurationNew) -> bool:
    """ai_then_human and no person approved yet: the curation stays in review."""
    scope = db.get(Scope, curation.scope_id)
    return _policy(scope) == "ai_then_human" and not person_approved(db, curation)


def approval_stamp(
    db: Session, curation: CurationNew, approver: UserNew | None
) -> dict[str, Any]:
    """approval_kind and approval_model for an activating curation: human when a person
    approves or approved it, else ai with the agent's model from its MCP agent block."""
    if approver is None or not approver.is_agent or person_approved(db, curation):
        return {"approval_kind": "human", "approval_model": None}
    return {
        "approval_kind": "ai",
        "approval_model": (request_agent.get() or {}).get("model"),
    }
