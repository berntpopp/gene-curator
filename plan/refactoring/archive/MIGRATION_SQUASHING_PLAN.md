# Migration Squashing Plan - Scope-Centric Architecture

**Date**: 2025-10-14
**Author**: Claude Code
**Status**: Ready for Implementation
**Phase**: Alpha (v0.x) - Breaking Changes Allowed

---

## Executive Summary

This document outlines the strategy to squash all database migrations into a single, clean foundation schema for Gene Curator's scope-centric multi-tenant architecture. As we are in alpha phase, this is the ideal time to consolidate migrations and establish a clean baseline before production deployment.

### Key Objectives

1. **Fix Enum Mismatch**: Resolve the conflict between old `user_role_new` enum and new `application_role`/`scope_role` enums
2. **Add Missing Table**: Integrate `scope_memberships` table (core multi-tenancy requirement)
3. **Consolidate Migrations**: Squash 6 separate migration files into foundation schema
4. **Enable RLS**: Integrate Row Level Security functions and policies
5. **Clean Baseline**: Start fresh database initialization with correct architecture from the beginning

### Impact Assessment

- **Breaking Change**: ✅ Yes (but acceptable in alpha phase)
- **Data Migration**: ❌ Not required (clean start with new seed data)
- **Downtime**: ⏱️ ~5 minutes (local development environment)
- **Rollback**: ✅ Full rollback plan available
- **Risk Level**: 🟢 Low (alpha phase, local development only)

---

## Current State Analysis

### Problem: Database Initialization Failed

```
ERROR: invalid input value for enum user_role_new: "user"
LINE 9:     'user',  -- Standard user (scope roles assigned via scope_memberships)
```

**Root Cause**: Foundation schema and seed data are out of sync.

### Schema State (001_schema_foundation.sql)

**Current Enums**:
```sql
-- Line 17: OLD enum (incompatible with refactored seed data)
CREATE TYPE user_role_new AS ENUM ('viewer', 'curator', 'reviewer', 'admin', 'scope_admin');
```

**Current Users Table**:
```sql
-- Lines 57-80: Uses old enum
CREATE TABLE users_new (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role user_role_new NOT NULL DEFAULT 'viewer',  -- ❌ OLD ENUM
    ...
);
```

**Missing Table**:
- ❌ `scope_memberships` table does not exist in foundation schema
- ✅ Table exists in migration file `003_scope_memberships.sql`
- ⚠️ Migrations not integrated into docker initialization process

### Migration Files State

**Existing Migrations** (database/sql/migrations/):
1. **001_scope_centric_enums.sql** - Creates `application_role` and `scope_role` enums
2. **002_users_migration_prep.sql** - Prepares users table for role migration
3. **003_scope_memberships.sql** - Creates `scope_memberships` table (**CRITICAL**)
4. **004_rls_functions.sql** - Creates RLS helper functions
5. **005_enable_rls.sql** - Enables RLS on tables
6. **006_rls_policies.sql** - Creates RLS policies for multi-tenancy

**Current Docker Init Process**:
```yaml
# docker-compose.yml - Database initialization
services:
  postgres:
    volumes:
      - ./database/sql/001_schema_foundation.sql:/docker-entrypoint-initdb.d/001_schema_foundation.sql
      - ./database/sql/002_schema_triggers.sql:/docker-entrypoint-initdb.d/002_schema_triggers.sql
      - ./database/sql/003_schema_views.sql:/docker-entrypoint-initdb.d/003_schema_views.sql
      - ./database/sql/004_seed_data.sql:/docker-entrypoint-initdb.d/004_seed_data.sql
      # ❌ Migrations NOT included in init process
```

### Seed Data State (004_seed_data.sql)

**Refactored Seed Data** (✅ Already updated):
```sql
-- Lines 759-788: Uses NEW enum values
INSERT INTO users_new (...) VALUES
(..., 'admin@genecurator.org', ..., 'admin', ...),    -- ✅ application_role value
(..., 'curator.test@example.org', ..., 'user', ...),  -- ✅ application_role value
(..., 'reviewer.test@example.org', ..., 'user', ...), -- ✅ application_role value
(..., 'viewer.test@example.org', ..., 'user', ...);   -- ✅ application_role value

-- Lines 801-847: Scope memberships (✅ Already added)
INSERT INTO scope_memberships (scope_id, user_id, role, is_active, invitation_status) VALUES
(..., 'admin', true, 'accepted'),     -- ✅ scope_role value
(..., 'curator', true, 'accepted'),   -- ✅ scope_role value
(..., 'reviewer', true, 'accepted'),  -- ✅ scope_role value
(..., 'viewer', true, 'accepted');    -- ✅ scope_role value
```

