# RLS Test Fix Plan - 5 Failing Tests

**Date**: 2025-10-14
**Status**: Investigation Complete, Ready for Implementation
**Tests Failing**: 5 / 250 total (98% passing)

---

## 🔍 Investigation Summary

### Current Test Status
```
✅ Passing: 245 tests (98%)
❌ Failing: 5 tests (2%)
⚠️ Warnings: 103 (mostly SQLAlchemy relationship warnings + datetime deprecations)
```

### Failing Tests
1. `test_user_cannot_see_other_user_scope` - User1 should NOT see User2's scope
2. `test_tenant_isolation_multiple_scopes` - Complete tenant isolation test
3. `test_rls_prevents_direct_membership_access` - Membership isolation test
4. `test_public_scope_visibility` - Public scopes should be visible to all
5. `test_rls_enforcement_after_membership_removal` - RLS updates after membership changes

### RLS Infrastructure Status
✅ **RLS is enabled** on scopes and scope_memberships tables
✅ **RLS functions exist** (is_scope_member, is_application_admin, etc.)
✅ **Test user configured** (test_user without BYPASSRLS privilege)
✅ **set_rls_context() function exists** in app/core/deps.py

---

## 🎯 Root Cause Analysis

Based on test output and code investigation:

### Issue 1: RLS Context Not Being Applied in Tests
**Problem**: Tests use fixtures with separate transactions, and `set_rls_context(db, user)` may not be persisting correctly across savepoint boundaries.

**Evidence**:
- `conftest.py` uses `set_test_user_context(db, str(user_id))` which uses session-level SET
- Test fixtures use `set_rls_context(db, user)` which also uses session-level SET
- These may be conflicting or not being applied before queries

**Impact**: RLS policies not enforced in test queries → all scopes visible regardless of membership

---

### Issue 2: Test Fixtures Create Memberships After Scope Creation
**Problem**: The fixtures create scopes first, then create memberships separately. This may cause timing issues.

**Evidence** from test_rls_policies.py:
```python
@pytest.fixture
def scope1(self, db: Session, user1: UserNew, test_run_id: str) -> Scope:
    set_rls_context(db, user1)  # Set context
    scope = scope_crud.create_with_owner(...)  # Create scope

    # Then create membership
    membership_data = ScopeMembershipCreate(...)
    scope_membership_crud.create_invitation(...)  # Creates membership

    return scope
```

**Issue**: Between scope creation and membership creation, RLS context may need to be refreshed.

---

### Issue 3: RLS Policies May Not Be Checking `accepted_at IS NOT NULL`
**Problem**: RLS policies need to verify membership is accepted, not just pending.

**Evidence Needed**: Need to verify actual RLS policy implementation in database.

**Expected Policy**:
```sql
CREATE POLICY scope_select_policy ON scopes
    FOR SELECT
    USING (
        is_application_admin()
        OR is_public = true
        OR EXISTS (
            SELECT 1 FROM scope_memberships
            WHERE scope_id = scopes.id
            AND user_id = get_current_user_uuid()
            AND is_active = true
            AND accepted_at IS NOT NULL  -- Critical condition
        )
    );
```

---

### Issue 4: Test Database State May Be Polluted
**Problem**: Tests may be seeing scopes from seed data or other tests due to transaction isolation issues.

**Evidence**: Tests should use unique identifiers (`test_run_id`) but RLS filtering may not be working.

---

### Issue 5: SQLAlchemy Relationship Warnings (Secondary Issue)
**Problem**: 9 different relationship warnings about conflicting relationships.

**Impact**: Low (warnings only), but should be fixed for clean test output.

**Example**:
```
SAWarning: relationship 'WorkflowPair.precuration_schema' will copy column...
Solution: Add overlaps="precuration_workflow_pairs" to relationship definition
```

---

## 📋 Fix Plan (Prioritized)

### **Phase 1: Verify RLS Policies (Day 1, 2-3 hours)**

#### Step 1.1: Inspect Current RLS Policies
```bash
# Check RLS functions
docker compose exec postgres psql -U dev_user -d gene_curator_dev -c "\df+ is_scope_member"
docker compose exec postgres psql -U dev_user -d gene_curator_dev -c "\df+ get_current_user_uuid"

# Check RLS policies
docker compose exec postgres psql -U dev_user -d gene_curator_dev -c "
SELECT policyname, tablename, cmd, qual, with_check
FROM pg_policies
WHERE tablename IN ('scopes', 'scope_memberships')
ORDER BY tablename, policyname;
"

# Test RLS function manually
docker compose exec postgres psql -U test_user -d gene_curator_dev -c "
SET app.current_user_id = '<uuid_here>';
SELECT is_scope_member('<scope_uuid_here>');
"
```

