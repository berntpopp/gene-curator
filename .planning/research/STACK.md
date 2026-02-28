# Technology Stack: Form Intelligence (v0.2)

**Project:** Gene Curator — Form Intelligence milestone
**Researched:** 2026-02-28
**Scope:** Conditional visibility, cross-field validation, cascading field dependencies

---

## Recommendation Summary

**Use Vue 3's built-in reactivity. Add `json-logic-js` for schema-serializable rule evaluation. No form library.**

The existing stack (Vue 3.4 + Vuetify 3.9 + Pinia 2.1 + VueUse 14.1) covers all three feature areas
without adding a form framework. A lightweight rule evaluator (`json-logic-js`, ~3 kB gzipped) is the
only new dependency worth adding — and only if the schema design requires serializing conditions to the
database. If conditions are expressed as simple predicate objects (field/operator/value triples), even
that library can be skipped.

---

## Decision: Pure Vue Reactivity vs. Form Library vs. Rule Engine

### Evaluated options

| Option | What it gives you | Cost |
|--------|------------------|------|
| Vue `computed` + `watch` | Conditional visibility, cross-field refs | Zero — already installed |
| Vuetify native rules (closure pattern) | Cross-field validation via closure over `formData` | Zero — already installed |
| `useValidationRules` composable (existing) | Extend with inter-field validators | Zero — file already exists |
| `json-logic-js` | Serializable rule evaluation from JSONB | ~3 kB gzipped, zero deps |
| VeeValidate v4 | Schema-based validation, form state | ~14 kB gzipped, conflicts with Vuetify v-form |
| Vuelidate 2 | Model-based validation, `requiredIf` | ~4 kB gzipped, redundant with existing composable |
| FormKit | Full form framework, JSON schema, conditional rendering | Large (~30–50 kB), requires replacing DynamicForm |
| Yup | Validation schema DSL | ~14 kB gzipped, need adapter for Vuetify rules |

### Why NOT a form library

**VeeValidate v4** (v4.15.1, last release June 2024; v5 in beta as of Feb 2026):
- Provides `useForm` + `useField` composition hooks that manage their own form state.
- This conflicts directly with `DynamicForm.vue` which owns `formData` ref and passes it through the
  tab/section/field component tree. Merging the two state systems would require a significant rewrite.
- Cross-field validation works via Yup's `.when()` or `@target` parameter syntax — but those rules
  live in JavaScript, not in the JSONB `field_definitions`. Conditions that can't be stored in the
  database break the schema-agnostic design.
- Confidence: MEDIUM (verified via VeeValidate v4 official docs and npm releases page)

**Vuelidate 2**:
- Lighter than VeeValidate (~4 kB). Supports `requiredIf`, `requiredUnless`, `sameAs`, and logical
  combinators (`and`, `or`, `not`).
- Rule definitions are reactive computed functions in JavaScript — not serializable to JSONB. Same
  schema-agnostic problem as VeeValidate.
- `useValidationRules.js` already exists and already handles required, minLength, maxLength, minimum,
  maximum, pattern, enum. Vuelidate would duplicate this layer.
- Confidence: HIGH (verified via Vuelidate official docs)

**FormKit**:
- Has a JSON schema with native `if/then/else` conditional nodes and `$cmp` for custom components.
  Technically capable of what is needed.
- Would require replacing the entire `DynamicForm` + `DynamicField` + `TabContent` component tree
  (3 files, 1,400+ LOC, 428 passing tests). That is a rewrite, not an addition.
- Bundle footprint is large relative to what is gained. FormKit's form state also conflicts with
  Vuetify's `v-form` ref validation lifecycle (`formRef.value.validate()`).
- Confidence: MEDIUM (verified via FormKit official schema docs)

**Yup**:
- Excellent DSL for schema validation but requires an adapter layer to produce Vuetify rule functions
  (arrays of `(value) => true | string`). Not a net simplification.
- `.when()` conditions are JavaScript closures, not JSONB-serializable.
- Confidence: HIGH (standard community knowledge)

### Why ONLY `json-logic-js` (conditionally)

The key architectural constraint is schema-agnosticism: conditions governing field visibility and
cross-field validation must be storable in the JSONB `field_definitions` and applied at render time.
This rules out JavaScript-closure-based rule DSLs (Yup, Vuelidate, VeeValidate).

