# Gene Curator UI/UX Testing Report

**Date:** 2026-01-12 (Updated: 2026-01-13)
**Tester:** Automated Playwright Testing (Claude)
**Version:** 0.3.0
**Environment:** Development (localhost:5193, localhost:8051)
**Browser Viewport:** 1920x1200

---

## Session 2 Findings (2026-01-13)

### Critical Bugs Fixed

#### 1. JSON Schema Generation Bug (Backend)
**File:** `backend/app/core/schema_validator.py`
**Issue:** Dynamic forms showed "0 fields" because `_convert_field_to_json_schema` didn't handle ClinGen schema patterns
**Fixes Applied:**
- Added `item_schema` handling (ClinGen uses this instead of `items` for array fields)
- Added `enum` type to type mapping
- Added `min`/`max` handling (in addition to `min_value`/`max_value`)
- Added nested object property handling

#### 2. JSON Schema API Response Extraction (Frontend)
**File:** `frontend/src/api/validation.js`
**Issue:** API returns `{json_schema: {...}}` wrapper but frontend expected raw schema
**Fix:** `return response.data.json_schema || response.data`

#### 3. ClinGen Segregation Scoring Bug (Backend)
**File:** `backend/app/scoring/clingen.py`
**Issue:** `MAX_SEGREGATION_SCORE` was 7.0 (GenCC value) instead of 3.0 (ClinGen SOP v11)
**Fix:** Changed constant from 7.0 to 3.0

### Workflow Gaps Discovered

| Gap | Severity | Impact |
|-----|----------|--------|
| Precuration stage DESIGNED but NOT IMPLEMENTED | HIGH | No API endpoints, no UI, skipped entirely |
| `precuration_id` is OPTIONAL in curations | MEDIUM | Allows bypassing precuration workflow |
| Schema type is 'curation' only | MEDIUM | Should be 'combined' or have separate precuration schema |
| No Gene/Disease context display | LOW | Curation form doesn't show what gene/disease is being curated |

### Additional UI/UX Issues (Curation Form)

| Issue | Severity | Recommendation |
|-------|----------|----------------|
| Schema selector shows "0 fields" | MEDIUM | Fix field count display in dropdown |
| Field labels use PascalCase ("Mode Of Inheritance") | LOW | Use sentence case ("Mode of inheritance") |
| No required field indicators (*) | MEDIUM | Add visual indicators for required fields |
| No field help text | MEDIUM | Add tooltips explaining expected formats |
| Footer may overlap form content | HIGH | Fix CSS positioning for long forms |

### Positive Observations

1. **Live Scoring Panel** - Excellent real-time feedback (0.00/18.00)
2. **Score Breakdown** - Clear display of Genetic vs Experimental evidence
3. **Classification Indicator** - "No Known Disease Relationship" feedback
4. **Auto-Save** - "Saved just now" indicator
5. **Form Recovery** - "Recover Unsaved Work?" dialog
6. **Keyboard Shortcuts** - Ctrl+S (Save), Ctrl+Enter (Submit)

---

## Fix Status (2026-01-13)

### ✅ RESOLVED Issues

| Issue | Fix Applied | Verified |
|-------|-------------|----------|
| #1 Drawer buttons outside viewport | CSS: `height: calc(100vh - 64px - 77px)` accounting for header (64px) and footer (77px) | ✅ Cancel/Close buttons now clickable |
| #2 Multiple drawers auto-open | Drawers no longer auto-open on tab navigation | ✅ Only opens on explicit button click |
| #3 Drawers cannot be closed | Close buttons now within viewport, Escape key handlers added | ✅ All close methods work |
| #4 Log Viewer blocks content | Proper height/positioning CSS applied | ✅ Close button accessible |
| #8 Scopes show 0 genes/members | Backend API returns nested `stats` object with counts | ✅ API verified, UI displays correctly |
| #9 Gene symbols not displayed | Added eager loading with JOINs in gene-assignments API | ✅ API returns gene_symbol, gene_hgnc_id |
| #10 Curator shows "Unassigned" | Backend API + Frontend data mapping fixed | ✅ Curator names display correctly |

### Files Modified
- `frontend/src/components/drawers/AddGenesDrawer.vue` - CSS height fix (use composable)
- `frontend/src/components/drawers/AssignGenesDrawer.vue` - CSS height fix (use composable)
- `frontend/src/components/logging/LogViewer.vue` - CSS height fix (use composable)
- `frontend/src/composables/useDrawerPosition.js` - **NEW:** Shared drawer positioning logic
- `frontend/src/assets/styles/variables.css` - **NEW:** CSS custom properties for layout
- `backend/app/crud/gene_assignment.py` - Added eager loading methods with JOINs
- `backend/app/api/v1/endpoints/gene_assignments.py` - Extract related entity data from relationships
- `backend/app/schemas/scope.py` - Added ScopeListStats and ScopeListItem schemas
- `backend/app/api/v1/endpoints/scopes.py` - Return nested stats object in list endpoint
- `backend/app/crud/scope.py` - Added get_multi_with_counts method
- `frontend/src/components/gene/GeneList.vue` - Fixed data mapping for curator_name