**Expected Result**: Policies should check `accepted_at IS NOT NULL` condition.

**If Missing**: Update RLS policies in `database/sql/005_rls_setup.sql`

---

#### Step 1.2: Verify RLS Functions Return Correct Results
```bash
# Test get_current_user_uuid
docker compose exec postgres psql -U test_user -d gene_curator_dev -c "
SET app.current_user_id = '<test_uuid>';
SELECT get_current_user_uuid(), current_setting('app.current_user_id');
"

# Test is_scope_member function
docker compose exec postgres psql -U test_user -d gene_curator_dev -c "
-- Set context
SET app.current_user_id = '<user1_uuid>';

-- Check membership (should return true for owned scope)
SELECT is_scope_member('<scope1_uuid>');

-- Check membership (should return false for other scope)
SELECT is_scope_member('<scope2_uuid>');
"
```

**Expected**: is_scope_member returns true/false correctly based on membership.

---

### **Phase 2: Fix Test Fixtures (Day 1, 2-3 hours)**

#### Step 2.1: Update scope1 and scope2 Fixtures
**File**: `backend/app/tests/security/test_rls_policies.py`

**Current Code** (lines 84-137):
```python
@pytest.fixture
def scope1(self, db: Session, user1: UserNew, test_run_id: str) -> Scope:
    set_rls_context(db, user1)
    scope_data = ScopeCreate(...)
    scope = scope_crud.create_with_owner(db, obj_in=scope_data, owner_id=user1.id)

    # Create membership
    membership_data = ScopeMembershipCreate(...)
    scope_membership_crud.create_invitation(...)

    return scope
```

**Problem**: RLS context may not persist correctly.

**Fix**:
```python
@pytest.fixture
def scope1(self, db: Session, user1: UserNew, test_run_id: str) -> Scope:
    # Set RLS context FIRST
    set_rls_context(db, user1)

    # Create scope
    scope_data = ScopeCreate(
        name=f"scope1-rls-test-{test_run_id}",
        display_name=f"Scope 1 RLS Test {test_run_id}",
        description="Test scope for RLS",
        institution="Test Inst",
        is_public=False,
        default_workflow_pair_id=None,
    )
    scope = scope_crud.create_with_owner(db, obj_in=scope_data, owner_id=user1.id)
    db.flush()  # Ensure scope is in DB

    # Create membership with immediate acceptance
    membership_data = ScopeMembershipCreate(
        user_id=user1.id,
        email=None,
        role=ScopeRole.ADMIN,
        notes="Owner",
        team_id=None,
    )
    membership = scope_membership_crud.create_invitation(
        db, scope_id=scope.id, invited_by_id=user1.id, obj_in=membership_data
    )
    db.flush()  # Ensure membership is in DB

    # CRITICAL: Refresh RLS context after membership creation
    # This ensures subsequent queries see the membership
    db.execute(text(f"SET app.current_user_id = '{user1.id}'"))

    # Verify membership was created correctly
    verify_result = db.execute(
        text("""
            SELECT COUNT(*) FROM scope_memberships
            WHERE scope_id = :scope_id
            AND user_id = :user_id
            AND is_active = true
            AND accepted_at IS NOT NULL
        """),
        {"scope_id": str(scope.id), "user_id": str(user1.id)}
    ).scalar()

    if verify_result != 1:
        raise RuntimeError(
            f"Membership verification failed: expected 1, got {verify_result}"
        )

    return scope
```

**Apply same fix to `scope2` fixture**.

---

#### Step 2.2: Add Debug Helper Fixture
Add to `backend/app/tests/security/test_rls_policies.py`:

```python
@pytest.fixture
def debug_rls_state(self, db: Session) -> None:
    """Debug fixture to print RLS state."""
    def _debug():
        # Get current RLS context
        context = db.execute(text("SHOW app.current_user_id")).scalar()

        # Get membership count
        membership_count = db.execute(
            text("SELECT COUNT(*) FROM scope_memberships")
        ).scalar()

        # Get scope count
        scope_count = db.execute(
            text("SELECT COUNT(*) FROM scopes")
        ).scalar()

        print(f"\n=== RLS DEBUG ===")
        print(f"Current context: {context}")
        print(f"Total memberships: {membership_count}")
        print(f"Total scopes: {scope_count}")
        print(f"=================\n")

    return _debug
```