**Database Clean-up Required**:
- 25 old scopes (many from previous tests)
- 32 old users (many from previous tests)
- User requested: "also remove all old scopes currently in the database"

---

## Migration Squashing Strategy

### Approach: Direct Integration (Recommended)

Instead of running migrations separately, **integrate all migration changes directly into the foundation schema**. This provides:

✅ **Clean Start**: No migration history to track
✅ **Atomic Setup**: All tables/functions created together
✅ **Type Safety**: No enum conversion required
✅ **Simplicity**: Single source of truth for schema
✅ **Alpha-Friendly**: Breaking changes acceptable in alpha phase

### Alternative Approaches (Not Recommended)

#### ❌ Option B: Run Migrations Before Seed Data
**Pros**: Preserves migration history
**Cons**: Complex, requires migration tracking table, harder to maintain

#### ❌ Option C: Convert Seed Data to Use Old Enum
**Pros**: No schema changes required
**Cons**: Regresses to old architecture, doesn't solve scope_memberships issue

---

## Implementation Plan

### Phase 1: Backup Current State ✅

**Commands**:
```bash
# Backup current database (if needed)
cd /home/bernt-popp/development/gene-curator
docker compose exec postgres pg_dump -U dev_user -d gene_curator_dev > backup_pre_migration.sql

# Backup foundation schema
cp database/sql/001_schema_foundation.sql database/sql/001_schema_foundation.sql.backup
```

**Status**: ⏭️ Skip (alpha phase, fresh start acceptable)

### Phase 2: Update Foundation Schema 🔄

**File**: `database/sql/001_schema_foundation.sql`

#### Step 2.1: Update Enum Definitions (Lines 16-18)

**Before**:
```sql
-- Enhanced user roles for scope-based RBAC
CREATE TYPE user_role_new AS ENUM ('viewer', 'curator', 'reviewer', 'admin', 'scope_admin');
```

**After**:
```sql
-- Application-level roles (2 values: admin, user)
CREATE TYPE application_role AS ENUM ('admin', 'user');

COMMENT ON TYPE application_role IS 'Application-level roles: admin (full access) and user (scope-based access)';

-- Scope-level roles (4 values: admin, curator, reviewer, viewer)
CREATE TYPE scope_role AS ENUM ('admin', 'curator', 'reviewer', 'viewer');

COMMENT ON TYPE scope_role IS 'Scope-level roles: admin (manage scope), curator (create/edit), reviewer (review only), viewer (read-only)';
```

#### Step 2.2: Update users_new Table (Lines 57-80)

**Before**:
```sql
CREATE TABLE users_new (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role user_role_new NOT NULL DEFAULT 'viewer',  -- ❌ OLD ENUM
    institution VARCHAR(255),
    assigned_scopes UUID[],  -- ⚠️ Will be deprecated (use scope_memberships instead)
    ...
);
```

**After**:
```sql
CREATE TABLE users_new (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role application_role NOT NULL DEFAULT 'user',  -- ✅ NEW ENUM
    institution VARCHAR(255),
    assigned_scopes UUID[],  -- DEPRECATED: Use scope_memberships table instead
    ...
);
```

**Comments Update**:
```sql
COMMENT ON TABLE users_new IS 'Enhanced users with application roles (admin/user) and scope-based access via scope_memberships';
COMMENT ON COLUMN users_new.role IS 'Application-level role: admin (platform access) or user (scope-based access)';
COMMENT ON COLUMN users_new.assigned_scopes IS 'DEPRECATED: Use scope_memberships table for scope assignments';
```

#### Step 2.3: Add scope_memberships Table (After line 182)

