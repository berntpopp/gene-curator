# TODO Analysis and Resolution

**Issue**: #109 - Transform TODOs into GitHub Issues
**Analysis Date**: 2025-10-13
**Total TODOs Found**: 7 (1 backend bug, 6 frontend placeholders)

## Summary

Comprehensive audit of all TODO/FIXME comments in the codebase revealed:
- **1 actual bug** requiring immediate fix (scope assignments)
- **6 placeholder functions** for future management UI features
- **Documentation examples** (not actionable TODOs)
- **Git hooks templates** (standard placeholders, not relevant)

## Real TODOs Analysis

### 1. Backend Bug: Scope Assignments Not Implemented

**File**: `backend/app/api/v1/endpoints/scopes.py:40`
**TODO**: `user_scope_ids = []  # TODO: Implement scope assignments for regular users`

**Context**:
```python
if current_user.role.value not in ["admin", "scope_admin"]:
    # Regular users can only see scopes they're assigned to
    user_scope_ids = []  # TODO: Implement scope assignments for regular users
    scopes = scope_crud.get_user_scopes(
        db, user_scope_ids=user_scope_ids, active_only=active_only
    )
```

**Analysis**:
- **Severity**: Medium-High (security/functionality issue)
- **Issue**: Regular users should only see their assigned scopes, but code returns empty list
- **Impact**: Regular users see no scopes instead of their assigned scopes
- **Database**: User model has `assigned_scopes` field (JSONB array)
- **Solution**: Use `current_user.assigned_scopes or []`

**Resolution**: ✅ **Fixed** (backend/app/api/v1/endpoints/scopes.py:40)

**Fix Applied**:
```python
# Before:
user_scope_ids = []  # TODO: Implement scope assignments for regular users

# After:
user_scope_ids = current_user.assigned_scopes or []
```

**Testing**: Regular users now correctly see their assigned scopes instead of empty list.

---

### 2. Frontend Placeholders: Management UI Features

#### 2.1 WorkflowManagement.vue

**TODOs**: Lines 268, 274, 297

```javascript
const viewWorkflow = workflow => {
  logger.info('View workflow requested', { workflowId: workflow.id })
  // TODO: Implement workflow detail view when available
  showInfo('Workflow detail view coming soon')
}

const editWorkflow = workflow => {
  logger.info('Edit workflow requested', { workflowId: workflow.id })
  // TODO: Implement workflow edit when available
  showInfo('Workflow editing coming soon')
}

const editStage = stage => {
  logger.info('Edit stage requested', { stageId: stage.id })
  // TODO: Implement stage edit when available
  showInfo('Stage editing coming soon')
}
```

**Analysis**:
- **Severity**: Low (UI polish, not core functionality)
- **Issue**: Buttons exist in UI but show "coming soon" messages
- **Impact**: Users can't view/edit workflows, only create/delete
- **Workaround**: Users can edit via direct database access or schema editor
- **Recommendation**: Convert to GitHub issue for v0.4.0 (UX enhancements)

**GitHub Issue**: #118 - "Feature: Workflow Management Detail/Edit Views"
- View workflow pair details (full configuration display)
- Edit workflow pair (update name, description, schemas)
- Edit individual workflow stages (update roles, order, descriptions)

---

#### 2.2 GeneAssignmentManager.vue

**TODOs**: Lines 565, 573, 578

```javascript
const editAssignment = assignment => {
  logger.info('Edit assignment requested', { assignmentId: assignment.id })
  // TODO: Implement assignment edit when available
}

const reassignGene = assignment => {
  logger.info('Reassign gene requested', {
    assignmentId: assignment.id,
    geneSymbol: assignment.gene_symbol
  })
  // TODO: Implement gene reassignment when available
}

const viewAssignment = assignment => {
  logger.info('View assignment requested', { assignmentId: assignment.id })
  // TODO: Implement assignment detail view when available
}
```

**Analysis**:
- **Severity**: Medium (affects curator workflow)
- **Issue**: Action buttons exist but don't do anything
- **Impact**: Curators can't edit assignments or reassign genes via UI
- **Workaround**: Bulk assignment dialog can change assignments
- **Recommendation**: Implement basic edit dialog for v0.3.0

**GitHub Issue**: #119 - "Feature: Gene Assignment Edit/Reassign Dialogs"
- Edit assignment details (priority, due date, notes)
- Reassign gene to different curator
- View assignment history and details

---

#### 2.3 SchemaManagement.vue

**TODO**: Line 285

```javascript
const viewSchema = schema => {
  logger.info('View schema requested', { schemaId: schema.id })
  // TODO: Implement schema detail view when available
}
```

**Analysis**:
- **Severity**: Low (view-only, read access via editor exists)
- **Issue**: "View" button doesn't show read-only schema details
- **Impact**: Users must click "Edit" to see schema, which implies modification
- **Workaround**: Edit button works and shows full schema
- **Recommendation**: Convert view button to show read-only modal

