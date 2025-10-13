# Backend Implementation Plan: Scope-Centric Architecture

**Version:** 2.0 (Security Hardened)
**Date:** 2025-10-13
**Prerequisites:** Read `SECURITY_AUDIT.md` first

---

## Implementation Order

### Phase 1: Database Foundation (Week 1-2)
### Phase 2: Core Backend Services (Week 3-4)
### Phase 3: API Endpoints (Week 4-5)
### Phase 4: Security & Testing (Week 5-6)

---

## PHASE 1: Database Foundation

### Step 1.1: Create New Enums

**File:** `database/sql/migrations/001_scope_centric_enums.sql`

```sql
-- Create new enums for scope-centric architecture
CREATE TYPE application_role AS ENUM ('admin', 'user');
CREATE TYPE scope_role AS ENUM ('admin', 'curator', 'reviewer', 'viewer');

-- Keep existing enums for backward compatibility during migration
-- user_role_new, workflow_stage, review_status, curation_status, schema_type
```

**Testing:**
```sql
-- Verify enums created
SELECT typname, enumlabel FROM pg_enum
JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
WHERE typname IN ('application_role', 'scope_role')
ORDER BY typname, enumsortorder;
```

---

### Step 1.2: Add New Columns to Users Table (Backward Compatible)

**File:** `database/sql/migrations/002_users_migration_prep.sql`

```sql
-- Add new columns without breaking existing system
ALTER TABLE users_new
  ADD COLUMN IF NOT EXISTS application_role application_role DEFAULT 'user',
  ADD COLUMN IF NOT EXISTS migration_complete BOOLEAN DEFAULT false;

-- Migrate existing roles to application_role
UPDATE users_new SET
  application_role = CASE
    WHEN role IN ('admin', 'scope_admin') THEN 'admin'::application_role
    ELSE 'user'::application_role
  END
WHERE application_role IS NULL;

-- Add NOT NULL constraint after populating
ALTER TABLE users_new ALTER COLUMN application_role SET NOT NULL;
```

**Update Model:** `backend/app/models/models.py`

**Line 132:** Add after `role` column:
```python
# New application-level role (scope-centric architecture)
application_role = Column(
    Enum('admin', 'user', name='application_role'),
    nullable=False,
    default='user',
    index=True
)
migration_complete = Column(Boolean, default=False)
```

---

### Step 1.3: Create Scope Memberships Table

**File:** `database/sql/migrations/003_scope_memberships.sql`

```sql
-- Core multi-tenancy table
CREATE TABLE scope_memberships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users_new(id) ON DELETE CASCADE,

    -- Scope-specific role
    role scope_role NOT NULL,

    -- Invitation tracking
    invited_by UUID REFERENCES users_new(id),
    invited_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accepted_at TIMESTAMPTZ,  -- NULL = pending invitation

    -- Team membership (for future)
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,

    -- Metadata
    notes TEXT,
    is_active BOOLEAN DEFAULT true,

    -- Constraints
    UNIQUE(scope_id, user_id)
);

-- Performance indexes
CREATE INDEX idx_scope_memberships_scope ON scope_memberships(scope_id);
CREATE INDEX idx_scope_memberships_user ON scope_memberships(user_id);
CREATE INDEX idx_scope_memberships_role ON scope_memberships(role);
CREATE INDEX idx_scope_memberships_active ON scope_memberships(is_active) WHERE is_active = true;
CREATE INDEX idx_scope_memberships_pending ON scope_memberships(accepted_at) WHERE accepted_at IS NULL;

-- CRITICAL: Composite index for permission checks (prevent N+1)
CREATE INDEX idx_scope_memberships_user_scope_active ON scope_memberships(user_id, scope_id, role)
WHERE is_active = true AND accepted_at IS NOT NULL;

COMMENT ON TABLE scope_memberships IS 'Core multi-tenancy: user roles within scopes';
```

**Create Model:** `backend/app/models/models.py`

