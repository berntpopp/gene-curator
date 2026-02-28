# Phase 1: Field Rendering - Research

**Researched:** 2026-01-22
**Domain:** Vue 3 dynamic form rendering with Vuetify 3 components
**Confidence:** HIGH

## Summary

This phase implements dynamic field rendering for Vue 3 with Vuetify 3, mapping JSON Schema field definitions to appropriate form components. The standard approach uses recursive Vue components with a component registry pattern for specialized inputs (MONDOAutocomplete, PMIDInput, HPOInheritanceSelect, OMIMAutocomplete, HPOInput).

**Current State:** DynamicForm and DynamicField components exist with basic type support (string, number, boolean, date, array, object). Five specialized components are implemented. The phase adds: (1) component registry integration, (2) nested depth styling, (3) robust fallback handling, and (4) format validation.

**Key Technical Challenges:**
- Recursive component self-reference in `<script setup>` (filename-based)
- Deep reactivity with nested objects/arrays (Vue 3 handles automatically via Proxy)
- Preventing infinite recursion with conditional v-if
- Component registry fallback when component missing
- Performance optimization for large schema objects passed as props

**Primary recommendation:** Use eager-loaded component registry with explicit mapping, implement conditional rendering depth limits, leverage Vue 3 deep reactivity for nested structures, and provide graceful fallbacks for unknown types.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vue | 3.4.21 | Component framework | Composition API, defineModel(), built-in recursion support |
| Vuetify | 3.9.3 | Material Design UI | Complete form component library (v-text-field, v-select, v-autocomplete, etc.) |
| @vueuse/core | 14.1.0 | Composition utilities | useDebounceFn for autocomplete debouncing (300ms recommended) |
| Pinia | 2.1.7 | State management | Stores for validation and schema data |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| axios | 1.13.2 | HTTP client | API calls for autocomplete components (MONDO, PMID, OMIM) |
| JSON Schema | N/A (standard) | Schema definition | Field type mapping (string, number, boolean, array, object) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Eager registry loading | Dynamic imports (defineAsyncComponent) | Complexity not worth it for 5 small components |
| Full schema props | provide/inject | Unnecessary - schema objects are stable, not frequently updated |
| Custom validation | VeeValidate/Vuelidate | Already using backend validation API - don't duplicate |

**Installation:**
```bash
# Already installed in package.json
cd frontend
npm install
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/components/
├── dynamic/
│   ├── DynamicForm.vue         # Container, fetches schema, handles submission
│   ├── DynamicField.vue        # Recursive renderer, maps types to components
│   └── componentRegistry.js    # Registry mapping component names to imports
└── evidence/
    ├── MONDOAutocomplete.vue   # Specialized ontology search
    ├── PMIDInput.vue           # PubMed ID validation
    ├── HPOInheritanceSelect.vue # Inheritance pattern dropdown
    ├── OMIMAutocomplete.vue    # OMIM disease search
    └── HPOInput.vue            # HPO term input
```

### Pattern 1: Component Registry (Eager Loading)

**What:** Centralized mapping from string names to component imports, loaded at module initialization.

**When to use:** When components are critical to form functionality (not conditional features).

**Example:**
```javascript
// componentRegistry.js
import MONDOAutocomplete from '@/components/evidence/MONDOAutocomplete.vue'
import PMIDInput from '@/components/evidence/PMIDInput.vue'
import HPOInheritanceSelect from '@/components/evidence/HPOInheritanceSelect.vue'
import OMIMAutocomplete from '@/components/evidence/OMIMAutocomplete.vue'
import HPOInput from '@/components/evidence/HPOInput.vue'

export const componentRegistry = {
  MONDOAutocomplete,
  PMIDInput,
  HPOInheritanceSelect,
  OMIMAutocomplete,
  HPOInput
}

export function getComponent(componentName) {
  return componentRegistry[componentName] || null
}
```

**Usage in DynamicField:**
```vue
<script setup>
import { componentRegistry } from './componentRegistry'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger()

// Check if field specifies custom component
const customComponent = computed(() => {
  if (props.fieldSchema.component) {
    const comp = componentRegistry[props.fieldSchema.component]
    if (!comp) {
      logger.warn('Component not found in registry', {
        component: props.fieldSchema.component,
        fieldName: props.fieldName
      })
    }
    return comp
  }
  return null
})
</script>

<template>
  <!-- Custom component if specified and found -->
  <component
    v-if="customComponent"
    :is="customComponent"
    v-model="modelValue"
    v-bind="fieldSchema"
    @update:model-value="updateValue"
  />
  <!-- Standard type-based rendering -->
  <v-text-field v-else-if="fieldSchema.type === 'string'" ... />
</template>
```

**Source:** Vue 3 dynamic components documentation and community patterns (Medium, DEV Community)

### Pattern 2: Recursive Component Self-Reference

**What:** DynamicField renders itself for nested object properties and array items. Vue 3 allows filename-based self-reference.

