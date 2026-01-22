# Phase 4: Validation - Research

**Researched:** 2026-01-23
**Domain:** Vue 3 + Vuetify 3 form validation with dynamic schema-driven rules
**Confidence:** MEDIUM

## Summary

This phase implements inline validation for DynamicForm by generating Vuetify validation rules from JSON schema constraints, integrating backend validation errors, and controlling form submission based on validation state. The implementation follows Vuetify's native validation patterns (rules prop, v-form methods) with a blur-then-eager validation strategy for optimal user experience.

**Key findings:**
- Vuetify 3's built-in validation system (rules prop + v-form ref methods) provides the foundation
- Validation timing matters for UX: validate on blur, then reactively clear errors as user fixes them
- Backend errors map to fields via error-messages prop, separate from client-side rules
- Tab validation requires manual tracking since inactive tabs may not register validation state
- Debouncing backend validation (300ms default) reduces API spam during form input

**Primary recommendation:** Use Vuetify's native validation with computed rules generated from schema constraints, layered with backend errors via error-messages prop. Implement blur-then-eager validation timing to balance user experience with immediate feedback.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vuetify 3 | 3.x | Form validation system | Native validation with rules prop, v-form component with validate() method |
| Vue 3 Composition API | 3.x | Reactive validation rules | Computed properties for dynamic rule generation from schema |
| lodash.debounce | 4.x | Debounce backend validation | Industry standard for throttling API calls during input |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| VeeValidate | 4.x | Advanced validation | If cross-field validation or complex schemas needed (FUTURE - not v0.1) |
| Vuelidate | 2.x | Alternative validation library | If preferring composable-based validation over Vuetify rules |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Vuetify rules | VeeValidate | More features (cross-field, complex schemas) but adds dependency; overkill for v0.1 requirements |
| Manual validation | Browser native | Less control over UX and error display timing |
| Immediate validation | Lazy/eager modes | Different UX, but blur-then-eager is industry best practice |

**Installation:**
```bash
# Core dependencies already installed in Gene Curator
npm install vuetify  # Already present
npm install lodash   # Already present for debouncing
```

## Architecture Patterns

### Recommended Component Structure
```
components/dynamic/
├── DynamicForm.vue          # v-form wrapper, validation orchestration
├── DynamicField.vue         # Field rendering + client-side rules
└── composables/
    └── useValidationRules.js  # Rule generation from schema (NEW)
```

### Pattern 1: Schema-to-Rules Generation (Computed)
**What:** Generate Vuetify validation rules array from JSON schema constraints
**When to use:** Every field that has schema constraints (required, minLength, pattern, enum, etc.)
**Example:**
```javascript
// In DynamicField.vue
import { computed } from 'vue'

const validationRules = computed(() => {
  const rules = []

  // Required rule
  if (props.fieldSchema.required) {
    const message = props.fieldSchema.errorMessage || 'Required'
    rules.push(v => (v !== null && v !== undefined && v !== '') || message)
  }

  // Min/max length for strings
  if (props.fieldSchema.minLength) {
    rules.push(v =>
      !v || v.length >= props.fieldSchema.minLength ||
      `Minimum ${props.fieldSchema.minLength} characters`
    )
  }

  // Pattern validation
  if (props.fieldSchema.pattern) {
    const regex = new RegExp(props.fieldSchema.pattern)
    const message = props.fieldSchema.errorMessage || 'Invalid format'
    rules.push(v => !v || regex.test(v) || message)
  }

  // Enum validation
  if (props.fieldSchema.enum) {
    rules.push(v =>
      !v || props.fieldSchema.enum.includes(v) ||
      'Must be one of the allowed values'
    )
  }

  // Number range
  if (props.fieldSchema.minimum !== undefined) {
    rules.push(v =>
      v === null || v === '' || v >= props.fieldSchema.minimum ||
      `Minimum value: ${props.fieldSchema.minimum}`
    )
  }

  return rules
})
```
**Source:** Vuetify official patterns + existing Gene Curator DynamicField.vue implementation

