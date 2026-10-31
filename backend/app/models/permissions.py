"""Capability matrix and per-scope allowed workflow pairs (migration 082, #284)."""

from uuid import UUID as PyUUID  # noqa: N811

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.db_types import compatible_uuid


class RoleCapability(Base):
    """One row per (scope role, capability) the role holds; read by require() and RLS."""

    __tablename__ = "role_capabilities"

    role: Mapped[str] = mapped_column(String(50), primary_key=True)  # scope_role enum
    capability: Mapped[str] = mapped_column(Text, primary_key=True)


class ScopeWorkflowPair(Base):
    """A workflow pair the scope may use besides its default pair."""

    __tablename__ = "scope_workflow_pairs"

    scope_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), ForeignKey("scopes.id", ondelete="CASCADE"), primary_key=True
    )
    workflow_pair_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("workflow_pairs.id", ondelete="CASCADE"),
        primary_key=True,
    )