**When to use:** For schema types 'object' and 'array' with nested properties.

**Example:**
```vue
<!-- DynamicField.vue -->
<template>
  <!-- Object Fields -->
  <div v-else-if="fieldSchema.type === 'object'">
    <v-label class="text-body-2 font-weight-medium mb-2">
      {{ getFieldLabel() }}
    </v-label>

    <v-card
      variant="outlined"
      :style="getNestedStyle(depth)"
    >
      <v-card-text>
        <v-row>
          <v-col
            v-for="(subFieldSchema, subFieldName) in fieldSchema.properties"
            :key="subFieldName"
            cols="12"
            :sm="Object.keys(fieldSchema.properties).length > 2 ? 6 : 12"
          >
            <!-- Self-reference via filename -->
            <DynamicField
              :field-name="subFieldName"
              :field-schema="subFieldSchema"
              :model-value="objectValue[subFieldName]"
              :depth="depth + 1"
              variant="outlined"
              :disabled="disabled"
              @update:model-value="updateObjectField(subFieldName, $event)"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </div>

  <!-- Array Fields with recursive items -->
  <div v-else-if="fieldSchema.type === 'array'">
    <v-label>{{ getFieldLabel() }}</v-label>
    <v-card variant="outlined">
      <v-card-text>
        <div v-for="(item, index) in arrayValue" :key="index" class="mb-4">
          <DynamicField
            v-for="(subFieldSchema, subFieldName) in fieldSchema.items?.properties"
            :key="subFieldName"
            :field-name="subFieldName"
            :field-schema="subFieldSchema"
            :model-value="item[subFieldName]"
            :depth="depth + 1"
            @update:model-value="updateArrayItem(index, subFieldName, $event)"
          />
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
const props = defineProps({
  fieldName: { type: String, required: true },
  fieldSchema: { type: Object, required: true },
  modelValue: { type: [String, Number, Boolean, Array, Object], default: null },
  depth: { type: Number, default: 0 }  // Track nesting depth
})

// Prevent infinite recursion
const MAX_DEPTH = 10
const effectiveDepth = computed(() => Math.min(props.depth, MAX_DEPTH))

// Progressive background tinting for depth 2+
function getNestedStyle(depth) {
  if (depth < 2) return {}
  const opacity = Math.min(0.02 + (depth - 2) * 0.01, 0.06)
  return { backgroundColor: `rgba(var(--v-theme-surface-variant), ${opacity})` }
}
</script>
```

**Recursion Safety:** Filename-based self-reference (DynamicField refers to itself as `<DynamicField />`) works automatically in Vue 3 SFC. Must use v-if with depth limit to prevent stack overflow.