`json-logic-js` (v2.0.5) evaluates JSON-native rule objects like:
```json
{ "==": [{ "var": "mode_of_inheritance" }, "autosomal_dominant"] }
```
against a data object. It is:
- ~3 kB gzipped, zero runtime dependencies
- Safe (no `eval()`)
- Isomorphic — the same JSON rule can be evaluated in Python on the backend using the `json-logic-python`
  library. This enables backend-side pre-validation using the same rule definitions stored in JSONB.
- Already used as the conceptual model in similar medical form systems

**However**: if the team decides that visibility rules use only simple equality/inequality predicates
(field == value, field != value, field in [values]), a tiny hand-written evaluator (~20 lines) is
sufficient and eliminates the dependency entirely. `json-logic-js` earns its place only when the
expressiveness of operators like `and`, `or`, `>`, `<`, `in`, `none`, `some` is actually needed in
the schemas.

Confidence: MEDIUM (json-logic-js npm page verified; bundle size estimate from json-logic-engine-slim
comparison; maintenance status: last npm publish ~2 years ago but library is stable/complete)

---

## Stack for Each Feature Area

### 1. Conditional Field Visibility (COND-01, COND-02)

**Approach: `computed` over `formData` ref, evaluated by a rule function.**

```javascript
// In useFieldVisibility.js (new composable)
import { computed } from 'vue'

export function useFieldVisibility(formData, fieldSchema) {
  const isVisible = computed(() => {
    const rule = fieldSchema.value?.visibility
    if (!rule) return true
    return evaluateRule(rule, formData.value)
  })
  return { isVisible }
}
```

`evaluateRule` can be:
- A hand-written predicate evaluator for simple cases (eq, ne, in, notIn)
- `jsonLogic.apply(rule, data)` from `json-logic-js` for complex cases

**Integration point**: `DynamicField.vue` already receives `fieldSchema` as a prop. Add `v-if="isVisible"` wrapper in `TabContent.vue` when rendering fields from `section.fields`. No changes needed in `DynamicForm.vue`.

**Schema convention** (new `visibility` key in field_definitions):
```json
{
  "predicted_or_proven_null_count": {
    "type": "number",
    "visibility": {
      "==": [{ "var": "mode_of_inheritance" }, "autosomal_dominant"]
    }
  }
}
```

**Libraries needed**: None (simple predicates) or `json-logic-js` (complex predicates).
**Confidence**: HIGH for the Vue reactivity pattern; MEDIUM for json-logic-js integration.

---

### 2. Cross-Field Validation (XVAL-01, XVAL-02)

**Approach: Extend `useValidationRules.js` composable to accept `formData` context.**

Vuetify's native validation rules are `(value) => true | string` functions. Rules can close over any
reactive state, including `formData`:

```javascript
// Extended useValidationRules signature
export function useValidationRules(fieldSchemaGetter, formDataGetter) {
  const validationRules = computed(() => {
    const fieldSchema = fieldSchemaGetter()
    const formData = formDataGetter?.()   // optional, for cross-field rules
    const rules = []

    // Existing rules (required, minLength, etc.) unchanged...

    // New: cross-field rules from schema
    if (fieldSchema.crossFieldRules && formData) {
      fieldSchema.crossFieldRules.forEach(rule => {
        rules.push(value => evaluateRule(rule, { ...formData, [fieldSchema.fieldName]: value }))
      })
    }

    return rules
  })
  return { validationRules }
}
```

**Schema convention** (new `crossFieldRules` key):
```json
{
  "experimental_score": {
    "type": "number",
    "crossFieldRules": [
      {
        "condition": { "<=": [{ "var": "experimental_score" }, { "var": "max_experimental_points" }] },
        "message": "Experimental score cannot exceed the maximum for this inheritance mode"
      }
    ]
  }
}
```

**Integration point**: `DynamicField.vue` already calls `useValidationRules(() => props.fieldSchema)`.
The call becomes `useValidationRules(() => props.fieldSchema, () => props.formData)`. This requires
passing `formData` down to `DynamicField` — a prop addition in `TabContent.vue` and `DynamicForm.vue`.

**Libraries needed**: None beyond what's used for conditional visibility.
**Confidence**: HIGH (pattern verified against existing Vuetify rule function signature and existing composable).

---

### 3. Cascading Field Dependencies (DEPS-01, DEPS-02)

**DEPS-01: Cascading selects (field B options depend on field A value)**

**Approach: `computed` over `formData` in `DynamicField.vue` for dynamic option filtering.**

