"""Backward-compatible re-exports; models live in domain modules (see __init__)."""

from app.models.curation import ActiveCuration, CurationNew, PrecurationNew, Review
from app.models.evidence import EvidenceItem, Publication
from app.models.genes import Gene, GeneScopeAssignment, GeneSummary
from app.models.identity import SchemaMigration, Scope, ScopeMembership, UserNew
from app.models.methodology import MethodologyVersion
from app.models.model_enums import (
    CurationStatus,
    NotificationType,
    ReviewStatus,
    SchemaType,
    UserRoleNew,
    WorkflowStage,
)
from app.models.schemas import CurationSchema, SchemaSelection, WorkflowPair
from app.models.system import AuditLogNew, NotificationNew, SystemLog, ValidationCache

__all__ = [
    "ActiveCuration",
    "AuditLogNew",
    "CurationNew",
    "CurationSchema",
    "CurationStatus",
    "EvidenceItem",
    "Gene",
    "GeneScopeAssignment",
    "GeneSummary",
    "MethodologyVersion",
    "NotificationNew",
    "NotificationType",
    "PrecurationNew",
    "Publication",
    "Review",
    "ReviewStatus",
    "SchemaMigration",
    "SchemaSelection",
    "SchemaType",
    "Scope",
    "ScopeMembership",
    "SystemLog",
    "UserNew",
    "UserRoleNew",
    "ValidationCache",
    "WorkflowPair",
    "WorkflowStage",
]
