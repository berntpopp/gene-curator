# PITFALLS.md - Dynamic Form Integration

**Domain:** Converting hardcoded Vue 3 forms to schema-driven dynamic forms
**Project:** Gene Curator - ClinGen SOP v11 to multi-schema support
**Researched:** 2026-01-22
**Stack:** Vue 3 + Vuetify 3 + Pinia

---

## Critical Pitfalls

Mistakes that cause rewrites, data loss, or major regressions.

---

### Pitfall 1: ClinGen Bypass Creates Dual Maintenance Burden

**What goes wrong:** The current `SchemaDrivenCurationForm.vue` (lines 199-201) detects ClinGen schemas by name and bypasses the dynamic form entirely, routing to `ClinGenCurationForm.vue`. If you wire DynamicForm to views without removing this bypass, you maintain two parallel systems indefinitely.

**Why it happens:** Fear of breaking existing curations leads to "just add dynamic forms alongside" rather than replacing. The bypass was a temporary scaffolding that became permanent.

**Consequences:**
- Bug fixes must be applied twice (dynamic + hardcoded)
- New field types added to DynamicField never work for ClinGen users
- Schema changes in database don't affect ClinGen users
- Technical debt compounds with each feature

**Warning signs:**
- Code comments saying "TODO: remove bypass"
- Tests passing for GenCC but failing for ClinGen
- Schema admin changes not reflected in ClinGen forms
- Duplicate validation logic in both form types

**Prevention:**
1. Phase 1: Make DynamicForm feature-complete for ClinGen schema first
2. Phase 2: Remove bypass after validating DynamicForm renders ClinGen correctly
3. Use feature flag for gradual rollout: `VITE_USE_DYNAMIC_CLINGEN=true`
4. Write comparison tests: render both forms, assert identical structure

**Phase:** Foundation (Phase 1) - must be addressed before any other integration work

**Detection code pattern to find:**
```javascript
// This pattern must be removed
const isClinGenSchema = computed(() => {
  const schemaName = schema.value?.name?.toLowerCase() || ''
  return schemaName.includes('clingen') || schemaName.includes('sop')
})
```

---

### Pitfall 2: Evidence Data Shape Mismatch Corrupts Existing Curations

**What goes wrong:** DynamicForm expects flat key-value `evidence_data`, but ClinGenCurationForm uses deeply nested structure (e.g., `genetic_evidence.case_level.autosomal_dominant_or_x_linked.predicted_or_proven_null[]`). Loading existing curations into wrong form corrupts data.

**Why it happens:** Schema `field_definitions` in database may not match the actual nested structure that ClinGen scoring algorithms expect. The schema definition and form implementation diverge.

**Consequences:**
- Existing curations display empty fields (data exists but path mismatch)
- Saving overwrites nested data with flat structure
- Score calculation fails (expects specific paths)
- Data migration required after the fact

**Warning signs:**
- "Loading gene information..." completes but form fields are empty
- Scores show 0 despite having evidence items
- Backend validation passes but frontend displays incorrectly
- `evidence_data` in network response doesn't match form fields

**Prevention:**
1. Before integration, map existing `evidence_data` structures in production DB
2. Ensure `field_definitions` in schema exactly matches existing data paths
3. Create data shape tests: `loadCuration() -> form fields populated correctly`
4. Add migration script if schema and data shapes must diverge
5. Use TypeScript interfaces to enforce data shapes

**Phase:** Foundation (Phase 1) - must validate data shapes before wiring forms

**Example of shape mismatch:**
```javascript
// Schema field_definitions might define:
{ field_name: "genetic_evidence", type: "object" }

// But existing evidence_data has:
{
  genetic_evidence: {
    case_level: {
      autosomal_dominant_or_x_linked: {
        predicted_or_proven_null: [...]  // 4 levels deep!
      }
    }
  }
}
```

---

### Pitfall 3: Reactivity Lost on Deep Nested Object Mutations

