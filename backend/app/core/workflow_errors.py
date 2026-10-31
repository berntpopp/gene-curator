"""4-eyes and workflow refusals (L6): 403 when the actor may not, 409 when the state forbids.

Both subclass ValueError, so callers that catch ValueError (bulk transitions) keep working.
"""

from fastapi import HTTPException, status


class ReviewForbiddenError(ValueError):
    """The actor may not do this: own work, disease corrector, no review role (D1)."""


class WorkflowConflictError(ValueError):
    """The item's workflow state forbids this: wrong stage or status, already reviewed."""


# ponytail: matches the messages validate_transition builds; keep them in step.
_CONFLICT = ("Invalid transition from", "Only a submitted precuration")
_DENIED = (
    "4-eyes principle violation",
    "User not authorized",
    "Insufficient permissions",
)


def transition_error(errors: list[str]) -> ValueError:
    """The refusal for a failed validate_transition: a wrong stage first, then a denial."""
    message = f"Invalid transition: {', '.join(errors)}"
    if any(e.startswith(_CONFLICT) for e in errors):
        return WorkflowConflictError(message)
    if any(e.startswith(_DENIED) for e in errors):
        return ReviewForbiddenError(message)
    return ValueError(message)


def http_error(e: ValueError) -> HTTPException:
    """403/409 for the refusals above, 400 for any other ValueError; keeps the message."""
    code = (
        status.HTTP_403_FORBIDDEN
        if isinstance(e, ReviewForbiddenError)
        else status.HTTP_409_CONFLICT
        if isinstance(e, WorkflowConflictError)
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(status_code=code, detail=str(e))
