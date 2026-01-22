# FEATURES.md - Dynamic Form Features

**Domain:** Schema-driven curation forms for clinical genetics
**Researched:** 2026-01-22
**Confidence:** HIGH (based on existing codebase analysis + industry patterns)

## Context

Gene Curator has existing DynamicForm and DynamicField components that are 70-80% complete. The task is wiring them to actual form views (PrecurationFormView, CurationFormView) so any scope can use their own curation methodology without code changes.

**Current State:**
- Backend: Complete schema system with `field_definitions`, `ui_configuration`, `scoring_configuration`
- Frontend: DynamicForm/DynamicField exist but aren't used by actual form views
- Hardcoding: Forms currently bypass dynamic rendering for ClinGen schemas

---

## Table Stakes (Required for v0.1)

Features that MUST work for the system to be usable. Without these, curators cannot effectively use schema-driven forms.

### 1. Schema-Driven Field Rendering

| Aspect | Details |
|--------|---------|
| What | Render form fields from `field_definitions` JSON, not hardcoded Vue templates |
| Complexity | Medium - DynamicField exists, needs wiring |
| Existing | DynamicField handles 14 types (text, number, boolean, date, array, object, select, multiselect, email, url, pmid, hgnc_id, score) |
| Gap | PrecurationFormView (777 lines hardcoded) ignores `precurationSchemaId` prop |
| Dependency | Backend `/api/v1/schemas/{id}` endpoint (already exists) |

### 2. Tab/Section Rendering from ui_configuration

| Aspect | Details |
|--------|---------|
| What | Render tabs and sections from schema's `ui_configuration.layout.sections` array |
| Complexity | Medium - v-tabs component exists in Vuetify, needs mapping |
| Existing | Schema format supports `sections` with `name`, `collapsible`, `collapsed`, `fields`, `columns` |
| Gap | CurationFormView has hardcoded 5 tabs (Summary, Genetic Evidence, Experimental Evidence, Contradictory, Lumping & Splitting) |
| Dependency | Schema `ui_configuration` parsing |

**Best Practice (from research):** Limit to 2 levels of nesting max. Beyond that, use accordions or progressive disclosure patterns.

### 3. Validation from Schema Rules

| Aspect | Details |
|--------|---------|
| What | Run validation against schema's `validation_rules`, not hardcoded patterns |
| Complexity | Low - validationStore exists with `validateEvidence()`, `validateField()` |
| Existing | Backend validation API complete, DynamicField has `getValidationRules()` |
| Gap | Currently validates at component level, not from schema rules |
| Dependency | `validationStore.validateEvidence(data, schemaId)` |

**Best Practice (from research):** "Reward early, punish late" - show success indicators immediately, delay error messages until blur or submit.

### 4. Live Score Calculation (Any Schema)

| Aspect | Details |
|--------|---------|
| What | Calculate and display scores in real-time for any schema type (not just ClinGen) |
| Complexity | Medium - scoring engines exist (clingen, gencc, qualitative), needs schema-driven selection |
| Existing | `scoring_configuration.engine` field, ScorePreview component, backend scoring APIs |
| Gap | Score calculation currently tied to ClinGen SOP categories |
| Dependency | Schema `scoring_configuration`, backend scoring endpoints |

### 5. Remove ClinGen Detection Bypass

| Aspect | Details |
|--------|---------|
| What | Remove the `isClinGenSchema` check that bypasses dynamic rendering |
| Complexity | Low - single condition removal, but requires confidence that dynamic form works |
| Existing | SchemaDrivenCurationForm line 199-201: `schemaName.includes('clingen')` |
| Gap | This bypass defeats the entire purpose of schema-driven design |
| Dependency | All other table stakes features working |

### 6. Nested/Recursive Field Rendering

| Aspect | Details |
|--------|---------|
| What | Render nested objects and arrays (e.g., evidence items with sub-fields) |
| Complexity | Low - DynamicField already supports recursive rendering |
| Existing | DynamicField handles `type: 'array'` and `type: 'object'` with nested properties |
| Gap | Already implemented, needs testing with real schema data |
| Dependency | None (already working) |

### 7. Form Submission and Draft Saving

| Aspect | Details |
|--------|---------|
| What | Submit form data, save drafts, handle workflow transitions |
| Complexity | Low - already implemented in SchemaDrivenCurationForm |
| Existing | `handleSubmit()`, `handleSaveDraft()`, curationsStore integration |
| Gap | None - this works |
| Dependency | Backend workflow endpoints |

