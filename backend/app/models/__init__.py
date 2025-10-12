"""
Database models package.
"""

# Import all models to ensure they are registered with SQLAlchemy
from .models import (
    ActiveCuration,
    AuditLogNew,
    CurationNew,
    CurationSchema,
    CurationStatus,
    GeneNew,
    GeneScopeAssignment,
    PrecurationNew,
    Review,
    ReviewStatus,
    SchemaSelection,
    SchemaType,
    Scope,
    UserNew,
    UserRoleNew,
    WorkflowPair,
    WorkflowStage,
)

# Create aliases for backward compatibility
User = UserNew
UserRole = UserRoleNew

__all__ = [
    "ActiveCuration",
    "AuditLogNew",
    "CurationNew",
    "CurationSchema",
    "CurationStatus",
    "GeneNew",
    "GeneScopeAssignment",
    "PrecurationNew",
    "Review",
    "ReviewStatus",
    "SchemaSelection",
    "SchemaType",
    "Scope",
    "User",
    "UserNew",
    "UserRole",
    "UserRoleNew",
    "WorkflowPair",
    "WorkflowStage",
]
