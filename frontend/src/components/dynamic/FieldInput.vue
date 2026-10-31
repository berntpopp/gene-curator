<template>
  <!-- Boolean Fields -->
  <div v-if="kind === 'boolean'" class="d-flex align-center">
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
    <!-- A required boolean must be answered and No is an answer: Yes / No, not a checkbox (monkey B14) -->
    <v-radio-group
      v-if="fieldSchema.required"
      :model-value="modelValue"
      :label="label"
      :rules="rules"
      :error-messages="errorMessages"
      :disabled="disabled"
      :hint="fieldSchema.hint"
      :persistent-hint="hasHint"
      inline
      hide-details="auto"
      @update:model-value="emit('update:model-value', $event)"
    >
      <v-radio label="Yes" :value="true" />
      <v-radio label="No" :value="false" />
    </v-radio-group>
    <v-checkbox
      v-else
      :model-value="modelValue"
      :label="label"
      :rules="rules"
      :error-messages="errorMessages"
      :disabled="disabled"
      :hint="fieldSchema.hint"
      :persistent-hint="hasHint"
      hide-details="auto"
      @update:model-value="emit('update:model-value', $event)"
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

  <!-- Text, textarea, select, number and date share one control with the same adornments -->
  <component
    :is="control"
    v-else
    v-bind="kindProps"
    :model-value="modelValue"
    :label="label"
    :variant="variant"
    :rules="rules"
    :error-messages="errorMessages"
    :required="fieldSchema.required"
    :disabled="disabled"
    :hint="needsHintTruncation ? undefined : fieldSchema.hint"
    :persistent-hint="hasHint && !needsHintTruncation"
    @update:model-value="emit('update:model-value', $event)"
    v-on="kind === 'select' ? {} : { blur: (e: FocusEvent) => emit('blur', e) }"
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
          <a class="text-primary ml-1" style="cursor: pointer" @click.prevent="hintExpanded = true">
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
  </component>
</template>

<script setup lang="ts">
  /**
   * The scalar inputs of the schema-driven form (text, textarea, select, number, date,
   * boolean) with their icon/tooltip, help link and long-hint toggle. DynamicField picks
   * the kind and owns validation and events.
   */
  import { computed, ref } from 'vue'
  import { VSelect, VTextField, VTextarea } from 'vuetify/components'
  import { humanize } from './fieldLabels'
  import { useLogger } from '@/composables/useLogger'
  import type { FieldSchema, FieldVariant } from './types'
  import type { ValidationRule } from './composables/useValidationRules'

  export type FieldInputKind = 'text' | 'textarea' | 'select' | 'number' | 'date' | 'boolean'

  /** Maximum hint length before truncation with show more/less toggle */
  const HINT_TRUNCATE_LENGTH = 100

  const props = defineProps<{
    kind: FieldInputKind
    fieldName: string
    fieldSchema: FieldSchema
    modelValue?: unknown
    label: string
    variant: FieldVariant
    rules: ValidationRule[]
    errorMessages: string[]
    disabled: boolean
  }>()

  const emit = defineEmits<{
    'update:model-value': [value: unknown]
    blur: [event: FocusEvent]
  }>()

  const logger = useLogger()
  const hintExpanded = ref(false)

  const control = computed(() =>
    props.kind === 'textarea' ? VTextarea : props.kind === 'select' ? VSelect : VTextField
  )

  const kindProps = computed(() => {
    const s = props.fieldSchema
    switch (props.kind) {
      case 'textarea':
        return { placeholder: s.placeholder, rows: s.rows || 3 }
      case 'select':
        return { placeholder: s.placeholder, items: getSelectItems(), clearable: !s.required }
      case 'number':
        return {
          placeholder: s.placeholder,
          type: 'number',
          min: s.minimum,
          max: s.maximum,
          step: s.type === 'integer' ? 1 : s.step || 0.1
        }
      case 'date':
        return { placeholder: s.placeholder || 'YYYY-MM-DD', type: 'date' }
      default:
        return { placeholder: s.placeholder }
    }
  })

  /** Show icon in prepend slot when icon OR tooltip defined */
  const hasIcon = computed(() => !!(props.fieldSchema.icon || props.fieldSchema.tooltip))
  /** Default to the info icon when a tooltip exists without an icon */
  const iconName = computed(() => props.fieldSchema.icon || 'mdi-information-outline')
  const hasHint = computed(
    () => !!props.fieldSchema.hint && props.fieldSchema.hint.trim().length > 0
  )
  const needsHintTruncation = computed(
    () => hasHint.value && props.fieldSchema.hint!.length > HINT_TRUNCATE_LENGTH
  )
  const truncatedHint = computed(() =>
    needsHintTruncation.value
      ? `${props.fieldSchema.hint!.substring(0, HINT_TRUNCATE_LENGTH)}...`
      : props.fieldSchema.hint
  )
  const hasTooltip = computed(
    () => !!props.fieldSchema.tooltip && props.fieldSchema.tooltip.trim().length > 0
  )
  const hasHelpUrl = computed(
    () =>
      !!props.fieldSchema.helpUrl &&
      (props.fieldSchema.helpUrl.startsWith('http://') ||
        props.fieldSchema.helpUrl.startsWith('https://'))
  )

  // Lowercase raw values ('mitochondrial', 'lump/split/undecided') read as labels; mixed case ('AD') is kept
  const optionTitle = (value: unknown): unknown =>
    typeof value === 'string' && /^[a-z0-9]+([_/ -][a-z0-9]+)*$/.test(value)
      ? humanize(value)
      : value

  function getSelectItems(): Array<{ title: unknown; value: unknown }> {
    const options = props.fieldSchema.enumOptions
    if (options) {
      return options.map(option => {
        if (typeof option === 'string') return { title: optionTitle(option), value: option }
        return {
          title: option.label || optionTitle(option.value),
          value: option.value
        }
      })
    }

    return props.fieldSchema.enum?.map(value => ({ title: optionTitle(value), value })) || []
  }

  /** Open help URL in new tab with security flags */
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
