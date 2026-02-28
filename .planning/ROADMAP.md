# Roadmap: Gene Curator

## Milestones

- ✅ **v0.1 Dynamic Forms** - Phases 1-5 (shipped 2026-01-23)
- 🚧 **v0.2 Form Intelligence** - Phases 6-8 (in progress)

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

### 🚧 v0.2 Form Intelligence (In Progress)

**Milestone Goal:** Make dynamic forms context-aware — fields react to each other through conditional visibility, cross-field validation, and cascading dependencies.

#### Phase 6: Conditional Visibility Engine
**Goal**: Fields show and hide based on other field values, driven by a single reactive composable with a safe, unified condition format
**Depends on**: Phases 1-5 (DynamicForm component tree complete)
**Requirements**: COND-01, COND-02, COND-03, COND-04, COND-05
**Success Criteria** (what must be TRUE):
  1. When a curator changes a field value, dependent fields appear or disappear immediately without page reload
  2. Fields defined with either legacy syntax (show_when object or condition string) behave identically to fields using the canonical visibility format
  3. When a field is hidden, its value is cleared to null and excluded from the form submission payload
  4. Loading a schema with a circular field dependency (A visibility depends on B, B visibility depends on A) logs a descriptive error and does not freeze the browser tab
  5. All four production schemas load and render fields correctly after syntax normalization runs
**Plans**: TBD

Plans:
- [ ] 06-01: useFieldInteractions composable — visibilityMap, DAG cycle detection, legacy syntax normalization
- [ ] 06-02: DynamicForm + TabContent + DynamicField wiring — v-if visibility, hidden field data handling

#### Phase 7: Cross-Field Validation
**Goal**: Validation rules can reference other field values so that conditional required fields and date/numeric constraints are enforced correctly
**Depends on**: Phase 6 (useFieldInteractions composable and visibility engine in place)
**Requirements**: XVAL-01, XVAL-02, XVAL-03
**Success Criteria** (what must be TRUE):
  1. When a curator leaves a conditionally required field empty after the triggering field is set, the form shows a validation error on that field and blocks submission
  2. Cross-field rules defined in schema validation_rules.cross_field (date ordering, numeric bounds) produce inline error messages on the dependent field
  3. Hidden fields never trigger required-field backend validation errors, even when the schema marks them required
**Plans**: TBD

Plans:
- [ ] 07-01: useFieldInteractions extended with crossFieldRules computed map and operator set
- [ ] 07-02: DynamicField cross-field rule merging and backend hidden-field alignment

#### Phase 8: Field Dependencies
**Goal**: Select options cascade from parent field values and MONDO ID selection auto-populates the disease name without manual entry
**Depends on**: Phase 7 (visibility and cross-field validation stable before adding formData mutations)
**Requirements**: DEPS-01, DEPS-02
**Success Criteria** (what must be TRUE):
  1. When a curator selects a value in a parent select field, the child select immediately shows only the options valid for that parent value
  2. When a curator changes the parent select, the child select clears its current value if that value is no longer in the updated option set
  3. When a curator selects a MONDO ID from the disease search, the disease_name field populates automatically without a second lookup action
  4. When a MONDO lookup is in flight and the curator selects a different MONDO ID, only the result for the second selection is applied (no stale overwrite)
**Plans**: TBD

Plans:
- [ ] 08-01: useFieldInteractions extended with dynamicOptions computed map and cascading select logic
- [ ] 08-02: MONDO auto-population via getAutoPopulateUpdates and AbortController race prevention

## Progress

**Execution Order:**
Phases execute in numeric order: 6 → 7 → 8

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Field Rendering | v0.1 | 2/2 | Complete | 2026-01-23 |
| 2. Tab Structure | v0.1 | 2/2 | Complete | 2026-01-23 |
| 3. Field Metadata | v0.1 | 2/2 | Complete | 2026-01-23 |
| 4. Validation | v0.1 | 2/2 | Complete | 2026-01-23 |
| 5. Scoring and Integration | v0.1 | 3/3 | Complete | 2026-01-23 |
| 6. Conditional Visibility Engine | v0.2 | 0/2 | Not started | - |
| 7. Cross-Field Validation | v0.2 | 0/2 | Not started | - |
| 8. Field Dependencies | v0.2 | 0/2 | Not started | - |
