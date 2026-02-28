# Domain Pitfalls: Form Intelligence (Conditional Visibility, Cross-Field Validation, Field Dependencies)

**Domain:** Adding reactive field interactions to an existing schema-driven dynamic form system
**Project:** Gene Curator — Vue 3 + Vuetify 3 + Pinia
**Researched:** 2026-02-28
**Confidence:** HIGH for Vue 3 reactivity pitfalls (official docs + codebase inspection); MEDIUM for UX patterns (community + form builder practice)

---

## Context: What Already Exists

Before reading any pitfall, understand the existing system to avoid solving problems that are already solved:

- `DynamicForm.vue` renders from schema with `formData` as a flat `ref({...initialData})`
- `DynamicField.vue` receives individual field values via `modelValue` prop; emits changes up
- `TabContent.vue` bridges tab structure to `DynamicField`; all field paths use dot notation
- `useValidationRules.js` generates Vuetify rules from schema constraints (per-field, not cross-field)
- Backend validation runs every 500ms via debounced `validateForm()` call in `DynamicForm.vue`
- `KeepAlive` wraps each `TabContent` so inactive tab state is preserved

Conditional visibility does NOT yet exist. Cross-field validation does NOT yet exist. Field dependencies (cascading options, auto-population) do NOT yet exist. The pitfalls below are for adding those capabilities.

---

## Critical Pitfalls

Mistakes that cause rewrites or correctness failures.

### Pitfall 1: Circular Dependency Between Fields

**What goes wrong:**
Field A shows/hides based on Field B's value. Field B's options or required status depends on Field A's value. A watcher on A triggers changes to B, which triggers the A watcher again. In Vue 3, `watch` with `{ deep: true }` does not protect against self-triggering loops the way `watchEffect` does — the loop runs until the browser stack overflows or the browser tab freezes.

**Concrete example in Gene Curator context:**
Imagine `evidence_category` (select) controls visibility of `variant_type`. If `variant_type` has a watcher that updates `evidence_category` options based on its own value, and the visibility logic for `variant_type` watches `evidence_category`, you have a cycle. The existing ClinGen schema already has `condition: "evidence_category == 'case_level'"` on multiple fields — adding cascading behavior here without cycle detection will create this bug.

**Warning signs:**
- Browser tab becomes unresponsive when a specific select field is changed
- Vue DevTools shows rapidly incrementing watcher trigger counts
- The bug reproduces only when two specific fields are changed in sequence, not in isolation
- Works fine in testing with a single field changed, breaks with real form interaction
- In production builds Vue may optimize differently — loops that survive dev mode may crash in prod (Vue production vs dev reactivity handling differs)

