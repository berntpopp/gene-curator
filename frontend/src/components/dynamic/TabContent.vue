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
          <div v-if="section.help_text" class="text-caption text-medium-emphasis mb-4">
            {{ section.help_text }}
          </div>

          <v-row>
            <v-col
              v-for="fieldPath in section.fields"
              :key="fieldPath"
              cols="12"
              :sm="section.fields.length > 2 ? 6 : 12"
            >
              <DynamicField
                :field-name="getFieldName(fieldPath)"
                :field-schema="getFieldSchema(fieldPath)"
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

<script setup>
  import { ref, onActivated, onDeactivated } from 'vue'
  import { useLogger } from '@/composables/useLogger'
  import DynamicField from './DynamicField.vue'

  const logger = useLogger()

  const props = defineProps({
    tab: {
      type: Object,
      required: true
    },
    schema: {
      type: Object,
      required: true
    },
    formData: {
      type: Object,
      required: true
    },
    validationResult: {
      type: Object,
      default: null
    },
    backendErrors: {
      type: Object,
      default: () => ({})
    },
    readonly: {
      type: Boolean,
      default: false
    }
  })

  defineEmits(['update:field', 'clear-backend-error'])

  // Initialize open sections based on schema defaults
  // Sections with collapsed: true start closed
  // Sections without collapsed or with collapsed: false start open
  const openSections = ref(
    props.tab.sections
      .map((section, index) => (!section.collapsed ? index : null))
      .filter(i => i !== null)
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
   * @param {string} fieldPath - Dot-notation field path (e.g., "case_info.gene_symbol")
   * @returns {string} Last segment of path
   */
  function getFieldName(fieldPath) {
    const parts = fieldPath.split('.')
    return parts[parts.length - 1]
  }

  /**
   * Navigate schema.properties using path segments, handling nested object/array types
   * @param {string} fieldPath - Dot-notation field path
   * @returns {Object} Field schema definition
   */
  function getFieldSchema(fieldPath) {
    const parts = fieldPath.split('.')
    let schema = props.schema.properties

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]

      if (schema[part]) {
        // Direct property found
        schema = schema[part]

        // If it's an object type, move into properties for next iteration
        if (i < parts.length - 1 && schema.type === 'object' && schema.properties) {
          schema = schema.properties
        }
        // If it's an array type, move into items.properties for next iteration
        else if (i < parts.length - 1 && schema.type === 'array' && schema.items?.properties) {
          schema = schema.items.properties
        }
      } else {
        logger.warn('Field schema not found', {
          fieldPath,
          part,
          availableKeys: Object.keys(schema)
        })
        // Return fallback schema
        return {
          type: 'string',
          title: fieldPath,
          description: 'Schema definition not found'
        }
      }
    }

    return schema
  }

  /**
   * Navigate formData using path segments
   * @param {string} fieldPath - Dot-notation field path
   * @returns {*} Field value
   */
  function getFieldValue(fieldPath) {
    const parts = fieldPath.split('.')
    let value = props.formData

    for (const part of parts) {
      value = value?.[part]
      if (value === undefined) break
    }

    return value
  }

  /**
   * Extract field-specific errors from validationResult
   * @param {string} fieldPath - Dot-notation field path
   * @returns {Object|null} Field validation result
   */
  function getFieldValidation(fieldPath) {
    if (!props.validationResult?.field_validations) return null

    const validation = props.validationResult.field_validations[fieldPath]
    return validation || null
  }
</script>