---

## Differentiators (Future Milestones)

Nice-to-have features that add value but are not required for v0.1. These can be deferred.

### 1. Conditional Field Visibility

| Aspect | Details |
|--------|---------|
| What | Show/hide fields based on other field values (e.g., show "distance willing to travel" only if "willing to travel" = true) |
| Complexity | High - requires expression evaluation, dependency tracking |
| Why Defer | v0.1 focus is wiring existing components; conditional logic adds significant complexity |
| Industry Pattern | Salesforce, Jotform, Gravity Forms all support this via rules-based conditions |

**Schema Support Needed:**
```json
{
  "field_name": {
    "visibility": {
      "conditions": [
        { "field": "other_field", "operator": "==", "value": true }
      ],
      "operator": "AND"
    }
  }
}
```

### 2. Cross-Field Validation

| Aspect | Details |
|--------|---------|
| What | Validate field A based on field B's value (e.g., "end date must be after start date") |
| Complexity | Medium - requires form-level validation context |
| Why Defer | Single-field validation covers most cases; cross-field is enhancement |
| Existing | Schema format supports `validation_rules` with custom functions |

### 3. Field Dependencies (Cascading Selects)

| Aspect | Details |
|--------|---------|
| What | When field A changes, update options in field B (e.g., select country -> update state options) |
| Complexity | Medium - requires API calls or data maps |
| Why Defer | Not common in curation workflows; defer until needed |

### 4. Inline Field Help/Documentation

| Aspect | Details |
|--------|---------|
| What | Show help text, tooltips, or documentation links per field |
| Complexity | Low - DynamicField already renders `fieldSchema.description` |
| Why Defer | Basic description support exists; rich help is enhancement |
| Existing | Line 206-208 in DynamicField: renders description below field |

### 5. Form Progress Indicator

| Aspect | Details |
|--------|---------|
| What | Show completion percentage, required fields remaining, section completion |
| Complexity | Medium - requires tracking filled vs required fields |
| Why Defer | Not essential for v0.1 functionality |
| Industry Pattern | Common in multi-step forms, wizard UIs |

### 6. Keyboard Navigation

| Aspect | Details |
|--------|---------|
| What | Tab through fields, Enter to advance, shortcuts for common actions |
| Complexity | Low - Vuetify handles basic tab navigation |
| Existing | SchemaDrivenCurationForm has Ctrl+S, Ctrl+Z, Ctrl+Enter, Esc |
| Why Defer | Basic keyboard support exists |

### 7. ARIA Accessibility Enhancements

| Aspect | Details |
|--------|---------|
| What | Full WCAG compliance with aria-describedby, aria-labelledby, screen reader support |
| Complexity | Medium - requires audit and systematic fixes |
| Why Defer | Vuetify provides baseline accessibility; full compliance is enhancement |

### 8. Form Templates / Presets

| Aspect | Details |
|--------|---------|
| What | Pre-fill forms with common values, copy from previous curation |
| Complexity | Medium - requires template storage and application |
| Why Defer | Nice productivity feature, not essential |

---

## Anti-Features (Do NOT Build in v0.1)

Features to explicitly avoid. Either out of scope, premature optimization, or wrong approach.

### 1. Drag-and-Drop Form Builder UI

| What | Visual form designer for creating schemas |
| Why Avoid | Schemas are defined by admin via database; this is a separate product |
| What Instead | Use existing admin UI or direct database editing |

### 2. Real-Time Collaboration (Multi-User Editing)

| What | Google Docs-style simultaneous editing |
| Why Avoid | Massive complexity (WebSocket, conflict resolution, presence); workflow handles review process |
| What Instead | Lock version field exists for optimistic concurrency |

### 3. Custom Component Registration at Runtime

| What | Allow schemas to reference custom Vue components dynamically |
| Why Avoid | Security risk, complexity, debugging nightmare |
| What Instead | Fixed set of registered components (14 field types) that cover all use cases |

### 4. Client-Side Schema Editing

| What | Edit schema definitions from the curation form UI |
| Why Avoid | Schemas are institutional configurations, not user data |
| What Instead | Admin-only schema management |

### 5. Offline-First / IndexedDB Storage

