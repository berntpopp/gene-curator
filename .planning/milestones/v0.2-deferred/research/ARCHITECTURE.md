# Architecture Patterns: Form Intelligence Integration

**Domain:** Dynamic form field interactions (conditional visibility, cross-field validation, field dependencies)
**Project:** Gene Curator v0.2 Form Intelligence
**Researched:** 2026-02-28
**Confidence:** HIGH (all findings based on direct codebase inspection)

---

## Existing Architecture (Baseline)

Before designing integration points, the existing component chain must be understood precisely.

### Current Component Chain

```
DynamicForm.vue
  ├── formData (ref) — single source of truth for all field values
  ├── validationStore.validateEvidence() — 500ms debounced backend call
  ├── TabContent.vue — renders tabs from ui_configuration.layout.tabs
  │     ├── section.fields[] — list of dot-notation field paths
  │     └── DynamicField.vue — renders one field by type
  │           ├── useValidationRules() — per-field Vuetify rules from fieldSchema
  │           ├── componentRegistry — specialized components (MONDOAutocomplete, etc.)
  │           └── emits: update:model-value, validate, clear-backend-error
  └── ScoreDisplay.vue — sidebar score panel
```

### Current Data Flow

```
User types in DynamicField
  → emit('update:model-value', value)
  → TabContent emits('update:field', fieldPath, value)
  → DynamicForm.handleTabFieldUpdate(fieldPath, value)
  → formData.value[fieldPath] = value
  → setTimeout(validateForm, 500)  [debounced]
  → validationStore.validateEvidence(formData, schemaId)
  → backend: POST /api/v1/validate-evidence
  → validationResult reactive computed updates
  → backendErrors distributed to DynamicField via props
```

### Existing Schema Properties Relevant to Form Intelligence

The database already contains partial form intelligence vocabulary. The precuration schema (migration 016) uses `show_when`:

```json
{
  "id": "moi_notes",
  "type": "textarea",
  "show_when": { "mode_of_inheritance": "Other" }
}
```

```json
{
  "id": "lumping_splitting_decision",
  "type": "select",
  "show_when": { "lumping_splitting_applicable": true }
}
```

The older curation schema (migration 014) uses a `condition` string expression:

```json
{
  "id": "variant_type",
  "type": "select",
  "condition": "evidence_category == 'case_level'"
}
```

The `validation_rules` object (migration 016) uses `conditional_required`:

```json
{
  "conditional_required": {
    "lumping_splitting_decision": {
      "when": { "lumping_splitting_applicable": true }
    }
  }
}
```

**Key finding:** Two incompatible syntaxes already exist in production schemas. The new composable must normalize both and establish a canonical format for future schemas.

---

## Recommended Architecture

### Guiding Principle: Rule Evaluation Lives in a Single Composable

All three capabilities (visibility, cross-field validation, cascading dependencies) share a common need: evaluating a condition against the current `formData`. Centralizing this in one engine composable avoids duplication and ensures consistent behavior.

### Integration Point Map

```
DynamicForm.vue                       [MODIFIED]
  ├── useFieldInteractions(schema, formData)  [NEW COMPOSABLE]
  │     ├── visibilityMap: { fieldPath → boolean }
  │     ├── dynamicRules: { fieldPath → Function[] }
  │     └── applyFieldEffect(fieldPath, value)
  │
  ├── TabContent.vue                  [MODIFIED - receives visibilityMap]
  │     └── DynamicField.vue         [MODIFIED - v-if from visibilityMap]
  │           └── useValidationRules() [EXTENDED - accepts cross-field rules]
  │
  └── formData watcher               [EXISTING - triggers interaction evaluation]
```

---

## Schema Extension: Where Rules Live

### Decision: Rules Stay in `field_definitions`, Not a Separate Property

Rationale: Field-level rules (show/hide, required-when) belong to the field they affect. Schema-level cross-field validation belongs in `validation_rules`, which already exists. Splitting these creates a third location to check.

### Canonical Rule Format for `field_definitions`

Adopt the `show_when` object syntax already present in migration 016 as the canonical form. The string `condition` from migration 014 is a legacy format to be normalized.