**Prevention:**
1. Before implementing any field dependency, build a directed acyclic graph (DAG) of all dependency declarations. Run cycle detection (DFS or Kahn's algorithm) at schema load time.
2. Use a `useFieldDependencies` composable that validates the dependency graph on initialization and throws a descriptive error (not a silent failure) when a cycle is detected.
3. Log a warning if the schema defines `field_A.visibility` depends on `field_B` AND `field_B.visibility` depends on `field_A`.
4. Prefer `computed` over `watch` for visibility: `computed(() => evaluateVisibility(schema, formData.value))` cannot cause a reactive loop because computed properties are pull-based, not push-based.

**Which phase addresses it:** The visibility engine design phase must include cycle detection before any schema with conditional fields is activated.

---

### Pitfall 2: Hidden Field Values Submitted to Backend and Causing Validation Failures

**What goes wrong:**
When a field is hidden because its visibility condition is false, its value may still exist in `formData`. The backend validation engine (`SchemaValidator.validate_evidence_data`) receives all data in `evidence_data`. If a hidden field's value fails validation (wrong type, out of range, required-but-empty), the backend returns an error for a field the user cannot see. The form appears stuck: there is an error but no visible field to fix.

**Concrete example:**
`variant_type` is required when `evidence_category == 'case_level'`. User selects `case_level`, fills `variant_type`, then changes `evidence_category` to `segregation`. `variant_type` is now hidden. Its value is still `'missense'` in `formData`. Backend validation runs. The backend `SchemaValidator` checks required fields without knowing about frontend visibility — it may flag `variant_type` as invalid because its value is irrelevant in the `segregation` context, or it may not. Either way, there is ambiguity.

**The actual failure mode is the reverse too:** Hidden field retains stale required value that passes validation but corrupts the saved curation record with data that has no business meaning in the current context.

**Warning signs:**
- Backend returns validation errors for fields that are not visible on the form
- Saved curations contain values for fields that should be contextually irrelevant
- The `nonFieldErrors` array in `DynamicForm.vue` shows generic errors with no visible field to fix
- Tab error badges show a tab has errors but no visible field within the tab has a red state

**Prevention — Clear vs Retain decision:**
The correct answer for Gene Curator is **clear on hide** for most fields, with **retain on re-show** for optional user convenience fields. The rule:
- **Always clear:** Fields whose value is semantically invalid when hidden (e.g., `variant_type` values only make sense in case-level evidence context)
- **Optionally retain:** Fields that could be valid in multiple contexts (e.g., a notes field that applies broadly)
- **Implementation:** The visibility transition from visible→hidden should call a `clearHiddenFieldValue(fieldPath)` function. This function sets the field value to `null` or `undefined` in `formData`, not to an empty string (which can itself fail required validation).

**Backend alignment:** The backend validator must also implement the same conditional-required logic. The `conditional_required` pattern already exists in `016_seed_precuration_schema.sql` (`lumping_splitting_decision` required when `lumping_splitting_applicable === true`). Extend the backend `SchemaValidator._validate_fields` method to skip validation of fields whose visibility condition is false. Front-end and backend visibility conditions must use the same expression syntax or you will have frontend/backend disagreement about which fields are required.

---

### Pitfall 3: Async Auto-Population Race Condition (MONDO API)

**What goes wrong:**
When a user selects a MONDO ID, the form should auto-populate `disease_name`. The auto-population involves an async API call (`ontologyAPI.searchMONDO`). If the user selects MONDO ID "A", triggering a search, then quickly changes to MONDO ID "B" before the first search completes, the first search may complete after the second and overwrite `disease_name` with the stale value for "A".

**Concrete example:**
`MONDOAutocomplete.vue` already does `handleSelect(item)` which emits `update:diseaseName`. When this is wired to auto-populate a sibling field, the watcher pattern `watch(() => props.modelValue, async (newValue) => { ... })` already exists in `MONDOAutocomplete.vue` at line 259 and makes an API call. This exact watcher has no cancellation of previous requests. If users type quickly in the MONDO search box and selections change rapidly, stale responses win.

**Warning signs:**
- `disease_name` field shows a disease that doesn't match the displayed MONDO ID
- Happens only with fast user interaction or slow network
- Difficult to reproduce in unit tests (requires timing control)
- The existing `MONDOAutocomplete.vue` `watch` at line 259 already exhibits this pattern for restoring initial values from `props.modelValue`

**Prevention:**
Use Vue 3.5+ `onWatcherCleanup` to abort stale requests. The pattern:
```javascript
watch(() => mondoId.value, async (newId, _oldId, onCleanup) => {
  const controller = new AbortController()
  onCleanup(() => controller.abort())
  const result = await ontologyAPI.searchMONDO(newId, { signal: controller.signal })
  // only reaches here if this is still the latest request
  formData.value['disease_name'] = result.label
})
```
**Critical limitation:** `onWatcherCleanup` must be called before the first `await`. The third `onCleanup` argument to the watch callback is the safe alternative that works after awaits. Use the callback parameter form, not the standalone function.

For the MONDO auto-population specifically: the `MONDOAutocomplete.vue` component already manages its own internal state. The integration pitfall is deciding whether auto-population is the component's responsibility or the form's responsibility. Mixing both creates double-update loops.

---

### Pitfall 4: The "Required but Hidden" Validation Paradox Breaking Form Submission

**What goes wrong:**
Vuetify's `v-form` `validate()` method runs rules on all registered input components, including hidden ones when `v-show` is used (hidden with CSS, still in DOM). If a field has `required: true` in its schema, `useValidationRules.js` adds the required rule. If the field is hidden with `v-show`, Vuetify still validates it. The form cannot be submitted even though the user correctly has not filled a contextually invisible required field.

**If `v-if` is used instead:** The component is unmounted, Vuetify does not validate it, but the value in `formData` is retained (the component is gone, the data is not). This is the lesser evil but still means stale hidden values persist in form state.

**Warning signs:**
- Form submit button is always disabled even when all visible fields are filled
- `formRef.value.validate()` returns `{ valid: false }` but no visible red fields
- The issue appears only after a conditional field becomes hidden

**Prevention:**
- Use `v-if` (not `v-show`) for conditional field rendering to unmount hidden field components from Vuetify's validation tree
- Pair `v-if` with explicit `clearHiddenFieldValue()` calls in the visibility transition logic
- Do NOT pass required validation rules to a field that is conditionally required but currently hidden. The `useValidationRules` composable must receive the current visibility state and return an empty rules array for hidden fields.
- Alternative: Wrap conditionally visible fields in a separate `<v-form>` scope so they don't affect the parent form's validity — but this conflicts with the existing single-form architecture in `DynamicForm.vue`.

---

## Moderate Pitfalls

Mistakes that cause delays or technical debt.

### Pitfall 5: Visibility Evaluation Expression Language Mismatch (Frontend vs Backend)

**What goes wrong:**
The existing ClinGen schema uses a string expression format: `"condition": "evidence_category == 'case_level'"`. The precuration schema uses an object format: `"when": {"lumping_splitting_applicable": true}`. These are two different syntaxes for the same concept and neither is implemented in the frontend yet.

If the frontend implements one syntax and the database schemas use the other, every schema will need migration. If both syntaxes are supported, the expression evaluator becomes complex with two parsing branches.

**Warning signs:**
- Frontend visibility engine works for precuration forms but not ClinGen forms (or vice versa)
- Different schema administrators use different syntax when creating new schemas
- Backend conditional_required logic and frontend visibility logic use different evaluators that give different answers for edge cases (null values, empty strings vs false, etc.)

**Prevention:**
Before implementation, audit all existing schemas to catalogue which syntax is in use. Choose one canonical format and write a migration SQL to normalize existing schemas. Implement one evaluator (not two). The object format `{"field": "evidence_category", "operator": "==", "value": "case_level"}` is more structured and easier to validate than free-form strings. The string format is more human-readable for schema authors.

Recommended: Adopt the object format for the schema definition, provide a DSL converter for schema authors who prefer string expressions, and apply a one-time migration to existing schemas.

---

### Pitfall 6: Tab Error Badge Not Reflecting Conditional Visibility Changes

**What goes wrong:**
`tabValidationErrors` in `DynamicForm.vue` (line 346) computes which tabs have errors by checking `backendErrors` for each field path in that tab. If a field is hidden (conditionally invisible), its backend error is cleared from `backendErrors` when the field is hidden — but only if the code does so. If the clearing logic is not tight, a tab shows an error badge for a hidden field error. The user navigates to the tab, sees no red field (it is hidden), and cannot understand why the badge is there.

**Warning signs:**
- Tab error badge persists after the triggering condition change makes the erroneous field invisible
- User reports "the form has an error but I can't find it"
- Tab badges only disappear after form re-submission

**Prevention:**
When a field becomes hidden (visibility condition changes from true to false), run three operations atomically:
1. Clear the field value in `formData`
2. Clear the field's entry in `backendErrors`
3. The tab badge will then recompute correctly via its existing `computed` dependency on `backendErrors`

Implement a `handleFieldHidden(fieldPath)` function that does all three.

---

### Pitfall 7: KeepAlive and Stale Computed State on Tab Reactivation

**What goes wrong:**
`DynamicForm.vue` wraps `TabContent` in `KeepAlive`. This means deactivated tab components are not unmounted — their computed properties are still reactive but may be stale if reactive dependencies were updated while the tab was inactive. When the user returns to the tab, the component `onActivated` lifecycle fires, but `v-if`-based conditional fields that were toggled while the tab was inactive may not have triggered their show/hide logic in the inactive component.

In practice: User is on Tab 2. On Tab 1 (inactive, KeepAlive), a field's visibility condition becomes true due to a formData change. The field should appear on Tab 1. User navigates to Tab 1. The field may or may not be visible depending on whether the reactive expression has been re-evaluated since the component was inactive.

**Warning signs:**
- Conditional fields appear/disappear with a one-tab-visit delay
- Works correctly if user visits the tab immediately after the triggering change; fails if they navigate elsewhere first
- Only reproducible with KeepAlive (not in tests that don't use tab switching)

**Prevention:**
Ensure visibility conditions are driven by `computed` properties (not watchers) that react to `formData` which is passed down as a prop from `DynamicForm.vue`. Since `formData` is the same reactive ref passed to all tabs, a computed visibility expression depending on `formData.value.someField` will re-evaluate correctly even for KeepAlive'd components because the reactive dependency tracking is still active.

Do not put visibility logic inside `onActivated` hooks — it creates a timing dependency on user navigation. Computed properties driven by shared reactive state are the correct solution.

---

### Pitfall 8: Cascading Select Option List Updates Losing User Selection

**What goes wrong:**
Field B's options depend on Field A's value. User selects option X in Field A, which populates Field B with 5 options. User selects option 3 in Field B. User then changes Field A to option Y. Field B's options update to 4 new options. Option 3 from the previous list no longer exists. The displayed selection in Field B may show a stale chip/text, or the value in `formData` is no longer in the valid options list, or the field appears blank while `formData` holds a stale value.

**Concrete example:**
`evidence_category` is Field A. `variant_type` is Field B with options dependent on the evidence category. Changing `evidence_category` from `case_level` to `experimental` should update `variant_type` options. The stale `variant_type` value `'missense'` may not be valid in the experimental context.

**Warning signs:**
- Select field shows a value but the dropdown options don't include that value
- Backend validation fails with "value not in allowed options" for a field the user believes they set correctly
- The chip in a multi-select shows values that are not in the current item list

**Prevention:**
When Field A changes and Field B's options are updated, check if Field B's current value is still in the new option list. If not, clear Field B's value. Implement this as:
```javascript
const updateCascadingField = (fieldPath, newOptions) => {
  const currentValue = getNestedValue(formData.value, fieldPath)
  const isStillValid = newOptions.some(opt => opt.value === currentValue)
  if (!isStillValid) {
    setNestedValue(formData.value, fieldPath, null)
  }
}
```
Run this check atomically with the options update, before the next render cycle.

---

### Pitfall 9: Performance — Watcher Proliferation with 50+ Fields

**What goes wrong:**
Implementing field dependencies with one `watch()` per field creates 50+ individual watchers. Each watcher tracks its own reactive dependencies. With `{ deep: true }` on `formData`, every form field change triggers all 50 watchers to re-run synchronously. With 20+ conditional visibility computations running on every keypress, plus debounced backend validation, form typing becomes laggy (>100ms latency per keypress).

**Warning signs:**
- Typing in a text field feels sluggish
- Vue DevTools performance profiler shows many watcher triggers per user interaction
- The issue worsens with schema complexity (more conditional fields = more watchers)
- Performance is acceptable for simple schemas (5 fields) but breaks for ClinGen schema (50+ fields)

**Prevention:**
1. **Use computed instead of watch for visibility:** A single `visibleFields` computed property that evaluates all visibility conditions at once is far more efficient than 50 individual watchers. Computed properties batch re-evaluation when reactive dependencies change.
2. **One dependency watcher, not one per field:** Instead of `watch(fieldA, updateFieldB)` and `watch(fieldB, updateFieldC)`, use a single `watchEffect` that rebuilds a dependency-resolved state object once.
3. **Separate the visibility computation from the value computation:** Visibility can be computed synchronously (fast). Value auto-population involves async API calls (slow). Keep them in separate execution paths.
4. **The existing 500ms debounce** on backend validation calls in `DynamicForm.vue` is correctly scoped — do not reduce it to compensate for async auto-population latency.

---

### Pitfall 10: Cross-Field Validation Error Attribution — Which Field Gets the Error?

**What goes wrong:**
A cross-field rule like "if `de_novo_status` is true then `variant_segregation_data` must be provided" involves two fields. Where does the error message appear? If the error is attributed to `de_novo_status` (the triggering field), the user may not understand why their correct selection is red. If attributed to `variant_segregation_data` (the field that needs filling), the error is more intuitive but the field may not be visible yet.

**Warning signs:**
- Cross-field error messages appear on the wrong field
- Error appears on a hidden field (invisible to user)
- Backend returns errors for a different field than the frontend shows
- Two error messages for what is logically one constraint

**Prevention:**
Establish a clear rule at design time: **cross-field validation errors are always attributed to the dependent field** (the one that must be filled or changed), not the trigger field. In the example, the error goes on `variant_segregation_data`.

The backend `SchemaValidator.add_error(field, message)` already attributes errors to a field. Ensure the backend expression and frontend UI attribution match. Document this convention in a code comment in `useValidationRules.js` so future developers don't reverse it.

---

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 11: Layout Shift When Fields Show/Hide in Tabs

**What goes wrong:**
When a conditional field appears or disappears, surrounding fields shift position. If the form has tight vertical layout, users lose their scroll position or a submit button they were about to click shifts up/down and they click the wrong element. This is especially disruptive in long forms with many conditionally visible groups.

**Prevention:**
- Use `v-if` (not `v-show`) for conditional rendering to avoid the invisible-but-space-consuming pattern
- Group conditionally visible fields in expansion panel sections (`v-expansion-panel`) which have smooth expand/collapse animations
- Avoid conditional fields at the top of sections — prefer putting conditional fields at the bottom of a section so the shift pushes content downward rather than shifting visible content up
- `TabContent.vue` already uses `v-expansion-panels` for sections — conditional fields within a section naturally shift only within that section boundary

---

### Pitfall 12: Form Recovery (localStorage) Persisting Hidden Field Values

**What goes wrong:**
`useFormRecovery.js` saves `formData` to localStorage every 5 seconds. If a user fills in conditionally visible fields, then the condition changes (hiding the fields), the clearHiddenFieldValue logic clears them from `formData`. But if the auto-save already captured the pre-clearing state, the recovery data has the stale values. When the form is recovered, the hidden field values are restored. Backend validation then runs against formData that includes values for fields that are currently invisible.

**Warning signs:**
- After browser crash recovery, the form shows errors for fields that were supposed to be cleared
- The recovered form data does not match what the user last explicitly saw

**Prevention:**
`clearHiddenFieldValue()` must write to `formData` synchronously, not in a nextTick or setTimeout. Since `useFormRecovery` saves `formData` by reference via deep watch, clearing hidden field values in `formData` will naturally be captured in the next auto-save. The risk is the 5-second save interval window. This is acceptable; document it.

The bigger risk: when restoring recovery data, re-evaluate all visibility conditions against the recovered `formData` values to determine which fields should be visible. Do not blindly restore all values including those whose conditions are false. The `restoreRecovery()` function in `useFormRecovery.js` does `Object.assign(formData.value, recoveryData.value)` — after this, run a `clearAllHiddenFields(formData, schema)` pass.

---

### Pitfall 13: The "Validation Before Schema Load" Flash

**What goes wrong:**
`DynamicForm.vue` watches `formData` with `{ deep: true }` and triggers `validateForm()` automatically when any value changes. If the `jsonSchema` has not yet loaded (it is fetched async in `onMounted`), and `initialData` is passed with pre-filled values, the watch fires `validateForm()` before the schema is available. The backend validation call happens with data but no schema context, or the validation runs without visibility condition knowledge and incorrectly marks hidden fields as required.

**Warning signs:**
- Validation errors flash briefly on form load then disappear
- Backend is called for validation immediately on mount before schema is ready
- Required field errors appear for fields that should be visible but schema hasn't been evaluated yet

**Prevention:**
The existing code at line 639 in `DynamicForm.vue` has `if (Object.keys(formData.value).length > 0) { validateForm() }` — this runs too eagerly. Add a guard: only run validation after the visibility engine has had one full evaluation pass. Use a `schemaReady` ref that is set to true after `generateJsonSchema()` completes, and gate the `formData` watcher on `schemaReady.value`.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Visibility engine design | Circular dependency (Pitfall 1) | Build DAG validator first; no visibility without cycle check |
| Visibility expression language | Syntax mismatch (Pitfall 5) | Audit all 4 existing schemas; pick one canonical format before coding |
| Hidden field value clearing | Backend errors on hidden fields (Pitfall 2) | Implement clear-on-hide atomically with visibility change |
| Vuetify validation integration | Required-but-hidden paradox (Pitfall 4) | Use `v-if` not `v-show`; gate required rules on visibility |
| Cascading selects | Stale value in Field B (Pitfall 8) | Check current value against new options; clear if invalid |
| Auto-population (MONDO API) | Race condition (Pitfall 3) | AbortController via onCleanup watcher parameter |
| Tab badge integration | Stale badge after field hidden (Pitfall 6) | Clear backendErrors atomically with field hiding |
| KeepAlive tab state | Stale visibility on tab reactivation (Pitfall 7) | Drive visibility via computed not watchers |
| Performance with 50+ fields | Watcher proliferation (Pitfall 9) | Single computed for all visibility; avoid per-field watchers |
| Cross-field error display | Wrong field attribution (Pitfall 10) | Convention: errors on dependent field; document in code |
| Form recovery integration | Stale hidden values restored (Pitfall 12) | Re-evaluate visibility after recovery restore |

---

## Integration Points Specific to Gene Curator

The following are Gene Curator-specific integration pitfalls that generic advice does not cover.

### Backend Validator Does Not Know About Frontend Visibility

The `SchemaValidator` in `backend/app/core/schema_validator.py` runs `_validate_fields()` against all fields in `field_definitions` without any visibility filtering. The frontend has no way to tell the backend "field X is currently hidden, don't validate it." Options:
1. Send `hidden_fields: ["variant_type", "lod_score"]` alongside `evidence_data` in the validation API call
2. The backend reads the same visibility condition expressions from the schema and evaluates them server-side before validation
3. Accept that hidden field values will be submitted and ensure clearing-on-hide makes them null so they pass the "not required, not provided" path in `_validate_fields()`

Option 3 is simplest and avoids a new API surface. The existing validator at line 233 already skips validation if `field_value is None`. Clear hidden field values to `None` (null in JSON), and the backend validator will skip them correctly.

### The Existing `condition` String in ClinGen Schema Is Not Yet Evaluated

The ClinGen schema in `014_seed_clingen_schema.sql` has `'condition', 'evidence_category == ''case_level'''` on several fields. This string is currently stored in the schema JSONB but nothing reads it — `DynamicField.vue` renders all fields unconditionally. When implementing the visibility engine, these conditions must be evaluated to show/hide fields. The expression evaluator must handle the existing string format OR a migration must rewrite them to the new format before the engine is activated.

Activating the visibility engine without migrating these schema expressions will immediately hide fields that should be visible (if the evaluator returns false for unparseable strings) or show all fields ignoring conditions (if the evaluator returns true as a fallback). Both are wrong. Test schema parsing before activating visibility on the ClinGen schema.

### `MONDOAutocomplete` Already Has an External `watch` for Value Restoration

`MONDOAutocomplete.vue` at line 259 already watches `props.modelValue` and calls `ontologyAPI.searchMONDO` to restore the display when the component receives an existing value. When auto-population is added (MONDO selection populates `disease_name`), this watch will also fire on auto-population events. This creates a potential double-call: the auto-population emits `update:diseaseName`, which the form stores, which may trigger another search if the form also passes `disease_name` back. Trace the data flow carefully before adding auto-population to avoid this feedback loop.

### The `formData` Deep Watch Already Triggers Backend Validation

`DynamicForm.vue` at line 643 runs a deep watch on `formData` that calls `validateForm()` (debounced at 500ms). When field dependency logic mutates `formData` (e.g., auto-populating `disease_name`, cascading options), each mutation will trigger this watch and a backend validation call. This is correct behavior, but if 5 fields are auto-populated in sequence, 5 debounce timers are started. Only the last one fires. Ensure that auto-population sequences complete within the 500ms debounce window; otherwise, intermediate states may trigger premature validation.

---

## Sources

- Gene Curator codebase analysis (HIGH confidence): `DynamicForm.vue`, `DynamicField.vue`, `TabContent.vue`, `useValidationRules.js`, `MONDOAutocomplete.vue`, `PMIDInput.vue`, `useFormRecovery.js`, `schema_validator.py`, `014_seed_clingen_schema.sql`, `016_seed_precuration_schema.sql`
- Vue 3 official documentation — Watchers: https://vuejs.org/guide/essentials/watchers (HIGH)
- Vue 3 official documentation — Conditional Rendering: https://vuejs.org/guide/essentials/conditional.html (HIGH)
- Vue 3.5 `onWatcherCleanup`: https://dev.to/alexanderop/vue-35s-onwatchercleanup-mastering-side-effect-management-in-vue-applications-9pn (MEDIUM)
- Infinite render loops in Vue 3: https://gist.github.com/AlexVipond/3be2803fef21ac6268855045483497f5 (MEDIUM)
- JotForm conditional logic — clear on hide behavior: https://www.jotform.com/answers/5357271 (MEDIUM — industry practice documentation)
- Prior phase research: `.planning/phases/04-validation/04-RESEARCH.md` (HIGH — same codebase)
- Prior codebase concerns: `.planning/codebase/CONCERNS.md` (HIGH — same codebase)
