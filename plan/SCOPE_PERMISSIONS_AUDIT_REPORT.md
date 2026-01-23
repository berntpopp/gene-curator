# Scope-Based Permission System Audit Report

**Date:** January 13, 2026
**Auditor:** Claude Code
**Scope:** Backend API permission checks, 4-eyes principle implementation

---

## Executive Summary

This report identifies **critical violations** of the scope-based permission system in the Gene Curator codebase. The primary issues are:

1. **Hardcoded 4-Eyes Principle** - The 4-eyes check is implemented globally and cannot be configured per scope or workflow
2. **Deprecated `assigned_scopes` Pattern** - 25+ instances still use the deprecated array field instead of the authoritative `scope_memberships` table
3. **Direct Global Role Checks** - 30+ instances check `user.role` without considering scope-specific roles
4. **Inconsistent Permission Service Usage** - Only some endpoints use `ScopePermissionService`

**Severity Assessment:** HIGH - These violations bypass the intended scope-based RBAC system and could lead to unauthorized access or workflow violations.

---

## 1. Four-Eyes Principle Analysis

### 1.1 Current Implementation (Hardcoded)

The 4-eyes principle is implemented in multiple locations but is **hardcoded** and **not configurable** per scope:

| File | Location | Implementation |
|------|----------|----------------|
| `workflow_engine.py` | Lines 126-144 | Validation during transition |
| `workflow_engine.py` | Lines 299-322 | Reviewer assignment validation |
| `workflow_engine.py` | Lines 684-698 | `_requires_peer_review()` definition |
| `scope_permissions.py` | Lines 266-330 | `can_approve_curation()` method |
| `curations.py` | Lines 78-99 | `_can_user_review_curation()` helper |
| `precurations.py` | Lines 399-404 | Explicit approval check |

### 1.2 Hardcoded Pattern Example

```python
# From workflow_engine.py - HARDCODED 4-eyes check
def _requires_peer_review(
    self, current_stage: WorkflowStage, target_stage: WorkflowStage
) -> bool:
    """Check if transition requires peer review (4-eyes principle)."""
    peer_review_transitions = [
        (WorkflowStage.REVIEW, WorkflowStage.ACTIVE),  # HARDCODED!
    ]
    return (current_stage, target_stage) in peer_review_transitions
```

### 1.3 Schema Exists But Not Used

A `WorkflowConfiguration` schema exists with configurable options but is **not persisted** or **enforced**:

```python
# From schemas/workflow_engine.py - DEFINED BUT NOT USED
class WorkflowConfiguration(BaseModel):
    require_peer_review: bool = Field(True, description="Require peer review")
    allow_self_review: bool = Field(False, description="Allow self-review (violates 4-eyes)")
    # ^ These are never read from a database or checked by the workflow engine!
```

### 1.4 Best Practices Recommendation