```json
{
  "field_definitions": {
    "variant_type": {
      "type": "select",
      "label": "Variant Type",
      "visibility": {
        "field": "evidence_category",
        "operator": "eq",
        "value": "case_level"
      },
      "required_when": {
        "field": "evidence_category",
        "operator": "eq",
        "value": "case_level"
      }
    },
    "lumping_splitting_decision": {
      "type": "select",
      "label": "Decision",
      "visibility": {
        "field": "lumping_splitting_applicable",
        "operator": "eq",
        "value": true
      }
    }
  }
}
```

**Normalization rule:** When loading a schema, if a field has `show_when` (dict) or `condition` (string), normalize to `visibility` format. This happens once in `useFieldInteractions`, not in each component.

### Cross-Field Validation in `validation_rules`

```json
{
  "validation_rules": {
    "cross_field": [
      {
        "id": "lod_score_requires_segregation",
        "fields": ["lod_score"],
        "condition": {
          "field": "evidence_category",
          "operator": "eq",
          "value": "segregation"
        },
        "rule": "required",
        "message": "LOD score is required when evidence category is Segregation"
      },
      {
        "id": "proband_count_positive",
        "fields": ["proband_count"],
        "condition": {
          "field": "evidence_category",
          "operator": "eq",
          "value": "case_level"
        },
        "rule": "min",
        "value": 1,
        "message": "At least one proband required for case-level evidence"
      }
    ]
  }
}
```

### Field Dependencies (Cascading / Auto-Population)

```json
{
  "field_definitions": {
    "disease_name": {
      "type": "string",
      "label": "Disease Name",
      "auto_populate": {
        "source_field": "mondo_id",
        "source_property": "label"
      }
    },
    "variant_options": {
      "type": "select",
      "label": "Variant Options",
      "options_from": {
        "field": "inheritance_pattern",
        "mapping": {
          "AD": ["predicted_null", "missense"],
          "AR": ["biallelic_null", "compound_het"],
          "XL": ["hemizygous_null"]
        }
      }
    }
  }
}
```

---

## New Composables

### 1. `useFieldInteractions` (Primary — build first)

**Location:** `frontend/src/components/dynamic/composables/useFieldInteractions.js`

**Purpose:** Single source of truth for all field interaction evaluation. Consumes the full schema and current formData; produces derived reactive maps consumed by rendering components.

**API:**

```javascript
// useFieldInteractions.js
export function useFieldInteractions(schemaGetter, formDataGetter) {
  // Returns:
  return {
    // Reactive map: fieldPath → boolean (true = visible)
    visibilityMap,

    // Reactive map: fieldPath → additional Vuetify rule functions
    // merged with existing useValidationRules output
    crossFieldRules,

    // Reactive map: fieldPath → computed options array
    // null means use static options from schema
    dynamicOptions,

    // Call when a field value changes, handles auto-population side effects
    // Returns { [fieldPath]: newValue } for any fields that should be updated
    getAutoPopulateUpdates(changedFieldPath, newValue)
  }
}
```

**Internal logic:**

```
visibilityMap = computed(() => {
  for each field in schema.field_definitions:
    if field has visibility rule:
      normalize rule (handle show_when, condition, visibility formats)
      evaluate rule against current formData
      set visibilityMap[fieldPath] = result
    else:
      set visibilityMap[fieldPath] = true  (visible by default)
})

crossFieldRules = computed(() => {
  for each rule in schema.validation_rules.cross_field:
    if rule.condition evaluates true against current formData:
      generate Vuetify rule function for rule.rule type
      assign to crossFieldRules[fieldPath]
})
```

**Condition evaluator (private):**

```javascript
function evaluateCondition(condition, formData) {
  // condition: { field, operator, value }
  // Normalizes legacy formats before evaluation
  const fieldValue = getNestedValue(formData, condition.field)
  switch (condition.operator) {
    case 'eq': return fieldValue === condition.value
    case 'neq': return fieldValue !== condition.value
    case 'in': return condition.value.includes(fieldValue)
    case 'nin': return !condition.value.includes(fieldValue)
    case 'gt': return fieldValue > condition.value
    case 'lt': return fieldValue < condition.value
    case 'truthy': return Boolean(fieldValue)
    case 'falsy': return !fieldValue
  }
}
```

**Legacy normalization:**

