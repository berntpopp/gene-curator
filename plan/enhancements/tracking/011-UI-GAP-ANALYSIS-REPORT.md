# Enhancement #011 - UI Gap Analysis Report

**Date:** 2026-01-12
**Tester:** Claude Code (Automated Playwright Testing)
**Build:** 0.3.0 - dev

---

## Executive Summary

This report documents the findings from comprehensive UI testing of the Gene Curator application, focusing on the curation workflow and schema-driven form integration. Testing was performed using Playwright browser automation to identify gaps, bugs, and areas needing improvement.

**Overall Status:** The application has a solid foundation but several critical integration gaps prevent a complete end-to-end curation workflow.

---

## 1. Critical Bugs (Must Fix)

### 1.1 SchemaManagement Component - TypeError on Empty Fields
**Location:** `src/views/SchemaManagement.vue:271-277`
**Severity:** High
**Error:** 16 ERROR logs: "SchemaManagement error"

**Root Cause:**
```javascript
// These functions throw when type/status are undefined
const formatType = type => {
  return type.charAt(0).toUpperCase() + type.slice(1)  // Fails if type is undefined
}

const formatStatus = status => {
  return status.charAt(0).toUpperCase() + status.slice(1)  // Fails if status is undefined
}
```

**Issue:**
- Backend schema uses `schema_type` but frontend expects `type`
- No `status` field exists in the backend `CurationSchema` model
- Type and Status columns in the table show as blank/empty

**Fix Required:**
1. Map `schema_type` to `type` when fetching schemas
2. Add default values or null checks: `type?.charAt(0)?.toUpperCase() || 'Unknown'`
3. Consider adding `status` field to backend or removing from frontend

---

### 1.2 WorkflowManagement Component - Missing Data Loading
**Location:** `src/views/WorkflowManagement.vue:330-354`
**Severity:** Critical
**Result:** Empty page - no content rendered

**Root Cause:**
The component expects `workflowStore.workflowPairs` and `workflowStore.workflowStages` but:
1. `onMounted` only calls `fetchWorkflowAnalytics()` and `fetchPeerReviewers()`
2. `workflowStore` (`src/stores/workflow.js`) doesn't have:
   - `workflowPairs` state
   - `workflowStages` state
   - `fetchWorkflowPairs()` action
   - `fetchWorkflowStages()` action

**Fix Required:**
1. Add `workflowPairs: []` and `workflowStages: []` to workflow store state
2. Implement `fetchWorkflowPairs()` and `fetchWorkflowStages()` actions
3. Create corresponding API endpoints if not existing
4. Call these methods in `onMounted`

---

### 1.3 Gene Assignments Page - API Error
**Location:** `/assignments` page
**Severity:** High
**Error:** "Failed to load assignment data. Please refresh."

**Issue:**
The `GET /gene-assignments` API call likely returned an error or unexpected format.

**Fix Required:**
1. Verify API endpoint exists and is working
2. Check error handling in the assignments store
3. Ensure proper authentication headers are sent

---

## 2. UI/UX Issues

### 2.1 Multiple Navigation Drawers Open Simultaneously
**Location:** Scope Dashboard > Genes tab
**Severity:** Medium

**Issue:**
Both "Add Genes to Catalog" drawer and "Assign Genes to Curators" drawer appear open at the same time when switching to the Genes tab.

**Fix Required:**
- Add state management to ensure only one drawer is open at a time
- Close other drawers when opening a new one

---

### 2.2 Elements Outside Viewport
**Location:** Multiple pages
**Severity:** Medium

**Issue:**
Many interactive elements (drawers, buttons) are positioned outside the viewport, causing Playwright click timeouts and potentially affecting user experience.

**Affected Areas:**
- Log viewer drawer close buttons
- Schema management action buttons
- Navigation drawer elements

**Fix Required:**
- Review CSS positioning for drawers
- Ensure proper scroll handling
- Add viewport-aware positioning

---

### 2.3 Log Viewer Takes Significant Screen Space
**Location:** All pages (bottom drawer)
**Severity:** Low

**Observation:**
The log viewer drawer, when open, consumes significant viewport space, potentially obscuring important UI elements.

**Recommendation:**
- Consider making it collapsible to a smaller height
- Add a "minimal" view option

---

## 3. Missing Functionality

