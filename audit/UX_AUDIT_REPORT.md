# Gene Curator UX Audit Report

**Date**: 2026-02-28
**Version Tested**: 0.3.0 (dev build)
**Auditor**: AI UX/Gene Curation Expert Review
**Method**: Playwright-driven systematic page-by-page review + ClinGen SOP compliance analysis

---

## Executive Summary

Gene Curator is a functional MVP for gene-disease validity curation with solid architectural foundations. The application successfully implements ClinGen's semi-quantitative scoring framework and multi-stage workflow. However, several critical UX issues significantly impair curator productivity, particularly on the curation detail form which is the core work surface.

---

## Ratings (1-10 Scale)

| Category | Score | Summary |
|---|---|---|
| **Overall Usability** | 5/10 | Functional but significant friction in core workflows |
| **ClinGen Compliance** | 7/10 | Good framework coverage, missing some SOP v12 features |
| **Visual Design** | 6/10 | Clean Vuetify foundation, inconsistent detail execution |
| **User Experience Flow** | 5/10 | Navigation works, but curation form is overwhelming |
| **Information Architecture** | 6/10 | Good top-level structure, deep pages lack orientation |
| **Error Prevention** | 4/10 | Active form warnings, truncated labels, no undo |
| **Accessibility** | 5/10 | Vuetify provides baseline, custom components lack ARIA |
| **Curator Productivity** | 4/10 | Long scroll form, no keyboard shortcuts, no autosave |

**Weighted Overall Score: 5.3/10**

---

## Page-by-Page Findings

### 1. Landing Page (/)
**Score: 7/10** - Good first impression

**Strengths:**
- Clear hero section with ClinGen compliance messaging
- Dashboard stats (Curated Genes, Active Curations, Clinical Scopes, Pending Review) provide quick orientation
- Key Features cards communicate value proposition
- Recent Activity section personalizes the experience

**Issues:**
- "BROWSE GENES" and "MANAGE GENES" buttons are ambiguous - a curator doesn't know the difference
- Footer overlaps "Key Features" cards on certain viewport heights (footer renders over feature cards at ~960px height)
- Version/build info in navbar is dev-facing, not user-facing

### 2. Clinical Scopes (/scopes)
**Score: 7/10** - Well-organized

**Strengths:**
- Card-based layout with clear scope metadata (genes, members, progress)
- Good filter bar (search, visibility, status, sort)
- Progress bar on each scope card
- "Create Scope" CTA is prominent

**Issues:**
- Lock icon for "Private" scopes is small and could be missed
- No visual distinction between scopes the user belongs to vs. others
- "0% complete" shown even when scope has curations - may be misleading
- No tooltip or explanation for what "Active" status badge means

### 3. Gene Catalogue (/genes)
**Score: 6/10** - Functional with errors

**Strengths:**
- Summary stats at top (Curated Genes, Active Curations, Clinical Scopes)
- Table with essential columns (Gene, Location, Best Score, Classification, Scopes, Diseases)
- Classification badge ("Definitive") is color-coded
- Expandable rows for detail

**Issues:**
- **Console error**: `net::ERR_FAILED` on `/gene-catalogue/filters/scopes` - Scope filter dropdown likely broken
- "Class..." filter label is truncated - should read "Classification"
- "Location: Unknown" for NAA10 - should pull from HGNC data
- No export functionality visible on this page
- Disease column shows "No disease" with a generic icon - unhelpful for curation context

### 4. Dashboard (/dashboard)
**Score: 6/10** - Good concept, empty state

**Strengths:**
- Clear stat cards (Active Assignments, Completed This Month, Pending Review, Active Scopes)
- Quick Actions section with prominent CTAs
- Pending Invitations section
- "My Clinical Scopes" section

**Issues:**
- "Welcome back, User" - should show actual display name (shows "User" not "Admin User")
- All stats show "0" despite existing curations - data isn't populating correctly for admin user
- "No scopes assigned" despite admin having access to scopes - confusing
- "VIEW ALL" link on Recent Activity has no visible destination
- Quick Actions buttons ("New Curation", "View Assignments", "Validation Dashboard", "Schema Management") all look the same - no visual hierarchy

### 5. Scope Detail (/scopes/:id/overview)
**Score: 7/10** - Well-structured

**Strengths:**
- Clear header with scope name, description, and user role badge
- Stats row (Total Genes, Completed, In Progress, Members)
- Progress bar with percentage
- Tabbed interface (Overview, Genes, Curations, Members, Settings) - good information organization
- Scope Information and Statistics side-by-side

**Issues:**
- "Recent Activity (Last 30 Days)" shows "0 Curations Created, 0 Curations Activated" even when curations exist (they were created > 30 days ago) - no fallback messaging
- Statistics list is dense plain text - could benefit from visual hierarchy
- No breadcrumb navigation back to Scopes list