```javascript
function normalizeVisibilityRule(field) {
  // show_when: { fieldName: value } → canonical form
  if (field.show_when) {
    const [f, v] = Object.entries(field.show_when)[0]
    return { field: f, operator: 'eq', value: v }
  }
  // condition: "evidence_category == 'case_level'" → canonical form
  if (field.condition && typeof field.condition === 'string') {
    return parseConditionString(field.condition)
  }
  // Already canonical
  return field.visibility || null
}
```

### 2. `useConditionalVisibility` (Thin adapter — optional)

**Location:** `frontend/src/components/dynamic/composables/useConditionalVisibility.js`

**Purpose:** If `useFieldInteractions` becomes large, this can expose only the visibility slice. In practice, building `useFieldInteractions` first makes this optional — only extract if the visibility logic needs to be used independently of other interaction features.

**Recommendation:** Do not build separately. Export `visibilityMap` from `useFieldInteractions` directly.

### 3. `useFieldDependencies` (Thin adapter — optional)

Same reasoning as above. Export `dynamicOptions` and `getAutoPopulateUpdates` directly from `useFieldInteractions`. Extract only if dependency logic becomes a distinct testing concern.

---

## Component Modifications

### DynamicForm.vue (Modified)

**What changes:**
- Import and instantiate `useFieldInteractions(jsonSchema, formData)`
- Pass `visibilityMap` and `crossFieldRules` down to `TabContent`
- In `handleTabFieldUpdate`: call `getAutoPopulateUpdates(fieldPath, value)` and apply any returned updates to `formData` before the validation debounce
- Existing `updateField` and `handleTabFieldUpdate` logic is otherwise unchanged

**New props passed to TabContent:**
```javascript
// DynamicForm.vue additions
const { visibilityMap, crossFieldRules, dynamicOptions, getAutoPopulateUpdates } =
  useFieldInteractions(
    () => jsonSchema.value,
    () => formData.value
  )

// In handleTabFieldUpdate, after setting formData:
const autoUpdates = getAutoPopulateUpdates(fieldPath, value)
Object.entries(autoUpdates).forEach(([path, val]) => {
  setNestedValue(formData.value, path, val)
})
```

### TabContent.vue (Modified)

**What changes:**
- Accept `visibilityMap` and `crossFieldRules` as props
- Pass them to each `DynamicField`
- Apply `v-if` based on `visibilityMap[fieldPath]` (not `v-show` — hidden fields should not submit values)

**New props:**
```javascript
defineProps({
  // existing props...
  visibilityMap: { type: Object, default: () => ({}) },
  crossFieldRules: { type: Object, default: () => ({}) },
  dynamicOptions: { type: Object, default: () => ({}) }
})
```

**Template change:**
```html
<v-col
  v-for="fieldPath in section.fields"
  :key="fieldPath"
  v-if="visibilityMap[fieldPath] !== false"
>
  <DynamicField
    :field-name="getFieldName(fieldPath)"
    :field-schema="getFieldSchema(fieldPath)"
    :model-value="getFieldValue(fieldPath)"
    :validation-result="getFieldValidation(fieldPath)"
    :backend-errors="backendErrors[fieldPath] || []"
    :cross-field-rules="crossFieldRules[fieldPath] || []"
    :dynamic-options="dynamicOptions[fieldPath] || null"
    :disabled="readonly"
    @update:model-value="$emit('update:field', fieldPath, $event)"
    @clear-backend-error="$emit('clear-backend-error', fieldPath)"
  />
</v-col>
```

**Critical:** `v-if` (not `v-show`) prevents hidden fields from contributing to form validation. A hidden field's value is not cleared automatically — that is a deliberate design choice. If a field becomes hidden, its existing value persists in `formData` but is excluded from validation. The backend must also apply visibility rules when validating submitted data.

### DynamicField.vue (Modified)

**What changes:**
- Accept `crossFieldRules` prop (additional Vuetify rule functions)
- Accept `dynamicOptions` prop (replaces static `enum`/`options` when provided)
- Merge `crossFieldRules` into the rules array passed to Vuetify inputs

**New props:**
```javascript
defineProps({
  // existing props...
  crossFieldRules: { type: Array, default: () => [] },
  dynamicOptions: { type: Array, default: null }
})
```

