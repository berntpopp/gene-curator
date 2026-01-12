<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-file-document-outline</v-icon>
      Select Curation Methodology
    </v-card-title>

    <v-card-text>
      <v-select
        v-model="selectedSchemaId"
        :items="availableSchemas"
        :loading="loading"
        item-title="name"
        item-value="id"
        label="Curation Schema"
        placeholder="Choose curation methodology..."
        variant="outlined"
        :hint="selectedSchema?.description"
        persistent-hint
        @update:model-value="handleSelection"
      >
        <template #item="{ props: itemProps, item }">
          <v-list-item v-bind="itemProps">
            <template #subtitle> {{ item.raw.schema_type }} | v{{ item.raw.version }} </template>
            <template #append>
              <v-chip size="x-small" color="info" variant="flat">
                {{ getFieldCount(item.raw) }} fields
              </v-chip>
            </template>
          </v-list-item>
        </template>
      </v-select>

      <v-alert v-if="selectedSchema" type="info" variant="tonal" class="mt-4">
        <template #prepend>
          <v-icon>mdi-information</v-icon>
        </template>
        <div class="font-weight-medium">{{ selectedSchema.name }}</div>
        <div class="text-body-2">{{ selectedSchema.description }}</div>
      </v-alert>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="primary"
        variant="flat"
        :disabled="!selectedSchemaId"
        aria-label="Continue to curation form"
        @click="confirmSelection"
      >
        <v-icon start>mdi-arrow-right</v-icon>
        Continue
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
  /**
   * CurationSchemaSelect Component
   *
   * Single-schema selector for the curation workflow.
   * Filters schemas by type (curation/combined) and provides
   * a confirmation step before proceeding.
   *
   * Named differently from SchemaSelector to avoid conflict with
   * the existing workflow pair selector in components/dynamic/.
   *
   * @example
   * <CurationSchemaSelect
   *   v-model="selectedSchemaId"
   *   :scope-id="scopeId"
   *   @update:model-value="handleSchemaSelected"
   * />
   */

  import { ref, computed, onMounted, watch } from 'vue'
  import { useSchemasStore } from '@/stores/schemas'

  const props = defineProps({
    modelValue: {
      type: String,
      default: null
    },
    scopeId: {
      type: String,
      required: true
    },
    schemaType: {
      type: String,
      default: 'curation',
      validator: v => ['curation', 'precuration', 'combined'].includes(v)
    }
  })

  const emit = defineEmits(['update:modelValue'])

  const schemasStore = useSchemasStore()
  const selectedSchemaId = ref(props.modelValue)

  const loading = computed(() => schemasStore.loading)

  // Filter schemas by type (curation or combined)
  const availableSchemas = computed(() => {
    return schemasStore.schemas.filter(
      s => s.schema_type === props.schemaType || s.schema_type === 'combined'
    )
  })

  const selectedSchema = computed(() => {
    if (!selectedSchemaId.value) return null
    return availableSchemas.value.find(s => s.id === selectedSchemaId.value)
  })

  function getFieldCount(schema) {
    return schema.field_definitions?.length || 0
  }

  function handleSelection(schemaId) {
    selectedSchemaId.value = schemaId
  }

  function confirmSelection() {
    if (selectedSchemaId.value) {
      emit('update:modelValue', selectedSchemaId.value)
    }
  }

  // Sync with external v-model changes
  watch(
    () => props.modelValue,
    newVal => {
      selectedSchemaId.value = newVal
    }
  )

  onMounted(async () => {
    if (schemasStore.schemas.length === 0) {
      await schemasStore.fetchSchemas()
    }
  })
</script>