**Source:** [Recursive components in Vue 3 (Medium)](https://michael-verschoof.medium.com/recursive-components-in-vue-3-e897643df82), [Vue 3 Template Recursion (Medium)](https://medium.com/@alemrandev/exploring-the-power-of-vue-template-recursion-vue-3-810003615e73)

### Pattern 3: v-model for Nested Reactivity

**What:** Vue 3 provides deep reactivity by default via Proxy. For nested objects/arrays, emit 'update:modelValue' with entire object/array.

**When to use:** All DynamicField components updating parent state.

**Example:**
```vue
<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  fieldSchema: { type: Object, required: true },
  modelValue: { type: [String, Number, Boolean, Array, Object], default: null }
})

const emit = defineEmits(['update:model-value'])

// For arrays: maintain local ref, emit on changes
const arrayValue = ref(Array.isArray(props.modelValue) ? [...props.modelValue] : [])

// Watch external changes
watch(
  () => props.modelValue,
  newValue => {
    if (props.fieldSchema.type === 'array' && Array.isArray(newValue)) {
      arrayValue.value = [...newValue]
    }
  }
)

// Array item mutations
const updateArrayItem = (index, fieldName, value) => {
  arrayValue.value[index][fieldName] = value
  emit('update:model-value', arrayValue.value)  // Emit entire array
}

const removeArrayItem = (index) => {
  arrayValue.value.splice(index, 1)
  emit('update:model-value', arrayValue.value)
}

// For objects: maintain local ref
const objectValue = ref(
  props.modelValue && typeof props.modelValue === 'object' && !Array.isArray(props.modelValue)
    ? { ...props.modelValue }
    : {}
)

const updateObjectField = (fieldName, value) => {
  objectValue.value[fieldName] = value
  emit('update:model-value', objectValue.value)  // Emit entire object
}
</script>
```

**Key Insight:** Vue 3's reactivity system handles deep objects/arrays automatically. No need for Vue.set() or special array methods (Vue 2 limitation removed). Simply emit the mutated object/array.

**Performance Note:** Passing large schema objects as props creates reactive dependencies. For this phase, acceptable because: (1) schemas are fetched once and stable, (2) field_definitions don't change during form editing. If performance issues arise, use `readonly()` wrapper or extract only needed props.

**Source:** [Vue 3 Reactivity Fundamentals](https://vuejs.org/guide/essentials/reactivity-fundamentals), [Component v-model Guide](https://vuejs.org/guide/components/v-model.html), [Deep Reactivity Discussion (Medium)](https://medium.com/@hichemdahi57/deep-dive-into-vue-3s-reactivity-and-nested-objects-5d4cedc85b64)

### Pattern 4: Vuetify Validation Rules

**What:** Vuetify form components accept `:rules` prop as array of functions. Each returns `true` or error string.

**When to use:** Client-side validation hints (backend validation is authoritative).

**Example:**
```vue
<script setup>
const getValidationRules = () => {
  const rules = []

  if (props.fieldSchema.required) {
    rules.push(value => {
      if (value === null || value === undefined || value === '') {
        return `${getFieldLabel()} is required`
      }
      return true
    })
  }

  if (props.fieldSchema.minLength) {
    rules.push(value => {
      if (value && value.length < props.fieldSchema.minLength) {
        return `${getFieldLabel()} must be at least ${props.fieldSchema.minLength} characters`
      }
      return true
    })
  }

  if (props.fieldSchema.format === 'email') {
    rules.push(value => {
      if (value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        return 'Invalid email format'
      }
      return true
    })
  }

  if (props.fieldSchema.pattern) {
    rules.push(value => {
      if (value && !new RegExp(props.fieldSchema.pattern).test(value)) {
        return props.fieldSchema.patternMessage || 'Invalid format'
      }
      return true
    })
  }

  return rules
}
</script>

<template>
  <v-text-field
    :model-value="modelValue"
    :label="getFieldLabel()"
    :rules="getValidationRules()"
    :error-messages="getErrorMessages()"
    @update:model-value="updateValue"
  />
</template>
```

**Backend Integration:** Rules provide immediate feedback, but backend validation (via validationStore) is authoritative. Display backend errors via `:error-messages` prop.

**Source:** [Vuetify 3 Validation Rules](https://vuetifyjs.com/features/rules/), [Using Vuetify Native Validation (Medium)](https://medium.com/@carlos.henrique.sa.filho/using-vuetify-2-3-native-validation-rules-the-right-way-138f9a974a49)

### Anti-Patterns to Avoid

- **Lazy loading registry for form-critical components:** Adds complexity for minimal benefit. All 5 specialized components are small and always needed.
- **Passing schema via provide/inject:** Increases complexity without benefit - schemas are stable objects, not frequently mutated shared state.
- **Using `is` operator for SQLAlchemy boolean filters in backend:** SQLAlchemy overloads `__bool__()`, use `==` or direct filter.
- **Global component registration:** Prevents tree-shaking, creates maintenance issues in large apps. Use local imports.
- **Readonly fallback for unknown types:** Should be editable text field per UX decision - allows manual data entry for unrecognized types.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Debounced autocomplete search | Custom setTimeout logic | `useDebounceFn` from @vueuse/core | Handles cleanup, cancellation, edge cases. 300ms is tested default. |
| Deep reactivity for nested objects | Manual Vue.set() or custom watchers | Vue 3 Proxy-based reactivity | Built-in, automatic, no special syntax needed for nested updates. |
| JSON Schema validation | Custom validators for each type | Backend validation API + Vuetify rules | Backend has schema-aware validation engine, consistent with curation rules. |
| Component error boundaries | Try-catch in every component | Vue's `onErrorCaptured` hook | Catches descendant errors, provides fallback UI mechanism. |
| Recursive depth tracking | Manual counter prop | Computed depth with MAX_DEPTH constant | Self-documenting, prevents infinite loops, easy to test. |

**Key insight:** Vue 3's Composition API and reactivity system solve most "dynamic form" complexity. The challenge is architecture (registry, recursion limits, fallbacks), not low-level reactivity management.

## Common Pitfalls

### Pitfall 1: Infinite Recursion Without Depth Limit

**What goes wrong:** Recursive DynamicField rendering circular/deeply nested schemas causes "Maximum call stack size exceeded" error. Browser freezes, app crashes.

**Why it happens:** Component calls itself without conditional breaking point. Can occur with malformed schemas (circular references) or extremely deep nesting (10+ levels).

**How to avoid:**
```vue
<script setup>
const MAX_DEPTH = 10

const props = defineProps({
  depth: { type: Number, default: 0 }
})

const canRenderNested = computed(() => props.depth < MAX_DEPTH)
</script>

<template>
  <div v-if="fieldSchema.type === 'object' && canRenderNested">
    <DynamicField
      v-for="(subSchema, subName) in fieldSchema.properties"
      :depth="depth + 1"
      ...
    />
  </div>
  <v-alert v-else-if="!canRenderNested" type="warning">
    Maximum nesting depth reached
  </v-alert>
</template>
```

**Warning signs:** Schema with self-referencing properties, deeply nested object definitions (5+ levels), browser dev tools showing stack overflow in Vue component lifecycle.

**Source:** [Vue Recursive Components Stack Overflow (GitHub Issues)](https://github.com/nolimits4web/swiper/issues/3881), [Vue Edge Cases Guide](https://vuejs.org/v2/guide/components-edge-cases.html)

### Pitfall 2: Component Registry Name Mismatch

**What goes wrong:** Schema specifies `component: 'MONDOAutocomplete'` but registry key is `'MondoAutocomplete'` (different casing). Component not found, fallback to text field, user confusion.

**Why it happens:** Inconsistent naming conventions between backend schema definitions and frontend registry keys.

**How to avoid:**
```javascript
// componentRegistry.js - Document expected names
/**
 * Component Registry for Dynamic Forms
 *
 * Schema component names (case-sensitive):
 * - MONDOAutocomplete: Disease ontology search
 * - PMIDInput: PubMed ID validation
 * - HPOInheritanceSelect: Inheritance pattern dropdown
 * - OMIMAutocomplete: OMIM disease search
 * - HPOInput: HPO term input
 */
export const componentRegistry = {
  MONDOAutocomplete,
  PMIDInput,
  HPOInheritanceSelect,
  OMIMAutocomplete,
  HPOInput
}

// DynamicField.vue - Warn on mismatch
const customComponent = computed(() => {
  if (props.fieldSchema.component) {
    const comp = componentRegistry[props.fieldSchema.component]
    if (!comp) {
      logger.warn('Component not found in registry', {
        component: props.fieldSchema.component,
        fieldName: props.fieldName,
        availableComponents: Object.keys(componentRegistry)
      })
    }
    return comp
  }
  return null
})
```

**Warning signs:** Fields rendering as plain text inputs when they should be autocompletes, console warnings about missing components, user reports of "wrong component type".

### Pitfall 3: Array Reactivity Loss with Direct Index Assignment

**What goes wrong:** In Vue 2, `arrayValue[index] = newItem` doesn't trigger reactivity. In Vue 3, this works BUT mutating props directly causes warnings.

**Why it happens:** Vue 3 allows array index assignment reactivity, but mutating props is still anti-pattern. Need to emit changes to parent.

**How to avoid:**
```vue
<script setup>
// ✅ CORRECT: Local ref + emit
const arrayValue = ref([...(props.modelValue || [])])

const updateArrayItem = (index, fieldName, value) => {
  arrayValue.value[index][fieldName] = value  // Mutate local
  emit('update:model-value', arrayValue.value)  // Emit to parent
}

// Watch for external changes
watch(
  () => props.modelValue,
  newValue => {
    if (Array.isArray(newValue)) {
      arrayValue.value = [...newValue]
    }
  }
)

// ❌ WRONG: Direct prop mutation
const updateArrayItemWrong = (index, fieldName, value) => {
  props.modelValue[index][fieldName] = value  // Mutates prop!
}
</script>
```

**Warning signs:** Console warnings about prop mutation, array changes not persisting, parent component not seeing updates, validation not triggering on array changes.

**Source:** [Vue 3 Reactivity Fundamentals](https://vuejs.org/guide/essentials/reactivity-fundamentals), [Arrays and v-model Discussion](https://dev.to/razi91/vue-arrays-and-v-model-17e0)

### Pitfall 4: Schema Prop Reactivity Performance

**What goes wrong:** Passing entire schema object as prop to deeply nested components (4-5 levels) spreads reactivity everywhere. Single parent schema update invalidates entire component tree, causing cascading re-renders.

**Why it happens:** Vue 3 Proxy-based reactivity tracks all property access. Large objects with many properties create many reactive dependencies.

**How to avoid:**
```vue
<!-- ✅ GOOD: Pass only needed properties -->
<DynamicField
  :field-schema="fieldSchema"  <!-- Small, specific object -->
  :model-value="value"
/>

<!-- ❌ PROBLEMATIC: Pass entire schema -->
<DynamicField
  :full-schema="entireSchemaObject"  <!-- 100+ fields -->
  :current-field="fieldName"
/>

<!-- ✅ OPTIMIZATION: Use readonly() for stable data -->
<script setup>
import { readonly } from 'vue'

const stableSchema = readonly(props.fieldSchema)
</script>
```

**For this phase:** Acceptable to pass fieldSchema directly because:
1. Schema fetched once, doesn't change during form editing
2. Each DynamicField receives only its field definition (not entire schema)
3. No observed performance issues in testing

**Future optimization if needed:** Use `shallowRef()` for schema storage in Pinia store, or extract only needed field properties before passing.

**Warning signs:** Laggy form inputs (>100ms delay), Vue DevTools showing excessive re-renders, performance profiler showing DynamicField mounting/unmounting frequently.

**Source:** [Vue 3 Performance Pitfalls (Medium)](https://medium.com/simform-engineering/7-vue-3-performance-pitfalls-that-quietly-derail-your-app-33c7180d68d4), [Vue Component Props Best Practices](https://teamhood.com/engineering/vue-js-component-props/)

### Pitfall 5: Missing Component Fallback Without Logging

**What goes wrong:** Component specified in schema doesn't exist in registry. User sees text field but doesn't know why. No error, no visibility into issue.

**Why it happens:** Schema updated with new component name before frontend registry updated, typo in component name, component file deleted/renamed.

**How to avoid:**
```vue
<script setup>
import { useLogger } from '@/composables/useLogger'
const logger = useLogger()

const customComponent = computed(() => {
  if (!props.fieldSchema.component) return null

  const comp = componentRegistry[props.fieldSchema.component]

  if (!comp) {
    logger.warn('Component not found in registry - using fallback', {
      requestedComponent: props.fieldSchema.component,
      fieldName: props.fieldName,
      fieldType: props.fieldSchema.type,
      availableComponents: Object.keys(componentRegistry)
    })
    // Emit event for parent to handle
    emit('component-fallback', {
      field: props.fieldName,
      component: props.fieldSchema.component
    })
  }

  return comp
})
</script>

<template>
  <component
    v-if="customComponent"
    :is="customComponent"
    v-bind="fieldSchema"
    v-model="modelValue"
  />
  <v-text-field
    v-else-if="fieldSchema.component"
    :label="getFieldLabel() + ' (Component Missing)'"
    v-model="modelValue"
    hint="Using fallback text input"
    persistent-hint
  />
</template>
```

**Warning signs:** User reports "expected autocomplete, got text field", schema defines component but it doesn't render, console shows no warnings.

**Source:** [Vue Component Registration](https://vuejs.org/guide/components/registration), [Vue Error Handling Best Practices](https://vueschool.io/articles/news/master-error-handling-in-a-vue-js-app/)

## Code Examples

Verified patterns from official sources and existing codebase:

### Complete DynamicField with Registry Integration

```vue
<!-- DynamicField.vue -->
<template>
  <div class="dynamic-field">
    <!-- Custom Component from Registry -->
    <component
      v-if="customComponent"
      :is="customComponent"
      :model-value="modelValue"
      v-bind="fieldSchema"
      :required="fieldSchema.required"
      :disabled="disabled"
      @update:model-value="updateValue"
    />

    <!-- Standard Text Field -->
    <v-text-field
      v-else-if="fieldSchema.type === 'string' && !fieldSchema.multiline && !fieldSchema.enum"
      :model-value="modelValue"
      :label="getFieldLabel()"
      :placeholder="fieldSchema.placeholder"
      :variant="variant"
      :rules="getValidationRules()"
      :error-messages="getErrorMessages()"
      :required="fieldSchema.required"
      :disabled="disabled"
      @update:model-value="updateValue"
      @blur="handleBlur"
    />

    <!-- Date Field -->
    <v-text-field
      v-else-if="fieldSchema.type === 'string' && fieldSchema.format === 'date'"
      :model-value="modelValue"
      :label="getFieldLabel()"
      :placeholder="fieldSchema.placeholder || 'YYYY-MM-DD'"
      :variant="variant"
      :rules="getValidationRules()"
      :error-messages="getErrorMessages()"
      :required="fieldSchema.required"
      type="date"
      :disabled="disabled"
      @update:model-value="updateValue"
    />

    <!-- Nested Object -->
    <div v-else-if="fieldSchema.type === 'object' && canRenderNested">
      <v-label class="text-body-2 font-weight-medium mb-2">
        {{ getFieldLabel() }}
        <span v-if="fieldSchema.required" class="text-error ml-1">*</span>
      </v-label>

      <v-card
        variant="outlined"
        :style="getNestedStyle(depth)"
      >
        <v-card-text>
          <v-row>
            <v-col
              v-for="(subFieldSchema, subFieldName) in fieldSchema.properties"
              :key="subFieldName"
              cols="12"
              :sm="Object.keys(fieldSchema.properties).length > 2 ? 6 : 12"
            >
              <DynamicField
                :field-name="subFieldName"
                :field-schema="subFieldSchema"
                :model-value="objectValue[subFieldName]"
                :depth="depth + 1"
                variant="outlined"
                :disabled="disabled"
                @update:model-value="updateObjectField(subFieldName, $event)"
              />
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </div>

    <!-- Array Field -->
    <div v-else-if="fieldSchema.type === 'array' && canRenderNested">
      <v-label class="text-body-2 font-weight-medium mb-2">
        {{ getFieldLabel() }}
        <span v-if="fieldSchema.required" class="text-error ml-1">*</span>
      </v-label>

      <v-card variant="outlined">
        <v-card-text>
          <div v-if="!arrayValue.length" class="text-center py-4 text-medium-emphasis">
            No items added yet
          </div>

          <div v-else>
            <div
              v-for="(item, index) in arrayValue"
              :key="index"
              class="mb-4 pa-4 border rounded"
              :style="getNestedStyle(depth + 1)"
            >
              <div class="d-flex justify-space-between align-center mb-2">
                <h4 class="text-subtitle-2">Item {{ index + 1 }}</h4>
                <v-btn
                  icon="mdi-delete"
                  size="small"
                  color="error"
                  variant="text"
                  :disabled="disabled"
                  @click="removeArrayItem(index)"
                />
              </div>

              <v-row>
                <v-col
                  v-for="(subFieldSchema, subFieldName) in fieldSchema.items?.properties"
                  :key="subFieldName"
                  cols="12"
                  sm="6"
                >
                  <DynamicField
                    :field-name="subFieldName"
                    :field-schema="subFieldSchema"
                    :model-value="item[subFieldName]"
                    :depth="depth + 1"
                    variant="outlined"
                    :disabled="disabled"
                    @update:model-value="updateArrayItem(index, subFieldName, $event)"
                  />
                </v-col>
              </v-row>
            </div>
          </div>

          <v-btn
            color="primary"
            variant="outlined"
            block
            :disabled="disabled"
            @click="addArrayItem"
          >
            <v-icon start>mdi-plus</v-icon>
            Add {{ fieldSchema.itemTitle || 'Item' }}
          </v-btn>
        </v-card-text>
      </v-card>
    </div>

    <!-- Max Depth Warning -->
    <v-alert v-else-if="!canRenderNested" type="warning" density="compact">
      Maximum nesting depth reached ({{ MAX_DEPTH }} levels)
    </v-alert>

    <!-- Unknown Type Fallback -->
    <v-text-field
      v-else
      :model-value="modelValue"
      :label="getFieldLabel() + ' (Unknown Type)'"
      :variant="variant"
      :disabled="disabled"
      :hint="`Field type '${fieldSchema.type}' not recognized`"
      persistent-hint
      @update:model-value="updateValue"
    />

    <!-- Help Text -->
    <div v-if="fieldSchema.description" class="text-caption text-medium-emphasis mt-1">
      {{ fieldSchema.description }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { componentRegistry } from './componentRegistry'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger()

const MAX_DEPTH = 10

const props = defineProps({
  fieldName: { type: String, required: true },
  fieldSchema: { type: Object, required: true },
  modelValue: { type: [String, Number, Boolean, Array, Object], default: null },
  validationResult: { type: Object, default: null },
  variant: { type: String, default: 'filled' },
  disabled: { type: Boolean, default: false },
  depth: { type: Number, default: 0 }
})

const emit = defineEmits(['update:model-value', 'validate', 'component-fallback'])

// Recursion safety
const canRenderNested = computed(() => props.depth < MAX_DEPTH)

// Component registry lookup
const customComponent = computed(() => {
  if (!props.fieldSchema.component) return null

  const comp = componentRegistry[props.fieldSchema.component]

  if (!comp) {
    logger.warn('Component not found in registry', {
      component: props.fieldSchema.component,
      fieldName: props.fieldName,
      availableComponents: Object.keys(componentRegistry)
    })
    emit('component-fallback', {
      field: props.fieldName,
      component: props.fieldSchema.component
    })
  }

  return comp
})

// Nested styling (depth 2+)
function getNestedStyle(depth) {
  if (depth < 2) return {}
  const opacity = Math.min(0.02 + (depth - 2) * 0.01, 0.06)
  return {
    backgroundColor: `rgba(var(--v-theme-surface-variant), ${opacity})`,
    transition: 'background-color 0.2s ease'
  }
}

// Array/Object local state
const arrayValue = ref(Array.isArray(props.modelValue) ? [...props.modelValue] : [])
const objectValue = ref(
  props.modelValue && typeof props.modelValue === 'object' && !Array.isArray(props.modelValue)
    ? { ...props.modelValue }
    : {}
)

// Watch external changes
watch(
  () => props.modelValue,
  newValue => {
    if (props.fieldSchema.type === 'array' && Array.isArray(newValue)) {
      arrayValue.value = [...newValue]
    } else if (props.fieldSchema.type === 'object' && newValue && typeof newValue === 'object') {
      objectValue.value = { ...newValue }
    }
  }
)

// Field label generation
const getFieldLabel = () => {
  return (
    props.fieldSchema.title ||
    props.fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  )
}

// Validation rules (client-side hints)
const getValidationRules = () => {
  const rules = []

  if (props.fieldSchema.required) {
    rules.push(value => {
      if (value === null || value === undefined || value === '') {
        return `${getFieldLabel()} is required`
      }
      return true
    })
  }

  if (props.fieldSchema.minLength) {
    rules.push(value => {
      if (value && value.length < props.fieldSchema.minLength) {
        return `Must be at least ${props.fieldSchema.minLength} characters`
      }
      return true
    })
  }

  if (props.fieldSchema.format === 'email') {
    rules.push(value => {
      if (value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        return 'Invalid email format'
      }
      return true
    })
  }

  return rules
}

// Backend validation errors
const getErrorMessages = () => {
  if (props.validationResult?.errors) {
    return props.validationResult.errors.map(error => error.message)
  }
  return []
}

// Event handlers
const updateValue = value => {
  emit('update:model-value', value)
}

const handleBlur = event => {
  emit('validate', event.target.value)
}

// Array operations
const addArrayItem = () => {
  const newItem = {}
  if (props.fieldSchema.items?.properties) {
    Object.keys(props.fieldSchema.items.properties).forEach(key => {
      const subSchema = props.fieldSchema.items.properties[key]
      newItem[key] = subSchema.default ?? (
        subSchema.type === 'string' ? '' :
        subSchema.type === 'number' || subSchema.type === 'integer' ? 0 :
        subSchema.type === 'boolean' ? false : null
      )
    })
  }
  arrayValue.value.push(newItem)
  emit('update:model-value', arrayValue.value)
}

const removeArrayItem = index => {
  arrayValue.value.splice(index, 1)
  emit('update:model-value', arrayValue.value)
}

const updateArrayItem = (index, fieldName, value) => {
  arrayValue.value[index][fieldName] = value
  emit('update:model-value', arrayValue.value)
}

// Object operations
const updateObjectField = (fieldName, value) => {
  objectValue.value[fieldName] = value
  emit('update:model-value', objectValue.value)
}
</script>

<style scoped>
.dynamic-field {
  width: 100%;
}

.border {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
```

**Source:** Existing Gene Curator codebase with enhancements based on research patterns

### Autocomplete Component Pattern (with Debounce)

```vue
<!-- Example: MONDOAutocomplete.vue pattern -->
<script setup>
import { ref, computed } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { useLogger } from '@/composables/useLogger'
import { ontologyAPI } from '@/api'

const logger = useLogger()

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: 'MONDO Disease' },
  required: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  minSearchLength: { type: Number, default: 2 },
  maxResults: { type: Number, default: 15 }
})

const emit = defineEmits(['update:modelValue', 'select'])

const searchQuery = ref('')
const searchResults = ref([])
const isSearching = ref(false)
const selectedItem = ref(null)

async function performSearch(query) {
  if (!query || query.length < props.minSearchLength) {
    searchResults.value = []
    return
  }

  isSearching.value = true
  try {
    const response = await ontologyAPI.searchMONDO(query, props.maxResults)
    searchResults.value = response.results.map(r => ({
      ...r,
      displayText: `${r.label} (${r.mondo_id})`
    }))
    logger.debug('MONDO search complete', {
      query,
      results: response.results.length
    })
  } catch (e) {
    logger.error('MONDO search error', { query, error: e.message })
    searchResults.value = []
  } finally {
    isSearching.value = false
  }
}

// 300ms debounce - tested default from @vueuse/core
const debouncedSearch = useDebounceFn(performSearch, 300)

function handleSearch(query) {
  if (query && query !== selectedItem.value?.label) {
    debouncedSearch(query)
  }
}

function handleSelect(item) {
  if (item) {
    selectedItem.value = item
    emit('update:modelValue', item.mondo_id)
    emit('select', item)
    logger.info('MONDO term selected', { mondo_id: item.mondo_id })
  } else {
    selectedItem.value = null
    emit('update:modelValue', '')
    emit('select', null)
  }
}

const errorMessages = computed(() => {
  if (props.required && !props.modelValue) {
    return ['MONDO disease is required']
  }
  return []
})
</script>

<template>
  <v-autocomplete
    v-model="selectedItem"
    v-model:search="searchQuery"
    :items="searchResults"
    :loading="isSearching"
    :label="label"
    :error-messages="errorMessages"
    :required="required"
    :disabled="disabled"
    item-title="displayText"
    item-value="mondo_id"
    variant="outlined"
    no-filter
    return-object
    @update:search="handleSearch"
    @update:model-value="handleSelect"
  >
    <template #no-data>
      <v-list-item v-if="searchQuery && searchQuery.length >= minSearchLength">
        <v-list-item-title>
          <span v-if="isSearching">Searching...</span>
          <span v-else>No results for "{{ searchQuery }}"</span>
        </v-list-item-title>
      </v-list-item>
      <v-list-item v-else>
        <v-list-item-title class="text-medium-emphasis">
          Type at least {{ minSearchLength }} characters to search
        </v-list-item-title>
      </v-list-item>
    </template>
  </v-autocomplete>
</template>
```

**Source:** Existing Gene Curator MONDOAutocomplete.vue with @vueuse/core patterns from [Vue 3 Autocomplete Composable Guide](https://runthatline.com/vue-3-autocomplete-how-to-build-a-reusable-composable/)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Options API component registration | `<script setup>` with direct imports | Vue 3.2+ (2021) | No explicit `components: {}` needed, cleaner code |
| `props` + `emit('input')` | `defineModel()` macro | Vue 3.4+ (2024) | Simpler two-way binding, less boilerplate |
| Manual debounce with setTimeout | `useDebounceFn` from @vueuse/core | @vueuse/core 10+ (2023) | Automatic cleanup, cancellation, better DX |
| Vue.set() for reactivity | Proxy-based deep reactivity | Vue 3.0 (2020) | No special syntax, works with nested objects/arrays |
| Global component registration | Tree-shakeable local registration | Vue 3 best practices (2021+) | Smaller bundles, better maintainability |
| String template refs | Composition API refs | Vue 3.0 (2020) | Type-safe, works with `<script setup>` |

**Deprecated/outdated:**
- **Options API for new components:** Still supported but Composition API is recommended for better logic reuse and TypeScript support
- **Manual array reactivity workarounds (Vue.set):** Removed in Vue 3, direct array mutations now reactive
- **Component naming prefix requirements (app-):** No longer enforced, use PascalCase for clarity

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal debounce timing for slow networks**
   - What we know: 300ms is standard for fast APIs (Europe PMC, MONDO)
   - What's unclear: Should debounce adjust based on detected network speed?
   - Recommendation: Start with 300ms, monitor performance metrics, consider adaptive debounce if users report lag (e.g., increase to 500ms if API response time > 2 seconds)

2. **Component registry scaling beyond 10 components**
   - What we know: 5 components work well with eager loading
   - What's unclear: At what point does eager loading impact initial bundle size?
   - Recommendation: Monitor bundle size. If registry grows beyond 15 components OR total component code exceeds 100KB, consider lazy loading with `defineAsyncComponent`

3. **Nested depth limit for real-world schemas**
   - What we know: MAX_DEPTH=10 is conservative, ClinGen schema reaches depth 3-4
   - What's unclear: Are there legitimate use cases for depth > 10?
   - Recommendation: Keep MAX_DEPTH=10, log warning at depth 7+ to identify schemas needing restructuring. If legitimate deep nesting found, increase to 15 with performance testing.

## Sources

### Primary (HIGH confidence)
- [Vue.js Component Registration](https://vuejs.org/guide/components/registration) - Official Vue 3 docs on local/global registration patterns
- [Vue.js Component v-model](https://vuejs.org/guide/components/v-model.html) - Official guide on defineModel() and two-way binding
- [Vue.js Reactivity Fundamentals](https://vuejs.org/guide/essentials/reactivity-fundamentals) - Deep reactivity with Proxy
- [Vuetify 3 Validation Rules](https://vuetifyjs.com/features/rules/) - Official validation patterns
- [Vuetify 3 Text Fields](https://vuetifyjs.com/en/components/text-fields/) - Component props and API
- Existing Gene Curator codebase - DynamicForm.vue, DynamicField.vue, specialized components (verified implementations)

### Secondary (MEDIUM confidence)
- [Building Dynamic Forms in Vue 3 (Medium)](https://medium.com/@natalia.afanaseva/building-a-dynamic-form-in-vue-3-with-nested-fields-conditions-and-validation-a096bb69219f) - Nested field patterns verified against official docs
- [Recursive Components in Vue 3 (Medium)](https://michael-verschoof.medium.com/recursive-components-in-vue-3-e897643df82) - Self-reference patterns, cross-verified with Vue.js edge cases guide
- [Vue 3 Autocomplete Composable (RunThatLine)](https://runthatline.com/vue-3-autocomplete-how-to-build-a-reusable-composable/) - Debounce patterns using @vueuse/core
- [Vue 3 Performance Pitfalls (Medium, Dec 2025)](https://medium.com/simform-engineering/7-vue-3-performance-pitfalls-that-quietly-derail-your-app-33c7180d68d4) - Prop passing performance, verified with multiple sources
- [Using Vuetify Native Validation (Medium)](https://medium.com/@carlos.henrique.sa.filho/using-vuetify-2-3-native-validation-rules-the-right-way-138f9a974a49) - Rules implementation patterns

### Tertiary (LOW confidence - requires validation)
- Community discussions on recursive depth limits (GitHub Issues, forum threads) - No official guidance, based on empirical testing
- @moirei/vuetify-dynamic-form library - Alternative approach, not using due to existing implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries installed, versions verified in package.json, patterns from official docs
- Architecture: HIGH - Patterns verified in existing codebase (DynamicForm, specialized components) and official Vue 3/Vuetify 3 documentation
- Component registry: HIGH - Standard Vue pattern, verified in multiple sources and existing codebase structure
- Recursion patterns: HIGH - Official Vue documentation + existing DynamicField implementation + verified community examples
- Pitfalls: MEDIUM-HIGH - Recursive depth and performance issues verified in Vue GitHub issues; prop mutation and array reactivity from official docs; component registry mismatches from existing code patterns

**Research date:** 2026-01-22
**Valid until:** 60 days (stable ecosystem - Vue 3.4, Vuetify 3.9, patterns unlikely to change rapidly)
