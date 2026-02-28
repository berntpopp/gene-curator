# Roadmap: Gene Curator

## Milestones

- ✅ **v0.1 Dynamic Forms** - Phases 1-5 (shipped 2026-01-23)
- 🚧 **MVP** - Phases M1-M4 (in progress)

<details>
<summary>📋 Deferred: v0.2 Form Intelligence — Phases 6-8 (post-MVP, research preserved in .planning/research/)</summary>

**Research:** `.planning/research/FEATURES.md`, `.planning/research/ARCHITECTURE.md`, `.planning/research/PITFALLS.md`
**Requirements:** `.planning/REQUIREMENTS.md` (10 requirements: COND-01..05, XVAL-01..03, DEPS-01..02)

When resumed, phases 6-8 cover conditional visibility, cross-field validation, and field dependencies.
</details>

## Phases

<details>
<summary>✅ v0.1 Dynamic Forms (Phases 1-5) - SHIPPED 2026-01-23</summary>

### Phase 1: Field Rendering
**Goal**: DynamicForm renders fields from schema field_definitions
**Plans**: Completed

Plans:
- [x] 01-01: DynamicField component with type routing
- [x] 01-02: Component registry for specialized evidence fields

### Phase 2: Tab Structure
**Goal**: DynamicForm renders tabs and sections from ui_configuration
**Plans**: Completed

Plans:
- [x] 02-01: TabContent component with section support
- [x] 02-02: Schema-driven tab navigation

### Phase 3: Field Metadata
**Goal**: Fields render with labels, hints, and constraints from schema
**Plans**: Completed

Plans:
- [x] 03-01: Label, hint, placeholder rendering
- [x] 03-02: Required, min, max, pattern constraints

### Phase 4: Validation
**Goal**: Form validation runs against schema rules with backend error integration
**Plans**: Completed

Plans:
- [x] 04-01: useValidationRules composable
- [x] 04-02: Backend error display integration

### Phase 5: Scoring and Integration
**Goal**: Live scoring works for all schema types; ClinGen bypass removed; feature flag controls rollout
**Plans**: Completed

Plans:
- [x] 05-01: Schema-agnostic scoring engine wiring
- [x] 05-02: ClinGen bypass removal and PrecurationFormView schema-driven rendering
- [x] 05-03: Feature flag infrastructure

</details>

### 🚧 MVP (In Progress)

**Milestone Goal:** Complete end-to-end curation workflow so a clinical genetics team can use Gene Curator for real curation work. Detailed plan: `.planning/MVP-PLAN.md`

#### Phase M1: Security Fix + Review Workflow
**Goal**: Fix SQL injection vulnerability and complete the 4-eyes review workflow frontend so curations can be approved by independent reviewers
**Depends on**: v0.1 complete (DynamicForm for read-only evidence display in review)
**Issues**: #116
**Success Criteria** (what must be TRUE):
  1. Gene search uses parameterized queries (no SQL injection)
  2. ReviewQueue shows pending reviews for current user across scopes
  3. CurationReview displays evidence read-only with score and verdict
  4. Approve/Reject/Request Revision all work end-to-end
  5. 4-eyes principle enforced (cannot review own curation)
  6. Review notification badge shows pending count
  7. All existing 529 tests still pass

Tasks:
- [ ] M1.1: Fix SQL injection in gene search (`backend/app/crud/gene.py`)
- [ ] M1.2: Complete ReviewQueue view (wire to workflow store)
- [ ] M1.3: Build CurationReview interface (read-only form + review actions)
- [ ] M1.4: Wire workflow store review methods (fetch, submit, history)
- [ ] M1.5: Review notification badge (nav item badge with auto-refresh)
- [ ] M1.6: End-to-end review workflow test

#### Phase M2: Precuration & Curation Enhancements
**Goal**: Improve daily curator experience with better prefilling, validation, and data integrity
**Depends on**: Phase M1 (review workflow working)
**Issues**: #61, #77, #87
**Success Criteria** (what must be TRUE):
  1. Lump/split fields have validation preventing accidental overwrite
  2. Creating curation from precuration prefills mapped fields via workflow config
  3. Cannot delete precuration that has associated curations
  4. Error messages are clear and actionable

Tasks:
- [ ] M2.1: Enhance precuration card — lump/split validation, prefill verification (#61)
- [ ] M2.2: Implement workflow prefill logic — `data_mapping` driven (#77)
- [ ] M2.3: Prevent precuration deletion with associated curations (#87)

#### Phase M3: Admin Management UI
**Goal**: Complete admin-facing management interfaces for assignments and workflows
**Depends on**: Independent (can run in parallel with M2)
**Issues**: #119, #118
**Success Criteria** (what must be TRUE):
  1. Gene assignment edit/reassign/view dialogs all functional
  2. Workflow view/edit/stage-edit dialogs all functional
  3. Changes immediately reflected in lists
  4. Audit trail maintained for reassignments

Tasks:
- [ ] M3.1: Gene assignment edit/reassign dialogs (#119)
- [ ] M3.2: Workflow management detail/edit views (#118)

#### Phase M4: MVP Hardening
**Goal**: Fix tech debt items, smoke test all paths, update documentation
**Depends on**: Phases M1-M3 complete
**Issues**: #104
**Success Criteria** (what must be TRUE):
  1. Gene summary shows actual curator count (not hardcoded 1)
  2. In-app notifications work for review events
  3. All workflow paths tested end-to-end
  4. Documentation updated for end users

Tasks:
- [ ] M4.1: Fix gene summary curator count
- [ ] M4.2: Fix notification store API integration
- [ ] M4.3: Smoke test all workflow paths
- [ ] M4.4: Update documentation

## Progress

**Execution Order:**
MVP phases: M1 → M2 (+ M3 in parallel) → M4

| Phase | Milestone | Tasks/Plans | Status | Completed |
|-------|-----------|-------------|--------|-----------|
| 1. Field Rendering | v0.1 | 2/2 | Complete | 2026-01-23 |
| 2. Tab Structure | v0.1 | 2/2 | Complete | 2026-01-23 |
| 3. Field Metadata | v0.1 | 2/2 | Complete | 2026-01-23 |
| 4. Validation | v0.1 | 2/2 | Complete | 2026-01-23 |
| 5. Scoring and Integration | v0.1 | 3/3 | Complete | 2026-01-23 |
| M1. Security + Review Workflow | MVP | 0/6 | Not started | - |
| M2. Curation Enhancements | MVP | 0/3 | Not started | - |
| M3. Admin Management UI | MVP | 0/2 | Not started | - |
| M4. MVP Hardening | MVP | 0/4 | Not started | - |