### Pattern 2: Backend Error Integration
**What:** Map backend validation errors to field-level error-messages prop
**When to use:** After form submission or debounced backend validation
**Example:**
```javascript
// In DynamicForm.vue
const backendErrors = ref({})

// On backend validation response
const handleBackendValidation = (validationResult) => {
  backendErrors.value = {}

  if (!validationResult.is_valid && validationResult.field_validations) {
    Object.entries(validationResult.field_validations).forEach(([field, validation]) => {
      if (validation.errors && validation.errors.length > 0) {
        // Take first error only (per CONTEXT decision)
        backendErrors.value[field] = [validation.errors[0].message]
      }
    })
  }
}

// Clear backend errors on field change
const clearFieldBackendError = (fieldName) => {
  if (backendErrors.value[fieldName]) {
    delete backendErrors.value[fieldName]
  }
}

// In template, pass to DynamicField
<DynamicField
  :backend-errors="backendErrors[fieldName]"
  @update:model-value="clearFieldBackendError(fieldName)"
/>
```
**Source:** Pattern from existing Login.vue (lines 25, 38) + [Medium article on Vuetify backend validation](https://medium.com/@alekswebnet/vue-js-practice-guide-display-client-and-server-side-validation-errors-consistently-with-vuetify-f8e31ff9feb0)

### Pattern 3: Form-Level Validation State
**What:** Use v-form ref to control submit button and trigger validation
**When to use:** Form submission blocking and programmatic validation
**Example:**
```javascript
// In DynamicForm.vue
const formRef = ref(null)
const isFormValid = ref(false)

// Submit handler
const handleSubmit = async () => {
  // Validate all fields
  const { valid } = await formRef.value.validate()

  if (!valid) {
    // Find first invalid tab and navigate to it
    const firstErrorTab = findFirstInvalidTab()
    if (firstErrorTab) {
      activeTab.value = firstErrorTab
      // Focus first invalid field (accessibility)
      await nextTick()
      focusFirstInvalidField()
    }
    return
  }

  // Proceed with submission
  emit('submit', formData.value)
}

// Template
<v-form ref="formRef" v-model="isFormValid" @submit.prevent="handleSubmit">
  <!-- Fields -->
  <v-btn type="submit" :disabled="!isFormValid">Submit</v-btn>
</v-form>
```
**Source:** Vuetify v-form documentation + existing Register.vue pattern (line 17, 72, 133)

### Pattern 4: Debounced Backend Validation
**What:** Debounce backend validation calls to reduce API spam
**When to use:** Live validation as user types (after blur has occurred)
**Example:**
```javascript
import { debounce } from 'lodash'
import { watch } from 'vue'

// Debounced validation function
const debouncedValidate = debounce(async (data, schemaId) => {
  try {
    const result = await validationStore.validateEvidence(data, schemaId)
    handleBackendValidation(result)
  } catch (error) {
    logger.error('Backend validation failed', { error: error.message })
  }
}, 300) // 300ms debounce

// Watch form data for changes
watch(
  () => formData.value,
  (newData) => {
    if (hasUserInteracted.value) {
      debouncedValidate(newData, props.schemaId)
    }
  },
  { deep: true }
)
```
**Source:** [Vue 3 debounce pattern](https://theroadtoenterprise.com/blog/how-to-create-a-debounced-ref-in-vue-3-using-composition-api) + existing validation store

### Pattern 5: Tab Validation Badges
**What:** Show error indicator on tabs containing invalid fields
**When to use:** Multi-tab forms where validation errors may be outside visible tab
**Example:**
```javascript
// In DynamicForm.vue
const tabValidationErrors = computed(() => {
  const errors = {}

  validTabs.value.forEach(tab => {
    const fieldsInTab = getFieldsInTab(tab)
    const hasErrors = fieldsInTab.some(fieldName => {
      return (
        backendErrors.value[fieldName]?.length > 0 ||
        clientErrors.value[fieldName]?.length > 0
      )
    })
    errors[tab.id] = hasErrors
  })

  return errors
})

// Template
<v-tab v-for="tab in validTabs" :key="tab.id">
  {{ tab.name }}
  <v-badge
    v-if="tabValidationErrors[tab.id]"
    color="error"
    dot
    inline
    class="ml-2"
  />
</v-tab>
```
**Source:** Vuetify badge component + manual validation tracking (Vuetify bug: [inactive tabs don't register validation](https://github.com/vuetifyjs/vuetify/issues/7555))

### Anti-Patterns to Avoid
- **Immediate/aggressive validation:** Don't validate on every keystroke before blur - violates UX best practices
- **v-model.number with blank values:** Vue bug converts blank back to string - validate type explicitly
- **Ignoring validation timing:** Vuetify's default eager validation can feel aggressive - use validate-on-blur or manual control
- **Spreading all props with v-bind:** Gene Curator decision [01-01] mandates explicit prop mapping for clarity

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Validation rule functions | Custom validation logic per field type | Vuetify rules array + computed generation | Rules are sequential, display max 1 error, integrate with v-form |
| Backend error mapping | Manual error state per field | Reactive object + error-messages prop | Vuetify handles display, you manage state |
| Debouncing | Custom setTimeout/clearTimeout | lodash.debounce | Handles edge cases (leading, trailing, cancel) |
| Form submission blocking | Manual button disable logic | v-form v-model binding | Vuetify tracks form validity automatically |
| Cross-field validation | Custom watchers between fields | VeeValidate (FUTURE) | Complex schemas with field dependencies need library support |
| Async validation | Custom promise handling per field | VeeValidate async rules (FUTURE) | Handles loading states, error recovery, cancellation |

**Key insight:** Vuetify's built-in validation is sufficient for schema constraint validation (required, length, pattern, enum, range). External libraries like VeeValidate are only needed for advanced scenarios (cross-field validation, conditional rules, complex async validation) which are deferred to v0.2+.

## Common Pitfalls

### Pitfall 1: Over-aggressive validation timing
**What goes wrong:** Validating on every keystroke or immediately on focus shows errors before user has chance to enter valid input
**Why it happens:** Default Vuetify behavior validates on blur, but developers often add @input validation for "immediate feedback"
**How to avoid:** Use blur-then-eager pattern: validate on blur, then if invalid, reactively clear errors as user types (field becomes valid). This is called "eager" mode in validation libraries.
**Warning signs:** Users complain about red error text appearing "too early" or form feeling "aggressive"
**Source:** [Fixing Vuetify's Form Validation](https://rmirabelle.medium.com/fixing-vuetifys-form-validation-3a5781ea43fe) + [VeeValidate Interaction Modes](https://vee-validate.logaretm.com/v3/guide/interaction-and-ux.html)

### Pitfall 2: Backend errors persisting after field change
**What goes wrong:** Backend validation error stays visible even after user modifies the field, feels "stuck"
**Why it happens:** Backend errors stored in separate state, not cleared on field update events
**How to avoid:** Clear backend errors for a field on @update:model-value event. Only client-side rules re-validate automatically.
**Warning signs:** User fixes field but error message doesn't disappear until form re-submission
**Implementation:**
```javascript
const updateField = (fieldName, value) => {
  formData.value[fieldName] = value
  // Clear backend error for this field
  if (backendErrors.value[fieldName]) {
    delete backendErrors.value[fieldName]
  }
}
```

### Pitfall 3: Validation rules not reactive to schema changes
**What goes wrong:** Schema updates (e.g., admin edits field_definitions) don't reflect in validation until page reload
**Why it happens:** Rules generated once in setup(), not as computed property
**How to avoid:** Use computed() for getValidationRules() so rules regenerate when props.fieldSchema changes
**Warning signs:** Schema changes in backend don't take effect until user refreshes page
**Example:**
```javascript
// BAD - rules computed once
const rules = getValidationRules(props.fieldSchema)

// GOOD - rules recompute when schema changes
const rules = computed(() => getValidationRules(props.fieldSchema))
```

### Pitfall 4: Inactive tabs not validating
**What goes wrong:** Form submission succeeds despite errors in tabs user hasn't visited
**Why it happens:** Vuetify bug/limitation - fields in inactive tabs may not register in v-form until tab is activated
**How to avoid:** Manually track validation state per tab, validate all tabs on submit attempt, auto-navigate to first error tab
**Warning signs:** Submit button enabled despite having required fields in unvisited tabs
**Workaround:**
```javascript
const validateAllTabs = async () => {
  // Force validation by temporarily visiting each tab
  for (const tab of validTabs.value) {
    activeTab.value = tab.id
    await nextTick()
  }
  // Return to current tab
  activeTab.value = currentTab
  // Now validate form
  return await formRef.value.validate()
}
```
**Source:** [GitHub Issue #7555](https://github.com/vuetifyjs/vuetify/issues/7555) - v-form doesn't validate fields in other tabs

### Pitfall 5: Mixing client and backend error display
**What goes wrong:** Two error messages shown for same field (one from rules, one from error-messages)
**Why it happens:** Both :rules and :error-messages props set simultaneously
**How to avoid:** Per CONTEXT decision: "Client errors take priority when both exist for same field." Only show error-messages when rules validation passes.
**Warning signs:** Double error messages, visual clutter
**Implementation:**
```javascript
const getErrorMessages = (fieldName) => {
  // Only show backend errors if no client-side errors present
  if (hasClientError(fieldName)) {
    return []
  }
  return backendErrors.value[fieldName] || []
}
```

### Pitfall 6: Not showing required indicator before interaction
**What goes wrong:** User doesn't know which fields are required until after blur
**Why it happens:** Only showing asterisk (*) when error appears
**How to avoid:** Use Vuetify's built-in required prop which adds asterisk to label immediately
**Warning signs:** User submits form with empty required fields, surprised by errors
**Solution:** Pass :required="fieldSchema.required" to all Vuetify input components

## Code Examples

Verified patterns from official sources and Gene Curator codebase:

### Required Field Validation
```javascript
// Source: Vuetify rules pattern + Gene Curator Register.vue (line 115-118)
const requiredRule = (fieldSchema) => {
  const message = fieldSchema.errorMessage || 'Required'
  return v => (v !== null && v !== undefined && v !== '') || message
}

// For arrays
const requiredArrayRule = (fieldSchema) => {
  const message = fieldSchema.errorMessage || 'At least one item required'
  return v => (Array.isArray(v) && v.length > 0) || message
}
```

### Pattern Validation with Custom Message
```javascript
// Source: Gene Curator Register.vue email validation (line 117)
const patternRule = (fieldSchema) => {
  if (!fieldSchema.pattern) return null

  const regex = new RegExp(fieldSchema.pattern)
  const message = fieldSchema.errorMessage || 'Invalid format'

  return v => !v || regex.test(v) || message
}

// Example patterns from backend
// Email: /.+@.+\..+/
// PMID: /^\d{1,8}$/
// HGNC ID: /^HGNC:\d+$/
```

### Length Validation
```javascript
// Source: Gene Curator Register.vue password validation (line 122)
const minLengthRule = (fieldSchema) => {
  if (!fieldSchema.minLength) return null

  const min = fieldSchema.minLength
  const message = fieldSchema.errorMessage || `Minimum ${min} characters`

  return v => !v || v.length >= min || message
}

const maxLengthRule = (fieldSchema) => {
  if (!fieldSchema.maxLength) return null

  const max = fieldSchema.maxLength
  const message = fieldSchema.errorMessage || `Maximum ${max} characters`

  return v => !v || v.length <= max || message
}
```

### Number Range Validation
```javascript
// Source: Backend schema_validator.py (line 269-280)
const minimumRule = (fieldSchema) => {
  if (fieldSchema.minimum === undefined) return null

  const min = fieldSchema.minimum
  const message = fieldSchema.errorMessage || `Minimum value: ${min}`

  return v => v === null || v === '' || v >= min || message
}

const maximumRule = (fieldSchema) => {
  if (fieldSchema.maximum === undefined) return null

  const max = fieldSchema.maximum
  const message = fieldSchema.errorMessage || `Maximum value: ${max}`

  return v => v === null || v === '' || v <= max || message
}
```

### Enum Validation
```javascript
// Source: Backend schema_validator.py + Vuetify select pattern
const enumRule = (fieldSchema) => {
  if (!fieldSchema.enum || !Array.isArray(fieldSchema.enum)) return null

  const allowedValues = fieldSchema.enum
  const message = fieldSchema.errorMessage || 'Must be one of the allowed values'

  return v => !v || allowedValues.includes(v) || message
}
```

### Complete Validation Rules Generator
```javascript
// Source: Composition of patterns above
const getValidationRules = (fieldSchema) => {
  const rules = []

  // Order matters: check required first, then format/constraints
  if (fieldSchema.required) {
    rules.push(requiredRule(fieldSchema))
  }

  if (fieldSchema.minLength) {
    rules.push(minLengthRule(fieldSchema))
  }

  if (fieldSchema.maxLength) {
    rules.push(maxLengthRule(fieldSchema))
  }

  if (fieldSchema.minimum !== undefined) {
    rules.push(minimumRule(fieldSchema))
  }

  if (fieldSchema.maximum !== undefined) {
    rules.push(maximumRule(fieldSchema))
  }

  if (fieldSchema.pattern) {
    rules.push(patternRule(fieldSchema))
  }

  if (fieldSchema.enum) {
    rules.push(enumRule(fieldSchema))
  }

  // Filter out null rules (not applicable to this field)
  return rules.filter(rule => rule !== null)
}
```

### Form-Level Alert for Non-Field Errors
```javascript
// Source: Gene Curator DynamicForm.vue (line 78-93) adapted
// For backend errors that don't map to specific fields
<v-alert
  v-if="hasNonFieldErrors"
  type="error"
  variant="tonal"
  class="mb-4"
  closable
  @click:close="clearNonFieldErrors"
>
  <template #prepend>
    <v-icon>mdi-alert-circle</v-icon>
  </template>
  <div class="font-weight-medium">Form Validation Error</div>
  <div>{{ nonFieldErrorMessage }}</div>
</v-alert>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| VeeValidate required for all validation | Vuetify native rules sufficient for simple schemas | Vuetify 3.0 (2022) | Reduces dependencies, simpler for schema-driven validation |
| Aggressive validation (on input) | Blur-then-eager pattern | Industry shift ~2020 | Better UX, less frustration for users |
| Single validation timing mode | Configurable modes (lazy, eager, aggressive) | VeeValidate 3.0+ | Flexibility to match use case |
| Manual error state management | Framework-integrated error-messages prop | Vue 3 + Vuetify 3 | Cleaner code, consistent display |
| Synchronous validation only | Async validation support | VeeValidate 4.0 | Enables real-time API validation (FUTURE for Gene Curator) |

**Deprecated/outdated:**
- Vuetify 2 `validate-on-blur` prop: Replaced with manual blur handling in Vuetify 3
- String-based rules (e.g., "required|email"): Modern approach uses function arrays for type safety
- Global validation config in Vuetify: v3 requires per-field configuration

## Open Questions

Things that couldn't be fully resolved:

1. **Array field item validation timing**
   - What we know: Array items need same blur-then-eager validation as regular fields
   - What's unclear: DynamicField handles arrays with add/remove - does each array item get individual validation state?
   - Recommendation: Treat each array item as a field with its own validation state. Use field path (e.g., "publications[0].pmid") for error mapping.

2. **Tab validation state initialization**
   - What we know: Vuetify may not register fields in inactive tabs ([GitHub Issue #7555](https://github.com/vuetifyjs/vuetify/issues/7555))
   - What's unclear: Does KeepAlive in Gene Curator's DynamicForm mitigate this issue?
   - Recommendation: Test thoroughly. If issue persists, implement manual tab validation tracking or force-visit all tabs before form submission.

3. **Backend validation response format**
   - What we know: Backend returns SchemaValidationResult with field_validations dict (backend/app/core/schema_validator.py line 18)
   - What's unclear: Exact format of error messages for nested fields (arrays, objects)
   - Recommendation: Document and test nested field error paths. Example: "genetic_evidence[0].pmid" for array item errors.

4. **Validation rule performance with large schemas**
   - What we know: Computed rules regenerate on schema change
   - What's unclear: Performance impact with 50+ fields, complex nested structures
   - Recommendation: Monitor performance. If issues arise, consider memoization or rule caching composable.

## Sources

### Primary (HIGH confidence)
- Vuetify v-form documentation: https://vuetifyjs.com/en/components/forms/
- Gene Curator existing code: Register.vue (lines 17, 24, 36, 115-131), Login.vue (lines 25, 38), DynamicField.vue (lines 22-23, 690-746)
- Backend validation schema: schema_validator.py (lines 11-68, 256-288)
- [Vuetify v-form ref methods documentation](https://v15.vuetifyjs.com/en/components/forms/)

### Secondary (MEDIUM confidence)
- [Consistent Form Validation Errors with Vue 3, Vuetify, and VeeValidate](https://medium.com/@alekswebnet/vue-js-practice-guide-display-client-and-server-side-validation-errors-consistently-with-vuetify-f8e31ff9feb0)
- [Vue 3 debounce pattern with customRef](https://theroadtoenterprise.com/blog/how-to-create-a-debounced-ref-in-vue-3-using-composition-api)
- [Fixing Vuetify's Form Validation](https://rmirabelle.medium.com/fixing-vuetifys-form-validation-3a5781ea43fe)
- [VeeValidate Interaction Modes](https://vee-validate.logaretm.com/v3/guide/interaction-and-ux.html)
- [GitHub Issue #7555 - v-form doesn't validate fields in other tabs](https://github.com/vuetifyjs/vuetify/issues/7555)

### Tertiary (LOW confidence)
- WebSearch results about Vue 3 validation patterns (general best practices)
- Community discussions on validation timing (requires official verification)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Vuetify 3 native validation verified in official docs and existing codebase
- Architecture: MEDIUM - Patterns verified in Gene Curator codebase, but tab validation workaround needs testing
- Pitfalls: MEDIUM - Drawn from GitHub issues and community articles, verified against Gene Curator requirements

**Research date:** 2026-01-23
**Valid until:** ~30 days (2026-02-23) - Vuetify 3 is stable, patterns unlikely to change

**Phase constraint validation:**
- ✅ CONTEXT.md decisions honored: blur timing, inline errors only, backend error clearing on change
- ✅ Requirements covered: VALD-01 through VALD-06 all researched
- ✅ Scoring excluded: Deferred to Phase 5 per phase boundary