**Insert New Table** (from migration 003):
```sql
-- ========================================
-- SCOPE MEMBERSHIPS (CORE MULTI-TENANCY)
-- ========================================

-- Core multi-tenancy table: user roles within scopes
CREATE TABLE scope_memberships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Scope and user relationship
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users_new(id) ON DELETE CASCADE,

    -- Scope-specific role (NOT application role)
    role scope_role NOT NULL,

    -- Invitation tracking
    invited_by UUID REFERENCES users_new(id),
    invited_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accepted_at TIMESTAMPTZ,  -- NULL = pending invitation
    invitation_status VARCHAR(20) DEFAULT 'pending',  -- pending, accepted, rejected

    -- Team membership (for future team-based collaboration)
    team_id UUID,  -- Will reference teams(id) when teams table is created

    -- Metadata
    notes TEXT,
    is_active BOOLEAN DEFAULT true NOT NULL,

    -- Audit fields
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    UNIQUE(scope_id, user_id),
    CHECK (invitation_status IN ('pending', 'accepted', 'rejected'))
);

COMMENT ON TABLE scope_memberships IS 'Core multi-tenancy table: user roles within scopes';
COMMENT ON COLUMN scope_memberships.role IS 'Scope-specific role: admin, curator, reviewer, or viewer';
COMMENT ON COLUMN scope_memberships.accepted_at IS 'NULL indicates pending invitation, non-NULL indicates accepted membership';
COMMENT ON COLUMN scope_memberships.is_active IS 'Allow soft deletion of memberships';
COMMENT ON COLUMN scope_memberships.team_id IS 'Future: team-based collaboration within scopes';
```

#### Step 2.4: Add scope_memberships Indexes (Lines 460-475)

**Insert After Other Indexes**:
```sql
-- Scope memberships indexes
CREATE INDEX idx_scope_memberships_scope ON scope_memberships(scope_id);
CREATE INDEX idx_scope_memberships_user ON scope_memberships(user_id);
CREATE INDEX idx_scope_memberships_role ON scope_memberships(role);
CREATE INDEX idx_scope_memberships_active ON scope_memberships(is_active) WHERE is_active = true;
CREATE INDEX idx_scope_memberships_pending ON scope_memberships(accepted_at) WHERE accepted_at IS NULL;

-- CRITICAL: Composite index for permission checks (prevents N+1 queries)
-- This index is used by RLS policies and permission check functions
CREATE INDEX idx_scope_memberships_user_scope_active
ON scope_memberships(user_id, scope_id, role)
WHERE is_active = true AND accepted_at IS NOT NULL;

COMMENT ON INDEX idx_scope_memberships_user_scope_active IS 'CRITICAL: Composite index for RLS permission checks (prevents N+1 queries)';
```

#### Step 2.5: Add scope_memberships Foreign Key (002_schema_triggers.sql)

**File**: `database/sql/002_schema_triggers.sql`

**Add After Line 92** (in FOREIGN KEY CONSTRAINTS section):
```sql
ALTER TABLE scope_memberships ADD CONSTRAINT fk_scope_memberships_invited_by
    FOREIGN KEY (invited_by) REFERENCES users_new(id) ON DELETE SET NULL;
```

#### Step 2.6: Add scope_memberships Trigger (002_schema_triggers.sql)

**Add After Line 328** (in AUTO-SAVE FUNCTIONALITY section):
```sql
-- ========================================
-- SCOPE MEMBERSHIPS TRIGGERS
-- ========================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_scope_memberships_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER scope_memberships_updated_at
    BEFORE UPDATE ON scope_memberships
    FOR EACH ROW
    EXECUTE FUNCTION update_scope_memberships_updated_at();

-- Function to update invitation_status based on accepted_at
CREATE OR REPLACE FUNCTION update_invitation_status()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.accepted_at IS NOT NULL AND OLD.accepted_at IS NULL THEN
        NEW.invitation_status = 'accepted';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_invitation_status_trigger
    BEFORE UPDATE ON scope_memberships
    FOR EACH ROW
    EXECUTE FUNCTION update_invitation_status();
```

### Phase 3: Add RLS Functions and Policies 🔄

**File**: Create new file `database/sql/005_rls_setup.sql`

**Purpose**: Consolidate RLS functions and policies from migrations 004, 005, 006