According to industry best practices ([Flagsmith](https://www.flagsmith.com/blog/what-is-the-four-eyes-principle), [Oso HQ](https://www.osohq.com/learn/rbac-best-practices)):

> "A feature flag that touches sensitive data should require the 4-eyes principle. But one that's toggled on/off for changing a button colour doesn't need one. It reduces the administrative burden and keeps processes focused on the things that truly matter."

**Recommendation:** Make 4-eyes configurable per:
- **Scope level** - Clinical scopes may require stricter controls
- **Workflow pair** - Different schemas may have different requirements
- **Classification result** - "Definitive" classifications may require review, "Limited" may not

---

## 2. Scope-Based Permission Violations

### 2.1 CRITICAL: Deprecated `assigned_scopes` Usage

**25+ instances** use `current_user.assigned_scopes` (a flat array on the User model) instead of querying the `scope_memberships` table.

**Why this is wrong:**
- `assigned_scopes` lacks role information (just scope IDs)
- `scope_memberships` is the authoritative source with `role` column
- Bypasses scope-specific role validation entirely

#### Affected Files

| File | Lines | Instances |
|------|-------|-----------|
| `precurations.py` | 50, 53, 93, 101-103 | 5 |
| `gene_assignments.py` | 73, 147, 185, 250, 346, 376, 419, 458, 570, 626, 662 | 11 |
| `genes.py` | 81, 174, 233, 392, 453 | 5 |
| `workflow.py` | 302, 323, 477, 535 | 4 |
| `user.py` (CRUD) | 39, 225, 241 | 3 |
| `gene_assignment.py` (CRUD) | 372 | 1 |
| `scope.py` (CRUD) | 499 | 1 |

#### Problematic Code Example

```python
# WRONG - from precurations.py:53
user_scope_ids: list[UUID] = current_user.assigned_scopes or []
if scope_id not in user_scope_ids:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, ...)
```

#### Correct Pattern

```python
# CORRECT - from curations.py helper
def _get_user_scope_role(db: Session, user_id: UUID, scope_id: UUID) -> str | None:
    """Get user's role for a specific scope from scope_memberships."""
    membership = db.query(ScopeMembership).filter(
        ScopeMembership.user_id == user_id,
        ScopeMembership.scope_id == scope_id,
        ScopeMembership.is_active,
    ).first()
    return membership.role if membership else None
```

### 2.2 CRITICAL: Direct Global Role Checks

**30+ instances** check `current_user.role` (global application role) instead of scope-specific roles.

**Why this is wrong:**
- Global roles (admin, user) are different from scope roles (admin, curator, reviewer, viewer)
- A "user" globally may be a "curator" or "reviewer" in specific scopes
- Hardcoded global checks bypass scope-based permissions

#### Affected Files

| File | Lines | Pattern |
|------|-------|---------|
| `precurations.py` | 50, 93, 262, 299, 400, 485 | `current_user.role == "admin"` |
| `curations.py` | 66-67, 134, 189, 205, 247, 401, 442, 523 | `user.role == "admin"` |
| `gene_assignments.py` | 72, 146, 281, 317, 482, 509 | `current_user.role not in ["admin"]` |
| `genes.py` | 80 | `current_user.role not in ["admin"]` |
| `users.py` | 77, 253 | `current_user.role != "admin"` |
| `logs.py` | 51, 72 | `current_user.role != UserRoleNew.ADMIN` |
| `schema_validation.py` | 514 | `current_user.role != "admin"` |
| `workflow.py` | 427, 476, 508, 534 | `current_user.role != "admin"` |
| `scopes.py` | 182, 409 | `current_user.role.value == "admin"` |
| `workflow_engine.py` (CRUD) | 650, 710 | `user.role == "admin"` |

#### Problematic Code Example

```python
# WRONG - from curations.py:66-67
def _can_user_edit_curation(db: Session, user: UserNew, curation) -> bool:
    if user.role == "admin":  # Only checks global app-level admin!
        return curation.status in [CurationStatus.DRAFT, CurationStatus.REJECTED]
    # Should also check scope-specific "admin" role
```

### 2.3 MEDIUM: Inconsistent ScopePermissionService Usage

Only **some endpoints** use the centralized `ScopePermissionService`:

| File | Uses Service | Pattern |
|------|--------------|---------|
| `curations.py` | Partial | Uses service for viewing, custom helpers for edit/review/delete |
| `precurations.py` | No | Never imports `ScopePermissionService` |
| `gene_assignments.py` | No | Direct `assigned_scopes` checks |
| `genes.py` | No | Direct scope filtering |
| `workflow.py` | No | Mixed patterns |
| `scopes.py` | Yes | Uses service correctly |

---

## 3. Industry Best Practices

Based on research from leading authorization frameworks:

### 3.1 Scope-Based RBAC ([Oso HQ](https://www.osohq.com/learn/rbac-best-practices))

> "'Admin' in marketing shouldn't mean 'Admin' in engineering! Real organizations need scoped roles, not global ones, where the same person has different access levels in different contexts."

**Key Principles:**
- Design for `User → Role → Scope` relationships from the start
- Reduce blast radius when accounts are compromised
- Enforce least privilege at scale

### 3.2 Configurable Four-Eyes ([Flagsmith](https://www.flagsmith.com/blog/what-is-the-four-eyes-principle))

> "You can avoid many incidents using the 4-eyes principle, but only if you actually enforce it. If your team is able to work around them... it'll be hard to solve the governance problem."

**Key Principles:**
- Make 4-eyes technically impossible to bypass
- Apply risk-based controls (not all actions need same scrutiny)
- Combine with RBAC for clear approval boundaries

### 3.3 Authorization Best Practices ([Cerbos](https://www.cerbos.dev/blog/role-based-access-control-best-practices))

> "Assign only the minimum permissions each person needs to carry out their duties."

**Key Principles:**
- Establish clear role hierarchies
- Conduct regular reviews of role assignments
- Prioritize logging and monitoring
- Develop incident response procedures

---

## 4. Recommendations

### 4.1 Phase 1: Critical Fixes (Immediate)

1. **Replace all `assigned_scopes` usage with `scope_memberships` queries**
   - Affects: 7 files, 25+ instances
   - Pattern: Use `_get_user_scope_role()` helper or `ScopePermissionService`

2. **Update global role checks to include scope role checks**
   - Affects: 11 files, 30+ instances
   - Pattern: `user.role == "admin" OR scope_role in ["admin", "curator"]`

### 4.2 Phase 2: Service Standardization

1. **Centralize all permission checks in `ScopePermissionService`**
   - Add methods: `can_create_precuration()`, `can_edit_gene_assignment()`, etc.
   - Remove custom permission helpers from endpoints

2. **Create a `require_scope_role()` dependency factory**
   - Similar to existing pattern but more flexible
   - Example: `Depends(require_scope_role(["curator", "reviewer"], scope_param="scope_id"))`

### 4.3 Phase 3: Configurable 4-Eyes

1. **Create `workflow_configurations` table**
   ```sql
   CREATE TABLE workflow_configurations (
       id UUID PRIMARY KEY,
       scope_id UUID REFERENCES scopes(id),
       workflow_pair_id UUID REFERENCES workflow_pairs(id),
       require_peer_review BOOLEAN DEFAULT TRUE,
       allow_self_review BOOLEAN DEFAULT FALSE,
       min_reviewers INTEGER DEFAULT 1,
       -- Risk-based rules
       require_review_for_classifications TEXT[] DEFAULT ARRAY['Definitive', 'Strong'],
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP DEFAULT NOW()
   );
   ```

2. **Update workflow engine to read configuration**
   ```python
   def _requires_peer_review(self, db: Session, scope_id: UUID, ...) -> bool:
       config = self._get_workflow_config(db, scope_id)
       if config and not config.require_peer_review:
           return False
       # ... existing logic
   ```

### 4.4 Phase 4: Cleanup

1. **Deprecate and remove `assigned_scopes` from User model**
2. **Add migration to drop column after all code updated**
3. **Add linting rule to prevent direct `user.role` checks without scope context**

---

## 5. Summary Table

| Issue | Severity | Files | Instances | Effort |
|-------|----------|-------|-----------|--------|
| `assigned_scopes` usage | HIGH | 7 | 25+ | Medium |
| Direct `user.role` checks | HIGH | 11 | 30+ | Medium |
| Inconsistent service usage | MEDIUM | 5 | Various | Low |
| Hardcoded 4-eyes | MEDIUM | 6 | 6 | High |

**Total Estimated Effort:** 2-3 development cycles

---

## 6. References

- [Flagsmith: What is the Four Eyes Principle?](https://www.flagsmith.com/blog/what-is-the-four-eyes-principle)
- [Open Risk Manual: Four Eyes Principle](https://www.openriskmanual.org/wiki/Four_Eyes_Principle)
- [Oso HQ: 10 RBAC Best Practices](https://www.osohq.com/learn/rbac-best-practices)
- [Cerbos: Role-Based Access Control Best Practices](https://www.cerbos.dev/blog/role-based-access-control-best-practices)
- [DZone: Implementing Four-Eyes Principle](https://dzone.com/articles/devops-guide-implementing-four-eyes-principle-with)
- [Zluri: Role-Based Access Control Guide](https://www.zluri.com/blog/role-based-access-control)

---

*This report was generated by automated codebase analysis. Manual verification is recommended before implementing changes.*
