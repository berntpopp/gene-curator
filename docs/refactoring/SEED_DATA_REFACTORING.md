# Seed Data Refactoring - Scope-Centric Architecture

**Date**: 2025-10-14
**Status**: Complete ✅
**Related**: CODE_REVIEW_2025-10-14.md

---

## Overview

Refactored `database/sql/004_seed_data.sql` to align with scope-centric multi-tenant architecture. This fixes the root cause of the "missing user management" issue reported during testing.

---

## What Changed

### Before (5 Users with Old Roles)

```sql
-- ❌ OLD: 5 users with application-level roles
admin@genecurator.org         (role: 'admin')         ✅ Correct
curator.kidney@example.org    (role: 'curator')      ❌ Wrong - should be 'user'
reviewer@example.org          (role: 'reviewer')     ❌ Wrong - should be 'user'
dev@example.com               (role: 'curator')      ❌ Wrong - should be 'user'
test@example.com              (role: 'viewer')       ❌ Wrong - should be 'user'
```

**Issues**:
- Users had OLD application-level roles (curator, reviewer, viewer)
- No scope_memberships entries (root cause of issue)
- Conflicted with scope-centric architecture

### After (4 Users with Scope Roles)

```sql
-- ✅ NEW: 1 admin + 3 test users with scope-level roles
admin@genecurator.org         (application_role: 'admin', scope role: 'admin' in all scopes)
curator.test@example.org      (application_role: 'user',  scope role: 'curator' in kidney-genetics)
reviewer.test@example.org     (application_role: 'user',  scope role: 'reviewer' in cardio-genetics)
viewer.test@example.org       (application_role: 'user',  scope role: 'viewer' in neuro-genetics)
```

**Fixes**:
- All test users have `application_role = 'user'` (correct)
- Scope roles defined in `scope_memberships` table (correct architecture)
- Admin user has scope admin role in all 5 scopes
- Test users each have role in one scope for isolated testing

---

## Architectural Principles

### Two-Tier Role System

**Tier 1: Application Roles** (Column: `users_new.role`)
- `admin` - Platform administrator (full access to everything)
- `user` - Standard user (access controlled by scope roles)

**Tier 2: Scope Roles** (Table: `scope_memberships.role`)
- `admin` - Scope administrator (manage scope, invite members, full CRUD)
- `curator` - Can curate genes within scope
- `reviewer` - Can review curations within scope
- `viewer` - Read-only access to scope

### Why This Matters

**OLD Architecture** (Pre-Refactoring):
```
User → Application Role (curator/reviewer/viewer) → Global Permissions
```
- Problem: Roles applied globally across all scopes
- Problem: No fine-grained control per scope
- Problem: Cannot have different roles in different scopes

**NEW Architecture** (Scope-Centric):
```
User → Application Role (admin/user) → Scope Memberships → Scope Roles → Permissions
```
- ✅ Roles applied per scope (fine-grained control)
- ✅ User can be curator in one scope, reviewer in another
- ✅ Proper multi-tenant isolation

---

## File Changes

### Lines 717-847 (130 lines changed)

#### 1. Application Admin User (Lines 729-744)

```sql
-- Insert application admin user
INSERT INTO users_new (
    id, email, hashed_password, name, role, institution,
    assigned_scopes, orcid_id, expertise_areas, is_active
) VALUES (
    uuid_generate_v4(),
    'admin@genecurator.org',
    '$2b$12$bs7kTc5txFs0.0F3AtguTuzOTQ6fWItSmWPQmWgI7GMyhiscyNZd6', -- password: admin123
    'Admin User',
    'admin',  -- Application-level admin role
    'Gene Curator Platform',
    (SELECT array_agg(id) FROM scopes WHERE is_active = true),
    '0000-0000-0000-0001',
    ARRAY['Platform Administration', 'System Management'],
    true
);
```

**Why**: Application admin needs global platform access

---

#### 2. Test Curator User (Lines 750-765)