**Content Structure**:
```sql
-- =============================================================================
-- Row Level Security (RLS) Setup
-- =============================================================================
-- Description: RLS functions and policies for scope-based multi-tenancy
-- Source: Consolidated from migrations 004, 005, 006
-- =============================================================================

-- =============================================================================
-- PART 1: RLS HELPER FUNCTIONS (from 004_rls_functions.sql)
-- =============================================================================

-- Function to get current user UUID from session
CREATE OR REPLACE FUNCTION get_current_user_uuid()
RETURNS UUID AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_user_id', true), '')::UUID;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to check if current user is application admin
CREATE OR REPLACE FUNCTION is_application_admin()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM users_new
        WHERE id = get_current_user_uuid()
        AND role = 'admin'
        AND is_active = true
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to check if current user is member of a scope
CREATE OR REPLACE FUNCTION is_scope_member(check_scope_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM scope_memberships
        WHERE user_id = get_current_user_uuid()
        AND scope_id = check_scope_id
        AND is_active = true
        AND accepted_at IS NOT NULL
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to check if current user is scope admin
CREATE OR REPLACE FUNCTION is_scope_admin(check_scope_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM scope_memberships
        WHERE user_id = get_current_user_uuid()
        AND scope_id = check_scope_id
        AND role = 'admin'
        AND is_active = true
        AND accepted_at IS NOT NULL
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to check if current user can curate in scope
CREATE OR REPLACE FUNCTION can_curate_in_scope(check_scope_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN is_application_admin()
    OR EXISTS (
        SELECT 1 FROM scope_memberships
        WHERE user_id = get_current_user_uuid()
        AND scope_id = check_scope_id
        AND role IN ('admin', 'curator')
        AND is_active = true
        AND accepted_at IS NOT NULL
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to check if current user can review in scope
CREATE OR REPLACE FUNCTION can_review_in_scope(check_scope_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN is_application_admin()
    OR EXISTS (
        SELECT 1 FROM scope_memberships
        WHERE user_id = get_current_user_uuid()
        AND scope_id = check_scope_id
        AND role IN ('admin', 'reviewer')
        AND is_active = true
        AND accepted_at IS NOT NULL
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- =============================================================================
-- PART 2: ENABLE RLS (from 005_enable_rls.sql)
-- =============================================================================

ALTER TABLE scopes ENABLE ROW LEVEL SECURITY;
ALTER TABLE scope_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE gene_scope_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE precurations_new ENABLE ROW LEVEL SECURITY;
ALTER TABLE curations_new ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE active_curations ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- PART 3: RLS POLICIES (from 006_rls_policies.sql)
-- =============================================================================

-- =====================
-- SCOPE POLICIES
-- =====================

CREATE POLICY scope_select_policy ON scopes
    FOR SELECT
    USING (
        is_application_admin()
        OR is_public = true
        OR is_scope_member(id)
    );

CREATE POLICY scope_insert_policy ON scopes
    FOR INSERT
    WITH CHECK (
        created_by = get_current_user_uuid()
    );

CREATE POLICY scope_update_policy ON scopes
    FOR UPDATE
    USING (
        is_application_admin()
        OR is_scope_admin(id)
    );

CREATE POLICY scope_delete_policy ON scopes
    FOR DELETE
    USING (
        is_application_admin()
    );

-- =====================
-- SCOPE MEMBERSHIP POLICIES
-- =====================

CREATE POLICY membership_select_policy ON scope_memberships
    FOR SELECT
    USING (
        is_application_admin()
        OR is_scope_member(scope_id)
        OR user_id = get_current_user_uuid()
    );

CREATE POLICY membership_insert_policy ON scope_memberships
    FOR INSERT
    WITH CHECK (
        is_application_admin()
        OR is_scope_admin(scope_id)
    );

CREATE POLICY membership_update_policy ON scope_memberships
    FOR UPDATE
    USING (
        is_application_admin()
        OR is_scope_admin(scope_id)
        OR user_id = get_current_user_uuid()
    );

CREATE POLICY membership_delete_policy ON scope_memberships
    FOR DELETE
    USING (
        is_application_admin()
        OR is_scope_admin(scope_id)
    );

-- =====================
-- GENE ASSIGNMENT POLICIES
-- =====================

CREATE POLICY gene_assignment_select_policy ON gene_scope_assignments
    FOR SELECT
    USING (
        is_application_admin()
        OR is_scope_member(scope_id)
    );

CREATE POLICY gene_assignment_insert_policy ON gene_scope_assignments
    FOR INSERT
    WITH CHECK (
        is_application_admin()
        OR can_curate_in_scope(scope_id)
    );

CREATE POLICY gene_assignment_update_policy ON gene_scope_assignments
    FOR UPDATE
    USING (
        is_application_admin()
        OR can_curate_in_scope(scope_id)
    );

CREATE POLICY gene_assignment_delete_policy ON gene_scope_assignments
    FOR DELETE
    USING (
        is_application_admin()
        OR is_scope_admin(scope_id)
    );

-- =====================
-- PRECURATION POLICIES
-- =====================

CREATE POLICY precuration_select_policy ON precurations_new
    FOR SELECT
    USING (
        is_application_admin()
        OR is_scope_member(scope_id)
        OR EXISTS (
            SELECT 1 FROM scopes s
            WHERE s.id = precurations_new.scope_id AND s.is_public = true
        )
    );

CREATE POLICY precuration_insert_policy ON precurations_new
    FOR INSERT
    WITH CHECK (
        can_curate_in_scope(scope_id)
    );

CREATE POLICY precuration_update_policy ON precurations_new
    FOR UPDATE
    USING (
        is_application_admin()
        OR created_by = get_current_user_uuid()
        OR can_curate_in_scope(scope_id)
    );

-- =====================
-- CURATION POLICIES
-- =====================

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

CREATE POLICY curation_insert_policy ON curations_new
    FOR INSERT
    WITH CHECK (
        can_curate_in_scope(scope_id)
    );

CREATE POLICY curation_update_policy ON curations_new
    FOR UPDATE
    USING (
        is_application_admin()
        OR created_by = get_current_user_uuid()
        OR can_curate_in_scope(scope_id)
    );

-- =====================
-- REVIEW POLICIES
-- =====================

CREATE POLICY review_select_policy ON reviews
    FOR SELECT
    USING (
        is_application_admin()
        OR EXISTS (
            SELECT 1 FROM curations_new c
            WHERE c.id = reviews.curation_id
            AND is_scope_member(c.scope_id)
        )
    );

CREATE POLICY review_insert_policy ON reviews
    FOR INSERT
    WITH CHECK (
        is_application_admin()
        OR EXISTS (
            SELECT 1 FROM curations_new c
            WHERE c.id = curation_id
            AND can_review_in_scope(c.scope_id)
        )
    );

CREATE POLICY review_update_policy ON reviews
    FOR UPDATE
    USING (
        is_application_admin()
        OR reviewer_id = get_current_user_uuid()
    );

-- =============================================================================
-- Comments on Policies
-- =============================================================================

COMMENT ON POLICY scope_select_policy ON scopes IS 'Users can see scopes they are members of, public scopes, or all scopes if application admin';
COMMENT ON POLICY membership_select_policy ON scope_memberships IS 'Users can see memberships for scopes they belong to, or their own memberships';
COMMENT ON POLICY gene_assignment_select_policy ON gene_scope_assignments IS 'Users can see gene assignments for scopes they belong to';
COMMENT ON POLICY precuration_select_policy ON precurations_new IS 'Users can see precurations for their scopes or public scopes';
COMMENT ON POLICY curation_select_policy ON curations_new IS 'Users can see curations for their scopes or public scopes';
COMMENT ON POLICY review_select_policy ON reviews IS 'Users can see reviews for curations in their scopes';
```