**What goes wrong:** Vue 3's reactivity tracks deep mutations by default, but when DynamicField creates new nested objects or arrays, the new items may not be reactive, causing form updates to not reflect in parent state.

**Why it happens:** `addArrayItem()` in DynamicField.vue (line 354-373) creates new objects with `const newItem = {}` and pushes to array. If parent doesn't use `reactive()` properly or replaces entire object instead of mutating, reactivity breaks.

**Consequences:**
- User adds evidence item, clicks save, item not in payload
- Score calculation doesn't update after adding items
- "Unsaved changes" warning doesn't trigger
- Data loss on form submission

**Warning signs:**
- Adding items works visually but save payload is empty
- Vue DevTools shows stale state
- Score doesn't recalculate after field changes
- `watch(..., { deep: true })` callbacks not firing

**Prevention:**
1. Use `reactive()` for root evidence_data, not `ref({})`
2. Mutate in place, never replace: `evidenceData.value.field = x` not `evidenceData.value = {...}`
3. In DynamicField, emit new array reference: `emit('update:model-value', [...arrayValue.value])`
4. Add watchers with explicit `{ deep: true }` when needed
5. Test: add item, check Vue DevTools, verify state propagates

**Phase:** Integration (Phase 2) - critical during form wiring

**Current code that may cause issues:**
```javascript
// DynamicField.vue line 372-373
arrayValue.value.push(newItem)
emit('update:model-value', arrayValue.value)  // Same reference!

// Should be:
emit('update:model-value', [...arrayValue.value])  // New reference
```

---

## Form Conversion Pitfalls

Mistakes when converting hardcoded forms to dynamic forms.

---

### Pitfall 4: Hardcoded Labels and Hints Lost in Translation

**What goes wrong:** PrecurationFormView.vue has carefully crafted UX: specific hints ("Use dyadic naming: Gene-associated phenotype"), validation messages, placeholder text. Dynamic rendering from schema loses this domain-specific guidance.

**Why it happens:** Schema `field_definitions` typically only store: name, type, required. Rich UX metadata (hints, placeholders, validation messages, icons) not captured in schema.

**Consequences:**
- Forms become generic "Enter disease_name" instead of helpful
- Curators lose domain-specific guidance (ClinGen terminology)
- Validation errors become cryptic ("Field required" vs "Disease name is required for ClinGen classification")
- User training materials become outdated

**Warning signs:**
- Curator complaints about "confusing new form"
- Support tickets asking "what goes in this field?"
- Forms look "technical" instead of domain-appropriate
- Missing prepend icons (`mdi-medical-bag`, `mdi-dna`)

**Prevention:**
1. Extend `field_definitions` schema to include:
   - `hint`: String for persistent help text
   - `placeholder`: String for input placeholder
   - `prepend_icon`: String for Vuetify icon
   - `validation_message_template`: String with `{field}` interpolation
2. Map existing hardcoded UX to schema before removing hardcoding
3. Create UX inventory spreadsheet: field -> label -> hint -> icon
4. Validate with curators before switching

**Phase:** Foundation (Phase 1) - audit existing UX before replacement

**Example of what to preserve:**
```vue
<!-- Current PrecurationFormView.vue -->
<v-text-field
  v-model="form.disease_name"
  label="Disease Name *"
  prepend-inner-icon="mdi-medical-bag"
  hint="Use dyadic naming: Gene-associated phenotype (e.g., SCN1A-related seizure disorder)"
  persistent-hint
/>

<!-- Schema should capture ALL of this, not just: -->
{ "field_name": "disease_name", "type": "string", "required": true }
```

---

### Pitfall 5: Tab/Section Structure Not Driven by Schema

**What goes wrong:** ClinGenCurationForm.vue has 5 hardcoded tabs (Summary, Genetic Evidence, Experimental Evidence, Contradictory, Lumping & Splitting). DynamicForm renders flat list of fields. Tabs disappear.

