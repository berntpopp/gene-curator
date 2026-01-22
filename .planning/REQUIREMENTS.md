# Requirements: Gene Curator v0.1 — Dynamic Forms

**Defined:** 2026-01-22
**Core Value:** Every scope can use their own curation methodology with dynamically rendered forms

## v0.1 Requirements

Requirements for milestone v0.1. Each maps to roadmap phases.

### Field Rendering

- [ ] **FRND-01**: DynamicForm receives schemaId prop and fetches field_definitions from schema API
- [ ] **FRND-02**: DynamicField renders appropriate Vuetify component based on field type (string, number, boolean, date, select, array, object)
- [ ] **FRND-03**: Nested objects render as grouped fields with v-card container
- [ ] **FRND-04**: Nested arrays render with add/remove item controls and recursive field rendering
- [ ] **FRND-05**: Component registry maps field `component` property to specialized Vue components (MONDOAutocomplete, PMIDInput, HPOInheritanceSelect, OMIMAutocomplete)
- [ ] **FRND-06**: DynamicField uses component from registry when field_definition specifies `component` property

### Tab/Section Structure

- [ ] **TABS-01**: DynamicForm reads ui_configuration.layout.tabs array from schema
- [ ] **TABS-02**: DynamicForm renders v-tabs with v-tab for each tab in configuration
- [ ] **TABS-03**: Each tab renders its sections as defined in tab.sections array
- [ ] **TABS-04**: Sections group related fields with optional collapsible behavior
- [ ] **TABS-05**: Tab headers display icon from tab configuration (icon property)
- [ ] **TABS-06**: Tab headers display score badge when tab.show_score_badge is true
- [ ] **TABS-07**: Fallback to flat field list when ui_configuration is absent (backward compatible)

### Field Metadata

- [ ] **META-01**: DynamicField displays prepend-icon from field_definition.icon property
- [ ] **META-02**: DynamicField shows persistent hint below field from field_definition.hint property
- [ ] **META-03**: DynamicField renders v-tooltip with field_definition.tooltip content on icon hover
- [ ] **META-04**: DynamicField shows help icon that links to field_definition.helpUrl when present
- [ ] **META-05**: Field metadata properties are optional and gracefully omitted when not defined

### Validation

- [ ] **VALD-01**: DynamicField generates Vuetify :rules from schema constraints (required, minLength, maxLength, minimum, maximum)
- [ ] **VALD-02**: DynamicField generates pattern validation rule from field_definition.pattern
- [ ] **VALD-03**: DynamicField generates enum validation rule when field_definition.enum is present
- [ ] **VALD-04**: DynamicForm calls validationStore.validateEvidence() on form data change (debounced)
- [ ] **VALD-05**: Backend validation errors display inline on affected fields via error-messages prop
- [ ] **VALD-06**: Form submission blocked when validation fails (v-form ref.validate())

### Scoring

- [ ] **SCOR-01**: DynamicForm displays score_calculations from validation response when available
- [ ] **SCOR-02**: Score calculation works for any schema type by using schema's scoring_configuration.engine
- [ ] **SCOR-03**: ScorePreview component renders score breakdown based on schema type (ClinGen categories, GenCC levels, Qualitative ratings)
- [ ] **SCOR-04**: Score updates live as user modifies evidence data (via debounced validation)
- [ ] **SCOR-05**: Classification label derived from schema's scoring_configuration.classification_thresholds

### Integration

- [ ] **INTG-01**: Remove isClinGenSchema check from SchemaDrivenCurationForm.vue
- [ ] **INTG-02**: SchemaDrivenCurationForm passes full schema (field_definitions + ui_configuration) to DynamicForm
- [ ] **INTG-03**: CurationFormView loads curations using DynamicForm for all schema types
- [ ] **INTG-04**: PrecurationFormView replaced with DynamicForm-based rendering
- [ ] **INTG-05**: Existing ClinGen curations load and save correctly through DynamicForm
- [ ] **INTG-06**: Existing precurations load and save correctly through DynamicForm
- [ ] **INTG-07**: Form recovery (localStorage auto-save) works with DynamicForm

## Future Requirements (v0.2+)

Deferred to future milestones. Tracked but not in current roadmap.

### Conditional Visibility

- **COND-01**: Fields show/hide based on other field values
- **COND-02**: Visibility rules defined in field_definition.visibility property

### Cross-Field Validation

- **XVAL-01**: Validation rules can reference other field values
- **XVAL-02**: Cross-field rules defined in schema validation_rules

### Field Dependencies

- **DEPS-01**: Cascading selects (field B options depend on field A value)
- **DEPS-02**: Auto-population (selecting MONDO ID populates disease_name)

### Form Progress

- **PROG-01**: Progress indicator showing completion percentage
- **PROG-02**: Required fields remaining count

### Accessibility

- **A11Y-01**: Full WCAG compliance for form fields
- **A11Y-02**: Screen reader support for dynamic forms

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Drag-and-drop form builder | Schemas defined by admin via database; separate product |
| Real-time collaboration | Massive complexity; workflow handles review process |
| Custom component registration at runtime | Security risk, debugging nightmare |
| Client-side schema editing | Schemas are institutional configurations |
| Offline-first / IndexedDB | Curation done online; localStorage recovery sufficient |
| AI-assisted field completion | Separate feature, out of scope for form infrastructure |
| PDF export / print layouts | Reporting feature, not form infrastructure |
| Form versioning (time-travel) | Audit log exists; undo/redo via useHistory |
| Backend schema changes | Backend is complete per PROJECT.md constraints |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FRND-01 | Phase 1 | Pending |
| FRND-02 | Phase 1 | Pending |
| FRND-03 | Phase 1 | Pending |
| FRND-04 | Phase 1 | Pending |
| FRND-05 | Phase 1 | Pending |
| FRND-06 | Phase 1 | Pending |
| TABS-01 | Phase 2 | Pending |
| TABS-02 | Phase 2 | Pending |
| TABS-03 | Phase 2 | Pending |
| TABS-04 | Phase 2 | Pending |
| TABS-05 | Phase 2 | Pending |
| TABS-06 | Phase 2 | Pending |
| TABS-07 | Phase 2 | Pending |
| META-01 | Phase 3 | Pending |
| META-02 | Phase 3 | Pending |
| META-03 | Phase 3 | Pending |
| META-04 | Phase 3 | Pending |
| META-05 | Phase 3 | Pending |
| VALD-01 | Phase 4 | Pending |
| VALD-02 | Phase 4 | Pending |
| VALD-03 | Phase 4 | Pending |
| VALD-04 | Phase 4 | Pending |
| VALD-05 | Phase 4 | Pending |
| VALD-06 | Phase 4 | Pending |
| SCOR-01 | Phase 5 | Pending |
| SCOR-02 | Phase 5 | Pending |
| SCOR-03 | Phase 5 | Pending |
| SCOR-04 | Phase 5 | Pending |
| SCOR-05 | Phase 5 | Pending |
| INTG-01 | Phase 5 | Pending |
| INTG-02 | Phase 5 | Pending |
| INTG-03 | Phase 5 | Pending |
| INTG-04 | Phase 5 | Pending |
| INTG-05 | Phase 5 | Pending |
| INTG-06 | Phase 5 | Pending |
| INTG-07 | Phase 5 | Pending |

**Coverage:**
- v0.1 requirements: 32 total
- Mapped to phases: 32
- Unmapped: 0

---
*Requirements defined: 2026-01-22*
*Last updated: 2026-01-22 after roadmap creation*
