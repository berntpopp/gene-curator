<template>
  <v-card-text>
    <v-expansion-panels v-model="openSections" multiple variant="accordion">
      <v-expansion-panel
        v-for="(section, index) in tab.sections"
        :key="section.name"
        :value="index"
      >
        <v-expansion-panel-title>
          <div class="d-flex align-center">
            <v-icon v-if="section.icon" :icon="section.icon" start class="mr-2" />
            <span class="font-weight-medium">{{ section.name }}</span>
          </div>
        </v-expansion-panel-title>

        <v-expansion-panel-text>
          <div v-if="section.help_text" class="text-body-small text-medium-emphasis mb-4">
            {{ section.help_text }}
          </div>

          <v-row>
            <v-col
              v-for="{ fieldPath, fieldSchema } in shownFields(section)"
              :key="fieldPath"
              cols="12"
              :sm="section.fields.length > 2 && fieldSchema.type !== 'evidence_table' ? 6 : 12"
            >
              <DynamicField
                :field-name="getFieldName(fieldPath)"
                :field-schema="fieldSchema"
                :model-value="getFieldValue(fieldPath)"
                :validation-result="getFieldValidation(fieldPath)"
                :backend-errors="backendErrors[fieldPath] || []"
                :disabled="readonly"
                @update:model-value="$emit('update:field', fieldPath, $event)"
                @clear-backend-error="$emit('clear-backend-error', fieldPath)"
              />
            </v-col>
          </v-row>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </v-card-text>
</template>

<script setup lang="ts">
  import { ref, onActivated, onDeactivated } from 'vue'
  import { useLogger } from '@/composables/useLogger'
  import DynamicField from './DynamicField.vue'
  import { resolveField } from './conditions'
  import type {
    FieldSchema,
    FieldValidation,
    FormValidationResult,
    JsonSchemaDocument,
    SectionConfig,
    TabConfig
  } from './types'

  const logger = useLogger()

  const props = withDefaults(
    defineProps<{
      tab: TabConfig
      schema: JsonSchemaDocument
      formData: Record<string, unknown>
      validationResult?: FormValidationResult | null
      /** Backend errors keyed by dot-notation field path */
      backendErrors?: Record<string, string[]>
      readonly?: boolean
    }>(),
    {
      validationResult: null,
      backendErrors: () => ({}),
      readonly: false
    }
  )

  defineEmits<{
    'update:field': [fieldPath: string, value: unknown]
    'clear-backend-error': [fieldPath: string]
  }>()

  // Initialize open sections based on schema defaults
  // Sections with collapsed: true start closed
  // Sections without collapsed or with collapsed: false start open
  const openSections = ref<number[]>(
    props.tab.sections
      .map((section, index) => (!section.collapsed ? index : null))
      .filter((i): i is number => i !== null)
  )

  // KeepAlive lifecycle hooks
  onActivated(() => {
    logger.debug('Tab activated', { tabId: props.tab.id })
  })

  onDeactivated(() => {
    logger.debug('Tab deactivated', { tabId: props.tab.id })
  })

  /**
   * Extract field name from dot-notation path
   * @param fieldPath - Dot-notation field path (e.g., "case_info.gene_symbol")
   * @returns Last segment of path
   */
  function getFieldName(fieldPath: string): string {
    const parts = fieldPath.split('.')
    return parts[parts.length - 1] ?? fieldPath
  }

  /**
   * Navigate schema.properties using path segments, handling nested object/array types
   * @param fieldPath - Dot-notation field path
   * @returns Field schema definition
   */
  function getFieldSchema(fieldPath: string): FieldSchema {
    const parts = fieldPath.split('.')
    // Current lookup level: a properties map, or a field node when the path is malformed
    let level: Record<string, unknown> | undefined = props.schema.properties
    let field: FieldSchema | undefined

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i] ?? ''
      field = level?.[part] as FieldSchema | undefined

      if (!field) {
        logger.warn('Field schema not found', {
          fieldPath,
          part,
          availableKeys: Object.keys(level ?? {})
        })
        // Return fallback schema
        return {
          type: 'string',
          title: fieldPath,
          description: 'Schema definition not found'
        }
      }

      const isLast = i === parts.length - 1
      // If it's an object type, move into properties for next iteration
      if (!isLast && field.type === 'object' && field.properties) {
        level = field.properties as Record<string, unknown>
      }
      // If it's an array type, move into items.properties for next iteration
      else if (!isLast && field.type === 'array' && field.items?.properties) {
        level = field.items.properties as Record<string, unknown>
      } else {
        level = field as Record<string, unknown>
      }
    }

    return field as FieldSchema
  }

  /** Visible fields of a section, with `required_when` resolved against the form data */
  function shownFields(section: SectionConfig) {
    return section.fields.flatMap(fieldPath => {
      const fieldSchema = resolveField(getFieldSchema(fieldPath), props.formData)
      return fieldSchema ? [{ fieldPath, fieldSchema }] : []
    })
  }

  /**
   * Navigate formData using path segments
   * @param fieldPath - Dot-notation field path
   * @returns Field value
   */
  function getFieldValue(fieldPath: string): unknown {
    const parts = fieldPath.split('.')
    let value: unknown = props.formData

    for (const part of parts) {
      value = (value as Record<string, unknown> | null | undefined)?.[part]
      if (value === undefined) break
    }

    return value
  }

  /**
   * Extract field-specific errors from validationResult
   * @param fieldPath - Dot-notation field path
   * @returns Field validation result
   */
  function getFieldValidation(fieldPath: string): FieldValidation | null {
    if (!props.validationResult?.field_validations) return null

    const validation = props.validationResult.field_validations[fieldPath]
    return validation || null
  }
</script>