```javascript
// In DynamicField.vue
const dynamicOptions = computed(() => {
  const options = props.fieldSchema.enum || props.fieldSchema.enumOptions || []
  const dep = props.fieldSchema.dependsOn
  if (!dep || !props.formData) return options

  const parentValue = props.formData[dep.field]
  if (!parentValue) return []

  // Filter options by parent value using schema-defined mapping
  return options.filter(opt => {
    const allowedParents = dep.optionMap?.[opt.value]
    return !allowedParents || allowedParents.includes(parentValue)
  })
})
```

**Schema convention** (new `dependsOn` key):
```json
{
  "variant_subtype": {
    "type": "string",
    "enum": ["frameshift", "missense", "synonymous"],
    "dependsOn": {
      "field": "variant_category",
      "optionMap": {
        "frameshift": ["loss_of_function"],
        "missense": ["gain_of_function", "unknown"],
        "synonymous": ["unknown"]
      }
    }
  }
}
```

**DEPS-02: Auto-population (selecting MONDO ID populates disease_name)**

**Approach: `watch` in `DynamicForm.vue` for field-triggered side effects.**

Auto-population is a side effect (not a derived value), so `watch` is correct here (not `computed`).
This is a controlled exception to the "prefer computed" guidance: the effect must write to another
field, which `computed` cannot do.

```javascript
// In DynamicForm.vue, auto-population watcher
watch(
  () => formData.value['mondo_id'],
  async (newMongoId) => {
    if (!newMondoId) return
    const schema = jsonSchema.value
    const autoPopFields = getAutoPopulationFields(schema, 'mondo_id')
    for (const { targetField, source } of autoPopFields) {
      // source could be 'disease_name_from_mondo_api' or a lookup map
      formData.value[targetField] = await resolveAutoPopulation(source, newMondoId)
    }
  }
)
```

For MONDO ID specifically, the `externalValidationStore` already handles HGNC/PubMed/HPO lookups
(verified in `useValidation.js`). MONDO lookup would follow the same pattern via a new store action.

**Libraries needed**: None for option filtering. A MONDO API call uses the existing axios `client.js`.
**Confidence**: HIGH for option filtering pattern; MEDIUM for MONDO auto-population (depends on whether
MONDO has a reliable REST endpoint for disease name lookup).

---

## New Composable: `useFieldConditions.js`

Consolidate all three feature areas into one composable to avoid prop-drilling and keep the
`DynamicField` component clean:

```javascript
// frontend/src/components/dynamic/composables/useFieldConditions.js
import { computed } from 'vue'

export function useFieldConditions(fieldSchemaGetter, formDataGetter) {
  const fieldSchema = () => fieldSchemaGetter()
  const formData = () => formDataGetter?.() ?? {}

  const isVisible = computed(() => {
    const rule = fieldSchema()?.visibility
    if (!rule) return true
    return evaluateRule(rule, formData())
  })

  const effectiveOptions = computed(() => {
    const schema = fieldSchema()
    const options = schema?.enum ?? schema?.enumOptions ?? []
    const dep = schema?.dependsOn
    if (!dep) return options
    const parentValue = formData()[dep.field]
    if (!parentValue) return []
    return options.filter(opt => {
      const allowed = dep.optionMap?.[opt.value ?? opt]
      return !allowed || allowed.includes(parentValue)
    })
  })

  return { isVisible, effectiveOptions }
}
```

This composable lives alongside the existing `useValidationRules.js` in
`frontend/src/components/dynamic/composables/`.

---

## Recommended New Dependency

| Library | Version | Purpose | Install |
|---------|---------|---------|---------|
| `json-logic-js` | 2.0.5 | Evaluate serializable JSON conditions from JSONB field_definitions | `npm install json-logic-js` |

**Conditional**: Add only if the team decides visibility/validation conditions require operators
beyond simple equality (eq, ne, in). If schemas only need `field == value`, write the 20-line
evaluator inline and skip this dependency.

**Size**: The package is approximately 3–4 kB gzipped. The npm page notes it was last published ~2
years ago; the library is intentionally stable, not abandoned (the specification is complete).
Confidence: MEDIUM (size from json-logic-engine comparison; last-publish date from npm page).

---

## Alternatives Considered and Rejected