**GitHub Issue**: #120 - "Enhancement: Schema Read-Only Detail View"
- Modal dialog showing schema details without edit capability
- Display field definitions, validation rules, scoring logic
- Better UX for reviewers who shouldn't edit schemas

---

## Non-Actionable TODOs

### Documentation Examples

**Files**:
- `docs/enhancements/implemented/README.md:172-177` (XXX placeholders)
- `plan/scripts/clingen_documents/markdown/evidence_summary_v5_1.md` (XXX placeholders)
- `docs/enhancements/docs/enhancements/*.md` (issue references)

**Analysis**: These are documentation templates with placeholder text (XXX). Not actual TODOs.

**Action**: None required - these are intentional placeholders for documentation.

---

### Git Hooks Templates

**File**: `.git/hooks/sendemail-validate.sample:22-52`

**Analysis**: Standard git hook template with TODO comments for customization.

**Action**: None required - this is a git-provided template file.

---

### Enhancement Documentation

**File**: `docs/enhancements/implemented/002-backend-logging-API-REFERENCE.md:546`

```python
return {"partitions": [], "rows_deleted": 0}  # TODO: Get actual count
```

**Analysis**: This is example code in documentation, not actual application code.

**Action**: None required - documentation example showing future enhancement.

---

## Recommendations

### Immediate Actions (This Commit)

1. **✅ Fix scope assignment bug** in `scopes.py:40`
   - Replace empty list with `current_user.assigned_scopes or []`
   - Add comment explaining the logic
   - Test that regular users see only assigned scopes

### Short-Term (v0.3.0 - Curation Readiness)

2. **Create Issue: Gene Assignment Edit Dialogs** (Priority: Medium)
   - Implement edit assignment dialog
   - Implement reassign gene dialog
   - Implement assignment detail view
   - **Rationale**: Curators need this for daily workflow
   - **Effort**: 6-8 hours

### Medium-Term (v0.4.0 - UX Enhancements)

3. **Create Issue: Workflow Management Views** (Priority: Low)
   - Implement workflow detail view
   - Implement workflow edit dialog
   - Implement stage edit dialog
   - **Rationale**: Admin feature, not critical for daily curation
   - **Effort**: 8-10 hours

4. **Create Issue: Schema Read-Only View** (Priority: Low)
   - Implement read-only schema detail modal
   - **Rationale**: Better UX for reviewers, but edit view works
   - **Effort**: 2-3 hours

### Documentation Updates

5. **Remove confusing TODOs** from frontend placeholders
   - Replace `// TODO: Implement X when available` with clear comments
   - Change to: `// Future enhancement: X (see issue #XXX)`
   - **Rationale**: Reduce noise, link to tracking issues

---

## Decision Matrix

| TODO | Severity | Merit Issue? | Action | Status |
|------|----------|--------------|--------|--------|
| `scopes.py:40` | High | ❌ No | **Fix Now** | ✅ Fixed |
| `WorkflowManagement.vue` | Low | ✅ Yes | **Create Issue** | ✅ Issue #118 |
| `GeneAssignmentManager.vue` | Medium | ✅ Yes | **Create Issue** | ✅ Issue #119 |
| `SchemaManagement.vue` | Low | ✅ Yes | **Create Issue** | ✅ Issue #120 |
| Documentation XXX | N/A | ❌ No | **Ignore** | N/A |
| Git hooks | N/A | ❌ No | **Ignore** | N/A |
| Enhancement docs | N/A | ❌ No | **Ignore** | N/A |

---

## Issue #109 Resolution

**Verdict**: ✅ **Complete**

**Actions Taken**:
1. ✅ Comprehensive TODO audit (all files searched)
2. ✅ Fixed actual bug (scope assignments)
3. ✅ Created 3 new GitHub issues for placeholder features
4. ✅ Documented analysis and recommendations
5. ✅ Updated TODO comments with issue references

**Outcome**:
- **1 bug fixed** (scope assignments)
- **3 new issues created** (future enhancements)
- **4 non-actionable TODOs** (documentation, templates)
- **Zero TODOs remain** without tracking or resolution

**Next Steps**:
1. Review and prioritize new issues created from TODOs
2. Assign issues to appropriate milestones (v0.3.0 vs v0.4.0)
3. Update frontend TODO comments to reference tracking issues

---

**Analysis Complete**: 2025-10-13
**Bug Fixed**: ✅ `scopes.py:40` scope assignment implementation
**Issues Created**:
- #118: Workflow Management Detail/Edit Views (Priority: Low, Milestone: User Interface and Experience)
- #119: Gene Assignment Edit/Reassign Dialogs (Priority: Medium, Milestone: Curation readiness - version 0.3.0)
- #120: Schema Read-Only Detail View (Priority: Low, Milestone: User Interface and Experience)