**In script, extend existing validation rules:**
```javascript
// Existing: const { validationRules } = useValidationRules(() => props.fieldSchema)
// New: merge cross-field rules
const allValidationRules = computed(() =>
  [...validationRules.value, ...props.crossFieldRules]
)
// Use allValidationRules instead of validationRules in template
```

**For dynamic options in v-select:**
```javascript
const selectItems = computed(() => {
  // If dynamicOptions provided by parent, use them
  if (props.dynamicOptions) return props.dynamicOptions
  // Otherwise fall back to existing getSelectItems()
  return getSelectItems()
})
```

### useValidationRules.js (Unchanged)

The existing composable stays as-is. Cross-field rules are generated by `useFieldInteractions` and merged at the `DynamicField` level. This preserves the single-field contract of `useValidationRules`.

---

## Data Flow: Field Value Changes

```
User changes field A value
  │
  ▼
DynamicField emits update:model-value
  │
  ▼
TabContent emits update:field(fieldPath, value)
  │
  ▼
DynamicForm.handleTabFieldUpdate(fieldPath, value)
  │
  ├─→ setNestedValue(formData, fieldPath, value)
  │
  ├─→ getAutoPopulateUpdates(fieldPath, value)     [useFieldInteractions]
  │     └─→ Apply auto-population to formData (synchronous)
  │
  ├─→ visibilityMap recomputes                      [Vue reactive, automatic]
  │     └─→ Fields with visibility rules show/hide
  │
  ├─→ crossFieldRules recomputes                   [Vue reactive, automatic]
  │     └─→ Conditional required rules activate/deactivate
  │
  ├─→ dynamicOptions recomputes                    [Vue reactive, automatic]
  │     └─→ Cascading select options update
  │
  └─→ setTimeout(validateForm, 500)                [existing debounce]
        └─→ POST /api/v1/validate-evidence
```

### Why Reactive Computed Maps Work Here

`visibilityMap`, `crossFieldRules`, and `dynamicOptions` are all `computed()` in Vue 3. Because they read from `formData.value` (a reactive `ref`), they automatically invalidate and recompute when any field changes. No explicit event wiring is needed between fields — Vue's dependency tracking handles propagation.

This is the key architectural decision: no custom event bus, no field-to-field subscription system. The reactive computed graph is the dependency system.

---

## Flat Rendering Path

DynamicForm has two rendering paths: tabbed (via `TabContent`) and flat (the `v-else-if` branch that renders `DynamicField` directly). Both must receive visibility context.

**Flat path modification:**
```html
<v-col
  v-for="(field, fieldName) in jsonSchema.properties"
  :key="fieldName"
  v-if="visibilityMap[fieldName] !== false"
>
  <DynamicField
    :field-name="fieldName"
    :field-schema="field"
    :model-value="formData[fieldName]"
    :cross-field-rules="crossFieldRules[fieldName] || []"
    :dynamic-options="dynamicOptions[fieldName] || null"
    ...
  />
</v-col>
```

---

## Backend Implications

### No Backend Changes Required for Visibility

The backend `SchemaValidator` in `schema_validator.py` validates submitted `evidence_data` against `field_definitions`. If a field is hidden (and therefore excluded from form display), the submitted data simply won't contain it. The backend already handles missing optional fields gracefully.

However, if a field is conditionally required and the condition is false (field hidden), the backend must not require it. The backend currently evaluates `required` as a static property. It does not evaluate `required_when` or `visibility` conditions.

**Short-term:** Hidden fields remain in `formData` with their existing values, so the backend receives them and validates them normally. This works for the immediate milestone.

**Medium-term:** The backend `SchemaValidator._validate_fields()` method should be extended to evaluate visibility conditions before checking `required`. This prevents backend validation errors for fields the user legitimately cannot see. This is a distinct backend task, flagged here as a follow-up.

### No Backend Changes Required for Cross-Field Validation Client Side

Cross-field validation rules in `validation_rules.cross_field` are evaluated purely client-side by `useFieldInteractions`. The existing backend validation (`validate-evidence` endpoint) can be extended later to also process these rules, but the client-side implementation is sufficient for v0.2.

---

## Build Order (Recommended)

### Phase 1: Conditional Visibility (Build First)