### 6. Scope Curations Tab (/scopes/:id/curations)
**Score: 7/10** - Good data table

**Strengths:**
- Table/Card view toggle
- Sortable columns
- Filter by Status and Curator
- "Start Curation" CTA
- Score displayed as "13.5 / 18" - clear context
- Classification badge color-coded

**Issues:**
- "Start Curation" links to the Genes tab, not a create-curation flow - indirect
- Action menu (three dots) doesn't indicate available actions without clicking
- Date format inconsistent (1/13/2026 vs elsewhere using "Oct 14, 2025, 08:57 PM")

### 7. Curation Detail (/scopes/:id/curations/:id) -- CRITICAL PAGE
**Score: 4/10** - Core workflow with major UX problems

This is the most important page in the application - where curators spend most of their time. It has the most issues.

**Strengths:**
- Score summary header with total points, classification badge, genetic/experimental breakdown
- Gene-Disease Association card with key metadata
- Evidence Score Breakdown table is clear and well-organized
- Export button available
- Save Draft / Submit buttons at bottom
- Metadata section with timestamps and version

**Critical Issues:**

1. **Extremely long single-page scroll form** - The page is ~6000px+ tall. Curators must scroll through the entire evidence form with no section navigation, no collapsible sections, and no progress indicator. This is the #1 usability problem.

2. **Truncated field labels** - Multiple labels are cut off: "Proban...", "Functio...", "Phenot...", "Explan...", "Zyg...", "Lod Sco...", "Segregations Co...", "Proband C...", "mis..." (for variant type). Curators cannot read what fields they're filling in.

3. **"Paternity Maternity Confirmed" checkbox label wraps badly** - Text breaks across 4 lines in a narrow column, barely readable.

4. **Form Warning displayed at bottom**: `evidence_summary: Unknown field type: string` - This is a schema configuration error leaking to the UI. The Evidence Summary field at the top of the form appears broken/non-functional.

5. **No autosave** - On a form this long, losing work to a session timeout or browser crash is a real risk. Only manual "Save Draft" at the very bottom.

6. **Left-heavy layout** - Case Level evidence items are crammed into the left ~40% of the page, while the right ~60% is empty white space. Poor use of horizontal space.

7. **No inline validation** - Fields accept any input without guidance. No indication of required vs. optional fields.

8. **Workflow Actions only shows "Delete"** - No Submit for Review, Request Changes, Approve, or other workflow transition buttons. The multi-stage workflow (Entry -> Precuration -> Curation -> Review -> Active) is not exposed in the UI.

9. **No evidence item summaries** - Each case-level item shows all fields expanded. No way to collapse completed items or see a summary view.

10. **Contradictory Evidence section at very bottom** - Easy to miss. Should be more prominent per ClinGen SOP.

### 8. User Profile (/profile)
**Score: 6/10** - Basic but functional

**Strengths:**
- Clean layout with user info and activity summary
- Change Password section

**Issues:**
- Activity Summary shows all zeros despite admin activity
- No ORCID integration field (important for ClinGen curators)
- No notification preferences
- Console error: `TypeError: Cannot read properties` - JavaScript error on load
- Multiple Vue warnings (`onScopeDispose`)

### 9. Admin - User Management (/admin/users)
**Score: 7/10** - Clean admin interface

**Strengths:**
- Stat cards (Total, Active, Inactive, Recent 30d)
- Search, table with clear columns
- Role badges (admin/user) are color-coded and clear
- Create User CTA

**Issues:**
- No bulk actions (activate/deactivate multiple users)
- "Carol Williams" Last Login shows "Never" - no visual indicator of inactive users
- No user detail/edit page link visible (only three-dot menu)

---

## ClinGen SOP Compliance Assessment

