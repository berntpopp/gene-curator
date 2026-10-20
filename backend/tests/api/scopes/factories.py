"""Shared data factories for scope, membership and workflow tests (SQLite)."""

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.models.models import (
    CurationNew,
    CurationSchema,
    CurationStatus,
    Gene,
    PrecurationNew,
    Scope,
    ScopeMembership,
    UserNew,
    WorkflowPair,
    WorkflowStage,
)

PASSWORD = "password123"  # noqa: S105 - test fixture credential


def make_user(
    db: Session,
    *,
    role: str = "user",
    is_active: bool = True,
    name: str | None = None,
) -> UserNew:
    """Create and persist a user with a unique e-mail address."""
    suffix = uuid4().hex[:10]
    user = UserNew(
        id=uuid4(),
        email=f"user-{suffix}@test.com",
        hashed_password=get_password_hash(PASSWORD),
        name=name or f"User {suffix}",
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_scope(
    db: Session,
    *,
    created_by: UUID | None = None,
    is_active: bool = True,
    name: str | None = None,
) -> Scope:
    """Create and persist a scope with a unique name."""
    scope = Scope(
        id=uuid4(),
        name=name or f"scope-{uuid4().hex[:10]}",
        display_name="Scope",
        description="Test scope",
        is_public=False,
        is_active=is_active,
        created_by=created_by,
    )
    db.add(scope)
    db.commit()
    db.refresh(scope)
    return scope


def make_member(
    db: Session,
    scope: Scope,
    user: UserNew,
    role: str,
    *,
    accepted: bool = True,
    is_active: bool = True,
    expires_at: datetime | None = None,
) -> ScopeMembership:
    """Create a membership row. accepted=False yields a pending invitation."""
    now = datetime.now(UTC)
    membership = ScopeMembership(
        scope_id=scope.id,
        user_id=user.id,
        role=role,
        invited_at=now,
        accepted_at=now if accepted else None,
        expires_at=expires_at if expires_at is not None else now + timedelta(days=7),
        is_active=is_active,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def make_gene(db: Session) -> Gene:
    """Create a gene with a unique HGNC id and record hash."""
    suffix = uuid4().hex[:8]
    gene = Gene(
        id=uuid4(),
        hgnc_id=f"HGNC:{suffix}",
        approved_symbol=f"GENE{suffix}".upper(),
        record_hash=hashlib.sha256(suffix.encode()).hexdigest(),
        previous_symbols=[],
        alias_symbols=[],
        details={},
    )
    db.add(gene)
    db.commit()
    db.refresh(gene)
    return gene


def make_workflow_pair(db: Session) -> WorkflowPair:
    """Create a workflow pair used by curations."""
    pair = WorkflowPair(id=uuid4(), name=f"wf-{uuid4().hex[:6]}", version="1.0")
    db.add(pair)
    db.commit()
    db.refresh(pair)
    return pair


def make_curation(
    db: Session,
    *,
    scope: Scope,
    gene: Gene,
    creator: UserNew,
    stage: WorkflowStage = WorkflowStage.REVIEW,
    status: CurationStatus = CurationStatus.IN_REVIEW,
    evidence_data: dict[str, Any] | None = None,
) -> CurationNew:
    """Create a curation in the given workflow stage."""
    pair = make_workflow_pair(db)
    curation = CurationNew(
        id=uuid4(),
        scope_id=scope.id,
        gene_id=gene.id,
        workflow_pair_id=pair.id,
        status=status,
        workflow_stage=stage,
        evidence_data=evidence_data if evidence_data is not None else {"summary": "ok"},
        created_by=creator.id,
        updated_by=creator.id,
    )
    db.add(curation)
    db.commit()
    db.refresh(curation)
    return curation


def make_precuration(
    db: Session,
    *,
    scope: Scope,
    gene: Gene,
    creator: UserNew,
    stage: WorkflowStage = WorkflowStage.PRECURATION,
) -> PrecurationNew:
    """Create a precuration in the given workflow stage."""
    schema = CurationSchema(
        id=uuid4(),
        name=f"schema-{uuid4().hex[:6]}",
        version="1.0",
        schema_type="precuration",
        description="Test schema",
        institution="Test",
        is_active=True,
        field_definitions={},
        validation_rules={},
        workflow_states={},
        ui_configuration={},
        schema_hash=uuid4().hex + uuid4().hex,
    )
    db.add(schema)
    db.commit()
    precuration = PrecurationNew(
        id=uuid4(),
        scope_id=scope.id,
        gene_id=gene.id,
        precuration_schema_id=schema.id,
        status=CurationStatus.DRAFT,
        workflow_stage=stage,
        evidence_data={},
        created_by=creator.id,
        updated_by=creator.id,
    )
    db.add(precuration)
    db.commit()
    db.refresh(precuration)
    return precuration


def token_for(user: UserNew) -> str:
    """Build a JWT in the same shape the login endpoint issues."""
    return create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )


def auth_headers(user: UserNew) -> dict[str, str]:
    """Authorization header for a user."""
    return {"Authorization": f"Bearer {token_for(user)}"}