**Why first:** Visibility is self-contained. It reads existing `show_when`/`condition` fields that are already in production schemas. No schema changes required. Provides immediate value (lumping/splitting fields in precuration already have `show_when` annotations).

**Deliverables:**
1. `useFieldInteractions.js` — implement `visibilityMap` computed only (defer rules and options)
2. `DynamicForm.vue` — instantiate composable, pass `visibilityMap` to `TabContent`
3. `TabContent.vue` — add `v-if` per field using `visibilityMap`
4. `DynamicField.vue` — no changes needed for visibility alone
5. Tests: `useFieldInteractions.spec.js` covering eq/neq/in operators and legacy format normalization

**Validates:** The reactive computed approach works with the existing prop chain before adding complexity.

### Phase 2: Cross-Field Validation (Build Second)

**Why second:** Builds on the same `useFieldInteractions` composable already established. Extends the `crossFieldRules` export. Requires adding the `cross_field` array to `validation_rules` in at least one schema for testing.

**Deliverables:**
1. `useFieldInteractions.js` — add `crossFieldRules` computed
2. `DynamicField.vue` — accept and merge `crossFieldRules` prop
3. `TabContent.vue` — pass `crossFieldRules` to `DynamicField`
4. `DynamicForm.vue` — pass `crossFieldRules` from composable to `TabContent`
5. Tests: cross-field required, cross-field min/max

### Phase 3: Field Dependencies (Build Third)

**Why third:** Most complex (auto-population involves writing to `formData`, not just reading). Cascading selects require `dynamicOptions` map. Auto-population requires the `getAutoPopulateUpdates` side-effect pattern in `handleTabFieldUpdate`.

**Deliverables:**
1. `useFieldInteractions.js` — add `dynamicOptions` computed and `getAutoPopulateUpdates` function
2. `DynamicForm.vue` — call `getAutoPopulateUpdates` in `handleTabFieldUpdate`
3. `DynamicField.vue` — accept and use `dynamicOptions` in v-select
4. `TabContent.vue` — pass `dynamicOptions` to `DynamicField`
5. Tests: cascading options, auto-population (MONDO ID → disease name)

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Field-to-Field Event Subscriptions

**What it looks like:** `DynamicField` emits `field-changed` events, other fields subscribe with `watch` calls, each field independently evaluates its own visibility.

**Why bad:** Creates an implicit dependency graph that is impossible to trace. When field A affects fields B, C, and D, debugging requires checking every field's watch handler. The reactive computed graph in `useFieldInteractions` makes all dependencies explicit and visible.

**Instead:** Single composable produces derived maps; components are pure consumers of those maps.

### Anti-Pattern 2: Clearing Hidden Field Values

**What it looks like:** When visibility changes and a field hides, automatically clear its value in `formData`.

**Why bad:** If the user hides field B by changing field A, then changes A back, field B's value is lost. This is a poor UX in complex forms where users may toggle conditions repeatedly.

**Instead:** Hidden fields retain their values in `formData`. They are excluded from form validation (via `v-if`) but their data is preserved for re-display. The backend receives all values in `formData` including those for hidden fields. This is consistent with how most production form libraries handle conditional visibility.

**Exception:** If a specific field's value is semantically invalid after hiding (e.g., `lumping_splitting_decision` when `lumping_splitting_applicable` is false), clearing can be done explicitly in `getAutoPopulateUpdates` on a field-by-field basis when the schema author configures it.

### Anti-Pattern 3: String Expression Evaluators

**What it looks like:** Evaluating `condition: "evidence_category == 'case_level'"` by calling `eval()` or building a custom expression parser.

**Why bad:** Security risk (eval), maintenance burden (custom parser), and brittle string matching. The existing string conditions in migration 014 are legacy; new schemas should use the structured object format.

**Instead:** Normalize string conditions to structured objects at load time using simple regex parsing for the `==` pattern. Flag anything more complex as an unrecognized condition (log warning, default to visible).

### Anti-Pattern 4: Backend-Only Visibility Logic

**What it looks like:** Frontend always shows all fields; visibility is enforced by backend validation rejecting visible-but-shouldn't-be-present data.