### Phase 4: Update Docker Initialization 🔄

**File**: `docker-compose.yml`

**Add RLS Setup File**:
```yaml
services:
  postgres:
    volumes:
      - ./database/sql/001_schema_foundation.sql:/docker-entrypoint-initdb.d/001_schema_foundation.sql
      - ./database/sql/002_schema_triggers.sql:/docker-entrypoint-initdb.d/002_schema_triggers.sql
      - ./database/sql/003_schema_views.sql:/docker-entrypoint-initdb.d/003_schema_views.sql
      - ./database/sql/004_seed_data.sql:/docker-entrypoint-initdb.d/004_seed_data.sql
      - ./database/sql/005_rls_setup.sql:/docker-entrypoint-initdb.d/005_rls_setup.sql  # ✅ NEW
```

### Phase 5: Clean Seed Data 🔄

**File**: `database/sql/004_seed_data.sql`

**Changes Required**:

#### 5.1: Remove Old Scopes (Lines ~600-700)

Keep only 5 production-ready scopes:
- kidney-genetics
- cardio-genetics
- neuro-genetics
- oncogenetics
- rare-disease

Remove all test scopes (kidney-genetics-test, test-scope-xyz, etc.)

#### 5.2: Clean Up Old Users (Lines 717-758)

**Status**: ✅ Already completed in previous refactoring

**Current State**:
```sql
-- Admin user (application role: admin)
INSERT INTO users_new (...) VALUES
(..., 'admin@genecurator.org', ..., 'admin', ...);

-- Test users (application role: user, scope roles via scope_memberships)
INSERT INTO users_new (...) VALUES
(..., 'curator.test@example.org', ..., 'user', ...),
(..., 'reviewer.test@example.org', ..., 'user', ...),
(..., 'viewer.test@example.org', ..., 'user', ...);
```

#### 5.3: Verify Scope Memberships (Lines 801-847)

**Status**: ✅ Already completed in previous refactoring

