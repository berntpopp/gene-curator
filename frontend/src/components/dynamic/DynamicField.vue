<template>
  <div class="dynamic-field">
    <!-- Custom Component from Registry -->
    <component
      :is="customComponent"
      v-if="customComponent"
      :model-value="modelValue"
      :label="fieldSchema.title || fieldSchema.label || getFieldLabel()"
      :hint="fieldSchema.description || fieldSchema.hint"
      :required="fieldSchema.required"
      :disabled="disabled"
      @update:model-value="updateValue"
    />

    <!-- Text Fields -->
    <v-text-field
      v-else-if="
        fieldSchema.type === 'string' &&
        !fieldSchema.multiline &&
        !fieldSchema.enum &&
        fieldSchema.format !== 'date'
      "
      :model-value="modelValue"
      :label="getFieldLabel()"
      :placeholder="fieldSchema.placeholder"
      :variant="variant"
      :rules="validationRules"
      :error-messages="getErrorMessages()"
      :required="fieldSchema.required"
      :disabled="disabled"
      :hint="needsHintTruncation ? undefined : fieldSchema.hint"
      :persistent-hint="hasHint && !needsHintTruncation"
      @update:model-value="updateValue"
      @blur="handleBlur"
    >
      <template v-if="hasIcon" #prepend-inner>
        <v-tooltip location="top" :open-delay="250" :disabled="!hasTooltip">
          <template #activator="{ props: tooltipProps }">
            <v-icon v-bind="tooltipProps" :icon="iconName" color="grey-darken-1" size="small" />
          </template>
          <span>{{ fieldSchema.tooltip }}</span>
        </v-tooltip>
      </template>

      <template v-if="hasHelpUrl" #append-inner>
        <v-icon
          icon="mdi-help-circle-outline"
          color="primary"
          size="small"
          style="cursor: pointer"
          @click.stop="openHelpUrl"
        />
      </template>

      <template v-if="needsHintTruncation" #details>
        <div class="text-body-small text-medium-emphasis">
          <span v-if="!hintExpanded">
            {{ truncatedHint }}
            <a
              class="text-primary ml-1"
              style="cursor: pointer"
              @click.prevent="hintExpanded = true"
            >
              show more
            </a>
          </span>
          <span v-else>
            {{ fieldSchema.hint }}
            <a
              class="text-primary ml-1"
              style="cursor: pointer"
              @click.prevent="hintExpanded = false"
            >
              show less
            </a>
          </span>
        </div>
      </template>
    </v-text-field>

    <!-- Textarea Fields -->
    <v-textarea
      v-else-if="fieldSchema.type === 'string' && fieldSchema.multiline"
      :model-value="modelValue"
      :label="getFieldLabel()"
      :placeholder="fieldSchema.placeholder"
      :variant="variant"
      :rules="validationRules"
      :error-messages="getErrorMessages()"
      :required="fieldSchema.required"
      :rows="fieldSchema.rows || 3"
      :disabled="disabled"
      :hint="needsHintTruncation ? undefined : fieldSchema.hint"
      :persistent-hint="hasHint && !needsHintTruncation"
      @update:model-value="updateValue"
      @blur="handleBlur"
    >
      <template v-if="hasIcon" #prepend-inner>
        <v-tooltip location="top" :open-delay="250" :disabled="!hasTooltip">
          <template #activator="{ props: tooltipProps }">
            <v-icon v-bind="tooltipProps" :icon="iconName" color="grey-darken-1" size="small" />
          </template>
          <span>{{ fieldSchema.tooltip }}</span>
        </v-tooltip>
      </template>

      <template v-if="hasHelpUrl" #append-inner>
        <v-icon
          icon="mdi-help-circle-outline"
          color="primary"
          size="small"
          style="cursor: pointer"
          @click.stop="openHelpUrl"
        />
      </template>

      <template v-if="needsHintTruncation" #details>
        <div class="text-body-small text-medium-emphasis">
          <span v-if="!hintExpanded">
            {{ truncatedHint }}
            <a
              class="text-primary ml-1"
              style="cursor: pointer"
              @click.prevent="hintExpanded = true"
            >
              show more
            </a>
          </span>
          <span v-else>
            {{ fieldSchema.hint }}
            <a
              class="text-primary ml-1"
              style="cursor: pointer"
              @click.prevent="hintExpanded = false"
            >
              show less
            </a>
          </span>
        </div>
      </template>
    </v-textarea>

    <!-- Select Fields -->
    <v-select
      v-else-if="fieldSchema.type === 'string' && fieldSchema.enum"
      :model-value="modelValue"
      :items="getSelectItems()"
      :label="getFieldLabel()"
      :placeholder="fieldSchema.placeholder"
      :variant="variant"
      :rules="validationRules"
      :error-messages="getErrorMessages()"
      :required="fieldSchema.required"
      :clearable="!fieldSchema.required"
      :disabled="disabled"
      :hint="needsHintTruncation ? undefined : fieldSchema.hint"
      :persistent-hint="hasHint && !needsHintTruncation"
      @update:model-value="updateValue"
    >
      <template v-if="hasIcon" #prepend-inner>
        <v-tooltip location="top" :open-delay="250" :disabled="!hasTooltip">
          <template #activator="{ props: tooltipProps }">
            <v-icon v-bind="tooltipProps" :icon="iconName" color="grey-darken-1" size="small" />
          </template>
          <span>{{ fieldSchema.tooltip }}</span>
        </v-tooltip>
      </template>

      <template v-if="hasHelpUrl" #append-inner>
        <v-icon
          icon="mdi-help-circle-outline"
          color="primary"
          size="small"
          style="cursor: pointer"
          @click.stop="openHelpUrl"
        />
      </template>

      <template v-if="needsHintTruncation" #details>
        <div class="text-body-small text-medium-emphasis">
          <span v-if="!hintExpanded">
            {{ truncatedHint }}
            <a
              class="text-primary ml-1"
              style="cursor: pointer"
              @click.prevent="hintExpanded = true"
            >
              show more
            </a>
          </span>
          <span v-else>
            {{ fieldSchema.hint }}
            <a
              class="text-primary ml-1"
              style="cursor: pointer"
              @click.prevent="hintExpanded = false"
            >
              show less
            </a>
          </span>
        </div>
      </template>
    </v-select>

    <!-- Number Fields -->
    <v-text-field
      v-else-if="fieldSchema.type === 'number' || fieldSchema.type === 'integer'"
      :model-value="modelValue"
      :label="getFieldLabel()"
      :placeholder="fieldSchema.placeholder"
      :variant="variant"
      :rules="validationRules"
      :error-messages="getErrorMessages()"
      :required="fieldSchema.required"
      type="number"
      :min="fieldSchema.minimum"
      :max="fieldSchema.maximum"
      :step="fieldSchema.type === 'integer' ? 1 : fieldSchema.step || 0.1"
      :disabled="disabled"
      :hint="needsHintTruncation ? undefined : fieldSchema.hint"
      :persistent-hint="hasHint && !needsHintTruncation"
      @update:model-value="updateValue"
      @blur="handleBlur"
    >
      <template v-if="hasIcon" #prepend-inner>
        <v-tooltip location="top" :open-delay="250" :disabled="!hasTooltip">
          <template #activator="{ props: tooltipProps }">
            <v-icon v-bind="tooltipProps" :icon="iconName" color="grey-darken-1" size="small" />
          </template>
          <span>{{ fieldSchema.tooltip }}</span>
        </v-tooltip>
      </template>

      <template v-if="hasHelpUrl" #append-inner>
        <v-icon
          icon="mdi-help-circle-outline"
          color="primary"
          size="small"
          style="cursor: pointer"
          @click.stop="openHelpUrl"
        />
      </template>

      <template v-if="needsHintTruncation" #details>
        <div class="text-body-small text-medium-emphasis">
          <span v-if="!hintExpanded">
            {{ truncatedHint }}
            <a
              class="text-primary ml-1"
              style="cursor: pointer"
              @click.prevent="hintExpanded = true"
            >
              show more
            </a>
          </span>
          <span v-else>
            {{ fieldSchema.hint }}
            <a
              class="text-primary ml-1"
              style="cursor: pointer"
              @click.prevent="hintExpanded = false"
            >
              show less
            </a>
          </span>
        </div>
      </template>
    </v-text-field>

    <!-- Boolean Fields -->
    <div v-else-if="fieldSchema.type === 'boolean'" class="d-flex align-center">
      <v-tooltip v-if="hasIcon" location="top" :open-delay="250" :disabled="!hasTooltip">
        <template #activator="{ props: tooltipProps }">
          <v-icon
            v-bind="tooltipProps"
            :icon="iconName"
            color="grey-darken-1"
            size="small"
            class="mr-2"
          />
        </template>
        <span>{{ fieldSchema.tooltip }}</span>
      </v-tooltip>
      <v-checkbox
        :model-value="modelValue"
        :label="getFieldLabel()"
        :rules="validationRules"
        :error-messages="getErrorMessages()"
        :disabled="disabled"
        :hint="fieldSchema.hint"
        :persistent-hint="hasHint"
        hide-details="auto"
        @update:model-value="updateValue"
      />
      <v-icon
        v-if="hasHelpUrl"
        icon="mdi-help-circle-outline"
        color="primary"
        size="small"
        class="ml-2"
        style="cursor: pointer"
        @click.stop="openHelpUrl"
      />
    </div>

    <!-- Date Fields -->
    <v-text-field
      v-else-if="fieldSchema.type === 'string' && fieldSchema.format === 'date'"
      :model-value="modelValue"
      :label="getFieldLabel()"
      :placeholder="fieldSchema.placeholder || 'YYYY-MM-DD'"
      :variant="variant"
      :rules="validationRules"
      :error-messages="getErrorMessages()"
      :required="fieldSchema.required"
      type="date"
      :disabled="disabled"
      :hint="needsHintTruncation ? undefined : fieldSchema.hint"
      :persistent-hint="hasHint && !needsHintTruncation"
      @update:model-value="updateValue"
      @blur="handleBlur"
    >
      <template v-if="hasIcon" #prepend-inner>
        <v-tooltip location="top" :open-delay="250" :disabled="!hasTooltip">
          <template #activator="{ props: tooltipProps }">
            <v-icon v-bind="tooltipProps" :icon="iconName" color="grey-darken-1" size="small" />
          </template>
          <span>{{ fieldSchema.tooltip }}</span>
        </v-tooltip>
      </template>

      <template v-if="hasHelpUrl" #append-inner>
        <v-icon
          icon="mdi-help-circle-outline"
          color="primary"
          size="small"
          style="cursor: pointer"
          @click.stop="openHelpUrl"
        />
      </template>

      <template v-if="needsHintTruncation" #details>
        <div class="text-body-small text-medium-emphasis">
          <span v-if="!hintExpanded">
            {{ truncatedHint }}
            <a
              class="text-primary ml-1"
              style="cursor: pointer"
              @click.prevent="hintExpanded = true"
            >
              show more
            </a>
          </span>
          <span v-else>
            {{ fieldSchema.hint }}
            <a
              class="text-primary ml-1"
              style="cursor: pointer"
              @click.prevent="hintExpanded = false"
            >
              show less
            </a>
          </span>
        </div>
      </template>
    </v-text-field>

    <!-- Object and Array Fields (rendered recursively) -->
    <DynamicNestedField
      v-else-if="(fieldSchema.type === 'array' || fieldSchema.type === 'object') && canRenderNested"
      :field-schema="fieldSchema"
      :label="getFieldLabel()"
      :model-value="modelValue"
      :depth="depth"
      :disabled="disabled"
      :error-messages="getErrorMessages()"
      @update:model-value="emit('update:model-value', $event)"
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
      :disabled="disabled"
      @update:model-value="updateValue"
    />

    <!-- Help Text -->
    <div
      v-if="fieldSchema.description && !fieldSchema.hint"
      class="text-body-small text-medium-emphasis mt-1"
    >
      {{ fieldSchema.description }}
    </div>
  </div>