**Why it happens:** Schema's `ui_configuration.tabs` array exists but DynamicForm doesn't read it. Forms render all fields in single column without grouping.

**Consequences:**
- 50+ field form becomes unusable wall of inputs
- Can't navigate to specific sections
- Visual hierarchy lost
- ClinGen workflow (fill genetic -> experimental -> review) broken

**Warning signs:**
- Form height explodes (scrolling forever)
- No tab navigation visible
- Fields that belong together are scattered
- Score sidebar has nothing to summarize per-section

**Prevention:**
1. Schema `ui_configuration` must define tabs:
   ```json
   {
     "tabs": [
       { "id": "summary", "label": "Summary", "icon": "mdi-file-document-outline", "fields": ["evidence_summary"] },
       { "id": "genetic", "label": "Genetic Evidence", "icon": "mdi-dna", "fields": ["genetic_evidence"] }
     ]
   }
   ```
2. DynamicForm must read and render `<v-tabs>` from schema
3. Current hardcoded tabs are template for schema migration
4. Test: form with 50 fields should have same tab count as hardcoded

**Phase:** Integration (Phase 2) - FORM-07 in PROJECT.md

---

### Pitfall 6: Specialized Components Lost to Generic Rendering

**What goes wrong:** PrecurationFormView uses specialized components: `MONDOAutocomplete`, `OMIMAutocomplete`, `HPOInheritanceSelect`, `PMIDInput`. These have API integrations, validation, auto-population. DynamicField renders them as generic `<v-text-field>`.

**Why it happens:** DynamicField.vue only knows 8 generic types (string, number, boolean, date, array, object, select, enum). No registry for domain-specific components.

**Consequences:**
- PMID validation lost (was checking PubMed API)
- MONDO autocomplete lost (was searching MONDO API)
- HPO inheritance patterns lost (was fetching HPO ontology)
- Auto-population flows broken (MONDO selection -> disease_name)

**Warning signs:**
- No autocomplete suggestions in disease/OMIM fields
- PMIDs not validated against PubMed
- Inheritance dropdown is empty or generic text input
- Cross-field auto-population stops working

**Prevention:**
1. Extend `field_definitions` with `component` field:
   ```json
   { "field_name": "mondo_id", "type": "string", "component": "MONDOAutocomplete" }
   ```
2. Create component registry in DynamicField:
   ```javascript
   const componentRegistry = {
     MONDOAutocomplete: () => import('@/components/evidence/MONDOAutocomplete.vue'),
     PMIDInput: () => import('@/components/evidence/PMIDInput.vue'),
     // ...
   }
   ```
3. Document all specialized components before conversion
4. Test: each specialized field type has working integration

**Phase:** Integration (Phase 2) - core to dynamic form functionality

---

## Validation Pitfalls

Form validation gotchas in dynamic contexts.

---

### Pitfall 7: Vuetify Form Validation Timing Issues

**What goes wrong:** DynamicForm.vue validates on every change with 500ms debounce (line 182-185). For complex schemas, validation API calls pile up, race conditions occur, stale validation results display.

**Why it happens:** `validateForm()` calls backend API (`validationStore.validateEvidence`). With deep watchers on `formData`, every keystroke triggers validation after debounce. Network latency causes out-of-order responses.

**Consequences:**
- Form shows "valid" then flips to "invalid" after delay
- Submit button enables/disables erratically
- Slow typing experience (waiting for validation)
- Incorrect validation state on submit

**Warning signs:**
- Network tab shows many `/api/v1/validation` calls
- Validation errors appear/disappear randomly
- Form feels "laggy" during typing
- Submitting form with stale validation state

**Prevention:**
1. Increase debounce for full form validation: 1000-2000ms
2. Validate individual fields locally (Vuetify rules), full form on blur/submit
3. Add request cancellation (AbortController) for pending validations
4. Use optimistic UI: assume valid until proven otherwise
5. Add loading indicator during validation

