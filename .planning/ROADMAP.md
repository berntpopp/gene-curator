# Roadmap: Gene Curator

## Milestones

- ✅ **v0.1 Dynamic Forms** — Phases 1-5 (shipped 2026-01-23)
- ✅ **MVP** — Phases M1-M4 (shipped 2026-02-28)
- 🚧 **v0.3 UX Overhaul** — Phases 10-12 (in progress)

<details>
<summary>Deferred: v0.2 Form Intelligence (research preserved in milestones/v0.2-deferred/)</summary>

**Research:** `milestones/v0.2-deferred/research/FEATURES.md`, `ARCHITECTURE.md`, `PITFALLS.md`
**Requirements:** `milestones/v0.2-deferred/REQUIREMENTS.md` (10 requirements: COND-01..05, XVAL-01..03, DEPS-01..02)

When resumed, covers conditional visibility, cross-field validation, and field dependencies.
</details>

## Phases

<details>
<summary>✅ v0.1 Dynamic Forms (Phases 1-5) — SHIPPED 2026-01-23</summary>

5 phases, 12 plans. Archives: `milestones/v0.1-phases/`, `milestones/v0.1-ROADMAP.md`
</details>

<details>
<summary>✅ MVP (Phases M1-M4) — SHIPPED 2026-02-28</summary>

4 phases, 14 plans. Archives: `milestones/mvp-phases/`, `milestones/mvp-ROADMAP.md`
</details>

### 🚧 v0.3 UX Overhaul (In Progress)

**Milestone Goal:** Fix critical UX issues identified by audit to raise curator productivity from 4/10 to production-grade.

- [ ] **Phase 10: Schema and Data Fixes** - Fix Evidence Summary field type error and dashboard data query bug
- [ ] **Phase 11: Curation Form Navigation** - Add section sidebar, collapsible sections, and breadcrumb navigation
- [ ] **Phase 12: Form Usability and Workflow Actions** - Fix label truncation, add autosave with recovery, and expose workflow transition buttons

## Phase Details

### Phase 10: Schema and Data Fixes
**Goal**: Backend defects that corrupt data presentation are resolved — the Evidence Summary field renders correctly and the dashboard shows accurate activity counts
**Depends on**: Nothing (first phase of v0.3)
**Requirements**: FORM-03, DASH-01
**Success Criteria** (what must be TRUE):
  1. Evidence Summary field renders as an editable text area on the curation form without any "Unknown field type: string" error message
  2. Dashboard activity counts reflect the actual number of curations, assignments, and reviews for every user role including admin
  3. Scope assignment counts on the dashboard are non-zero for users who have active scope memberships
**Plans**: TBD

### Phase 11: Curation Form Navigation
**Goal**: Curators can orient themselves within the curation detail page and reach any section without scrolling the full page
**Depends on**: Phase 10
**Requirements**: FORM-01, FORM-05, NAV-01
**Success Criteria** (what must be TRUE):
  1. A sticky sidebar (desktop) or tab bar shows all evidence sections (Gene-Disease Info, Genetic Evidence, Experimental Evidence, Contradictory Evidence, Summary) and highlights the active section as the user scrolls
  2. Clicking a section name in the sidebar scrolls directly to that section without full-page reload
  3. Each evidence section can be individually collapsed to a one-line summary preview and re-expanded without losing entered data
  4. Deep pages (e.g., a curation detail page) show a breadcrumb trail such as "Scopes > Scope Name > Curations > Gene Symbol" allowing one-click navigation to any parent level
**Plans**: TBD

### Phase 12: Form Usability and Workflow Actions
**Goal**: Curators can complete a full curation session without losing work and can advance or transition the workflow directly from the curation detail page
**Depends on**: Phase 11
**Requirements**: FORM-02, FORM-04, WKFL-01
**Success Criteria** (what must be TRUE):
  1. All form field labels are fully visible across all form views — no label is clipped or truncated regardless of field name length
  2. The curation form autosaves every 60 seconds and displays a visible timestamp of the last autosave
  3. After a session loss or browser crash, reopening the curation form presents an offer to restore the unsaved draft
  4. Workflow transition buttons (Submit for Review, Approve, Request Changes, Reject) appear on the curation detail page matching the current stage and the logged-in user's role, and clicking one transitions the curation state immediately
**Plans**: TBD

## Progress

**Execution Order:** Phases execute in numeric order: 10 → 11 → 12

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-5 (Field Rendering → Scoring) | v0.1 | 12/12 | Complete | 2026-01-23 |
| M1-M4 (Security → Hardening) | MVP | 14/14 | Complete | 2026-02-28 |
| 10. Schema and Data Fixes | v0.3 | 0/TBD | Not started | - |
| 11. Curation Form Navigation | v0.3 | 0/TBD | Not started | - |
| 12. Form Usability and Workflow Actions | v0.3 | 0/TBD | Not started | - |