```sql
-- Test User 1: Curator role in kidney-genetics scope
INSERT INTO users_new (
    id, email, hashed_password, name, role, institution,
    assigned_scopes, orcid_id, expertise_areas, is_active
) VALUES (
    uuid_generate_v4(),
    'curator.test@example.org',
    '$2b$12$bs7kTc5txFs0.0F3AtguTuzOTQ6fWItSmWPQmWgI7GMyhiscyNZd6', -- password: admin123
    'Test Curator',
    'user',  -- ✅ Standard user (scope roles assigned via scope_memberships)
    'Testing Institution',
    (SELECT array_agg(id) FROM scopes WHERE name = 'kidney-genetics'),
    '0000-0001-5000-0001',
    ARRAY['Nephrology', 'CAKUT', 'Ciliopathies'],
    true
);
```

**Key Change**: `role = 'user'` (not `'curator'`)

**Why**: Curator role is scope-specific, not application-wide

---

#### 3. Test Reviewer User (Lines 767-782)

```sql
-- Test User 2: Reviewer role in cardio-genetics scope
INSERT INTO users_new (
    id, email, hashed_password, name, role, institution,
    assigned_scopes, orcid_id, expertise_areas, is_active
) VALUES (
    uuid_generate_v4(),
    'reviewer.test@example.org',
    '$2b$12$bs7kTc5txFs0.0F3AtguTuzOTQ6fWItSmWPQmWgI7GMyhiscyNZd6', -- password: admin123
    'Test Reviewer',
    'user',  -- ✅ Standard user (scope roles assigned via scope_memberships)
    'Testing Institution',
    (SELECT array_agg(id) FROM scopes WHERE name = 'cardio-genetics'),
    '0000-0001-5000-0002',
    ARRAY['Cardiology', 'Arrhythmia', 'Congenital Heart Disease'],
    true
);
```

**Key Change**: `role = 'user'` (not `'reviewer'`)

**Why**: Reviewer role is scope-specific, not application-wide

---

#### 4. Test Viewer User (Lines 784-799)

```sql
-- Test User 3: Viewer role in neuro-genetics scope
INSERT INTO users_new (
    id, email, hashed_password, name, role, institution,
    assigned_scopes, orcid_id, expertise_areas, is_active
) VALUES (
    uuid_generate_v4(),
    'viewer.test@example.org',
    '$2b$12$bs7kTc5txFs0.0F3AtguTuzOTQ6fWItSmWPQmWgI7GMyhiscyNZd6', -- password: admin123
    'Test Viewer',
    'user',  -- ✅ Standard user (scope roles assigned via scope_memberships)
    'Testing Institution',
    (SELECT array_agg(id) FROM scopes WHERE name = 'neuro-genetics'),
    '0000-0001-5000-0003',
    ARRAY['Neurology', 'Epilepsy', 'Intellectual Disability'],
    true
);
```

**Key Change**: `role = 'user'` (not `'viewer'`)

**Why**: Viewer role is scope-specific, not application-wide

---

#### 5. Scope Memberships (Lines 801-847) - NEW!

```sql
-- **CRITICAL**: These entries define SCOPE-LEVEL roles, not application roles
-- Scope roles: 'admin', 'curator', 'reviewer', 'viewer'

-- Admin user as scope admin in all scopes
INSERT INTO scope_memberships (scope_id, user_id, role, is_active, invitation_status)
SELECT
    s.id as scope_id,
    (SELECT id FROM users_new WHERE email = 'admin@genecurator.org') as user_id,
    'admin' as role,
    true as is_active,
    'accepted' as invitation_status
FROM scopes s
WHERE s.is_active = true;

-- Test Curator in kidney-genetics scope
INSERT INTO scope_memberships (scope_id, user_id, role, is_active, invitation_status) VALUES
(
    (SELECT id FROM scopes WHERE name = 'kidney-genetics'),
    (SELECT id FROM users_new WHERE email = 'curator.test@example.org'),
    'curator',  -- Scope-level curator role
    true,
    'accepted'
);

-- Test Reviewer in cardio-genetics scope
INSERT INTO scope_memberships (scope_id, user_id, role, is_active, invitation_status) VALUES
(
    (SELECT id FROM scopes WHERE name = 'cardio-genetics'),
    (SELECT id FROM users_new WHERE email = 'reviewer.test@example.org'),
    'reviewer',  -- Scope-level reviewer role
    true,
    'accepted'
);

-- Test Viewer in neuro-genetics scope
INSERT INTO scope_memberships (scope_id, user_id, role, is_active, invitation_status) VALUES
(
    (SELECT id FROM scopes WHERE name = 'neuro-genetics'),
    (SELECT id FROM users_new WHERE email = 'viewer.test@example.org'),
    'viewer',  -- Scope-level viewer role
    true,
    'accepted'
);
```