**Phase:** Validation (Phase 3) - FORM-06 in PROJECT.md

**Current problematic pattern:**
```javascript
// DynamicForm.vue - triggers too often
watch(
  formData,
  () => {
    if (Object.keys(formData.value).length > 0) {
      validateForm()  // API call on every change!
    }
  },
  { deep: true }
)
```

---

### Pitfall 8: Validation Rules Not Matching Schema Constraints

**What goes wrong:** DynamicField.vue generates validation rules from schema (line 287-336), but rules don't cover all constraint types: patterns, conditional requirements, cross-field validation.

**Why it happens:** `getValidationRules()` only handles: required, minLength, maxLength, minimum, maximum. Schema may have regex patterns, enum values that should validate, custom business rules.

**Consequences:**
- Invalid data passes frontend validation
- Backend rejects what frontend allowed
- User submits, sees unexpected errors
- Different validation UX between field types

**Warning signs:**
- Backend returns 422 after form shows "valid"
- Pattern-constrained fields accept invalid input
- Enum fields allow values not in list
- Cross-field rules (if X then Y required) not enforced

**Prevention:**
1. Extend `getValidationRules()` to handle:
   - `pattern`: Regex validation
   - `enum`: Value must be in list
   - `format`: email, uri, date-time
2. Add cross-field validation support via schema `validation_rules`
3. Mirror backend validation in frontend (generate from same schema)
4. Test: submit with each invalid pattern, verify frontend catches it

**Phase:** Validation (Phase 3)

**Example of missing validation:**
```javascript
// Schema defines:
{ "field_name": "pmid", "type": "string", "pattern": "^\\d{7,8}$" }

// But DynamicField.vue doesn't generate pattern rule - accepts "invalid"
```

---

### Pitfall 9: Form Reset Clears Data Instead of Resetting Validation

**What goes wrong:** Using Vuetify's `formRef.value.reset()` clears all field values, not just validation state. After reset, user loses all entered data.