Usage in tests:
```python
def test_user_cannot_see_other_user_scope(
    self, db: Session, user1: UserNew, user2: UserNew, scope2: Scope, debug_rls_state
) -> None:
    debug_rls_state()  # Print state before test
    set_rls_context(db, user1)
    debug_rls_state()  # Print state after context set

    scopes = db.execute(select(Scope).where(Scope.id == scope2.id)).scalars().all()
    debug_rls_state()  # Print state after query

    assert len(scopes) == 0
```

---

### **Phase 3: Fix RLS Policies (Day 2, 3-4 hours)**

#### Step 3.1: Review and Update RLS Policies
**File**: `database/sql/005_rls_setup.sql`

**Check Policy for Scopes**:
```sql
-- Current policy (need to verify)
CREATE POLICY scope_select_policy ON scopes
    FOR SELECT
    USING (...);  -- Need to inspect actual implementation
```

**Expected Policy** (ensure this logic exists):
```sql
CREATE POLICY scope_select_policy ON scopes
    FOR SELECT
    USING (
        -- Application admins see all scopes
        is_application_admin()
        OR
        -- Public scopes visible to all
        is_public = true
        OR
        -- User is an active, accepted member of the scope
        EXISTS (
            SELECT 1
            FROM scope_memberships sm
            WHERE sm.scope_id = scopes.id
            AND sm.user_id = get_current_user_uuid()
            AND sm.is_active = true
            AND sm.accepted_at IS NOT NULL  -- CRITICAL: Only accepted memberships
        )
    );
```

**If Policy Needs Update**:
1. Drop old policy:
```sql
DROP POLICY IF EXISTS scope_select_policy ON scopes;
```

2. Create new policy with correct logic

3. Test manually:
```bash
docker compose exec postgres psql -U test_user -d gene_curator_dev -c "
-- Set context
SET app.current_user_id = '<user1_uuid>';

-- Should return 1 scope (user1's scope only)
SELECT COUNT(*) FROM scopes WHERE id IN ('<scope1_uuid>', '<scope2_uuid>');
"
```

---

#### Step 3.2: Verify Other RLS Policies
Check policies for:
- `scope_memberships` - Members can see memberships of their scopes
- `gene_scope_assignments` - Scope-based filtering
- `precurations` - Scope-based filtering
- `curations` - Scope-based filtering

**Verification Script**:
```bash
# Generate verification script
cat > /tmp/verify_rls.sql <<'EOF'
-- Set context to user1
SET app.current_user_id = '<user1_uuid>';

-- Test 1: User1 should see their scope
SELECT 'Test 1: User sees own scope' as test,
       COUNT(*) as result,
       1 as expected
FROM scopes
WHERE id = '<scope1_uuid>';

-- Test 2: User1 should NOT see user2's scope
SELECT 'Test 2: User cannot see other scope' as test,
       COUNT(*) as result,
       0 as expected
FROM scopes
WHERE id = '<scope2_uuid>';

-- Test 3: Check membership visibility
SELECT 'Test 3: User sees own memberships' as test,
       COUNT(*) as result,
       1 as expected
FROM scope_memberships
WHERE scope_id = '<scope1_uuid>'
AND user_id = '<user1_uuid>';

-- Test 4: User cannot see other user's memberships
SELECT 'Test 4: User cannot see other memberships' as test,
       COUNT(*) as result,
       0 as expected
FROM scope_memberships
WHERE scope_id = '<scope2_uuid>';
EOF

# Run verification
docker compose exec -T postgres psql -U test_user -d gene_curator_dev < /tmp/verify_rls.sql
```

---

### **Phase 4: Fix SQLAlchemy Warnings (Day 2, 1-2 hours)**

#### Step 4.1: Fix Relationship Overlaps
**File**: `backend/app/models/models.py`

**Problem**: Multiple relationships accessing same foreign keys without declaring overlaps.

**Fix Example** (WorkflowPair model):
```python
# Current (line ~466)
precuration_schema: Mapped["CurationSchema | None"] = relationship(
    "CurationSchema", foreign_keys=[precuration_schema_id]
)

# Fixed
precuration_schema: Mapped["CurationSchema | None"] = relationship(
    "CurationSchema",
    foreign_keys=[precuration_schema_id],
    overlaps="precuration_workflow_pairs"  # ADD THIS
)
```

