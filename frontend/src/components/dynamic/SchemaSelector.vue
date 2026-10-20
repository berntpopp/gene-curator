<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-file-document-outline</v-icon>
      Select Curation Methodology
    </v-card-title>

    <v-card-text>
      <v-row>
        <v-col cols="12" md="6">
          <v-select
            v-model="selectedPrecurationSchema"
            :items="precurationSchemas"
            :loading="loading"
            item-title="name"
            item-value="id"
            label="Precuration Schema"
            placeholder="Choose precuration methodology..."
            variant="outlined"
            return-object
          >
            <template #item="{ props, item }">
              <v-list-item v-bind="props">
                <v-list-item-title>{{ item.raw.name }}</v-list-item-title>
                <v-list-item-subtitle>
                  {{ item.raw.description || 'No description available' }}
                </v-list-item-subtitle>
                <template #append>
                  <v-chip size="small" color="info" variant="flat">
                    v{{ item.raw.version }}
                  </v-chip>
                </template>
              </v-list-item>
            </template>
          </v-select>
        </v-col>

        <v-col cols="12" md="6">
          <v-select
            v-model="selectedCurationSchema"
            :items="curationSchemas"
            :loading="loading"
            item-title="name"
            item-value="id"
            label="Curation Schema"
            placeholder="Choose curation methodology..."
            variant="outlined"
            return-object
          >
            <template #item="{ props, item }">
              <v-list-item v-bind="props">
                <v-list-item-title>{{ item.raw.name }}</v-list-item-title>
                <v-list-item-subtitle>
                  {{ item.raw.description || 'No description available' }}
                </v-list-item-subtitle>
                <template #append>
                  <v-chip size="small" color="info" variant="flat">
                    v{{ item.raw.version }}
                  </v-chip>
                </template>
              </v-list-item>
            </template>
          </v-select>
        </v-col>
      </v-row>

      <v-alert v-if="canCreateWorkflowPair" type="success" variant="tonal" class="mt-4">
        <template #prepend>
          <v-icon>mdi-check-circle</v-icon>
        </template>
        <div class="font-weight-medium mb-1">Methodology Pair Selected</div>
        <div class="text-body-2">
          Precuration: {{ selectedPrecurationSchema?.name }} v{{ selectedPrecurationSchema?.version
          }}<br />
          Curation: {{ selectedCurationSchema?.name }} v{{ selectedCurationSchema?.version }}
        </div>
      </v-alert>

      <v-alert v-if="existingWorkflowPair" type="info" variant="tonal" class="mt-4">
        <template #prepend>
          <v-icon>mdi-information</v-icon>
        </template>
        <div class="font-weight-medium mb-1">Using Existing Workflow Pair</div>
        <div class="text-body-2">{{ existingWorkflowPair.name }}</div>
      </v-alert>
    </v-card-text>

    <v-card-actions v-if="canCreateWorkflowPair || existingWorkflowPair">
      <v-spacer />
      <v-btn
        v-if="canCreateWorkflowPair && !existingWorkflowPair"
        color="secondary"
        variant="outlined"
        :loading="creating"
        @click="createWorkflowPair"
      >
        <v-icon start>mdi-plus</v-icon>
        Create Workflow Pair
      </v-btn>
      <v-btn color="primary" variant="flat" :disabled="!canProceed" @click="proceedWithSchemas">
        <v-icon start>mdi-arrow-right</v-icon>
        Continue
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
  import { ref, computed, onMounted, watch } from 'vue'
  import { useLogger } from '@/composables/useLogger'
  import { useSchemasStore } from '@/stores'
  import { errorDetails } from './errorDetails'
  import type { ComponentLogger, SchemaOption, WorkflowPairOption } from './types'

  const logger = useLogger() as ComponentLogger

  const emit = defineEmits<{
    'schemas-selected': [
      data: {
        precurationSchema: SchemaOption | null
        curationSchema: SchemaOption | null
        workflowPair: WorkflowPairOption | null | undefined
      }
    ]
  }>()

  const schemasStore = useSchemasStore()
  const selectedPrecurationSchema = ref<SchemaOption | null>(null)
  const selectedCurationSchema = ref<SchemaOption | null>(null)
  const existingWorkflowPair = ref<WorkflowPairOption | null | undefined>(null)
  const creating = ref(false)

  // The schemas store is untyped JS; these getters are typed at this boundary
  const loading = computed(() => schemasStore.loading)
  const precurationSchemas = computed(() => schemasStore.getPrecurationSchemas as SchemaOption[])
  const curationSchemas = computed(() => schemasStore.getCurationSchemas as SchemaOption[])

  const canCreateWorkflowPair = computed(
    () => !!selectedPrecurationSchema.value && !!selectedCurationSchema.value
  )

  const canProceed = computed(() => !!existingWorkflowPair.value || canCreateWorkflowPair.value)

  // Check for existing workflow pairs when schemas are selected
  watch([selectedPrecurationSchema, selectedCurationSchema], () => {
    if (selectedPrecurationSchema.value && selectedCurationSchema.value) {
      // Check if workflow pair already exists
      const pairs = schemasStore.workflowPairs as WorkflowPairOption[]
      existingWorkflowPair.value = pairs.find(
        pair =>
          pair.precuration_schema_id === selectedPrecurationSchema.value?.id &&
          pair.curation_schema_id === selectedCurationSchema.value?.id
      )
    } else {
      existingWorkflowPair.value = null
    }
  })

  const createWorkflowPair = async () => {
    const precuration = selectedPrecurationSchema.value
    const curation = selectedCurationSchema.value
    if (!precuration || !curation) return

    creating.value = true
    try {
      const pairData = {
        name: `${precuration.name}_${curation.name}`,
        precuration_schema_id: precuration.id,
        curation_schema_id: curation.id,
        description: `Workflow pair for ${precuration.name} precuration and ${curation.name} curation`
      }

      const newPair = (await schemasStore.createWorkflowPair(pairData)) as WorkflowPairOption
      existingWorkflowPair.value = newPair
    } catch (err) {
      logger.error('Failed to create workflow pair:', errorDetails(err))
    } finally {
      creating.value = false
    }
  }

  const proceedWithSchemas = () => {
    const data = {
      precurationSchema: selectedPrecurationSchema.value,
      curationSchema: selectedCurationSchema.value,
      workflowPair: existingWorkflowPair.value
    }
    emit('schemas-selected', data)
  }

  onMounted(async () => {
    try {
      await Promise.all([schemasStore.fetchSchemas(), schemasStore.fetchWorkflowPairs()])
    } catch (err) {
      logger.error('Failed to load schemas:', errorDetails(err))
    }
  })
</script>
