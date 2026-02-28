# Requirements: Gene Curator

**Defined:** 2026-02-28
**Core Value:** Every scope can use their own curation methodology with dynamically rendered forms that adapt to any schema definition.

## v0.3 Requirements

Requirements for UX Overhaul milestone. Derived from UX Audit Report (audit/UX_AUDIT_REPORT.md).

### Curation Form UX

- [ ] **FORM-01**: Curation detail page has section navigation with sticky sidebar showing evidence sections (Gene-Disease Info, Genetic Evidence, Experimental Evidence, Contradictory Evidence, Summary)
- [ ] **FORM-02**: All form field labels are fully visible without truncation across all form views
- [ ] **FORM-03**: Evidence Summary field renders correctly (resolve "Unknown field type: string" schema error)
- [ ] **FORM-04**: Curation form autosaves periodically and recovers unsaved work after session loss or browser crash
- [ ] **FORM-05**: Evidence item sections can be collapsed and expanded individually with summary preview when collapsed

### Workflow UI

- [ ] **WKFL-01**: Curation detail page shows workflow transition buttons appropriate to current stage and user role (Submit for Review, Approve, Request Changes, Reject)

### Navigation

- [ ] **NAV-01**: Deep pages show breadcrumb navigation trail (e.g., Scopes > Scope Name > Curations > Gene Symbol)

### Dashboard

- [ ] **DASH-01**: Dashboard displays correct activity counts and scope assignments for all user roles including admin

## Future Requirements

Deferred to future milestone. Tracked from UX audit P2 items.

### ClinGen Compliance

- **CLIN-01**: MONDO disease identifiers displayed alongside disease names per ClinGen SOP
- **CLIN-02**: Score modification justification field for explaining score adjustments
- **CLIN-03**: Curator GCEP affiliation shown on curations

### Curator Productivity

- **PROD-01**: Keyboard shortcuts for common actions (Ctrl+S save, section navigation hotkeys)
- **PROD-02**: Date formatting consistent across all views (standardized format)
- **PROD-03**: Bulk export at scope level for all curations

### Polish

- **POLSH-01**: Log viewer panel hidden by default in production
- **POLSH-02**: Responsive form layouts for viewports < 1024px

## Out of Scope

| Feature | Reason |
|---------|--------|
| Dark mode optimization | Cosmetic, not blocking curator productivity |
| ORCID integration | Requires external API integration, separate effort |
| Inline help / ClinGen SOP links | Content creation effort, not a code fix |
| Notification bell/count | Already implemented in MVP M4 |
| v0.2 Form Intelligence (conditional fields) | Deferred separately, research preserved |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FORM-03 | Phase 10 | Pending |
| DASH-01 | Phase 10 | Pending |
| FORM-01 | Phase 11 | Pending |
| FORM-05 | Phase 11 | Pending |
| NAV-01 | Phase 11 | Pending |
| FORM-02 | Phase 12 | Pending |
| FORM-04 | Phase 12 | Pending |
| WKFL-01 | Phase 12 | Pending |

**Coverage:**
- v0.3 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-02-28 — traceability mapped to phases 10-12*