**Add after `UserNew` class (around line 181):**
```python
class ScopeMembership(Base):
    """User membership in scopes with role-based permissions."""

    __tablename__ = "scope_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scopes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users_new.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Scope-specific role (NOT application role)
    role = Column(
        Enum('admin', 'curator', 'reviewer', 'viewer', name='scope_role'),
        nullable=False,
        index=True
    )

    # Invitation tracking
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users_new.id"))
    invited_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    accepted_at = Column(DateTime(timezone=True))  # NULL = pending

    # Optional team membership
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"))

    # Metadata
    notes = Column(Text)
    is_active = Column(Boolean, default=True, index=True)

    # Relationships
    scope = relationship("Scope", back_populates="memberships")
    user = relationship("UserNew", foreign_keys=[user_id], back_populates="scope_memberships")
    inviter = relationship("UserNew", foreign_keys=[invited_by])
    team = relationship("Team", back_populates="members")

    __table_args__ = (
        UniqueConstraint("scope_id", "user_id", name="uq_scope_user"),
        Index("idx_scope_memberships_user_scope_active", "user_id", "scope_id", "role",
              postgresql_where="is_active = true AND accepted_at IS NOT NULL")
    )
```

**Update Scope Model Relationships:** `backend/app/models/models.py`

**Line 116:** Add to `Scope` class:
```python
# Add to relationships section
memberships = relationship("ScopeMembership", back_populates="scope")
```

**Line 158:** Add to `UserNew` class:
```python
# Add to relationships section
scope_memberships = relationship("ScopeMembership", foreign_keys="[ScopeMembership.user_id]", back_populates="user")
```

---

### Step 1.4: Create RLS Helper Functions (SECURE)

**File:** `database/sql/migrations/004_rls_functions.sql`

```sql
-- ==========================================
-- SECURE RLS HELPER FUNCTIONS
-- ==========================================

-- Function 1: Get current user UUID (with validation)
CREATE OR REPLACE FUNCTION get_current_user_uuid()
RETURNS UUID AS $$
DECLARE
    user_uuid UUID;
BEGIN
    -- Safely cast current_setting to UUID
    user_uuid := CAST(current_setting('app.current_user_id', TRUE) AS UUID);
    RETURN user_uuid;
EXCEPTION
    WHEN OTHERS THEN
        -- Invalid UUID or setting not found
        RAISE WARNING 'Invalid or missing app.current_user_id: %', SQLERRM;
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION get_current_user_uuid() IS 'Safely retrieve current user UUID from session variable';

-- Function 2: Check if user is application admin
CREATE OR REPLACE FUNCTION is_application_admin()
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM users_new
        WHERE id = get_current_user_uuid()
        AND application_role = 'admin'
        AND is_active = true
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

COMMENT ON FUNCTION is_application_admin() IS 'Check if current user is application administrator';

-- Function 3: Check scope membership (OPTIMIZED for caching)
CREATE OR REPLACE FUNCTION is_scope_member(scope_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM scope_memberships
        WHERE scope_id = scope_uuid
        AND user_id = get_current_user_uuid()
        AND is_active = true
        AND accepted_at IS NOT NULL
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

COMMENT ON FUNCTION is_scope_member(UUID) IS 'Check if current user is member of given scope (STABLE for query caching)';

-- Function 4: Check scope admin role
CREATE OR REPLACE FUNCTION is_scope_admin(scope_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM scope_memberships
        WHERE scope_id = scope_uuid
        AND user_id = get_current_user_uuid()
        AND role = 'admin'
        AND is_active = true
        AND accepted_at IS NOT NULL
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

COMMENT ON FUNCTION is_scope_admin(UUID) IS 'Check if current user is admin of given scope';

-- Function 5: Get user role in scope
CREATE OR REPLACE FUNCTION get_user_scope_role(scope_uuid UUID)
RETURNS scope_role AS $$
    SELECT role FROM scope_memberships
    WHERE scope_id = scope_uuid
    AND user_id = get_current_user_uuid()
    AND is_active = true
    AND accepted_at IS NOT NULL
    LIMIT 1
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

COMMENT ON FUNCTION get_user_scope_role(UUID) IS 'Get current users role in given scope';
```

---

### Step 1.5: Enable RLS on Tables (SECURE)

**File:** `database/sql/migrations/005_enable_rls.sql`