| Category | Recommended | Alternative | Why Rejected |
|----------|-------------|-------------|--------------|
| Condition evaluation | `json-logic-js` or inline | Yup `.when()` | Not JSONB-serializable; JavaScript closures only |
| Form validation | Extend `useValidationRules.js` | VeeValidate v4 | Conflicts with `formData` ref ownership; rewrite cost |
| Form state | Existing `formData` ref | Vuelidate 2 | Redundant with existing composable; not serializable |
| Full form framework | None | FormKit | Requires replacing 1,400+ LOC component tree; conflicts with Vuetify v-form |
| Cross-field access | Closure over `formData` prop | Global Pinia store for form state | Pinia is correct for server state; local form state belongs in the component |

---

## Integration Points with Existing Stack

| Existing Component/Composable | Change Needed | Reason |
|-------------------------------|---------------|--------|
| `DynamicField.vue` | Add `formData` prop; wrap output in `v-if="isVisible"` | Required by both visibility and cascading deps |
| `TabContent.vue` | Pass `formData` down to `DynamicField` | Required by cross-field validation and deps |
| `DynamicForm.vue` | Add auto-population watchers; pass `formData` to `TabContent` | Required by DEPS-02 |
| `useValidationRules.js` | Add optional `formDataGetter` parameter | Required by XVAL-01 |
| `curation_schemas` JSONB | New keys: `visibility`, `crossFieldRules`, `dependsOn` | Schema conventions for new features |
| Backend `schema_validator.py` | Already has `_apply_dependency_rule`; extend for new schema keys | Enables server-side validation parity |

---

## What NOT to Add

- **VeeValidate v5 (beta)**: Still in beta as of February 2026. API not stable. Do not adopt.
- **React Hook Form port**: Not applicable; this is Vue.
- **Pinia store for form data**: Form data is component-local state. The existing `formData` ref in
  `DynamicForm.vue` is correct. Only server-fetched data (schemas, validation results) belong in Pinia.
- **vue-json-schema-form libraries**: These are form renderers that replace `DynamicForm`. The existing
  renderer is 428-test-covered and well-suited to the domain. Do not replace it.
- **JSON Schema `if/then/else` keywords**: The project's JSONB field_definitions do not use standard
  JSON Schema format (they use a custom schema with `type`, `required`, `enumOptions`, `ui_component`,
  etc.). Adopting JSON Schema `if/then/else` would require migrating all 4 schemas and the backend
  validator. This is out of scope for the v0.2 milestone.

---

## Version Verification

All versions checked against npm package registry and official documentation as of 2026-02-28:

| Package | Version in use | Latest stable | Status |
|---------|---------------|---------------|--------|
| `vue` | ^3.4.21 | 3.5.x series | Active; 3.4.x fully supported |
| `vuetify` | ^3.9.3 | 3.9.x | Active |
| `pinia` | ^2.1.7 | 2.1.x | Active |
| `@vueuse/core` | ^14.1.0 | 14.x | Active |
| `vee-validate` | Not installed | 4.15.1 (v5 beta) | Rejected |
| `vuelidate` | Not installed | 2.x | Rejected |
| `json-logic-js` | Not installed | 2.0.5 | Candidate (conditional add) |

Confidence: HIGH for existing packages (package.json verified); MEDIUM for json-logic-js (npm page
consulted; last-publish date ~2 years ago, library considered complete).

---

## Sources

- VeeValidate v4 official docs: https://vee-validate.logaretm.com/v4/guide/overview/
- VeeValidate cross-field validation: https://vee-validate.logaretm.com/v3/advanced/cross-field-validation.html
- VeeValidate GitHub releases (v4.15.1, v5 beta): https://github.com/logaretm/vee-validate/releases
- Vuelidate validators (requiredIf, sameAs): https://vuelidate-next.netlify.app/validators
- FormKit schema (if/then/else, $cmp): https://formkit.com/essentials/schema
- JsonLogic specification: https://jsonlogic.com/
- json-logic-js npm page: https://www.npmjs.com/package/json-logic-js
- Vue 3 reactivity best practices: https://vuejs.org/api/reactivity-core.html
- Vue 3 computed vs watch: https://www.sabbirz.com/blog/vue-3-reactivity-computed-vs-watch-vs-watcheffect-when-to-use-which
- Vuetify 3 form component: https://vuetifyjs.com/en/components/forms/
- project `frontend/package.json` (actual installed versions)
- project `DynamicForm.vue`, `DynamicField.vue`, `TabContent.vue`, `useValidationRules.js` (existing implementation)
- project `backend/app/core/schema_validator.py` (existing backend validation)
- project `.planning/PROJECT.md` (milestone requirements COND-01/02, XVAL-01/02, DEPS-01/02)