**Why bad:** Poor UX (users filling in fields they don't need), increased network chatter, confusing error messages.

**Instead:** Evaluate visibility client-side for immediate feedback. The backend validates submitted data independently but does not drive UI visibility.

### Anti-Pattern 5: Separate Visibility Store

**What it looks like:** Pinia store `useVisibilityStore` manages which fields are visible, fields register themselves on mount.

**Why bad:** Over-engineering for what is a derived computation from schema + formData. Stores are for shared global state; visibility is local to a form instance. Adding a store creates unnecessary coupling between `DynamicForm` instances and global state.

**Instead:** Composable scoped to each `DynamicForm` instance. Each form has its own `useFieldInteractions()` invocation.

---

## Scalability Considerations

| Concern | At 20 fields | At 100 fields | Notes |
|---------|-------------|---------------|-------|
| visibilityMap recompute | Negligible | ~1ms | Pure JS object traversal |
| crossFieldRules recompute | Negligible | ~2ms | Linear scan of rules array |
| React to keystrokes | Each keystroke triggers recompute | Still negligible | Computed memoization handles this |
| Backend validation | 500ms debounce | 500ms debounce | Unchanged from v0.1 |

The ClinGen schema has ~50 fields at top level, more in nested arrays. Computed performance will not be a bottleneck. No memoization beyond Vue's built-in `computed()` caching is needed.

---

## Testing Architecture

### New Test File

**Location:** `frontend/src/components/dynamic/__tests__/useFieldInteractions.spec.js`

**Test cases required:**

```
useFieldInteractions
  ├── visibilityMap
  │   ├── returns true for fields without visibility rules
  │   ├── eq operator: hides field when condition not met
  │   ├── eq operator: shows field when condition met
  │   ├── neq operator
  │   ├── in operator (value in array)
  │   ├── truthy/falsy operators for boolean fields
  │   ├── normalizes legacy show_when format
  │   ├── normalizes legacy condition string format
  │   └── updates reactively when formData changes
  ├── crossFieldRules
  │   ├── returns no rules when condition not met
  │   ├── returns required rule when condition met
  │   └── returned rule function validates correctly
  └── dynamicOptions
      ├── returns null when no options_from defined
      ├── returns mapped options based on source field value
      └── updates reactively when source field changes
```

### Modified Test Files

**`DynamicForm.validation.spec.js`** — Add tests that verify hidden fields do not produce validation errors.

**`TabContent.spec.js`** — Add tests that verify `v-if` hides fields when `visibilityMap[fieldPath]` is false.

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| Existing component boundaries | HIGH | Direct code inspection |
| Schema visibility syntax variants | HIGH | Direct inspection of migrations 014, 016 |
| `useFieldInteractions` composable design | HIGH | Matches Vue 3 reactivity patterns and existing composable style |
| Build order rationale | HIGH | Phase ordering follows dependency graph |
| Backend implications | MEDIUM | schema_validator.py inspected; "skip hidden fields" requires future work |
| Performance at 100+ fields | MEDIUM | Not benchmarked, reasoning from JS engine characteristics |

---

## Sources

- `/home/bernt-popp/development/gene-curator/frontend/src/components/dynamic/DynamicForm.vue` — full component inspection
- `/home/bernt-popp/development/gene-curator/frontend/src/components/dynamic/DynamicField.vue` — full component inspection
- `/home/bernt-popp/development/gene-curator/frontend/src/components/dynamic/TabContent.vue` — full component inspection
- `/home/bernt-popp/development/gene-curator/frontend/src/components/dynamic/composables/useValidationRules.js` — validation rule pattern
- `/home/bernt-popp/development/gene-curator/frontend/src/composables/useSchemaScoring.js` — composable design pattern
- `/home/bernt-popp/development/gene-curator/database/sql/016_seed_precuration_schema.sql` — `show_when` syntax in production
- `/home/bernt-popp/development/gene-curator/database/sql/014_seed_clingen_schema.sql` — `condition` string syntax in production
- `/home/bernt-popp/development/gene-curator/backend/app/core/schema_validator.py` — backend validation architecture
- `/home/bernt-popp/development/gene-curator/backend/app/api/v1/endpoints/schema_validation.py` — validation API contract
- `/home/bernt-popp/development/gene-curator/.planning/PROJECT.md` — v0.2 requirements (COND-01, COND-02, XVAL-01, XVAL-02, DEPS-01, DEPS-02)