```sql
-- ==========================================
-- ENABLE ROW LEVEL SECURITY (SECURE)
-- ==========================================

-- Enable RLS on scope-sensitive tables
ALTER TABLE scopes ENABLE ROW LEVEL SECURITY;
ALTER TABLE scopes FORCE ROW LEVEL SECURITY;  -- ✅ Force even for owners

ALTER TABLE scope_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE scope_memberships FORCE ROW LEVEL SECURITY;

ALTER TABLE gene_scope_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE gene_scope_assignments FORCE ROW LEVEL SECURITY;

ALTER TABLE precurations_new ENABLE ROW LEVEL SECURITY;
ALTER TABLE precurations_new FORCE ROW LEVEL SECURITY;

ALTER TABLE curations_new ENABLE ROW LEVEL SECURITY;
ALTER TABLE curations_new FORCE ROW LEVEL SECURITY;

ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews FORCE ROW LEVEL SECURITY;

-- Create service role (WITHOUT BYPASSRLS)
CREATE ROLE app_service NOLOGIN;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_service;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_service;

-- Ensure application uses app_service role, NOT superuser
ALTER DATABASE gene_curator_dev OWNER TO app_service;
```

---

### Step 1.6: Create RLS Policies (OPTIMIZED & SECURE)

**File:** `database/sql/migrations/006_rls_policies.sql`

```sql
-- ==========================================
-- SCOPE RLS POLICIES (OPTIMIZED)
-- ==========================================

-- Policy: SELECT scopes
CREATE POLICY scope_select_policy ON scopes
    FOR SELECT
    USING (
        is_application_admin()      -- App admins see all
        OR is_public = true          -- Public scopes visible to all
        OR is_scope_member(id)       -- Members see their scopes (STABLE function)
    );

-- Policy: INSERT scopes (any authenticated user)
CREATE POLICY scope_insert_policy ON scopes
    FOR INSERT
    WITH CHECK (
        creator_id = get_current_user_uuid()  -- Must be creating for yourself
    );

-- Policy: UPDATE scopes (admins only)
CREATE POLICY scope_update_policy ON scopes
    FOR UPDATE
    USING (
        is_application_admin() OR is_scope_admin(id)
    );

-- Policy: DELETE scopes (application admin only)
CREATE POLICY scope_delete_policy ON scopes
    FOR DELETE
    USING (
        is_application_admin()
    );

-- ==========================================
-- SCOPE MEMBERSHIP RLS POLICIES
-- ==========================================

-- Policy: SELECT memberships
CREATE POLICY membership_select_policy ON scope_memberships
    FOR SELECT
    USING (
        is_application_admin()           -- App admins see all
        OR is_scope_member(scope_id)     -- Scope members see scope memberships
        OR user_id = get_current_user_uuid()  -- Users see their own memberships
    );

-- Policy: INSERT memberships (scope admins only)
CREATE POLICY membership_insert_policy ON scope_memberships
    FOR INSERT
    WITH CHECK (
        is_application_admin() OR is_scope_admin(scope_id)
    );

-- Policy: UPDATE memberships
CREATE POLICY membership_update_policy ON scope_memberships
    FOR UPDATE
    USING (
        is_application_admin()
        OR is_scope_admin(scope_id)
        OR user_id = get_current_user_uuid()  -- Users can update their own
    );

-- Policy: DELETE memberships
CREATE POLICY membership_delete_policy ON scope_memberships
    FOR DELETE
    USING (
        is_application_admin() OR is_scope_admin(scope_id)
    );

-- ==========================================
-- CURATION RLS POLICIES
-- ==========================================

-- Policy: SELECT curations
CREATE POLICY curation_select_policy ON curations_new
    FOR SELECT
    USING (
        is_application_admin()
        OR is_scope_member(scope_id)
        OR EXISTS (
            SELECT 1 FROM scopes s
            WHERE s.id = curations_new.scope_id AND s.is_public = true
        )
    );

-- Policy: INSERT curations (curators and admins)
CREATE POLICY curation_insert_policy ON curations_new
    FOR INSERT
    WITH CHECK (
        get_user_scope_role(scope_id) IN ('curator', 'admin')
    );

-- Policy: UPDATE curations (creators, curators, admins)
CREATE POLICY curation_update_policy ON curations_new
    FOR UPDATE
    USING (
        is_application_admin()
        OR created_by = get_current_user_uuid()
        OR get_user_scope_role(scope_id) = 'admin'
    );
```

