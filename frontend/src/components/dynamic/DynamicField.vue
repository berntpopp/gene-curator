<template>
  <div class="dynamic-field">
    <ReadonlyValue
      v-if="readonly && !typeEditor && !(fieldSchema.properties || fieldSchema.items?.properties)"
      :schema="fieldSchema"
      :model-value="modelValue"
      :label="getFieldLabel()"
    />
    <!-- Custom Component from Registry -->
    <component
      :is="customComponent"
      v-else-if="customComponent"
      :model-value="modelValue"
      :label="fieldSchema.title || fieldSchema.label || getFieldLabel()"
      :hint="fieldSchema.description || fieldSchema.hint"
      :required="fieldSchema.required"
      :disabled="isDisabled"
      @update:model-value="updateValue"
      @update:disease-name="emit('update:disease-name', $event)"
    />

    <FieldInput
      v-else-if="inputKind"
      :kind="inputKind"
      :field-name="fieldName"
      :field-schema="fieldSchema"
      :model-value="modelValue"
      :label="getFieldLabel()"
      :variant="variant"
      :rules="validationRules"
      :error-messages="getErrorMessages()"
      :disabled="isDisabled"
      @update:model-value="updateValue"
      @blur="handleBlur"
    />

    <!-- List values: multiselect picks options; an array without item fields takes typed entries -->
    <component
      :is="fieldSchema.enum ? VSelect : VCombobox"
      v-else-if="isList"
      :model-value="modelValue ?? []"
      :items="listItems"
      :label="getFieldLabel()"
      :variant="variant"
      :hint="fieldSchema.hint"
      :persistent-hint="!!fieldSchema.hint"
      :rules="validationRules"
      :error-messages="getErrorMessages()"
      :disabled="isDisabled"
      multiple
      chips
      closable-chips
      @update:model-value="updateValue"
    />

    <!-- Registry editor for the field type (evidence_table) -->
    <component
      :is="typeEditor"
      v-else-if="typeEditor"
      :field-schema="fieldSchema"
      :label="getFieldLabel()"
      :model-value="modelValue"
      :disabled="isDisabled"
      :readonly="readonly"
      :error-messages="getErrorMessages()"
      @update:model-value="updateValue"
    />

    <!-- Object and Array Fields (rendered recursively) -->
    <DynamicNestedField
      v-else-if="(fieldSchema.type === 'array' || fieldSchema.type === 'object') && canRenderNested"
      :field-schema="fieldSchema"
      :label="getFieldLabel()"
      :model-value="modelValue"
      :depth="depth"
      :disabled="isDisabled"
      :readonly="readonly"
      :error-messages="getErrorMessages()"
      @update:model-value="!readonly && emit('update:model-value', $event)"
      @component-fallback="emit('component-fallback', $event)"
    />

    <!-- Max Depth Warning for Nested Types -->
    <v-alert
      v-else-if="
        !canRenderNested && (fieldSchema.type === 'object' || fieldSchema.type === 'array')
      "
      type="warning"
      density="compact"
    >
      Maximum nesting depth reached ({{ MAX_DEPTH }} levels)
    </v-alert>

    <!-- Fallback for unsupported types -->
    <v-text-field
      v-else
      :model-value="modelValue"
      :label="getFieldLabel() + ' (Unknown Type: ' + fieldSchema.type + ')'"
      :variant="variant"
      :hint="'Field type not recognized - using text input'"
      persistent-hint
      :disabled="isDisabled"
      @update:model-value="updateValue"
    />

    <!-- Help Text -->
    <div
      v-if="fieldSchema.description && !fieldSchema.hint && !typeEditor"
      class="text-body-small text-medium-emphasis mt-1"
    >
      {{ fieldSchema.description }}
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, type Component } from 'vue'
  import { VCombobox, VSelect } from 'vuetify/components'
  import { componentRegistry, fieldTypes } from './componentRegistry'
  import { useLogger } from '@/composables/useLogger'
  import { useValidationRules } from './composables/useValidationRules'
  import DynamicNestedField from './DynamicNestedField.vue'
  import ReadonlyValue from './ReadonlyValue.vue'
  import FieldInput, { type FieldInputKind } from './FieldInput.vue'
  import type { ComponentFallbackEvent, FieldSchema, FieldValidation, FieldVariant } from './types'

  const logger = useLogger()

  // Bound nested recursion to prevent infinite recursion and stack overflow.
  const MAX_DEPTH = 10

  const props = withDefaults(
    defineProps<{
      fieldName: string
      fieldSchema: FieldSchema
      modelValue?: unknown
      validationResult?: FieldValidation | null
      backendErrors?: string[]
      variant?: FieldVariant
      disabled?: boolean
      readonly?: boolean
      depth?: number
    }>(),
    {
      modelValue: undefined,
      validationResult: null,
      backendErrors: () => [],
      variant: 'filled',
      disabled: false,
      depth: 0
    }
  )

  const emit = defineEmits<{
    'update:model-value': [value: unknown]
    'update:disease-name': [name: string] // MONDOAutocomplete's label for the picked term
    validate: [value: unknown]
    'component-fallback': [payload: ComponentFallbackEvent]
    'clear-backend-error': []
  }>()

  /**
   * Lookup custom component from registry when fieldSchema.component is specified.
   * Logs warning and emits component-fallback event when component not found.
   */
  const customComponent = computed<Component | undefined>(() => {
    if (!props.fieldSchema.component) return undefined

    const comp = componentRegistry[props.fieldSchema.component]

    if (!comp) {
      logger.warn('Component not found in registry', {
        component: props.fieldSchema.component,
        fieldName: props.fieldName,
        availableComponents: Object.keys(componentRegistry)
      })
      // Emit fallback event when component specified but not found
      emit('component-fallback', {
        requestedComponent: props.fieldSchema.component,
        fieldName: props.fieldName,
        fallbackType: 'text-field'
      })
    }

    return comp
  })

  /** Scalar kind rendered by FieldInput; null for nested, editor and unknown types */
  const inputKind = computed<FieldInputKind | null>(() => {
    const s = props.fieldSchema
    if (s.type === 'boolean') return 'boolean'
    if (s.type === 'number' || s.type === 'integer') return 'number'
    if (s.type !== 'string') return null
    return s.multiline ? 'textarea' : s.enum ? 'select' : s.format === 'date' ? 'date' : 'text'
  })

  const isList = computed(
    () =>
      props.fieldSchema.type === 'multiselect' ||
      (props.fieldSchema.type === 'array' && !props.fieldSchema.items)
  )
  const listItems = computed(() =>
    (props.fieldSchema.enumOptions ?? props.fieldSchema.enum ?? []).map(o =>
      typeof o === 'object' ? { title: o.label ?? o.value, value: o.value } : { title: o, value: o }
    )
  )

  const typeEditor = computed(() => fieldTypes[props.fieldSchema.type ?? '']?.editor)
  const isDisabled = computed(
    () => props.disabled || props.readonly || !!props.fieldSchema.readOnly
  )

  /**
   * Check if nested rendering is allowed based on current depth.
   * Prevents infinite recursion by stopping at MAX_DEPTH.
   */
  const canRenderNested = computed(() => props.depth < MAX_DEPTH)

  const getFieldLabel = (): string => {
    return (
      props.fieldSchema.title ||
      props.fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    )
  }

  // Initialize validation rules from composable
  const { validationRules } = useValidationRules(() => props.fieldSchema)

  const getErrorMessages = (): string[] => {
    // Backend errors passed via prop (from DynamicForm)
    if (props.backendErrors && props.backendErrors.length > 0) {
      return props.backendErrors
    }

    // Fallback to validationResult (existing pattern)
    if (props.validationResult?.errors) {
      return props.validationResult.errors.map(error => error.message)
    }
    return []
  }

  const updateValue = (value: unknown) => {
    if (props.readonly) return
    emit('update:model-value', value)
    emit('clear-backend-error') // Signal to parent to clear backend error
  }

  const handleBlur = (event: FocusEvent) => {
    emit('validate', (event.target as HTMLInputElement).value)
  }
</script>

<style scoped>
  .dynamic-field {
    width: 100%;
    min-width: 0;
    max-width: 100%;
  }
</style>
