<template>
  <v-container class="fill-height">
    <v-row justify="center" align="center">
      <v-col cols="12" md="8" lg="6">
        <!-- Progress Stepper -->
        <v-stepper v-model="currentStep" alt-labels class="mb-6">
          <v-stepper-header>
            <v-stepper-item
              :complete="currentStep > 1"
              :value="1"
              title="Select Scope"
              subtitle="Choose clinical specialty"
            />
            <v-divider />
            <v-stepper-item
              :complete="currentStep > 2"
              :value="2"
              title="Choose Methodology"
              subtitle="Select curation schemas"
            />
            <v-divider />
            <v-stepper-item
              :complete="currentStep > 3"
              :value="3"
              title="Gene Assignment"
              subtitle="Start curation"
            />
          </v-stepper-header>
        </v-stepper>

        <!-- Step Content -->
        <v-window v-model="currentStep">
          <!-- Step 1: Scope Selection -->
          <v-window-item :value="1">
            <ScopeSelector @scope-selected="handleScopeSelected" />
          </v-window-item>

          <!-- Step 2: Schema Selection -->
          <v-window-item :value="2">
            <SchemaSelector
              v-if="selectedScope"
              :scope-id="selectedScope.id"
              @schemas-selected="handleSchemasSelected"
            />
          </v-window-item>

          <!-- Step 3: Gene Assignment -->
          <v-window-item :value="3">
            <v-card>
              <v-card-title class="d-flex align-center">
                <v-icon start>mdi-dna</v-icon>
                Gene Assignment
              </v-card-title>

              <v-card-text>
                <div class="mb-4">
                  <div class="text-subtitle-1 font-weight-medium mb-2">Selected Configuration</div>
                  <v-row dense>
                    <v-col cols="12" sm="4">
                      <div class="text-caption text-medium-emphasis">Clinical Scope</div>
                      <div class="text-body-2">{{ selectedScope?.display_name }}</div>
                    </v-col>
                    <v-col cols="12" sm="4">
                      <div class="text-caption text-medium-emphasis">Precuration Schema</div>
                      <div class="text-body-2">{{ selectedSchemas?.precurationSchema?.name }}</div>
                    </v-col>
                    <v-col cols="12" sm="4">
                      <div class="text-caption text-medium-emphasis">Curation Schema</div>
                      <div class="text-body-2">{{ selectedSchemas?.curationSchema?.name }}</div>
                    </v-col>
                  </v-row>
                </div>

                <v-divider class="my-4" />

                <!-- Gene Search and Selection -->
                <div class="mb-4">
                  <div class="text-subtitle-1 font-weight-medium mb-2">Gene Selection</div>
                  <v-autocomplete
                    v-model="selectedGene"
                    :items="availableGenes"
                    :loading="searchingGenes"
                    :search="geneSearchQuery"
                    item-title="approved_symbol"
                    item-value="id"
                    label="Search for a gene"
                    placeholder="Type gene symbol or name..."
                    variant="outlined"
                    return-object
                    clearable
                    @update:search="searchGenes"
                  >
                    <template #item="{ props, item }">
                      <v-list-item v-bind="props">
                        <v-list-item-title>{{ item.raw.approved_symbol }}</v-list-item-title>
                        <v-list-item-subtitle>
                          {{ item.raw.hgnc_id }} • {{ item.raw.location }}
                        </v-list-item-subtitle>
                        <template #append>
                          <v-chip
                            v-if="item.raw.is_assigned"
                            color="warning"
                            size="small"
                            variant="outlined"
                          >
                            Assigned
                          </v-chip>
                        </template>
                      </v-list-item>
                    </template>
                  </v-autocomplete>
                </div>

                <!-- Assignment Options -->
                <div class="mb-4">
                  <div class="text-subtitle-1 font-weight-medium mb-2">Assignment Options</div>
                  <v-row>
                    <v-col cols="12" sm="6">
                      <v-select
                        v-model="assignmentPriority"
                        :items="priorityOptions"
                        label="Priority Level"
                        variant="outlined"
                      />
                    </v-col>
                  </v-row>
                  <v-textarea
                    v-model="assignmentNotes"
                    label="Assignment Notes (Optional)"
                    placeholder="Add any specific instructions or context..."
                    variant="outlined"
                    rows="3"
                  />
                </div>
              </v-card-text>

              <v-card-actions>
                <v-btn variant="outlined" @click="currentStep = 2">
                  <v-icon start>mdi-arrow-left</v-icon>
                  Back
                </v-btn>
                <v-spacer />
                <v-btn
                  color="primary"
                  variant="flat"
                  :loading="creating"
                  :disabled="!canCreateAssignment"
                  @click="createAssignment"
                >
                  <v-icon start>mdi-plus</v-icon>
                  Create Assignment
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-window-item>
        </v-window>

        <!-- Navigation -->
        <div v-if="currentStep < 3" class="text-center mt-6">
          <v-btn v-if="currentStep > 1" variant="outlined" class="mr-4" @click="currentStep--">
            <v-icon start>mdi-arrow-left</v-icon>
            Back
          </v-btn>
          <v-btn variant="text" to="/dashboard"> Cancel </v-btn>
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
  import { useLogger } from '@/composables/useLogger'

  // useLogger's JSDoc types its return as a bare Object; narrow it to the methods used here
  interface Logger {
    debug: (message: string, data?: object) => void
    info: (message: string, data?: object) => void
    warn: (message: string, data?: object) => void
    error: (message: string, data?: object) => void
  }

  const logger = useLogger() as Logger
  import { ref, computed } from 'vue'
  import { useRouter } from 'vue-router'
  import { useGenesStore, useAssignmentsStore } from '@/stores'
  import type { Schema } from '@/types/api'
  import ScopeSelector from '@/components/dynamic/ScopeSelector.vue'
  import SchemaSelector from '@/components/dynamic/SchemaSelector.vue'
  import type { SchemaOption, WorkflowPairOption } from '@/components/dynamic/types'

  // Minimal shape of errors thrown by the API client (axios) or the stores
  interface ApiError {
    message?: string
    stack?: string
  }

  interface ScopeOption {
    id: string
    name?: string
    display_name?: string
  }

  interface SelectedSchemas {
    workflowPair: WorkflowPairOption | null | undefined
    precurationSchema: SchemaOption | null
    curationSchema: SchemaOption | null
  }

  type GeneOption = Schema<'GeneSummary'>

  const router = useRouter()
  const genesStore = useGenesStore()
  const assignmentsStore = useAssignmentsStore()

  // Reactive state
  const currentStep = ref(1)
  const selectedScope = ref<ScopeOption | null>(null)
  const selectedSchemas = ref<SelectedSchemas | null>(null)
  const selectedGene = ref<GeneOption | null>(null)
  const assignmentPriority = ref('medium')
  const assignmentNotes = ref('')
  const creating = ref(false)

  // Search states
  const geneSearchQuery = ref('')
  const searchingGenes = ref(false)
  const availableGenes = ref<GeneOption[]>([])

  const priorityOptions = [
    { title: 'Low', value: 'low' },
    { title: 'Medium', value: 'medium' },
    { title: 'High', value: 'high' },
    { title: 'Urgent', value: 'urgent' }
  ]

  const canCreateAssignment = computed(() => {
    return selectedScope.value && selectedSchemas.value && selectedGene.value
  })

  // Step handlers
  const handleScopeSelected = (scope: ScopeOption) => {
    selectedScope.value = scope
    currentStep.value = 2
  }

  const handleSchemasSelected = (schemas: SelectedSchemas) => {
    selectedSchemas.value = schemas
    currentStep.value = 3
  }

  // Search functions
  const searchGenes = async (query: string) => {
    if (!query || query.length < 2) {
      availableGenes.value = []
      return
    }

    searchingGenes.value = true
    try {
      // The API answers with a plain GeneSummary list (is_assigned replaces the old status field)
      const results = (await genesStore.searchGenes({
        query,
        scope_id: selectedScope.value?.id,
        limit: 20
      })) as unknown as GeneOption[]
      availableGenes.value = results
    } catch (error) {
      const err = error as ApiError
      logger.error('Gene search failed:', { error: err.message, stack: err.stack })
      availableGenes.value = []
    } finally {
      searchingGenes.value = false
    }
  }

  // Create assignment
  const createAssignment = async () => {
    const scope = selectedScope.value
    const gene = selectedGene.value
    if (!scope || !selectedSchemas.value || !gene) return

    creating.value = true
    try {
      const assignmentData: Schema<'GeneScopeAssignmentCreate'> = {
        gene_id: gene.id,
        scope_id: scope.id,
        priority_level: assignmentPriority.value,
        assignment_notes: assignmentNotes.value || null
      }

      // TODO(stage2): missing store API assignmentsStore.createAssignment (api: assignmentsAPI.createAssignment)
      const assignment = await assignmentsStore.createAssignment(assignmentData)

      // Navigate to the new assignment
      router.push({ name: 'AssignmentDetail', params: { id: assignment.id } })
    } catch (error) {
      const err = error as ApiError
      logger.error('Failed to create assignment:', { error: err.message, stack: err.stack })
    } finally {
      creating.value = false
    }
  }
</script>

<style scoped>
  .fill-height {
    min-height: 100vh;
  }
</style>
