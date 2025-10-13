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
                    item-title="symbol"
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
                        <v-list-item-title>{{ item.raw.symbol }}</v-list-item-title>
                        <v-list-item-subtitle>
                          {{ item.raw.name }} • {{ item.raw.location }}
                        </v-list-item-subtitle>
                        <template #append>
                          <v-chip
                            v-if="item.raw.assignment_status"
                            :color="getAssignmentStatusColor(item.raw.assignment_status)"
                            size="small"
                            variant="outlined"
                          >
                            {{ formatAssignmentStatus(item.raw.assignment_status) }}
                          </v-chip>
                        </template>
                      </v-list-item>
                    </template>
                  </v-autocomplete>
                </div>

                <!-- Disease/Phenotype Selection -->
                <div class="mb-4">
                  <div class="text-subtitle-1 font-weight-medium mb-2">
                    Associated Disease/Phenotype
                  </div>
                  <v-autocomplete
                    v-model="selectedDisease"
                    :items="availableDiseases"
                    :loading="searchingDiseases"
                    :search="diseaseSearchQuery"
                    item-title="name"
                    item-value="id"
                    label="Search for a disease or phenotype"
                    placeholder="Type disease name or OMIM ID..."
                    variant="outlined"
                    return-object
                    clearable
                    @update:search="searchDiseases"
                  >
                    <template #item="{ props, item }">
                      <v-list-item v-bind="props">
                        <v-list-item-title>{{ item.raw.name }}</v-list-item-title>
                        <v-list-item-subtitle>
                          OMIM: {{ item.raw.omim_id }} • {{ item.raw.category }}
                        </v-list-item-subtitle>
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
                    <v-col cols="12" sm="6">
                      <v-text-field
                        v-model="assignmentDueDate"
                        type="date"
                        label="Due Date (Optional)"
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

<script setup>
  import { useLogger } from '@/composables/useLogger'

  const logger = useLogger()
  import { ref, computed, watch } from 'vue'
  import { useRouter } from 'vue-router'
  import { useGenesStore, useAssignmentsStore } from '@/stores'
  import ScopeSelector from '@/components/dynamic/ScopeSelector.vue'
  import SchemaSelector from '@/components/dynamic/SchemaSelector.vue'

  const router = useRouter()
  const genesStore = useGenesStore()
  const assignmentsStore = useAssignmentsStore()

  // Reactive state
  const currentStep = ref(1)
  const selectedScope = ref(null)
  const selectedSchemas = ref(null)
  const selectedGene = ref(null)
  const selectedDisease = ref(null)
  const assignmentPriority = ref('medium')
  const assignmentDueDate = ref('')
  const assignmentNotes = ref('')
  const creating = ref(false)

  // Search states
  const geneSearchQuery = ref('')
  const diseaseSearchQuery = ref('')
  const searchingGenes = ref(false)
  const searchingDiseases = ref(false)
  const availableGenes = ref([])
  const availableDiseases = ref([])

  const priorityOptions = [
    { title: 'Low', value: 'low' },
    { title: 'Medium', value: 'medium' },
    { title: 'High', value: 'high' },
    { title: 'Urgent', value: 'urgent' }
  ]

  const canCreateAssignment = computed(() => {
    return (
      selectedScope.value && selectedSchemas.value && selectedGene.value && selectedDisease.value
    )
  })

  // Step handlers
  const handleScopeSelected = scope => {
    selectedScope.value = scope
    currentStep.value = 2
  }

  const handleSchemasSelected = schemas => {
    selectedSchemas.value = schemas
    currentStep.value = 3
  }

  // Search functions
  const searchGenes = async query => {
    if (!query || query.length < 2) {
      availableGenes.value = []
      return
    }

    searchingGenes.value = true
    try {
      const results = await genesStore.searchGenes({
        query,
        scope_id: selectedScope.value?.id,
        include_assignment_status: true,
        limit: 20
      })
      availableGenes.value = results
    } catch (error) {
      logger.error('Gene search failed:', { error: error.message, stack: error.stack })
      availableGenes.value = []
    } finally {
      searchingGenes.value = false
    }
  }

  const searchDiseases = async query => {
    if (!query || query.length < 2) {
      availableDiseases.value = []
      return
    }

    searchingDiseases.value = true
    try {
      // Mock disease search - replace with actual API call
      const mockDiseases = [
        {
          id: '1',
          name: 'Cardiomyopathy, Hypertrophic',
          omim_id: '192600',
          category: 'Cardiovascular'
        },
        { id: '2', name: 'Long QT Syndrome', omim_id: '192500', category: 'Cardiovascular' },
        { id: '3', name: 'Brugada Syndrome', omim_id: '601144', category: 'Cardiovascular' }
      ]

      availableDiseases.value = mockDiseases.filter(
        d => d.name.toLowerCase().includes(query.toLowerCase()) || d.omim_id.includes(query)
      )
    } catch (error) {
      logger.error('Disease search failed:', { error: error.message, stack: error.stack })
      availableDiseases.value = []
    } finally {
      searchingDiseases.value = false
    }
  }

  // Helper functions
  const getAssignmentStatusColor = status => {
    const colorMap = {
      available: 'success',
      assigned: 'warning',
      in_progress: 'primary',
      completed: 'grey'
    }
    return colorMap[status] || 'grey'
  }

  const formatAssignmentStatus = status => {
    return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  // Create assignment
  const createAssignment = async () => {
    if (!canCreateAssignment.value) return

    creating.value = true
    try {
      const assignmentData = {
        gene_id: selectedGene.value.id,
        disease_id: selectedDisease.value.id,
        scope_id: selectedScope.value.id,
        workflow_pair_id: selectedSchemas.value.workflowPair.id,
        priority: assignmentPriority.value,
        due_date: assignmentDueDate.value || null,
        notes: assignmentNotes.value || null,
        precuration_schema_id: selectedSchemas.value.precurationSchema.id,
        curation_schema_id: selectedSchemas.value.curationSchema.id
      }

      const assignment = await assignmentsStore.createAssignment(assignmentData)

      // Navigate to the new assignment
      router.push({ name: 'AssignmentDetail', params: { id: assignment.id } })
    } catch (error) {
      logger.error('Failed to create assignment:', { error: error.message, stack: error.stack })
    } finally {
      creating.value = false
    }
  }

  // Watch for gene selection to trigger disease search
  watch(selectedGene, gene => {
    if (gene) {
      // Auto-search for related diseases based on gene
      searchDiseases(gene.symbol)
    }
  })
</script>

<style scoped>
  .fill-height {
    min-height: 100vh;
  }
</style>