</template>

<script setup lang="ts">
  import { ref, computed, type Component } from 'vue'
  import { componentRegistry } from './componentRegistry'
  import { humanize } from './fieldLabels'
  import { useLogger } from '@/composables/useLogger'
  import { useValidationRules } from './composables/useValidationRules'
  import DynamicNestedField from './DynamicNestedField.vue'
  import type { ComponentFallbackEvent, FieldSchema, FieldValidation, FieldVariant } from './types'

  const logger = useLogger()

  /**
   * Maximum recursion depth for nested object/array fields.
   * Prevents infinite recursion and stack overflow.
   */
  const MAX_DEPTH = 10

  /**
   * Maximum hint length before truncation with show more/less toggle
   */
  const HINT_TRUNCATE_LENGTH = 100

  const props = withDefaults(
    defineProps<{
      fieldName: string
      fieldSchema: FieldSchema
      modelValue?: unknown
      validationResult?: FieldValidation | null
      backendErrors?: string[]
      variant?: FieldVariant
      disabled?: boolean
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
    validate: [value: unknown]
    'component-fallback': [payload: ComponentFallbackEvent]
    'clear-backend-error': []
  }>()

  const hintExpanded = ref(false)

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

  /**
   * Check if nested rendering is allowed based on current depth.
   * Prevents infinite recursion by stopping at MAX_DEPTH.
   */
  const canRenderNested = computed(() => props.depth < MAX_DEPTH)

  /**
   * Show icon in prepend slot when icon OR tooltip defined
   */
  const hasIcon = computed(() => !!(props.fieldSchema.icon || props.fieldSchema.tooltip))

  /**
   * Get icon name, defaulting to info icon when tooltip exists without icon
   */
  const iconName = computed(() => props.fieldSchema.icon || 'mdi-information-outline')

  /**
   * Check if hint exists and is non-empty
   */
  const hasHint = computed(
    () => !!props.fieldSchema.hint && props.fieldSchema.hint.trim().length > 0
  )

  /**
   * Check if hint needs truncation
   */
  const needsHintTruncation = computed(
    () => hasHint.value && props.fieldSchema.hint!.length > HINT_TRUNCATE_LENGTH
  )

  /**
   * Get truncated hint text
   */
  const truncatedHint = computed(() =>
    needsHintTruncation.value
      ? `${props.fieldSchema.hint!.substring(0, HINT_TRUNCATE_LENGTH)}...`
      : props.fieldSchema.hint
  )

  /**
   * Check if tooltip exists and is non-empty
   */
  const hasTooltip = computed(
    () => !!props.fieldSchema.tooltip && props.fieldSchema.tooltip.trim().length > 0
  )

  /**
   * Check if helpUrl exists and is valid URL
   */
  const hasHelpUrl = computed(
    () =>
      !!props.fieldSchema.helpUrl &&
      (props.fieldSchema.helpUrl.startsWith('http://') ||
        props.fieldSchema.helpUrl.startsWith('https://'))
  )

  const getFieldLabel = (): string => {
    return (
      props.fieldSchema.title ||
      props.fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    )
  }

  // Initialize validation rules from composable
  const { validationRules } = useValidationRules(() => props.fieldSchema)

  // Lowercase raw values ('mitochondrial', 'lump/split/undecided') read as labels; mixed case ('AD') is kept
  const optionTitle = (value: unknown): unknown =>
    typeof value === 'string' && /^[a-z0-9]+([_/ -][a-z0-9]+)*$/.test(value)
      ? humanize(value)
      : value

  const getSelectItems = (): Array<{ title: unknown; value: unknown }> => {
    const options = props.fieldSchema.enumOptions
    if (options) {
      return options.map(option => {
        if (typeof option === 'string') return { title: optionTitle(option), value: option }
        return {
          title: option.label || optionTitle(option.value) || option,
          value: option.value || option
        }
      })
    }

    return props.fieldSchema.enum?.map(value => ({ title: optionTitle(value), value })) || []
  }

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
    emit('update:model-value', value)
    emit('clear-backend-error') // Signal to parent to clear backend error
  }

  const handleBlur = (event: FocusEvent) => {
    emit('validate', (event.target as HTMLInputElement).value)
  }

  /**
   * Open help URL in new tab with security flags
   */
  const openHelpUrl = () => {
    if (!props.fieldSchema.helpUrl) {
      logger.warn('Help URL not defined', { fieldName: props.fieldName })
      return
    }
    window.open(props.fieldSchema.helpUrl, '_blank', 'noopener,noreferrer')
    logger.info('Help documentation opened', {
      fieldName: props.fieldName,
      helpUrl: props.fieldSchema.helpUrl
    })
  }
</script>

<style scoped>
  .dynamic-field {
    width: 100%;
  }
</style>