---

## PHASE 2: Core Backend Services

### Step 2.1: Create Enums (Python)

**File:** `backend/app/core/enums.py` (CREATE NEW)

```python
"""
Enums for scope-centric architecture.
Centralized enum definitions following DRY principle.
"""

from enum import Enum


class ApplicationRole(str, Enum):
    """Application-level roles (simplified)"""
    ADMIN = "admin"
    USER = "user"


class ScopeRole(str, Enum):
    """Scope-level roles (detailed permissions)"""
    ADMIN = "admin"
    CURATOR = "curator"
    REVIEWER = "reviewer"
    VIEWER = "viewer"

    def can_curate(self) -> bool:
        """Check if role can create/edit curations"""
        return self in (ScopeRole.ADMIN, ScopeRole.CURATOR)

    def can_review(self) -> bool:
        """Check if role can review curations"""
        return self in (ScopeRole.ADMIN, ScopeRole.REVIEWER)

    def can_manage_scope(self) -> bool:
        """Check if role can manage scope settings"""
        return self == ScopeRole.ADMIN
```

---

### Step 2.2: Create Secure RLS Context Manager

**File:** `backend/app/core/dependencies.py`

**Add imports at top:**
```python
from typing import Annotated, Callable
from uuid import UUID
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.enums import ApplicationRole, ScopeRole
from app.models.models import User, Scope, ScopeMembership
from app.core.logging import get_logger

logger = get_logger(__name__)
```

**Add at end of file:**
```python
# ============================================
# SECURE RLS CONTEXT MANAGER
# ============================================

async def set_rls_context(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
) -> None:
    """
    Set PostgreSQL RLS session variables (SECURE).

    SECURITY: Uses parameterized queries to prevent SQL injection.
    """
    try:
        # ✅ SECURE: Use parameterized queries
        db.execute(
            text("SET LOCAL app.current_user_id = :user_id"),
            {"user_id": str(current_user.id)}
        )
        db.commit()

        logger.debug("RLS context set", user_id=str(current_user.id))
    except Exception as e:
        logger.error("Failed to set RLS context", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set security context"
        )


# ============================================
# SCOPE PERMISSION DEPENDENCIES (SECURE)
# ============================================

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current authenticated and active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    return current_user


async def get_scope(
    scope_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> Scope:
    """
    Get scope by ID with permission check.

    Returns scope if:
    - User is application admin, OR
    - Scope is public, OR
    - User is a member of the scope
    """
    scope = db.query(Scope).filter(Scope.id == scope_id).first()

    if not scope:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scope not found"
        )

    # Check access permission
    if not scope.is_public and current_user.application_role != ApplicationRole.ADMIN.value:
        # Check membership
        membership = db.query(ScopeMembership).filter(
            ScopeMembership.scope_id == scope_id,
            ScopeMembership.user_id == current_user.id,
            ScopeMembership.is_active == True,
            ScopeMembership.accepted_at.isnot(None)
        ).first()

        if not membership:
            logger.warning(
                "Unauthorized scope access attempt",
                user_id=str(current_user.id),
                scope_id=str(scope_id)
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to scope denied"
            )

    return scope


def require_scope_role(required_roles: list[ScopeRole]) -> Callable:
    """
    Factory for creating scope role dependencies (SECURE).

    Prevents TOCTOU race conditions with row-level locking.
    """

    async def check_role(
        scope: Annotated[Scope, Depends(get_scope)],
        current_user: Annotated[User, Depends(get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
    ) -> ScopeMembership | None:
        """Check if user has required role in scope."""

        # Application admins bypass scope-level checks
        if current_user.application_role == ApplicationRole.ADMIN.value:
            return None

        # ✅ SECURE: Use SELECT FOR SHARE to prevent TOCTOU
        membership = db.query(ScopeMembership).filter(
            ScopeMembership.scope_id == scope.id,
            ScopeMembership.user_id == current_user.id,
            ScopeMembership.is_active == True,
            ScopeMembership.accepted_at.isnot(None)
        ).with_for_update(of=ScopeMembership, read=True).first()

        if not membership:
            logger.warning(
                "User not a scope member",
                user_id=str(current_user.id),
                scope_id=str(scope.id)
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this scope"
            )

        # Check role
        if membership.role not in [r.value for r in required_roles]:
            logger.warning(
                "Insufficient scope permissions",
                user_id=str(current_user.id),
                scope_id=str(scope.id),
                user_role=membership.role,
                required_roles=[r.value for r in required_roles]
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(r.value for r in required_roles)}"
            )

        return membership

    return check_role


# Convenience typed dependencies
RequireScopeAdmin = Annotated[
    ScopeMembership | None,
    Depends(require_scope_role([ScopeRole.ADMIN]))
]

RequireScopeCurator = Annotated[
    ScopeMembership | None,
    Depends(require_scope_role([ScopeRole.ADMIN, ScopeRole.CURATOR]))
]

RequireScopeReviewer = Annotated[
    ScopeMembership | None,
    Depends(require_scope_role([ScopeRole.ADMIN, ScopeRole.REVIEWER]))
]

RequireScopeMember = Annotated[
    ScopeMembership | None,
    Depends(require_scope_role([ScopeRole.ADMIN, ScopeRole.CURATOR, ScopeRole.REVIEWER, ScopeRole.VIEWER]))
]
```