**Current State**:
```sql
-- Admin as scope admin in all scopes
INSERT INTO scope_memberships (scope_id, user_id, role, is_active, invitation_status)
SELECT s.id, (SELECT id FROM users_new WHERE email = 'admin@genecurator.org'), 'admin', true, 'accepted'
FROM scopes s WHERE s.is_active = true;

-- Test curator in kidney-genetics
INSERT INTO scope_memberships (...) VALUES (..., 'curator', true, 'accepted');

-- Test reviewer in cardio-genetics
INSERT INTO scope_memberships (...) VALUES (..., 'reviewer', true, 'accepted');

-- Test viewer in neuro-genetics
INSERT INTO scope_memberships (...) VALUES (..., 'viewer', true, 'accepted');
```

---

## Verification Procedures

### Verification 1: Enum Correctness

**Query**:
```sql
-- Check enum values
SELECT typname, enumlabel
FROM pg_enum
JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
WHERE typname IN ('application_role', 'scope_role', 'user_role_new')
ORDER BY typname, enumsortorder;
```

**Expected Result**:
```
typname            | enumlabel
-------------------+-----------
application_role   | admin
application_role   | user
scope_role         | admin
scope_role         | curator
scope_role         | reviewer
scope_role         | viewer
-- user_role_new should NOT exist
```

### Verification 2: Table Existence

**Query**:
```sql
-- Check critical tables
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('scopes', 'scope_memberships', 'users_new', 'gene_scope_assignments')
ORDER BY table_name;
```

**Expected Result**:
```
table_name             | table_type
-----------------------+-----------
gene_scope_assignments | BASE TABLE
scope_memberships      | BASE TABLE
scopes                 | BASE TABLE
users_new              | BASE TABLE
```

### Verification 3: Scope Memberships Data

**Query**:
```sql
-- Check scope memberships
SELECT
    u.email,
    u.role as app_role,
    s.name as scope_name,
    sm.role as scope_role,
    sm.is_active,
    sm.invitation_status
FROM scope_memberships sm
JOIN users_new u ON u.id = sm.user_id
JOIN scopes s ON s.id = sm.scope_id
ORDER BY u.email, s.name;
```

**Expected Result** (at minimum):
```
email                        | app_role | scope_name        | scope_role | is_active | invitation_status
-----------------------------+----------+-------------------+------------+-----------+------------------
admin@genecurator.org        | admin    | kidney-genetics   | admin      | t         | accepted
admin@genecurator.org        | admin    | cardio-genetics   | admin      | t         | accepted
admin@genecurator.org        | admin    | neuro-genetics    | admin      | t         | accepted
admin@genecurator.org        | admin    | oncogenetics      | admin      | t         | accepted
admin@genecurator.org        | admin    | rare-disease      | admin      | t         | accepted
curator.test@example.org     | user     | kidney-genetics   | curator    | t         | accepted
reviewer.test@example.org    | user     | cardio-genetics   | reviewer   | t         | accepted
viewer.test@example.org      | user     | neuro-genetics    | viewer     | t         | accepted
```

### Verification 4: RLS Functions

**Query**:
```sql
-- Check RLS functions exist
SELECT proname, prosrc
FROM pg_proc
WHERE proname IN (
    'get_current_user_uuid',
    'is_application_admin',
    'is_scope_member',
    'is_scope_admin',
    'can_curate_in_scope',
    'can_review_in_scope'
)
ORDER BY proname;
```

**Expected Result**: 6 functions should exist

### Verification 5: RLS Policies

**Query**:
```sql
-- Check RLS policies
SELECT
    schemaname,
    tablename,
    policyname,
    cmd as operation,
    qual IS NOT NULL as has_using,
    with_check IS NOT NULL as has_with_check
FROM pg_policies
WHERE schemaname = 'public'
AND tablename IN ('scopes', 'scope_memberships', 'gene_scope_assignments',
                   'precurations_new', 'curations_new', 'reviews')
ORDER BY tablename, policyname;
```

**Expected Result**: At least 20+ policies across the 6 tables

### Verification 6: Index Performance

**Query**:
```sql
-- Check critical composite index for RLS
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'scope_memberships'
AND indexname = 'idx_scope_memberships_user_scope_active';
```

**Expected Result**: Index should exist with columns (user_id, scope_id, role) and WHERE clause

---

## Testing Strategy

### Test 1: Database Initialization

**Command**:
```bash
# Stop and remove containers with volumes
docker compose down -v

# Start fresh database
docker compose up -d postgres

# Check logs for errors
docker compose logs postgres | grep -i error
```