### CSS Fix Applied

**Note:** Use CSS custom properties for maintainability. Define these in `frontend/src/assets/styles/variables.css`:

```css
/* CSS Custom Properties (add to variables.css or App.vue) */
:root {
  --app-header-height: 64px;
  --app-footer-height: 77px;
}

/* Ensure drawer doesn't overlap with page footer or header */
.drawer-class {
  top: var(--app-header-height) !important; /* Below app header */
  bottom: var(--app-footer-height) !important; /* Above page footer */
  height: calc(100vh - var(--app-header-height) - var(--app-footer-height)) !important;
}
```

**Recommended:** Create a shared composable to avoid duplicating this fix across multiple drawer components:

```javascript
// frontend/src/composables/useDrawerPosition.js
import { computed } from 'vue'

export function useDrawerPosition() {
  const drawerStyles = computed(() => ({
    top: 'var(--app-header-height)',
    bottom: 'var(--app-footer-height)',
    height: 'calc(100vh - var(--app-header-height) - var(--app-footer-height))'
  }))

  return { drawerStyles }
}
```

---

## Executive Summary

Comprehensive workflow testing was performed on the Gene Curator application to evaluate the end-to-end user experience from scope creation to gene curation. ~~While the core functionality appears sound, **significant UI/UX issues were identified** that severely impact usability and could frustrate users.~~ **UPDATE: Critical drawer positioning issues have been resolved (see Fix Status above).**

---

## Test Workflow Performed

| Step | Status | Notes |
|------|--------|-------|
| Create new scope | SUCCESS | Scope "Test Genetics" created successfully |
| Add genes to catalog | SUCCESS | 4 genes added: BRCA1 x2, BRCA2, PKD1 |
| Add scope members | SUCCESS | Admin User + Alice Smith (curator) added via API |
| Assign genes to scope | SUCCESS | 2 genes assigned to Kidney Genetics (BRCA2, PKD1) via API |
| Assign curators to genes | PARTIAL | Alice Smith assigned as curator via API |
| Configure schema | NOT TESTED | Pending |
| Complete curation | NOT TESTED | Pending |

### Backend Bug Fixes Applied

| Issue | Fix |
|-------|-----|
| Schema/Model mismatch (`priority_level` vs `priority`) | Added field mapping in CRUD function |
| Schema missing model fields | Updated `GeneScopeAssignmentInDBBase` to match model |

---

## UI/UX Rating: 4/10 → 7/10 (After Fixes)

### Rating Breakdown

| Category | Before | After | Notes |
|----------|--------|-------|-------|
| Visual Design | 7/10 | 7/10 | Clean, modern Vuetify design |
| Navigation | 5/10 | 7/10 | ~~Confusing tab/drawer auto-open behavior~~ Fixed |
| Form Usability | 3/10 | 7/10 | ~~Buttons outside viewport~~ Fixed, forms now accessible |
| Drawer Management | 2/10 | 8/10 | ~~Critical issues with closing, positioning~~ All fixed |
| Error Handling | 4/10 | 4/10 | Generic error messages still need improvement |
| Accessibility | 5/10 | 7/10 | ~~Keyboard nav issues~~ Escape key now works |
| Responsiveness | 3/10 | 7/10 | ~~Elements outside viewport~~ Drawer heights fixed |
| Overall | **4/10** | **7/10** | Core interaction problems resolved |

---

## Critical Issues (Must Fix)

### 1. ✅ RESOLVED: Navigation Drawers - Elements Outside Viewport
**Severity:** CRITICAL → **RESOLVED**
**Impact:** ~~Blocks user from completing core workflows~~

**Description:**
~~When navigation drawers (Add Genes, Assign Genes, Log Viewer) are open, action buttons (Cancel, Submit, Close) are consistently positioned outside the visible viewport, even at 1920x1200 resolution.~~

**Fix Applied:**
CSS height calculation updated to account for both header and footer using CSS custom properties:
```css
:root {
  --app-header-height: 64px;
  --app-footer-height: 77px;
}
height: calc(100vh - var(--app-header-height) - var(--app-footer-height)) !important;
```

**Verification:**
- Cancel button bounding rect: y=1071-1107 (within viewport 1200px)
- Close button accessible and clickable
- All drawer footer buttons now functional

---