**All Relationships to Fix** (9 warnings):
1. `WorkflowPair.precuration_schema` - add `overlaps="precuration_workflow_pairs"`
2. `WorkflowPair.curation_schema` - add `overlaps="curation_workflow_pairs"`
3. `WorkflowPair.scope_defaults` - add `overlaps="default_workflow_pair"`
4. `Gene.creator` - add `overlaps="created_genes"`
5. `GeneScopeAssignment.assigned_curator` - add `overlaps="curator_assignments"`
6. `PrecurationNew.creator` - add `overlaps="created_precurations"`
7. `CurationNew.creator` - add `overlaps="created_curations"`
8. `CurationNew.approver` - add `overlaps="approved_curations"`
9. `Review.reviewer` - add `overlaps="reviews_assigned"`

---

#### Step 4.2: Fix Datetime Deprecation Warnings
**File**: `backend/app/crud/scope_membership.py`

**Problem** (lines 106-107):
```python
invited_at=datetime.utcnow(),  # Deprecated
accepted_at=datetime.utcnow()  # Deprecated
```

**Fix**:
```python
from datetime import datetime, UTC

# Replace datetime.utcnow() with:
invited_at=datetime.now(UTC),
accepted_at=datetime.now(UTC)
```

**Also check in**:
- `app/core/security.py` (lines 44, 46, 87)
- Search for all `utcnow()` usage:
```bash
grep -r "datetime.utcnow()" backend/app/
```

---

### **Phase 5: Verify Fixes (Day 2-3, 2 hours)**

#### Step 5.1: Run Failing Tests
```bash
cd backend

# Run just the 5 failing tests
uv run pytest app/tests/security/test_rls_policies.py::TestRLSPolicies::test_user_cannot_see_other_user_scope -vv
uv run pytest app/tests/security/test_rls_policies.py::TestRLSPolicies::test_tenant_isolation_multiple_scopes -vv
uv run pytest app/tests/security/test_rls_policies.py::TestRLSPolicies::test_rls_prevents_direct_membership_access -vv
uv run pytest app/tests/security/test_rls_policies.py::TestRLSPolicies::test_public_scope_visibility -vv
uv run pytest app/tests/security/test_rls_policies.py::TestRLSPolicies::test_rls_enforcement_after_membership_removal -vv
```

**Expected Result**: All 5 tests passing.

---

#### Step 5.2: Run Full RLS Test Suite
```bash
cd backend
uv run pytest app/tests/security/test_rls_policies.py -v
```

**Expected Result**: All 15 tests passing (10 already passing + 5 fixed).

---

#### Step 5.3: Run All Tests
```bash
cd backend
uv run pytest app/tests/ -v
```

**Expected Result**: 250 tests passing, 0 failures.

---

#### Step 5.4: Check Warning Count
```bash
cd backend
uv run pytest app/tests/ --tb=no 2>&1 | tail -5
```

**Expected Result**:
- ✅ 250 passed
- ⚠️ Warnings reduced from 103 to ~5 (after fixing relationship warnings and datetime)

---

## 📊 Implementation Checklist

### Day 1 (6 hours)
- [ ] **Phase 1.1**: Inspect current RLS policies (1 hour)
- [ ] **Phase 1.2**: Manually test RLS functions (1 hour)
- [ ] **Phase 2.1**: Fix scope1 and scope2 fixtures (2 hours)
- [ ] **Phase 2.2**: Add debug helper fixture (30 min)
- [ ] **Test**: Run failing tests with debug output (30 min)
- [ ] **Commit**: "fix(tests): improve RLS test fixtures with verification"

### Day 2 (7 hours)
- [ ] **Phase 3.1**: Review and update RLS policies if needed (3 hours)
- [ ] **Phase 3.2**: Create and run RLS verification script (1 hour)
- [ ] **Phase 4.1**: Fix SQLAlchemy relationship warnings (2 hours)
- [ ] **Phase 4.2**: Fix datetime deprecation warnings (30 min)
- [ ] **Commit**: "fix(rls): update RLS policies and fix warnings"
- [ ] **Test**: Run all RLS tests (30 min)