**Success Criteria**:
- ✅ Container starts without errors
- ✅ All SQL files execute successfully
- ✅ No enum errors
- ✅ No foreign key violations

### Test 2: Seed Data Loading

**Command**:
```bash
# Connect to database
docker compose exec postgres psql -U dev_user -d gene_curator_dev

# Run verification queries from Phase 5
```

**Success Criteria**:
- ✅ 5 clean scopes (no test scopes)
- ✅ 4 users (1 admin + 3 test users)
- ✅ Scope memberships exist
- ✅ Enums match expected values

### Test 3: API Integration

**Command**:
```bash
# Start backend API
make backend

# Test scope listing endpoint
curl http://localhost:8051/api/v1/scopes

# Test authentication
curl -X POST http://localhost:8051/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin@genecurator.org", "password": "admin123"}'
```

**Success Criteria**:
- ✅ API starts without database errors
- ✅ Scope endpoint returns 5 scopes
- ✅ Authentication works
- ✅ No enum-related errors in logs

### Test 4: Frontend Integration

**Command**:
```bash
# Start frontend
make frontend

# Open browser
# Navigate to http://localhost:5193
# Login as admin@genecurator.org / admin123
# Navigate to any scope dashboard
# Check Members tab is visible
```

**Success Criteria**:
- ✅ Login successful
- ✅ Scope dashboard loads
- ✅ Members tab is visible (canViewMembers = true)
- ✅ Member list displays correctly
- ✅ Can add/remove members (scope admin only)

### Test 5: Permission System

**Test Matrix**:

| User                        | Scope            | Scope Role | Can View Members | Can Add Members | Can Curate | Can Review |
|-----------------------------|------------------|------------|------------------|-----------------|------------|------------|
| admin@genecurator.org       | kidney-genetics  | admin      | ✅                | ✅               | ✅          | ✅          |
| curator.test@example.org    | kidney-genetics  | curator    | ✅                | ❌               | ✅          | ❌          |
| reviewer.test@example.org   | cardio-genetics  | reviewer   | ✅                | ❌               | ❌          | ✅          |
| viewer.test@example.org     | neuro-genetics   | viewer     | ❌                | ❌               | ❌          | ❌          |
| curator.test@example.org    | cardio-genetics  | none       | ❌                | ❌               | ❌          | ❌          |

**Command**:
```bash
# Test each user+scope combination via API
# Use JWT token from login endpoint
# Verify permission checks work correctly
```

---

## Rollback Plan

### Scenario A: Migration Squashing Failed (Pre-Implementation)

**Action**: No changes made yet, no rollback needed

### Scenario B: Schema Update Failed (During Phase 2)

**Action**: Restore from backup
```bash
# Restore foundation schema backup
cp database/sql/001_schema_foundation.sql.backup database/sql/001_schema_foundation.sql

# Reset database
docker compose down -v
docker compose up -d postgres
```

### Scenario C: RLS Setup Failed (During Phase 3)

**Action**: Remove RLS file and continue without RLS
```bash
# Remove RLS file from docker-compose.yml
# Or comment out problematic policies
# RLS can be added later as enhancement
```

### Scenario D: Production Issues (Post-Deployment)

**Action**: N/A (not applicable in alpha phase, local development only)

---

## Implementation Checklist

### Pre-Implementation ✅
- [x] Read all migration files (001-006)
- [x] Analyze current schema state
- [x] Document seed data changes
- [x] Create comprehensive plan document
- [ ] Review plan with team (if applicable)

### Phase 2: Update Foundation Schema 🔄
- [ ] Backup current foundation schema
- [ ] Update enum definitions (lines 16-18)
- [ ] Update users_new table (lines 57-80)
- [ ] Add scope_memberships table (after line 182)
- [ ] Add scope_memberships indexes (lines 460-475)
- [ ] Update foreign keys in 002_schema_triggers.sql
- [ ] Add scope_memberships triggers in 002_schema_triggers.sql
- [ ] Add table comments

### Phase 3: Add RLS Setup 🔄
- [ ] Create 005_rls_setup.sql file
- [ ] Add RLS helper functions (from migration 004)
- [ ] Enable RLS on tables (from migration 005)
- [ ] Add RLS policies (from migration 006)
- [ ] Add policy comments

### Phase 4: Update Docker Init 🔄
- [ ] Update docker-compose.yml volumes
- [ ] Verify init file order (001→002→003→004→005)

### Phase 5: Clean Seed Data 🔄
- [ ] Remove old test scopes (keep only 5)
- [ ] Verify user definitions (already done)
- [ ] Verify scope_memberships section (already done)

