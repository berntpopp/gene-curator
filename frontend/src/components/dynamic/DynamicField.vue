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
      v-else-if="fieldSchema.type === 'string' && !fieldSchema.multiline && !fieldSchema.enum"
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
        <div class="text-caption text-medium-emphasis">
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
        <div class="text-caption text-medium-emphasis">
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
        <div class="text-caption text-medium-emphasis">
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
        <div class="text-caption text-medium-emphasis">
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
        <div class="text-caption text-medium-emphasis">
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

    <!-- Array Fields (Dynamic Table) -->
    <div v-else-if="fieldSchema.type === 'array' && canRenderNested">
      <v-label class="text-body-2 font-weight-medium mb-2">
        {{ getFieldLabel() }}
        <span v-if="fieldSchema.required" class="text-error ml-1">*</span>
      </v-label>

      <v-card variant="outlined" :style="getNestedStyle(depth)">
        <v-card-text>
          <div v-if="!arrayValue.length" class="text-center py-4 text-medium-emphasis">
            No items added yet
          </div>

          <div v-else>
            <div v-for="(item, index) in arrayValue" :key="index" class="mb-4 pa-4 border rounded">
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
                    @component-fallback="$emit('component-fallback', $event)"
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

      <div v-if="getErrorMessages().length" class="text-error text-caption mt-1">
        {{ getErrorMessages().join(', ') }}
      </div>
    </div>

    <!-- Object Fields -->
    <div v-else-if="fieldSchema.type === 'object' && canRenderNested">
      <v-label class="text-body-2 font-weight-medium mb-2">
        {{ getFieldLabel() }}
        <span v-if="fieldSchema.required" class="text-error ml-1">*</span>
      </v-label>

      <v-card variant="outlined" :style="getNestedStyle(depth)">
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
                @component-fallback="$emit('component-fallback', $event)"
              />
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <div v-if="getErrorMessages().length" class="text-error text-caption mt-1">
        {{ getErrorMessages().join(', ') }}
      </div>
    </div>

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
      class="text-caption text-medium-emphasis mt-1"
    >
      {{ fieldSchema.description }}
    </div>
  </div>
</template>

<script setup>
  import { ref, computed, watch } from 'vue'
  import { componentRegistry } from './componentRegistry'
  import { useLogger } from '@/composables/useLogger'
  import { useValidationRules } from './composables/useValidationRules'

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

  const props = defineProps({
    fieldName: {
      type: String,
      required: true
    },
    fieldSchema: {
      type: Object,
      required: true
    },
    modelValue: {
      type: [String, Number, Boolean, Array, Object],
      default: null
    },
    validationResult: {
      type: Object,
      default: null
    },
    variant: {
      type: String,
      default: 'filled'
    },
    disabled: {
      type: Boolean,
      default: false
    },
    depth: {
      type: Number,
      default: 0
    }
  })

  const emit = defineEmits(['update:model-value', 'validate', 'component-fallback'])

  // Reactive refs for complex types
  const arrayValue = ref(Array.isArray(props.modelValue) ? [...props.modelValue] : [])
  const hintExpanded = ref(false)
  const objectValue = ref(
    props.modelValue && typeof props.modelValue === 'object' && !Array.isArray(props.modelValue)
      ? { ...props.modelValue }
      : {}
  )

  // Watch for external model value changes
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

  /**
   * Lookup custom component from registry when fieldSchema.component is specified.
   * Logs warning and emits component-fallback event when component not found.
   */
  const customComponent = computed(() => {
    if (!props.fieldSchema.component) return null

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
  const hasIcon = computed(() => props.fieldSchema.icon || props.fieldSchema.tooltip)

  /**
   * Get icon name, defaulting to info icon when tooltip exists without icon
   */
  const iconName = computed(() => props.fieldSchema.icon || 'mdi-information-outline')

  /**
   * Check if hint exists and is non-empty
   */
  const hasHint = computed(() => props.fieldSchema.hint && props.fieldSchema.hint.trim().length > 0)

  /**
   * Check if hint needs truncation
   */
  const needsHintTruncation = computed(
    () => hasHint.value && props.fieldSchema.hint.length > HINT_TRUNCATE_LENGTH
  )

  /**
   * Get truncated hint text
   */
  const truncatedHint = computed(() =>
    needsHintTruncation.value
      ? `${props.fieldSchema.hint.substring(0, HINT_TRUNCATE_LENGTH)}...`
      : props.fieldSchema.hint
  )

  /**
   * Check if tooltip exists and is non-empty
   */
  const hasTooltip = computed(
    () => props.fieldSchema.tooltip && props.fieldSchema.tooltip.trim().length > 0
  )

  /**
   * Check if helpUrl exists and is valid URL
   */
  const hasHelpUrl = computed(
    () =>
      props.fieldSchema.helpUrl &&
      (props.fieldSchema.helpUrl.startsWith('http://') ||
        props.fieldSchema.helpUrl.startsWith('https://'))
  )

  /**
   * Generate progressive background styling for nested objects/arrays.
   * Applies subtle tinting at depth 2+ for visual hierarchy.
   *
   * @param {number} depth - Current nesting depth
   * @returns {Object} CSS style object
   */
  function getNestedStyle(depth) {
    if (depth < 2) return {}
    const opacity = Math.min(0.02 + (depth - 2) * 0.01, 0.06)
    return {
      backgroundColor: `rgba(var(--v-theme-surface-variant), ${opacity})`,
      transition: 'background-color 0.2s ease'
    }
  }

  const getFieldLabel = () => {
    return (
      props.fieldSchema.title ||
      props.fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    )
  }

  // Initialize validation rules from composable
  const { validationRules } = useValidationRules(() => props.fieldSchema)

  const getSelectItems = () => {
    if (props.fieldSchema.enumOptions) {
      return props.fieldSchema.enumOptions.map(option => ({
        title: option.label || option,
        value: option.value || option
      }))
    }

    return (
      props.fieldSchema.enum?.map(value => ({
        title: value,
        value
      })) || []
    )
  }

  const getErrorMessages = () => {
    if (props.validationResult?.errors) {
      return props.validationResult.errors.map(error => error.message)
    }
    return []
  }

  const updateValue = value => {
    emit('update:model-value', value)
  }

  const handleBlur = event => {
    emit('validate', event.target.value)
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

  // Array field methods
  const addArrayItem = () => {
    const newItem = {}
    if (props.fieldSchema.items?.properties) {
      // Initialize with default values
      Object.keys(props.fieldSchema.items.properties).forEach(key => {
        const subSchema = props.fieldSchema.items.properties[key]
        if (subSchema.default !== undefined) {
          newItem[key] = subSchema.default
        } else if (subSchema.type === 'string') {
          newItem[key] = ''
        } else if (subSchema.type === 'number' || subSchema.type === 'integer') {
          newItem[key] = 0
        } else if (subSchema.type === 'boolean') {
          newItem[key] = false
        }
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

  // Object field methods
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