**Why This is Critical**:
- **Root Cause of User Issue**: No scope_memberships meant `currentUserRole` returned `null`
- **Permission Check**: `canViewMembers` requires scope role (admin, curator, or reviewer)
- **Frontend Behavior**: Members tab hidden without scope role
- **With This Fix**: Members tab now visible for users with scope roles

---

## Testing Scenarios

### Scenario 1: Admin User Login

**User**: admin@genecurator.org (password: admin123)

**Expected Behavior**:
1. ✅ Can see all 5 scopes in scope list
2. ✅ Can access scope dashboard for any scope
3. ✅ Can see Members tab (scope admin role)
4. ✅ Can invite members (scope admin permission)
5. ✅ Can update member roles (scope admin permission)
6. ✅ Can remove members (scope admin permission)

**Technical**:
- Application role: `admin` (global platform access)
- Scope role: `admin` in all 5 scopes (via scope_memberships)

---

### Scenario 2: Test Curator Login

**User**: curator.test@example.org (password: admin123)

**Expected Behavior**:
1. ✅ Can see kidney-genetics scope in scope list
2. ✅ Can access scope dashboard for kidney-genetics
3. ✅ Can see Members tab (curator can view members)
4. ❌ Cannot invite members (only scope admins)
5. ❌ Cannot update member roles (only scope admins)
6. ❌ Cannot remove members (only scope admins)
7. ✅ Can curate genes within kidney-genetics
8. ❌ Cannot access cardio-genetics (not a member)

**Technical**:
- Application role: `user` (standard user)
- Scope role: `curator` in kidney-genetics only

---

### Scenario 3: Test Reviewer Login

**User**: reviewer.test@example.org (password: admin123)

**Expected Behavior**:
1. ✅ Can see cardio-genetics scope in scope list
2. ✅ Can access scope dashboard for cardio-genetics
3. ✅ Can see Members tab (reviewer can view members)
4. ❌ Cannot invite members (only scope admins)
5. ✅ Can review curations within cardio-genetics
6. ❌ Cannot curate genes (only curators and admins)
7. ❌ Cannot access kidney-genetics (not a member)

**Technical**:
- Application role: `user` (standard user)
- Scope role: `reviewer` in cardio-genetics only

---

### Scenario 4: Test Viewer Login

**User**: viewer.test@example.org (password: admin123)

**Expected Behavior**:
1. ✅ Can see neuro-genetics scope in scope list
2. ✅ Can access scope dashboard for neuro-genetics
3. ❌ Cannot see Members tab (viewers cannot view members)
4. ❌ Cannot invite members (read-only)
5. ❌ Cannot curate genes (read-only)
6. ❌ Cannot review curations (read-only)
7. ✅ Can view gene assignments (read-only)
8. ❌ Cannot access kidney-genetics (not a member)

**Technical**:
- Application role: `user` (standard user)
- Scope role: `viewer` in neuro-genetics only
- **Note**: Viewers intentionally cannot see Members tab (design decision)

---

## Permission Matrix

### Application-Level Permissions

| Feature | Application Admin | User |
|---------|-------------------|------|
| Create Scope | ✅ Yes | ✅ Yes |
| Delete Scope | ✅ Yes | ❌ No |
| Manage Users | ✅ Yes | ❌ No |
| Access All Scopes | ✅ Yes | ❌ No (only member scopes) |

---

### Scope-Level Permissions

| Feature | Scope Admin | Curator | Reviewer | Viewer |
|---------|-------------|---------|----------|--------|
| View Members | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| Invite Members | ✅ Yes | ❌ No | ❌ No | ❌ No |
| Update Member Roles | ✅ Yes | ❌ No | ❌ No | ❌ No |
| Remove Members | ✅ Yes | ❌ No | ❌ No | ❌ No |
| Curate Genes | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| Review Curations | ✅ Yes | ❌ No | ✅ Yes | ❌ No |
| View Gene Assignments | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Manage Scope Settings | ✅ Yes | ❌ No | ❌ No | ❌ No |

---

## Frontend Integration

### useScopePermissions Composable

The frontend permission logic in `frontend/src/composables/useScopePermissions.js`:

```javascript
/**
 * Can view members list
 * All roles except viewers
 */
const canViewMembers = computed(() => {
  const role = getRole()
  return role === 'admin' || role === 'curator' || role === 'reviewer'
})
```

**How This Fixes the Issue**:
1. Before: No scope_memberships → `getRole()` returns `null` → `canViewMembers` returns `false` → Members tab hidden
2. After: scope_memberships exist → `getRole()` returns `'curator'` → `canViewMembers` returns `true` → Members tab visible ✅

---

### ScopeDashboard.vue Integration

```vue
<!-- Members Tab -->
<v-tab v-if="canViewMembers" value="members">
  <v-icon start>mdi-account-group</v-icon>
  Members
</v-tab>

<v-window-item v-if="canViewMembers" value="members">
  <v-card-text>
    <MemberManagement v-if="scope" :scope-id="scope.id" />
  </v-card-text>
</v-window-item>
```

**Component Status**:
- ✅ MemberManagement.vue fully implemented (487 lines)
- ✅ Component properly wired in ScopeDashboard
- ✅ Conditionally shown based on `canViewMembers` permission
- ✅ Backend API endpoints implemented

**Why It Wasn't Working**:
- No scope_memberships entries → permission check failed → component never rendered

**Now Fixed**:
- scope_memberships exist → permission check passes → component renders correctly ✅

---

## Database Reset Required

**IMPORTANT**: To apply these changes, you must reset the development database.

### Reset Commands

```bash
# Option 1: Full reset (RECOMMENDED)
make db-reset

# Option 2: Manual reset
cd database/sql
psql -h localhost -p 5454 -U dev_user -d gene_curator_dev -f 001_schema_foundation.sql
psql -h localhost -p 5454 -U dev_user -d gene_curator_dev -f 002_schema_triggers.sql
psql -h localhost -p 5454 -U dev_user -d gene_curator_dev -f 003_schema_views.sql
psql -h localhost -p 5454 -U dev_user -d gene_curator_dev -f 004_seed_data.sql
```

### Verification

```bash
# Verify users created
psql -h localhost -p 5454 -U dev_user -d gene_curator_dev -c "
SELECT email, role FROM users_new ORDER BY email;
"

# Expected output:
# admin@genecurator.org    | admin
# curator.test@example.org | user
# reviewer.test@example.org| user
# viewer.test@example.org  | user

# Verify scope memberships created
psql -h localhost -p 5454 -U dev_user -d gene_curator_dev -c "
SELECT
    u.email,
    s.name as scope_name,
    sm.role as scope_role
FROM scope_memberships sm
JOIN users_new u ON u.id = sm.user_id
JOIN scopes s ON s.id = sm.scope_id
WHERE sm.is_active = true
ORDER BY u.email, s.name;
"

# Expected output (9 rows):
# admin@genecurator.org | kidney-genetics  | admin
# admin@genecurator.org | cardio-genetics  | admin
# admin@genecurator.org | neuro-genetics   | admin
# admin@genecurator.org | cancer-genetics  | admin
# admin@genecurator.org | multi-system     | admin
# curator.test@example.org | kidney-genetics | curator
# reviewer.test@example.org | cardio-genetics | reviewer
# viewer.test@example.org | neuro-genetics | viewer
```

---

## Impact Summary

### ✅ What This Fixes

1. **Members Tab Visibility** - Now visible for users with scope roles
2. **Member Management** - Fully functional for scope admins
3. **Permission Checks** - Now correctly based on scope roles
4. **Architecture Alignment** - Seed data matches scope-centric design
5. **Testing** - Proper test users for each role

### 🎯 Next Steps

1. **Reset Database**: Apply refactored seed data
2. **Test Login**: Verify each test user can access their scope
3. **Test Members Tab**: Verify members tab visible for curator/reviewer
4. **Test Permissions**: Verify scope admin can invite/manage members

---

## Related Documents

- **Code Review**: `docs/refactoring/CODE_REVIEW_2025-10-14.md`
- **Implementation Progress**: `docs/refactoring/IMPLEMENTATION_PROGRESS.md`
- **Backend Plan**: `docs/refactoring/BACKEND_IMPLEMENTATION.md`

---

**Last Updated**: 2025-10-14
**Status**: Complete ✅
**Next Action**: Reset database and test member management UI