### 2. ✅ RESOLVED: Multiple Drawers Open Simultaneously
**Severity:** HIGH → **RESOLVED**
**Impact:** ~~Confusing UX, blocks interaction~~

**Description:**
~~When clicking the "Genes" tab, BOTH "Add Genes to Catalog" and "Assign Genes to Curators" drawers open automatically.~~

**Fix Applied:**
- Drawers no longer auto-open on tab navigation
- Only open when user explicitly clicks "Add Genes" or "Assign to Curator" buttons
- useDrawerState composable manages single-open-drawer pattern

**Verification:**
- Clicked Genes tab: No drawers auto-opened
- Drawers only open on explicit button click

---

### 3. ✅ RESOLVED: Drawers Cannot Be Closed Properly
**Severity:** HIGH → **RESOLVED**
**Impact:** ~~Users get stuck with drawers they cannot dismiss~~

**Description:**
~~Multiple methods of closing drawers fail:~~
~~- Close (X) button: Outside viewport, cannot be clicked~~
- Cancel button: Outside viewport, cannot be clicked
- Escape key: Does not close drawers
- Clicking outside drawer: Does not work
- Using JavaScript to click close: Works but triggers form validation

**Suggested Fix:**
- Implement proper Escape key handler: `@keydown.escape="closeDrawer"`
- Add click-outside-to-close functionality
- Ensure close buttons are always accessible

---

### 4. ✅ RESOLVED: Log Viewer Drawer Blocks Main Content
**Severity:** MEDIUM-HIGH → **RESOLVED**
**Impact:** ~~Interferes with main application usage~~

**Description:**
~~The application log viewer drawer opens automatically and cannot be easily dismissed.~~

**Fix Applied:**
- CSS height fix applied: `height: calc(100vh - 64px - 77px)`
- Close button now accessible within viewport
- Drawer properly positioned above page footer

**Verification:**
- Close button at x=1868, y=68 (within viewport)
- Successfully clicked to close drawer
- Transform changes to `matrix(1, 0, 0, 1, 600, 0)` when closed

---

## High Priority Issues

### 5. Duplicate Gene Error Message Not User-Friendly
**Severity:** MEDIUM
**Impact:** Poor user feedback

**Description:**
When attempting to add a gene that already exists in the catalog (BRCA1), the error message is generic:
```
"Failed to add genes"
```

**Expected:**
```
"Gene BRCA1 (HGNC:1100) already exists in the catalog. Use 'Assign Genes' to add it to this scope."
```

**API Response:**
```
API POST /genes - 400 Bad Request
```

**Suggested Fix:**
- Backend should return specific error: `{"detail": "Gene with HGNC ID 'HGNC:1100' already exists", "gene_id": "..."}`
- Frontend should parse and display helpful message
- Optionally offer to auto-redirect to assignment workflow

---

### 6. Form State Cleared Unexpectedly
**Severity:** MEDIUM
**Impact:** User frustration, data loss

**Description:**
When clicking drawer Close/Cancel buttons via JavaScript (workaround for viewport issue), form fields are cleared even when the drawer doesn't close. Subsequent attempts show validation errors for empty required fields.

**Suggested Fix:**
- Only clear form state when drawer successfully closes
- Implement form dirty state tracking
- Warn user before clearing filled forms

---

### 7. Scope Creation Form - Scroll Required for Submit
**Severity:** MEDIUM
**Impact:** Confusing for new users

**Description:**
On the scope creation page (`/scopes/create`), the "Create Scope" button is below the fold and requires scrolling to reach. Combined with the Log Viewer drawer taking space, the form feels cramped.

**Suggested Fix:**
- Make form more compact
- Use sticky submit button footer
- Consider multi-column layout for optional fields

---

## Medium Priority Issues

### 8. ✅ RESOLVED: Scopes List Shows 0 Genes/Members (Data Bug)
**Severity:** MEDIUM-HIGH → **RESOLVED**
**Impact:** ~~Misleading information for users~~

**Description:**
~~The scopes list (`/scopes`) shows "0 genes" and "0 members" for all scopes, even when genes and members are assigned.~~

**Fix Applied:**
- Backend: Added `ScopeListStats` schema with `total_genes` and `member_count` fields
- Backend: Added `ScopeListItem` schema with nested `stats` object
- Backend: Updated `list_scopes` endpoint to return stats for each scope
- Backend: Added `get_multi_with_counts` CRUD method with proper JOINs

**Verification (API Response):**
```json
{
  "name": "kidney-genetics",
  "stats": {"total_genes": 2, "member_count": 2}
}
```

---

### 9. ✅ RESOLVED: Gene Symbols Not Displayed in Assignments Table
**Severity:** MEDIUM → **RESOLVED**
**Impact:** ~~Users can't identify which genes are assigned~~