---

### Step 2.3: Create Pydantic Schemas

**File:** `backend/app/schemas/scope_membership.py` (CREATE NEW)

```python
"""
Pydantic schemas for scope memberships.
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from app.core.enums import ScopeRole


class ScopeMembershipBase(BaseModel):
    """Base schema for scope membership"""
    role: ScopeRole
    notes: str | None = None


class ScopeMembershipCreate(ScopeMembershipBase):
    """Create scope membership (for invitations)"""
    user_id: UUID | None = None
    email: str | None = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v and not re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "curator@example.com",
                "role": "curator",
                "notes": "Expert in kidney genetics"
            }
        }
    }


class ScopeMembershipUpdate(BaseModel):
    """Update scope membership"""
    role: ScopeRole | None = None
    is_active: bool | None = None
    notes: str | None = None


class ScopeMembershipResponse(ScopeMembershipBase):
    """Scope membership response"""
    id: UUID
    scope_id: UUID
    user_id: UUID
    invited_by: UUID | None
    invited_at: datetime
    accepted_at: datetime | None
    is_active: bool

    # Include user details
    user: "UserResponse" | None = None

    model_config = {"from_attributes": True}


class ScopeMemberListResponse(BaseModel):
    """List of scope members"""
    members: list[ScopeMembershipResponse]
    total: int
```

---

## PHASE 3: API Endpoints (Week 4-5)

### Step 3.1: Scope Management Endpoints

**File:** `backend/app/api/v1/endpoints/scopes_new.py` (CREATE NEW)

