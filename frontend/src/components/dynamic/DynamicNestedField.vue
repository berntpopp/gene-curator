<template>
  <div v-if="fieldSchema.type === 'array'">
    <v-label class="text-body-medium font-weight-medium mb-2">
      {{ label }}
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
              <h4 class="text-title-small">Item {{ index + 1 }}</h4>
              <v-btn
                aria-label="Remove item"
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
                v-for="(subFieldSchema, subFieldName) in shown(fieldSchema.items?.properties)"
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

        <v-btn color="primary" variant="outlined" block :disabled="disabled" @click="addArrayItem">
          <v-icon start>mdi-plus</v-icon>
          Add {{ fieldSchema.itemTitle || 'Item' }}
        </v-btn>
      </v-card-text>
    </v-card>

    <div v-if="errorMessages.length" class="text-error text-body-small mt-1">
      {{ errorMessages.join(', ') }}
    </div>
  </div>

  <!-- Object Fields -->
  <div v-else>
    <v-label class="text-body-medium font-weight-medium mb-2">
      {{ label }}
      <span v-if="fieldSchema.required" class="text-error ml-1">*</span>
    </v-label>

    <v-card variant="outlined" :style="getNestedStyle(depth)">
      <v-card-text>
        <v-row>
          <v-col
            v-for="(subFieldSchema, subFieldName) in shown(fieldSchema.properties)"
            :key="subFieldName"
            cols="12"
            :sm="Object.keys(fieldSchema.properties ?? {}).length > 2 ? 6 : 12"
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

    <div v-if="errorMessages.length" class="text-error text-body-small mt-1">
      {{ errorMessages.join(', ') }}
    </div>
  </div>
</template>

<script setup lang="ts">
  /**
   * Nested `object` and `array` fields of the schema-driven form.
   *
   * Renders child fields through DynamicField (recursion is bounded by the
   * parent's depth check) and keeps a local copy of the value so child edits
   * can be emitted as a whole.
   */
  import { inject, ref, watch } from 'vue'
  import { generateUUID } from '@/utils/uuidPolyfill'
  import DynamicField from './DynamicField.vue'
  import { FORM_DATA, resolveField } from './conditions'
  import type { ComponentFallbackEvent, FieldSchema } from './types'

  const props = defineProps<{
    fieldSchema: FieldSchema
    /** Label shown above the nested block */
    label: string
    modelValue?: unknown
    depth: number
    disabled?: boolean
    /** Error messages to show below the block */
    errorMessages: string[]
  }>()

  const emit = defineEmits<{
    'update:model-value': [value: unknown]
    'component-fallback': [payload: ComponentFallbackEvent]
  }>()

  type Item = Record<string, unknown>

  // Condition paths start at the root of the form data (DynamicForm provides it)
  const root = inject(FORM_DATA, undefined)

  /** Child fields as the form data shows them: hidden ones dropped, `required_when` resolved */
  const shown = (fields?: Record<string, FieldSchema>) =>
    Object.fromEntries(
      Object.entries(fields ?? {}).flatMap(([name, field]) => {
        const resolved = resolveField(field, root?.value ?? {})
        return resolved ? [[name, resolved]] : []
      })
    )

  const arrayValue = ref<Item[]>(
    Array.isArray(props.modelValue) ? [...(props.modelValue as Item[])] : []
  )
  const objectValue = ref<Item>(
    props.modelValue && typeof props.modelValue === 'object' && !Array.isArray(props.modelValue)
      ? { ...(props.modelValue as Item) }
      : {}
  )

  // Watch for external model value changes
  watch(
    () => props.modelValue,
    newValue => {
      if (props.fieldSchema.type === 'array' && Array.isArray(newValue)) {
        arrayValue.value = [...(newValue as Item[])]
      } else if (props.fieldSchema.type === 'object' && newValue && typeof newValue === 'object') {
        objectValue.value = { ...(newValue as Item) }
      }
    }
  )

  /**
   * Generate progressive background styling for nested objects/arrays.
   * Applies subtle tinting at depth 2+ for visual hierarchy.
   */
  function getNestedStyle(depth: number): Record<string, string> {
    if (depth < 2) return {}
    const opacity = Math.min(0.02 + (depth - 2) * 0.01, 0.06)
    return {
      backgroundColor: `rgba(var(--v-theme-surface-variant), ${opacity})`,
      transition: 'background-color 0.2s ease'
    }
  }

  // Array field methods
  const addArrayItem = () => {
    const newItem: Item = {}
    if (props.fieldSchema.items?.properties) {
      // Initialize with default values
      Object.entries(props.fieldSchema.items.properties).forEach(([key, subSchema]) => {
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

    // Stable row identity for review diffs and anchored comments (removing a row must not
    // shift the identity of the rows after it)
    if (!newItem.id) newItem.id = generateUUID()

    arrayValue.value.push(newItem)
    emit('update:model-value', arrayValue.value)
  }

  const removeArrayItem = (index: number) => {
    arrayValue.value.splice(index, 1)
    emit('update:model-value', arrayValue.value)
  }

  const updateArrayItem = (index: number, fieldName: string, value: unknown) => {
    arrayValue.value[index]![fieldName] = value
    emit('update:model-value', arrayValue.value)
  }

  // Object field methods
  const updateObjectField = (fieldName: string, value: unknown) => {
    objectValue.value[fieldName] = value
    emit('update:model-value', objectValue.value)
  }
</script>

<style scoped>
  .border {
    border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  }
</style>