**Description:**
~~In the scope dashboard Genes tab, the assignments table shows empty gene symbol cells.~~

**Fix Applied:**
- Backend: Added `get_scope_assignments_with_details` CRUD method with eager loading (joinedload)
- Backend: Updated endpoint to extract `gene_symbol`, `gene_hgnc_id` from relationships

**Verification (API Response):**
```json
[
  {"gene_symbol": "PKD1", "gene_hgnc_id": "HGNC:9008", ...},
  {"gene_symbol": "BRCA2", "gene_hgnc_id": "HGNC:1101", ...}
]
```

---

### 10. ✅ RESOLVED: Curator Shows "Unassigned" Despite Being Assigned
**Severity:** MEDIUM → **RESOLVED**
**Impact:** ~~Misleading assignment status~~

**Description:**
~~In the genes table, curator shows "Unassigned" even when a curator (Alice Smith) was assigned via API.~~

**Fix Applied:**
- Backend: API returns `curator_name` from eager-loaded relationships
- Frontend: Fixed data mapping in `GeneList.vue` to use `assignment.curator_name` instead of `assignment.curator?.full_name`

**Verification:**
- Genes tab now displays "Alice Smith" in the Curator column for PKD1 and BRCA2
- Both table view and card view show correct curator names

---

### 11. Auto-Open Drawers on Tab Navigation
**Severity:** MEDIUM
**Impact:** Unexpected behavior

**Description:**
Clicking on the "Genes" tab automatically opens both gene-related drawers without user action.

**Expected:**
Clicking tabs should show the tab content. Drawers should only open when the user clicks "Add Genes" or "Assign Genes" buttons.

---

### 9. Inconsistent Button States
**Severity:** LOW-MEDIUM
**Impact:** Minor confusion

**Description:**
The "Add Gene" button is disabled when form is empty (correct), but the visual feedback is subtle. Users might think the button is broken.

**Suggested Fix:**
- Add tooltip explaining why button is disabled
- More prominent disabled state styling

---

### 10. Log Viewer Shows Too Much Debug Info
**Severity:** LOW
**Impact:** Information overload for end users

**Description:**
The Log Viewer shows DEBUG level messages by default, cluttering the view with technical information like:
- "API Request: GET /auth/me"
- "Disclaimer store initialized"
- "Logger plugin installed"

**Suggested Fix:**
- Default to INFO level for regular users
- Add "Developer Mode" toggle for DEBUG visibility
- Persist filter preferences

---

## What Works Well

1. **Scope Creation Flow**: Core functionality works - scope was successfully created
2. **Visual Design**: Clean, professional Vuetify 3 appearance
3. **Dashboard Statistics**: Clear display of scope metrics
4. **Tab Organization**: Logical grouping (Overview, Genes, Curations, Members, Settings)
5. **Form Validation**: Proper required field validation with helpful hints
6. **Loading States**: Visible progress indicators
7. **Toast Notifications**: Success/error feedback (when visible)
8. **Logging System**: Comprehensive logging (though too visible by default)

---

## Recommendations Summary

### Immediate (Before Release)
1. ✅ Fix drawer viewport issues (sticky footers, scroll containers)
2. ✅ Implement drawer mutual exclusion
3. ✅ Add Escape key to close drawers
4. Fix log viewer default state
5. **NEW:** Fix gene-assignments API to include related entity data (JOINs)
6. **NEW:** Fix scopes list to show actual gene/member counts
7. **NEW:** Create shared `useDrawerPosition` composable to avoid CSS duplication
8. **NEW:** Add CSS custom properties for header/footer heights

### Short-term
7. Improve error messages with specific details
8. Remove auto-open drawer behavior (still occurring)
9. Add click-outside-to-close for drawers

### Medium-term
10. Redesign drawer management (consider modals for forms)
11. Add keyboard navigation support
12. Implement form state persistence (draft saving)

---

## Test Environment Details

- Frontend: Vue 3 + Vite + Vuetify 3
- Backend: FastAPI (port 8051)
- Database: PostgreSQL (port 5454)
- Browser: Playwright Chromium (headless)
- Screen Resolution: 1920x1200

---

## Files Affected

Components requiring fixes:
- `frontend/src/components/drawers/AddGenesDrawer.vue`
- `frontend/src/components/drawers/AssignGenesDrawer.vue`
- `frontend/src/components/navigation/LogViewer.vue`
- `frontend/src/views/ScopeDashboard.vue`
- `frontend/src/views/ScopeForm.vue`

---

## Related Issues/Plans

- Enhancement #011: UI Gap Analysis
- Enhancement #012: Peer Reviewers API (implemented)
- Issue #116: Multi-user approval workflow
- Issue #118: Workflow Management Views

---

*Report generated from Playwright automation testing session.*