### Day 3 (2 hours)
- [ ] **Phase 5.1**: Run failing tests individually (30 min)
- [ ] **Phase 5.2**: Run full RLS test suite (15 min)
- [ ] **Phase 5.3**: Run all 250 tests (30 min)
- [ ] **Phase 5.4**: Verify warning count reduced (15 min)
- [ ] **Documentation**: Update test status in REFACTORING_STATUS_SUMMARY.md (30 min)
- [ ] **Commit**: "test(rls): all RLS security tests passing"

---

## 🎯 Success Criteria

### Must Have
- ✅ All 5 failing RLS tests passing
- ✅ No regression in 245 passing tests
- ✅ RLS policies enforce tenant isolation correctly
- ✅ Manual RLS verification script confirms isolation

### Should Have
- ✅ SQLAlchemy relationship warnings fixed (9 warnings)
- ✅ Datetime deprecation warnings fixed (~20 warnings)
- ✅ Debug helper fixture for future RLS debugging

### Nice to Have
- ✅ RLS verification script added to test suite
- ✅ Documentation updated with RLS testing patterns
- ✅ CI/CD integration for RLS tests

---

## 🔍 Risk Assessment

### Low Risk
- **Fixture Updates**: Only affects test setup, not production code
- **Debug Helpers**: Optional debugging, no impact on actual tests
- **Warning Fixes**: Cosmetic improvements, no logic changes

### Medium Risk
- **RLS Policy Updates**: Could affect production security if policies are wrong
  - **Mitigation**: Test thoroughly with verification script before deployment
  - **Mitigation**: Have rollback SQL ready

### High Risk (If Applicable)
- **None identified** - All changes are isolated to tests or verified policies

---

## 📝 Verification Queries

### Verify RLS Functions
```sql
-- Test get_current_user_uuid()
SET app.current_user_id = '123e4567-e89b-12d3-a456-426614174000';
SELECT get_current_user_uuid();
-- Expected: 123e4567-e89b-12d3-a456-426614174000

-- Test is_scope_member()
SELECT is_scope_member('scope_uuid_here');
-- Expected: true/false based on membership

-- Test is_application_admin()
SELECT is_application_admin();
-- Expected: true for admin role, false otherwise
```

### Verify RLS Policies Applied
```sql
-- Check RLS is enabled
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('scopes', 'scope_memberships');
-- Expected: rowsecurity = t for both

-- Check policies exist
SELECT COUNT(*) FROM pg_policies
WHERE tablename IN ('scopes', 'scope_memberships');
-- Expected: At least 8 policies (4 per table: SELECT, INSERT, UPDATE, DELETE)

-- Check FORCE RLS
SELECT tablename, (relforcerowsecurity) FROM pg_class
WHERE relname IN ('scopes', 'scope_memberships');
-- Expected: relforcerowsecurity = t for both
```

### Verify Test Database State
```sql
-- Count users
SELECT COUNT(*), role FROM users GROUP BY role;
-- Expected: At least admin + 2 test users

-- Count scopes
SELECT COUNT(*) FROM scopes;
-- Expected: At least seed data scopes

-- Count memberships
SELECT COUNT(*), is_active, (accepted_at IS NOT NULL) as accepted
FROM scope_memberships
GROUP BY is_active, accepted;
-- Expected: Mix of active/inactive, accepted/pending
```

---

## 📖 Related Documentation

- `database/sql/005_rls_setup.sql` - RLS policy definitions
- `backend/app/core/deps.py` - set_rls_context() function
- `backend/app/tests/conftest.py` - Test fixtures and helpers
- `backend/app/tests/security/test_rls_policies.py` - RLS test suite
- SQLAlchemy RLS Pattern: https://docs.sqlalchemy.org/en/20/orm/session_transaction.html

---

## 💡 Future Improvements

### After Tests Pass
1. **Add More RLS Edge Case Tests**
   - Concurrent membership changes
   - Membership role changes
   - Scope deactivation scenarios

2. **Performance Testing**
   - Verify composite index usage in RLS queries
   - Check for N+1 query problems
   - Measure RLS overhead

3. **RLS Monitoring**
   - Add RLS context logging in production
   - Monitor RLS policy hit rates
   - Alert on RLS failures

4. **Documentation**
   - Add RLS architecture diagram
   - Document RLS testing patterns
   - Create RLS troubleshooting guide

---

**Document Version**: 1.0
**Last Updated**: 2025-10-14
**Next Update**: After Phase 1 completion
**Status**: 🟡 **Ready for Implementation** - Awaiting execution
