"""4-eyes and workflow refusals (L6): 403 when the actor may not, 409 when the state forbids.

All subclass ValueError, so callers that catch ValueError (bulk transitions) keep working.
"""

from typing import TYPE_CHECKING

from fastapi import HTTPException, status

if TYPE_CHECKING:
    from app.schemas.workflow_engine import WorkflowValidationResult


class ReviewForbiddenError(ValueError):
    """The actor may not do this: own work, disease corrector, no review role (D1)."""


class WorkflowConflictError(ValueError):
    """The item's workflow state forbids this: wrong stage or status, already reviewed."""


class ItemNotFoundError(ValueError):
    """The item does not exist or RLS hides it (a pending invitation grants nothing)."""


def transition_error(validation: "WorkflowValidationResult") -> ValueError:
    """The refusal for a failed validate_transition: a wrong stage first, then a denial."""
    cls = (
        WorkflowConflictError
        if validation.conflict
        else ReviewForbiddenError
        if validation.denied
        else ValueError
    )
    return cls(f"Invalid transition: {', '.join(validation.errors)}")


_CODES = {
    ReviewForbiddenError: status.HTTP_403_FORBIDDEN,
    WorkflowConflictError: status.HTTP_409_CONFLICT,
    ItemNotFoundError: status.HTTP_404_NOT_FOUND,
}


def http_error(e: ValueError) -> HTTPException:
    """403/409/404 for the refusals above, 400 for any other ValueError; keeps the message."""
    return HTTPException(
        status_code=_CODES.get(type(e), status.HTTP_400_BAD_REQUEST), detail=str(e)
    )
