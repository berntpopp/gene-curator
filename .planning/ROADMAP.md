# Roadmap: Gene Curator v0.1 — Dynamic Forms

## Overview

This milestone transforms the Gene Curator frontend from hardcoded ClinGen forms to schema-driven dynamic forms. The journey starts with completing DynamicField rendering, adds tab/section structure and field metadata, wires validation and scoring, and culminates with removing the ClinGen bypass and refactoring existing form views. Each phase builds on the previous, with highest-risk integration work (bypass removal, precuration refactor) deferred until dynamic forms are proven working.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Field Rendering** - Complete DynamicField component to handle all field types with component registry
- [x] **Phase 2: Tab Structure** - Add ui_configuration-driven tab and section rendering to DynamicForm
- [x] **Phase 3: Field Metadata** - Enhance DynamicField with icons, hints, tooltips, and help links
- [ ] **Phase 4: Validation** - Wire Vuetify rules generation and backend validation integration
- [ ] **Phase 5: Scoring and Integration** - Display live scores and integrate DynamicForm into form views

## Phase Details

### Phase 1: Field Rendering
**Goal**: DynamicField renders any field type defined in schema field_definitions, including nested structures and specialized components
**Depends on**: Nothing (first phase)
**Requirements**: FRND-01, FRND-02, FRND-03, FRND-04, FRND-05, FRND-06
**Success Criteria** (what must be TRUE):
  1. DynamicForm displays all fields from schema field_definitions when given a schemaId
  2. Nested object fields render as grouped cards with all child fields visible
  3. Array fields have working add/remove controls that maintain data integrity
  4. Specialized components (MONDOAutocomplete, PMIDInput, HPOInheritanceSelect, OMIMAutocomplete) render when field specifies component property
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Create component registry and enhance DynamicField with registry integration, depth tracking, nested styling
- [x] 01-02-PLAN.md — Add test coverage for componentRegistry and DynamicField enhancements

### Phase 2: Tab Structure
**Goal**: DynamicForm organizes fields into tabs and sections based on schema ui_configuration
**Depends on**: Phase 1
**Requirements**: TABS-01, TABS-02, TABS-03, TABS-04, TABS-05, TABS-06, TABS-07
**Success Criteria** (what must be TRUE):
  1. Form renders with v-tabs matching ui_configuration.layout.tabs array
  2. Each tab displays its sections with fields grouped correctly
  3. Tab headers show icons and score badges when configured
  4. Forms without ui_configuration render as flat field list (backward compatible)
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Create TabContent component and enhance DynamicForm with v-tabs/v-window navigation and fallback
- [x] 02-02-PLAN.md — Add score badges to tabs and comprehensive test coverage for tab structure

### Phase 3: Field Metadata
**Goal**: DynamicField displays rich metadata (icons, hints, tooltips, help links) from field_definitions
**Depends on**: Phase 1
**Requirements**: META-01, META-02, META-03, META-04, META-05
**Success Criteria** (what must be TRUE):
  1. Fields display prepend icons when icon property is defined
  2. Persistent hints appear below fields when hint property is defined
  3. Tooltip shows on icon hover when tooltip property is defined
  4. Help icon links to external documentation when helpUrl property is defined
  5. Fields render correctly when any metadata property is absent
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Add metadata computed properties and slots to DynamicField (icon, hint, tooltip, helpUrl)
- [x] 03-02-PLAN.md — Add test coverage for field metadata features

### Phase 4: Validation
**Goal**: DynamicForm enforces schema validation rules with inline error display
**Depends on**: Phase 1, Phase 2
**Requirements**: VALD-01, VALD-02, VALD-03, VALD-04, VALD-05, VALD-06
**Success Criteria** (what must be TRUE):
  1. Required fields show validation error when empty
  2. Fields enforce min/max length, minimum/maximum value, pattern, and enum constraints
  3. Backend validation errors appear inline on affected fields
  4. Form submission is blocked when validation fails
**Plans**: TBD

Plans:
- [ ] 04-01: TBD

### Phase 5: Scoring and Integration
**Goal**: DynamicForm displays live scores and replaces hardcoded form views
**Depends on**: Phase 4
**Requirements**: SCOR-01, SCOR-02, SCOR-03, SCOR-04, SCOR-05, INTG-01, INTG-02, INTG-03, INTG-04, INTG-05, INTG-06, INTG-07
**Success Criteria** (what must be TRUE):
  1. Score preview displays breakdown based on schema scoring engine (ClinGen, GenCC, Qualitative)
  2. Scores update live as user modifies evidence data
  3. Classification label derived from schema scoring thresholds
  4. ClinGen bypass removed from SchemaDrivenCurationForm (all schemas use DynamicForm)
  5. Existing ClinGen curations load and save correctly through DynamicForm
  6. PrecurationFormView uses DynamicForm instead of hardcoded panels
  7. Form recovery (localStorage auto-save) works with DynamicForm
**Plans**: TBD

Plans:
- [ ] 05-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Field Rendering | 2/2 | ✓ Complete | 2026-01-22 |
| 2. Tab Structure | 2/2 | ✓ Complete | 2026-01-22 |
| 3. Field Metadata | 2/2 | ✓ Complete | 2026-01-22 |
| 4. Validation | 0/TBD | Not started | - |
| 5. Scoring and Integration | 0/TBD | Not started | - |

---
*Roadmap created: 2026-01-22*
*Phase 1 planned: 2026-01-22*
*Phase 1 completed: 2026-01-22*
*Phase 2 planned: 2026-01-22*
*Phase 2 completed: 2026-01-22*
*Phase 3 planned: 2026-01-22*
*Phase 3 completed: 2026-01-22*
*Total requirements: 32 | Phases: 5 | Coverage: 100%*