| What | Full offline capability with background sync |
| Why Avoid | Curation is typically done online; localStorage recovery is sufficient |
| What Instead | useFormRecovery composable (already exists) with localStorage auto-save |

### 6. AI-Assisted Field Completion

| What | Auto-suggest field values based on ML models |
| Why Avoid | Out of scope for form infrastructure; separate feature |
| What Instead | Standard form inputs with validation |

### 7. PDF Export / Print Layouts

| What | Generate printable reports from form data |
| Why Avoid | This is a reporting feature, not form infrastructure |
| What Instead | Defer to reporting milestone |

### 8. Form Versioning (Time-Travel)

| What | See form state at any point in history |
| Why Avoid | Complexity; audit log exists for change tracking |
| What Instead | Undo/redo (already exists via useHistory composable) |

### 9. Dynamic Field Type Switching

| What | Change field type (e.g., text -> select) based on conditions |
| Why Avoid | Schema defines field types; runtime switching adds complexity |
| What Instead | Use conditional visibility to show/hide different field variants |

---

## Feature Dependencies

```
Schema-Driven Field Rendering
    |
    +-- Tab/Section Rendering (needs fields first)
    |
    +-- Validation from Schema Rules (validates rendered fields)
    |
    +-- Live Score Calculation (scores based on field values)
            |
            +-- Remove ClinGen Bypass (only after above work)
```

### Dependency Details

| Feature | Depends On | Reason |
|---------|-----------|--------|
| Tab/Section Rendering | Field Rendering | Tabs organize fields; fields must render first |
| Validation | Field Rendering | Validation triggers on field events |
| Live Scoring | Field Rendering + Validation | Scores calculated from valid field values |
| Remove ClinGen Bypass | All above | Can only remove after dynamic forms proven working |

### Implementation Order (Recommended)

1. **Field Rendering** - Wire DynamicForm to PrecurationFormView
2. **Tab/Section Rendering** - Implement ui_configuration parsing
3. **Validation** - Connect schema validation rules
4. **Live Scoring** - Enable scoring for any schema
5. **Remove Bypass** - Final step after testing

---

## Existing Infrastructure Summary

| Component | Status | Location |
|-----------|--------|----------|
| DynamicForm | Exists, unused | `frontend/src/components/dynamic/DynamicForm.vue` |
| DynamicField | Exists, 14 field types | `frontend/src/components/dynamic/DynamicField.vue` |
| useFormRecovery | Exists, working | `frontend/src/composables/useFormRecovery.js` |
| useHistory (undo/redo) | Exists, working | `frontend/src/composables/useHistory.js` |
| validationStore | Exists, working | `frontend/src/stores/validation.js` |
| schemasStore | Exists, working | `frontend/src/stores/schemas.js` |
| Backend validation API | Exists, working | `/api/v1/validation/` |
| Backend schemas API | Exists, working | `/api/v1/schemas/` |
| ui_configuration spec | Exists | `docs/schema-format/specifications.md` |

---

## Sources

**Industry Research:**
- [Vueform Builder](https://builder.vueform.com) - Vue 3 dynamic form builder with nested fields
- [FormKit](https://formkit.com/) - Open-source form framework for Vue
- [VeeValidate Nested Objects](https://vee-validate.logaretm.com/v4/guide/composition-api/nested-objects-and-arrays/) - Array field handling
- [JSON Forms](https://jsonforms.io/) - Schema-driven form rendering
- [Smashing Magazine - Inline Validation UX](https://www.smashingmagazine.com/2022/09/inline-validation-web-forms-ux/) - Validation patterns
- [Expedia - Schema Driven UIs](https://medium.com/expedia-group-tech/schema-driven-uis-dd8fdb516120) - Architecture patterns
- [Nested Tab UI Examples](https://www.designmonks.co/blog/nested-tab-ui) - Tab depth best practices
- [Eleken - Tabs UX](https://www.eleken.co/blog-posts/tabs-ux) - When to use tabs

**Codebase Analysis:**
- `DynamicForm.vue` - 317 lines, handles schemaId prop, validation, scoring
- `DynamicField.vue` - 402 lines, 14 field types, recursive rendering
- `SchemaDrivenCurationForm.vue` - 641 lines, ClinGen bypass at line 199
- `useFormRecovery.js` - localStorage auto-save with recovery dialog
- `docs/schema-format/specifications.md` - Complete schema format spec