Based on [ClinGen Gene-Disease Validity SOP v11/v12](https://clinicalgenome.org/docs/gene-disease-validity-standard-operating-procedure/):

| ClinGen Requirement | Status | Notes |
|---|---|---|
| Gene-Disease-MOI triple | Present | Shown in Gene-Disease Association card |
| Semi-quantitative scoring (Genetic + Experimental) | Present | 12-point genetic + 6-point experimental correctly implemented |
| 7 classification levels | Partial | "Definitive" shown; need to verify Disputed/Refuted are available |
| Case-level evidence (AD/XL, AR) | Present | Both autosomal recessive and dominant/X-linked sections exist |
| Segregation scoring (LOD) | Present | LOD score field with points |
| Experimental evidence categories | Present | Biochemical Function, Protein Interaction, Expression, Functional Alteration, Models, Rescue |
| Contradictory evidence | Present | Section exists but is at very bottom, easy to miss |
| Disease ontology (MONDO) | Not visible | No MONDO ID shown, only disease name |
| Evidence summary / rationale | Broken | Field exists but has "Unknown field type" error |
| 4-eyes review workflow | Partial | Workflow stages exist in backend but not exposed in curation detail UI |
| Curator GCEP affiliation | Missing | No Expert Panel affiliation shown |
| Publication tracking (PMID) | Present | PMID fields in evidence items |
| Score modification justification | Missing | No field for explaining score adjustments |
| Lumping/splitting documentation | Missing | No disease curation tracking |

**ClinGen Compliance Score: 7/10** - Good framework, gaps in advanced SOP requirements.

---

## Top 10 Recommendations (Priority Order)

### P0 - Critical (Must Fix)

1. **Add section navigation to curation detail page** - Implement a sticky sidebar or tab navigation with sections: Gene-Disease Info, Genetic Evidence (Case Level, Segregation, Case-Control), Experimental Evidence, Contradictory Evidence, Summary. Add collapse/expand per section.

2. **Fix truncated field labels** - Audit all form fields and ensure labels are fully visible. Use tooltips for long labels, or restructure the grid to give fields adequate width.

3. **Fix Evidence Summary field** - Resolve the "Unknown field type: string" schema error. This is the curator's primary narrative field.

4. **Add autosave with recovery** - Implement periodic autosave (every 30-60 seconds) and session recovery for the curation form. The `useFormRecovery` composable exists but may not be active.

### P1 - High Priority

5. **Expose workflow transitions in curation UI** - Add Submit for Review, Approve, Request Changes, and Reject buttons based on user's role and current workflow stage. The backend supports this but the UI only shows "Delete".

6. **Add breadcrumb navigation** - Curators lose context on deep pages. Add breadcrumbs: Scopes > NAA10 Curation Demo > Curations > NAA10.

7. **Fix dashboard data** - Dashboard shows all zeros and "No scopes assigned" for admin user. Fix the data queries to properly aggregate user activity.

### P2 - Important Improvements

8. **Add MONDO disease IDs** - Display MONDO identifiers alongside disease names per ClinGen SOP requirements.

9. **Improve date formatting consistency** - Standardize across the app (currently mixing "1/13/2026", "Oct 14, 2025", "February 28, 2026").

10. **Add keyboard shortcuts** - For power curators: Ctrl+S to save draft, section navigation hotkeys, Tab-order optimization through evidence items.

---

## Additional Recommendations

- **Log viewer panel**: The bottom log panel (Ctrl+L) is always partially loaded, consuming vertical space. Should be hidden by default in production, dev-only feature.
- **Dark mode**: Theme toggle exists but core curation pages aren't optimized for dark mode.
- **Responsive design**: Form layouts break on smaller viewports (< 1024px). The evidence items become unusably narrow.
- **Export**: Export button exists on curation detail but should also be available at scope level for bulk export.
- **Notifications**: Bell icon/count for pending reviews would help reviewers stay on top of their queue.
- **ORCID integration**: Add ORCID fields for curator identification per ClinGen best practices.
- **Inline help**: Add contextual help text or links to ClinGen SOP sections next to complex scoring fields.

---

## Reference Sources

- [ClinGen Gene-Disease Validity Framework](https://clinicalgenome.org/curation-activities/gene-disease-validity/)
- [ClinGen Gene-Disease Validity SOP](https://clinicalgenome.org/docs/gene-disease-validity-standard-operating-procedure/)
- [ClinGen Gene Curation Interface](https://clinicalgenome.org/tools/curation-modules/clingen-gene-disease-validity-curation-module/)
- [GCI Help Docs](https://vci-gci-docs.clinicalgenome.org/vci-gci-docs/gci-help/about-gene-disease-clinical-validity-curation)
- [Better Bioinformatics Through Usability Analysis](https://academic.oup.com/bioinformatics/article/25/3/406/244207)
- [Medical Software UX Design Guide](https://www.devicelab.com/blog/medical-software-ux-design-a-complete-guide/)
- [Harnessing UX Design in Bioinformatics](https://ncanto.in/harnessing_ux_design_in_bioinformatic/)

---

## Screenshots

All audit screenshots saved to `audit/` directory:
- `01-landing-full.png` - Landing page (full)
- `03-scopes-page.png` - Clinical Scopes listing
- `04-gene-catalogue.png` - Gene Catalogue with filters and table
- `05-dashboard.png` - User Dashboard
- `06-scope-detail.png` - Scope detail (Overview tab)
- `07-scope-curations-tab.png` - Scope curations table
- `08a-curation-detail-top.png` - Curation detail header and score breakdown
- `08b-curation-detail-mid.png` - Evidence form (genetic evidence section)
- `08c-curation-detail-lower.png` - Evidence form (case items, truncated labels)
- `08d-curation-detail-bottom.png` - Evidence form (more items)
- `08e-curation-detail-very-bottom.png` - Form bottom with warnings and submit
- `09-profile.png` - User profile page
- `10-admin-users.png` - Admin user management