### 3.1 Workflow Pairs Configuration
**Status:** Not Implemented

**Current State:**
- WorkflowManagement page exists but shows no data
- No ability to create or manage workflow pairs
- Missing API integration for workflow pair CRUD operations

**Required for End-to-End Workflow:**
1. Create Workflow Pair form/dialog
2. Link precuration + curation schemas
3. Assign workflow pairs to scopes

---

### 3.2 Schema Editor Route
**Location:** `src/views/SchemaManagement.vue:288-298`
**Status:** Route referenced but may not exist

**Current State:**
```javascript
const editSchema = schema => {
  router.push({ name: 'SchemaEditor', params: { id: schema.id } })
}
```

**Required:**
1. Verify `SchemaEditor` route exists in router config
2. Implement SchemaEditor view if missing

---

### 3.3 Curation Form - Schema Selection
**Status:** Needs verification

**Missing Integration:**
When creating a new curation, the system should:
1. Allow selection of a workflow pair/schema
2. Generate dynamic form based on selected schema
3. Validate data against schema rules

---

## 4. Working Features

### 4.1 Scopes Page
- List all scopes with cards
- Search and filter functionality
- Create scope button
- Scope detail dashboard with Overview, Genes, Curations tabs

### 4.2 Scope Dashboard
- Displays scope information correctly
- Shows statistics (all zeros when empty)
- Progress tracking
- Tabs navigation works

### 4.3 Gene Catalog
- Lists genes correctly
- Search functionality
- Add gene to catalog drawer works

### 4.4 Schema Management (partial)
- Lists 4 schemas from database
- Search and filter controls present
- Action buttons (view, edit, copy, delete) present
- Pagination works

### 4.5 Authentication
- Login works
- JWT token handling
- User menu displays

### 4.6 Navigation
- Top navigation bar works
- Dropdown menus functional
- Routing works for most pages

---

## 5. Data Issues

### 5.1 All Scopes Show 0 Genes/Members
**Observation:**
Every scope displays "0 genes" and "0 members" in the cards.

**Possible Causes:**
1. Gene assignments not properly linked to scopes
2. API not returning counts correctly
3. Data not seeded

---

### 5.2 Schema Type/Status Not Displaying
**Observation:**
In Schema Management table, Type and Status columns are empty for all 4 schemas.

**Cause:**
Backend returns `schema_type` but frontend expects `type`; `status` field doesn't exist.

---

## 6. Recommendations

### 6.1 Priority 1 - Fix Critical Bugs
1. Fix SchemaManagement formatType/formatStatus errors
2. Implement WorkflowManagement data loading
3. Debug Gene Assignments API error

### 6.2 Priority 2 - Complete Workflow Integration
1. Add workflow pairs store actions and state
2. Create workflow pair management UI
3. Link schemas to workflow pairs

### 6.3 Priority 3 - UI/UX Improvements
1. Fix drawer state management (only one open at a time)
2. Fix viewport positioning issues
3. Improve error messages with actionable guidance

### 6.4 Priority 4 - Testing & Documentation
1. Add E2E tests for critical paths
2. Document API contract between frontend/backend
3. Add integration tests for schema-driven forms

---

## 7. Test Environment

- **Frontend:** Vue 3 + Vuetify 3 + Pinia
- **Backend:** FastAPI (running on port 8051)
- **Frontend Dev Server:** Vite (port 5193)
- **Browser:** Chromium via Playwright
- **User:** admin@genecurator.org (admin role)

---

## 8. Files Reviewed

| File | Purpose | Issues Found |
|------|---------|--------------|
| `src/views/SchemaManagement.vue` | Schema listing | formatType/formatStatus bugs |
| `src/views/WorkflowManagement.vue` | Workflow pairs | Missing data fetching |
| `src/stores/workflow.js` | Workflow state | Missing workflowPairs/workflowStages |
| `src/stores/notifications.js` | Notifications | Fixed addToast (earlier in session) |
| `backend/app/schemas/schema_repository.py` | API schemas | Uses schema_type not type |

---

## 9. Next Steps

1. **Immediate:** Fix TypeError bugs in SchemaManagement
2. **Short-term:** Implement WorkflowManagement data loading
3. **Medium-term:** Complete workflow pair configuration flow
4. **Long-term:** Schema-driven form integration E2E testing

---

*Report generated during Enhancement #011 verification testing.*