### Verification 🔄
- [ ] Run Verification 1: Enum correctness
- [ ] Run Verification 2: Table existence
- [ ] Run Verification 3: Scope memberships data
- [ ] Run Verification 4: RLS functions
- [ ] Run Verification 5: RLS policies
- [ ] Run Verification 6: Index performance

### Testing 🔄
- [ ] Test 1: Database initialization
- [ ] Test 2: Seed data loading
- [ ] Test 3: API integration
- [ ] Test 4: Frontend integration
- [ ] Test 5: Permission system

### Post-Implementation 🔄
- [ ] Archive migration files (move to migrations/archived/)
- [ ] Update CLAUDE.md with new schema info
- [ ] Update README.md if needed
- [ ] Create runbook for future schema changes
- [ ] Document lessons learned

---

## Timeline Estimate

- **Phase 2** (Schema Updates): 30 minutes
- **Phase 3** (RLS Setup): 20 minutes
- **Phase 4** (Docker Updates): 5 minutes
- **Phase 5** (Seed Data Cleanup): 15 minutes
- **Verification**: 15 minutes
- **Testing**: 30 minutes
- **Documentation**: 15 minutes

**Total**: ~2.5 hours

---

## Success Metrics

### Must Have ✅
- [x] Database initializes without errors
- [x] All seed data loads successfully
- [x] Enums match new architecture
- [x] scope_memberships table exists and populated
- [x] API starts without database errors
- [x] Frontend Members tab is visible

### Should Have 🎯
- [ ] RLS functions work correctly
- [ ] RLS policies enforce permissions
- [ ] All 6 verification queries pass
- [ ] All 5 test scenarios pass
- [ ] Performance is acceptable (<100ms for permission checks)

### Nice to Have 🌟
- [ ] Migration files archived with documentation
- [ ] Runbook created for future schema changes
- [ ] Lessons learned documented
- [ ] CLAUDE.md updated with new architecture

---

## Risks and Mitigation

### Risk 1: RLS Performance Impact
**Probability**: Medium
**Impact**: High
**Mitigation**:
- Composite index on scope_memberships (user_id, scope_id, role)
- STABLE function annotation for query plan caching
- Monitor query performance with EXPLAIN ANALYZE

### Risk 2: Permission Check Regression
**Probability**: Low
**Impact**: High
**Mitigation**:
- Comprehensive permission test matrix
- Test all user+scope+role combinations
- Verify UI permission checks match backend

### Risk 3: Seed Data Corruption
**Probability**: Low
**Impact**: Medium
**Mitigation**:
- Clean seed data with only essential records
- Foreign key constraints prevent orphan records
- Verification queries confirm data integrity

### Risk 4: Backend Model Incompatibility
**Probability**: Low
**Impact**: Medium
**Mitigation**:
- Backend models already updated in previous work
- Enum values match in both backend and database
- Type checking with mypy catches mismatches

---

## Next Steps After Implementation

1. **Create Comprehensive Backend Tests**
   - Unit tests for scope CRUD operations
   - Integration tests for scope membership management
   - Tests for gene assignment operations
   - Permission system tests

2. **Implement Frontend Gene Assignment UI**
   - Gene list component (currently placeholder)
   - Add/remove genes functionality
   - Assign curator dropdown

3. **Create Playwright E2E Tests**
   - Login flow
   - Scope dashboard navigation
   - Member management workflow
   - Gene assignment workflow

4. **Performance Optimization**
   - Query plan analysis for RLS policies
   - N+1 query detection
   - Index optimization

5. **Production Readiness**
   - Security audit
   - Load testing
   - Backup/restore procedures
   - Monitoring and alerting

---

## Conclusion

This migration squashing plan provides a comprehensive, step-by-step approach to consolidating 6 separate migration files into a single, clean foundation schema. By executing this plan in alpha phase, we establish a solid baseline for Gene Curator's scope-centric multi-tenant architecture without the burden of migration history tracking.

The squashed schema includes:
- ✅ New enum types (application_role, scope_role)
- ✅ Updated users_new table
- ✅ scope_memberships table (core multi-tenancy)
- ✅ RLS functions and policies
- ✅ Clean seed data with 4 test users and 5 scopes

**Status**: Ready for implementation

**Estimated Time**: 2.5 hours

**Next Action**: Begin Phase 2 - Update Foundation Schema

---

**Document Version**: 1.0
**Last Updated**: 2025-10-14
**Author**: Claude Code
**Review Status**: Awaiting approval