**Why it happens:** [Known Vuetify issue](https://github.com/vuetifyjs/vuetify/issues/3316): `form.reset()` doesn't only reset validation, it also clears the inputs. Developers expect it to just clear error messages.

**Consequences:**
- User clicks "Clear Errors", loses all work
- Navigation away and back clears form
- Form recovery features fight with reset behavior
- Undo/redo state desyncs from form state

**Warning signs:**
- "Reset" button empties form fields
- Dismissing validation errors clears data
- Form recovery dialog offers to restore "lost" data that was just reset

**Prevention:**
1. Use `formRef.value.resetValidation()` not `formRef.value.reset()`
2. Store form data copy before any reset operation
3. Implement explicit "Clear Form" vs "Clear Errors" actions
4. Test: trigger validation error, reset validation, verify data intact

**Phase:** Validation (Phase 3)

---

## Performance Pitfalls

Complex form performance issues.

---

### Pitfall 10: Deep Watcher on Large Evidence Data Causes Lag

**What goes wrong:** ClinGen curations can have 50+ evidence items across categories. Deep watcher on entire `evidenceData` object triggers on every nested change, causing expensive re-renders.

**Why it happens:** Vue 3 deep watch traverses ALL nested properties. Each evidence item add/edit/delete triggers full tree walk. Combined with validation debounce, creates cascade of expensive operations.

**Consequences:**
- Typing in any field causes 100-500ms delay
- Adding evidence items freezes UI briefly
- Score calculation lags behind actual state
- Users report "slow form"

**Warning signs:**
- Vue DevTools shows excessive component updates
- Performance profiler shows watcher callbacks taking >50ms
- Users complain about typing lag
- Mobile/low-power devices especially affected

**Prevention:**
1. Use `shallowRef` for top-level evidence data
2. Implement per-section state management (each tab manages own state)
3. Use `watchEffect` for specific dependencies instead of deep watch
4. Consider Formily pattern: fields managed independently
5. Benchmark: 50+ field form should type smoothly

**Phase:** Performance (Phase 4)

**Pattern to avoid:**
```javascript
// Expensive - walks entire tree on any change
watch(evidenceData, () => { ... }, { deep: true })

// Better - only watch specific changes
watchEffect(() => {
  // Only triggers when accessed properties change
  const score = calculateScore(evidenceData.value.genetic_evidence)
})
```

---

### Pitfall 11: Recursive DynamicField Rendering Stack Overflow

**What goes wrong:** DynamicField.vue is recursive (renders itself for nested objects/arrays). Deeply nested schema (4+ levels like ClinGen genetic_evidence) can cause render stack issues, especially with circular references.

**Why it happens:** Each nested level creates new DynamicField components. Vue's render cycle processes synchronously. With 4 levels of nesting and arrays at each level, component count explodes exponentially.

**Consequences:**
- Browser tab crashes on complex forms
- "Maximum call stack size exceeded" errors
- Slow initial render (5+ seconds)
- Memory usage spikes

**Warning signs:**
- Form renders partially then errors
- Browser DevTools show 1000+ component instances
- Schema with type=object inside type=array causes issues
- Render time increases non-linearly with nesting depth

**Prevention:**
1. Limit nesting depth in DynamicField (max 3-4 levels)
2. For deeper nesting, use specialized components (EvidenceItemCard)
3. Implement lazy rendering for collapsed sections
4. Add schema validation: reject circular references
5. Test with production ClinGen schema (deepest nesting case)

**Phase:** Integration (Phase 2) and Performance (Phase 4)

---

### Pitfall 12: JSON Schema Generation on Every Schema Load

**What goes wrong:** `validationStore.generateJsonSchema(schemaId)` is called in multiple places (DynamicForm mount, SchemaDrivenCurationForm load, CurationFormView load). Generates same JSON schema repeatedly.

**Why it happens:** No caching awareness in components - each assumes it needs to fetch/generate. Backend may regenerate on each call, or frontend may store but not check.

**Consequences:**
- 3-4 API calls for same schema on form load
- Backend JSON schema generation is expensive (processes field_definitions)
- Increased form load time
- Unnecessary server load

**Warning signs:**
- Network tab shows duplicate `/api/v1/schemas/{id}/json-schema` calls
- Form load time increases with schema complexity
- Backend logs show repeated schema generation
- Cache headers not set on response

**Prevention:**
1. Check cache before generating: `if (validationStore.getJsonSchema(schemaId)) return`
2. Add cache TTL to jsonSchemas store (5 min)
3. Generate JSON schema once at app startup for known schemas
4. Add ETag/If-None-Match headers for schema endpoints
5. Test: load form twice, verify single schema fetch

**Phase:** Performance (Phase 4)

**Pattern to implement:**
```javascript
// In validationStore.generateJsonSchema
async generateJsonSchema(schemaId) {
  // Check cache first
  if (this.jsonSchemas[schemaId]) {
    return this.jsonSchemas[schemaId]
  }
  // ... fetch and cache
}
```

---

## Backward Compatibility Pitfalls

Breaking existing functionality during migration.

---

### Pitfall 13: Existing Curations Fail to Load in New Form

**What goes wrong:** Curations created with hardcoded ClinGenCurationForm have specific `evidence_data` structure. DynamicForm expects structure matching `field_definitions`. Mismatch causes load failure or empty form.

**Why it happens:** Schema evolution: `field_definitions` updated for DynamicForm but existing curations have old structure. No migration, no backward compatibility layer.

**Consequences:**
- Curator opens existing curation, sees empty form
- Edit existing -> save -> data corrupted/lost
- Can't complete review on curations started before migration
- Production data integrity compromised

**Warning signs:**
- "This curation has no evidence data" on curations that definitely have data
- Editing curation changes its structure (visible in DB)
- Review workflow broken for in-progress curations
- Curator reports "my work disappeared"

**Prevention:**
1. **Data compatibility layer:** Transform old structure to new on load, new to old on save (if needed)
2. **Schema versioning:** `evidence_data` includes `_schema_version`
3. **Read-only mode for old curations:** Prevent editing, only viewing
4. **Migration script:** One-time update of all existing evidence_data
5. **Parallel testing:** Load every production curation in test environment

**Phase:** Foundation (Phase 1) - CRITICAL before any rollout

**Migration approach:**
```javascript
function normalizeEvidenceData(data, schemaVersion) {
  if (schemaVersion === 1 || !data._schema_version) {
    // Transform v1 (hardcoded) structure to v2 (dynamic) structure
    return migrateV1ToV2(data)
  }
  return data
}
```

---

### Pitfall 14: Score Calculation Breaks for Non-ClinGen Schemas

**What goes wrong:** Score calculation is hardcoded for ClinGen SOP v11 point values. GenCC uses different classification system. Dynamic schema with different scoring engine fails.

**Why it happens:** `ClinGenCurationForm.vue` has `calculateGeneticScore()` and `calculateExperimentalScore()` with hardcoded max values (12, 6), point categories, and classification thresholds (12=Definitive, 7=Strong).

**Consequences:**
- GenCC curations show ClinGen scores (wrong)
- Custom schemas can't calculate scores at all
- Classification labels don't match methodology
- Scoring sidebar shows incorrect information

**Warning signs:**
- Non-ClinGen curation shows "Definitive" when it shouldn't
- Score breakdown categories don't match schema type
- Backend score differs from frontend score
- ScoreSummary component crashes for non-ClinGen

**Prevention:**
1. Move scoring to backend: `/api/v1/scoring/calculate`
2. Schema `scoring_engine` field determines algorithm
3. Frontend calls scoring API, displays result agnostically
4. ScoreDisplay.vue renders whatever backend returns
5. Test: create curation with each schema type, verify appropriate scoring

**Phase:** Scoring (Phase 4) - FORM-05 in PROJECT.md

**Current hardcoding to remove:**
```javascript
// ClinGenCurationForm.vue - hardcoded for ClinGen only
const currentClassification = computed(() => {
  const score = scores.value.total
  if (score >= 12) return 'Definitive'  // ClinGen-specific!
  if (score >= 7) return 'Strong'
  // ...
})
```

---

### Pitfall 15: Form Recovery Data Incompatible Across Schema Changes

**What goes wrong:** `useFormRecovery` composable stores form data in localStorage keyed by curation ID. If schema changes, recovered data structure doesn't match new form, causing errors or data loss.

**Why it happens:** Recovery key is `curation-${id}-schema-${schemaId}` but if schema's `field_definitions` change, recovered data has old field names/structure.

**Consequences:**
- User resumes work, form shows partial/corrupted data
- Recovery dialog offers to restore incompatible data
- Accepting recovery causes validation errors
- Silent data loss when fields removed from schema

**Warning signs:**
- Recovery dialog shows fields that no longer exist
- Restoring causes "undefined" values in form
- Validation errors immediately after recovery
- Schema admin changes break user's draft recovery

**Prevention:**
1. Include schema version/hash in recovery key
2. Validate recovered data against current schema before offering restore
3. Clear recovery data when schema changes
4. Show warning if schema changed since last save
5. Implement recovery data migration for schema updates

**Phase:** Integration (Phase 2) - affects draft workflow

**Key pattern from SchemaDrivenCurationForm.vue:**
```javascript
// Already has schema-aware key - good!
const recoveryKey = computed(
  () => `curation-${props.curationId || 'new'}-schema-${props.schemaId}`
)

// But needs: schema version check on recovery
watch(() => props.schemaId, (newId, oldId) => {
  if (oldId && newId !== oldId) {
    clearRecovery()  // Good - clears on schema change
  }
})
```

---

## Integration Pitfalls

Mistakes when wiring dynamic forms to existing views.

---

### Pitfall 16: Route Parameters Not Passed to DynamicForm

**What goes wrong:** `PrecurationFormView.vue` extracts `scopeId`, `geneId` from route and uses them for API calls. When switching to DynamicForm, these parameters must be threaded through but may be lost.

**Why it happens:** DynamicForm designed as generic component, doesn't know about scope/gene context. Parent view must pass context, but prop drilling gets complex.

**Consequences:**
- Form saves without scope_id -> 400 error
- Gene context lost -> form header shows "Unknown Gene"
- Workflow pair resolution fails -> wrong schema loaded
- Precuration link broken -> curation can't access precuration data

**Warning signs:**
- Save returns "scope_id is required"
- Form loads but gene name/symbol missing
- Schema selection shows wrong options for scope
- API calls missing required parameters

**Prevention:**
1. Create wrapper composable: `useCurationContext()` that extracts all route params
2. DynamicForm receives `context` prop with all needed IDs
3. Test each form route: verify all context params available
4. Add defensive checks: show error if context missing

**Phase:** Integration (Phase 2)

**Props that must be threaded:**
```javascript
// These are currently extracted in views, must reach DynamicForm
const scopeId = computed(() => route.params.scopeId)
const geneId = computed(() => route.params.geneId)
const curationId = computed(() => route.params.curationId)
const precurationSchemaId = ref(null)  // From workflow pair
```

---

### Pitfall 17: Event Handlers Disconnect During Refactor

**What goes wrong:** Hardcoded forms emit specific events (`@submit`, `@save-draft`, `@cancel`). DynamicForm may emit differently or not at all. Parent views break silently.

**Why it happens:** DynamicForm.vue emits events, but:
- Emit names may differ (`submit` vs `form-submit`)
- Payload structure may differ
- Some events may be missing
- Parent handlers assume specific payload shape

**Consequences:**
- Submit button does nothing (handler not connected)
- Save draft silently fails (event name mismatch)
- Cancel leaves user stuck (no navigation)
- Success notifications don't show

**Warning signs:**
- Clicking buttons has no visible effect
- No network requests on submit
- Console shows "event handler is not a function"
- Navigation doesn't happen after submit

**Prevention:**
1. Document all events each form component emits
2. Create event interface: `CurationFormEvents { submit(data), saveDraft(data), cancel() }`
3. Verify event connection in tests: trigger event, assert handler called
4. Add console.warn in dev mode when events fire with no handler

**Phase:** Integration (Phase 2)

**Events to verify:**
```javascript
// DynamicForm.vue
const emit = defineEmits(['submit', 'save-draft', 'update:modelValue', 'validation-change'])

// SchemaDrivenCurationForm.vue
const emit = defineEmits(['submit', 'cancel', 'saved'])

// Parent view handlers must match
<DynamicForm @submit="handleSubmit" @save-draft="handleSaveDraft" ... />
```

---

### Pitfall 18: Store State Conflicts Between Form Types

**What goes wrong:** `SchemaDrivenCurationForm` uses multiple stores (schemas, curations, precurations, validation). If form switches between ClinGen bypass and dynamic mode, store state from one mode pollutes the other.

**Why it happens:** Stores are global singletons. `currentSchema` set by ClinGen form may not be cleared when switching to dynamic form, causing stale data.

**Consequences:**
- Wrong schema displayed in header
- Validation runs against wrong schema
- Score calculation uses wrong schema's rules
- Form recovery restores wrong data type

**Warning signs:**
- Schema name in UI doesn't match actual form
- Validation errors reference fields not in form
- DevTools shows schema store has stale `currentSchema`
- Race condition between schema loads

**Prevention:**
1. Clear relevant store state on component mount/unmount
2. Use scoped state (composition API refs) instead of global store where possible
3. Schema store's `currentSchema` should only be set explicitly, not assumed
4. Add store state reset in `onBeforeUnmount`

**Phase:** Integration (Phase 2)

**Cleanup pattern:**
```javascript
onBeforeUnmount(() => {
  validationStore.clearValidationResult('form')
  schemasStore.clearCurrentSchema()
  // Don't clear schemas list - that's cached intentionally
})
```

---

## Phase Assignment Summary

| Pitfall | Phase | Priority |
|---------|-------|----------|
| 1. ClinGen Bypass | Foundation (Phase 1) | CRITICAL |
| 2. Evidence Data Shape | Foundation (Phase 1) | CRITICAL |
| 13. Existing Curations Load | Foundation (Phase 1) | CRITICAL |
| 4. Hardcoded Labels Lost | Foundation (Phase 1) | HIGH |
| 3. Reactivity Lost | Integration (Phase 2) | CRITICAL |
| 5. Tab Structure | Integration (Phase 2) | HIGH |
| 6. Specialized Components | Integration (Phase 2) | HIGH |
| 11. Recursive Rendering | Integration (Phase 2) | MEDIUM |
| 15. Form Recovery Compat | Integration (Phase 2) | MEDIUM |
| 16. Route Parameters | Integration (Phase 2) | HIGH |
| 17. Event Handlers | Integration (Phase 2) | HIGH |
| 18. Store State Conflicts | Integration (Phase 2) | MEDIUM |
| 7. Validation Timing | Validation (Phase 3) | HIGH |
| 8. Validation Rules | Validation (Phase 3) | HIGH |
| 9. Form Reset Behavior | Validation (Phase 3) | MEDIUM |
| 10. Deep Watcher Lag | Performance (Phase 4) | MEDIUM |
| 12. JSON Schema Caching | Performance (Phase 4) | LOW |
| 14. Score Calculation | Scoring (Phase 4) | HIGH |

---

## Sources

### Official Documentation (HIGH confidence)
- [Vue 3 Reactivity Fundamentals](https://vuejs.org/guide/essentials/reactivity-fundamentals)
- [Vue 3 Watchers](https://vuejs.org/guide/essentials/watchers.html)
- [Vuetify 3 Form Component](https://vuetifyjs.com/en/components/forms/)
- [Vue 3 Breaking Changes Migration Guide](https://v3-migration.vuejs.org/breaking-changes/)

### Community Best Practices (MEDIUM confidence)
- [Vue.js Dynamic Forms Best Practices](https://medium.com/@emperorbrains/vue-js-dynamic-forms-best-practices-and-techniques-a633a696283b)
- [Building Dynamic Forms in Vue 3](https://medium.com/@natalia.afanaseva/building-a-dynamic-form-in-vue-3-with-nested-fields-conditions-and-validation-a096bb69219f)
- [Common Mistakes in Vue 3 Reactivity](https://infinitejs.com/posts/common-mistakes-vue-3-reactivity/)
- [Deep Dive into Vue 3 Reactivity and Nested Objects](https://medium.com/@hichemdahi57/deep-dive-into-vue-3s-reactivity-and-nested-objects-5d4cedc85b64)

### Known Issues (MEDIUM confidence)
- [Vuetify form.reset() Issue #3316](https://github.com/vuetifyjs/vuetify/issues/3316)
- [Vuetify VForm validation model-value Issue #15568](https://github.com/vuetifyjs/vuetify/issues/15568)
- [Vue 3 Updates to deep/nested reactive props Issue #1387](https://github.com/vuejs/core/issues/1387)

### Libraries Referenced
- [FormVueLate - Schema-driven forms](https://github.com/formvuelate/formvuelate)
- [Vue3 Schema Forms (Vuetify)](https://github.com/MaciejDybowski/vue3-schema-forms)
- [Formily - High performance forms](https://github.com/alibaba/formily)