```python
"""
Scope management endpoints (scope-centric architecture).
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import (
    get_current_active_user,
    get_scope,
    RequireScopeAdmin,
    set_rls_context
)
from app.core.enums import ApplicationRole
from app.schemas.scope import ScopeCreate, ScopeUpdate, ScopeResponse, ScopeListResponse
from app.crud import scope as scope_crud
from app.core.logging import get_logger

router = APIRouter(prefix="/scopes", tags=["scopes"])
logger = get_logger(__name__)


@router.post("/", response_model=ScopeResponse, status_code=status.HTTP_201_CREATED)
async def create_scope(
    scope_data: ScopeCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: None = Depends(set_rls_context)  # Set RLS context
):
    """
    Create a new curation scope.

    Any authenticated user can create a scope and becomes its admin.
    """
    logger.info("Creating scope", user_id=str(current_user.id), scope_name=scope_data.name)

    # Create scope
    scope = scope_crud.create_scope(
        db=db,
        scope_data=scope_data,
        creator_id=current_user.id
    )

    logger.info("Scope created successfully", scope_id=str(scope.id), scope_name=scope.name)
    return scope


@router.get("/", response_model=ScopeListResponse)
async def list_scopes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    is_public: bool | None = None,
    institution: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: None = Depends(set_rls_context)
):
    """
    List scopes visible to the current user.

    Returns:
    - Public scopes
    - Scopes where user is a member
    - All scopes (if application admin)
    """
    scopes = scope_crud.list_user_scopes(
        db=db,
        user_id=current_user.id,
        is_admin=(current_user.application_role == ApplicationRole.ADMIN.value),
        skip=skip,
        limit=limit,
        is_public=is_public,
        institution=institution
    )

    return {"scopes": scopes, "total": len(scopes)}


@router.get("/{scope_id}", response_model=ScopeResponse)
async def get_scope_details(
    scope: Scope = Depends(get_scope),
    _: None = Depends(set_rls_context)
):
    """Get detailed information about a scope."""
    return scope


@router.patch("/{scope_id}", response_model=ScopeResponse)
async def update_scope(
    scope_data: ScopeUpdate,
    scope: Scope = Depends(get_scope),
    membership: RequireScopeAdmin = None,  # Only admins can update
    db: Session = Depends(get_db),
    _: None = Depends(set_rls_context)
):
    """Update scope details (admin only)."""
    updated_scope = scope_crud.update_scope(
        db=db,
        scope_id=scope.id,
        scope_data=scope_data
    )

    logger.info("Scope updated", scope_id=str(scope.id))
    return updated_scope


@router.delete("/{scope_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scope(
    scope: Scope = Depends(get_scope),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: None = Depends(set_rls_context)
):
    """Delete scope (application admin only)."""
    if current_user.application_role != ApplicationRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only application administrators can delete scopes"
        )

    scope_crud.delete_scope(db=db, scope_id=scope.id)
    logger.info("Scope deleted", scope_id=str(scope.id))
```

**Register Router:** `backend/app/api/v1/api.py`

**Add import and include:**
```python
from app.api.v1.endpoints import scopes_new

# Add to router includes
api_router.include_router(scopes_new.router)
```

---

## Summary of Key Files to Create/Modify

### Create New Files:
1. `database/sql/migrations/001-006_*.sql` - All migration files
2. `backend/app/core/enums.py` - Centralized enums
3. `backend/app/schemas/scope_membership.py` - Membership schemas
4. `backend/app/api/v1/endpoints/scopes_new.py` - Scope endpoints
5. `backend/app/crud/scope_membership.py` - Membership CRUD operations

### Modify Existing Files:
1. `backend/app/models/models.py` - Add ScopeMembership model (line ~181)
2. `backend/app/models/models.py` - Update Scope relationships (line 116)
3. `backend/app/models/models.py` - Update UserNew relationships (line 158)
4. `backend/app/models/models.py` - Add application_role to UserNew (line 132)
5. `backend/app/core/dependencies.py` - Add RLS and permission functions (append)
6. `backend/app/api/v1/api.py` - Register new scopes_new router

---

## Testing Checklist

### Database Testing:
- [ ] Run migrations in correct order (001-006)
- [ ] Verify all indexes created
- [ ] Test RLS functions with sample data
- [ ] Verify FORCE ROW LEVEL SECURITY enabled
- [ ] Test RLS policies prevent cross-scope access

### API Testing:
- [ ] Create scope as regular user
- [ ] List scopes (verify RLS filtering)
- [ ] Update scope as admin
- [ ] Update scope as non-admin (should fail)
- [ ] Delete scope as admin
- [ ] Delete scope as non-admin (should fail)

### Security Testing:
- [ ] Attempt SQL injection in set_rls_context
- [ ] Verify type casting doesn't crash on invalid UUIDs
- [ ] Test TOCTOU race condition prevention
- [ ] Verify application admin can bypass scope checks
- [ ] Test RLS with 1000+ scopes (performance)

---

## Performance Benchmarks

Target performance metrics:
- Permission check: < 50ms
- Scope list (100 scopes): < 200ms
- RLS query overhead: < 10% vs non-RLS
- Concurrent users (100): No deadlocks
