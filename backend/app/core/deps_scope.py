"""Scope-based permission dependencies for FastAPI.

Design Principles:
- KISS: Uses Request object for simple parameter extraction
- No complex aliasing or factory patterns
- Clear error messages with role requirements

Reference: https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/
"""

from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.logging import get_logger
from app.models import UserNew
from app.services.scope_permissions import ScopePermissionService

logger = get_logger(__name__)


def require_scope_access(
    required_roles: list[str] | None = None,
    scope_param_name: str = "scope_id",
) -> Callable[..., None]:
    """Factory for scope access dependency.

    Extracts scope_id from path or query parameters using Request object.
    This is simpler and more reliable than Query aliasing.

    Usage:
        @router.get("/{scope_id}/items")
        def get_items(
            scope_id: UUID = Path(...),
            db: Session = Depends(get_db),
            current_user: UserNew = Depends(get_current_active_user),
            _: None = Depends(require_scope_access(["curator", "admin"])),
        ):
            # Scope access validated by dependency
            ...

        @router.get("/items/")
        def list_items(
            scope_id: UUID | None = Query(None),
            db: Session = Depends(get_db),
            current_user: UserNew = Depends(get_current_active_user),
            _: None = Depends(require_scope_access()),
        ):
            # If scope_id is None, no validation (allows listing all accessible)
            ...

    Args:
        required_roles: List of required scope roles. If None, any membership is sufficient.
        scope_param_name: Name of the parameter containing scope_id (default: "scope_id")

    Returns:
        Dependency function that validates scope access
    """

    def dependency(
        request: Request,
        db: Session = Depends(get_db),
        current_user: UserNew = Depends(get_current_active_user),
    ) -> None:
        # Extract scope_id from path params first, then query params
        scope_id_str = request.path_params.get(
            scope_param_name
        ) or request.query_params.get(scope_param_name)

        if not scope_id_str:
            # No scope specified - allow (endpoint will filter by user's scopes)
            logger.debug(
                "No scope_id in request, skipping scope validation",
                user_id=str(current_user.id),
            )
            return

        # Parse UUID
        try:
            scope_id = UUID(scope_id_str)
        except ValueError:
            logger.warning(
                "Invalid scope_id format",
                scope_id=scope_id_str,
                user_id=str(current_user.id),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scope_id format: {scope_id_str}",
            ) from None

        # Check access
        if not ScopePermissionService.has_scope_access(
            db, current_user, scope_id, required_roles=required_roles
        ):
            detail = "Not authorized to access this scope"
            if required_roles:
                detail += f" (requires one of: {', '.join(required_roles)})"

            logger.warning(
                "Scope access denied",
                user_id=str(current_user.id),
                scope_id=str(scope_id),
                required_roles=required_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )

        logger.debug(
            "Scope access granted",
            user_id=str(current_user.id),
            scope_id=str(scope_id),
        )

    return dependency


def require_scope_role(*roles: str) -> Callable[..., None]:
    """Convenience function to require specific scope role(s).

    Usage:
        @router.post("/curations/")
        def create_curation(
            scope_id: UUID,
            _: None = Depends(require_scope_role("curator", "admin")),
            ...
        ):
            ...
    """
    return require_scope_access(required_roles=list(roles))


# Convenience dependencies for common patterns
require_curator_access = require_scope_access(
    required_roles=["admin", "curator", "scope_admin"]
)
require_reviewer_access = require_scope_access(
    required_roles=["admin", "curator", "reviewer", "scope_admin"]
)
require_viewer_access = require_scope_access()  # Any membership
