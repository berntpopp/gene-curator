<template>
  <v-container fluid>
    <div v-if="loading" class="text-center py-12">
      <v-progress-circular indeterminate color="primary" size="64" />
      <div class="mt-4 text-h6">Loading assignment...</div>
    </div>

    <div v-else-if="assignment">
      <!-- Page Header -->
      <div class="d-flex align-center mb-6">
        <v-btn icon="mdi-arrow-left" variant="text" class="mr-4" @click="$router.back()" />
        <div>
          <h1 class="text-h4 font-weight-bold">
            {{ assignment.gene_symbol }} - {{ assignment.disease_name }}
          </h1>
          <p class="text-body-1 text-medium-emphasis mt-1">
            {{ assignment.scope_display_name }} • {{ assignment.workflow_pair_name }}
          </p>
        </div>
        <v-spacer />
        <v-chip :color="getStatusColor(assignment.status)" size="large" variant="flat">
          {{ formatStatus(assignment.status) }}
        </v-chip>
      </div>

      <!-- Assignment Overview Card -->
      <v-card class="mb-6">
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-information</v-icon>
          Assignment Overview
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" sm="6" md="3">
              <div class="text-caption text-medium-emphasis">Gene</div>
              <div class="text-body-1 font-weight-medium">{{ assignment.gene_symbol }}</div>
              <div class="text-body-2">{{ assignment.gene_name }}</div>
            </v-col>
            <v-col cols="12" sm="6" md="3">
              <div class="text-caption text-medium-emphasis">Disease</div>
              <div class="text-body-1 font-weight-medium">{{ assignment.disease_name }}</div>
              <div class="text-body-2">OMIM: {{ assignment.omim_id }}</div>
            </v-col>
            <v-col cols="12" sm="6" md="3">
              <div class="text-caption text-medium-emphasis">Assigned To</div>
              <div v-if="assignment.assigned_to" class="text-body-1">
                {{ assignment.assignee_name }}
              </div>
              <div v-else class="text-body-1 text-medium-emphasis">Unassigned</div>
            </v-col>
            <v-col cols="12" sm="6" md="3">
              <div class="text-caption text-medium-emphasis">Due Date</div>
              <div
                v-if="assignment.due_date"
                class="text-body-1"
                :class="getDueDateClass(assignment.due_date)"
              >
                {{ formatDate(assignment.due_date) }}
              </div>
              <div v-else class="text-body-1 text-medium-emphasis">No due date</div>
            </v-col>
          </v-row>

          <div v-if="assignment.notes" class="mt-4">
            <div class="text-caption text-medium-emphasis">Assignment Notes</div>
            <div class="text-body-2 mt-1">{{ assignment.notes }}</div>
          </div>
        </v-card-text>
      </v-card>

      <!-- Main Content Tabs -->
      <v-tabs v-model="activeTab" bg-color="transparent">
        <v-tab value="precuration">
          <v-icon start>mdi-file-document-edit</v-icon>
          Precuration
        </v-tab>
        <v-tab value="curation" :disabled="!canAccessCuration">
          <v-icon start>mdi-file-document-check</v-icon>
          Curation
        </v-tab>
        <v-tab value="scoring">
          <v-icon start>mdi-calculator</v-icon>
          Scoring
        </v-tab>
        <v-tab value="history">
          <v-icon start>mdi-history</v-icon>
          History
        </v-tab>
      </v-tabs>

      <v-window v-model="activeTab" class="mt-4">
        <!-- Precuration Tab -->
        <v-window-item value="precuration">
          <DynamicForm
            v-if="assignment.precuration_schema_id"
            :schema-id="assignment.precuration_schema_id"
            :title="'Precuration: ' + assignment.gene_symbol"
            :initial-data="precurationData"
            @submit="handlePrecurationSubmit"
            @save-draft="handlePrecurationDraft"
          />
        </v-window-item>

        <!-- Curation Tab -->
        <v-window-item value="curation">
          <DynamicForm
            v-if="assignment.curation_schema_id && canAccessCuration"
            :schema-id="assignment.curation_schema_id"
            :title="'Curation: ' + assignment.gene_symbol + ' - ' + assignment.disease_name"
            :initial-data="curationData"
            @submit="handleCurationSubmit"
            @save-draft="handleCurationDraft"
          />
          <v-alert v-else-if="!canAccessCuration" type="info" variant="tonal">
            <template #prepend>
              <v-icon>mdi-information</v-icon>
            </template>
            Complete precuration stage to access curation.
          </v-alert>
        </v-window-item>

        <!-- Scoring Tab -->
        <v-window-item value="scoring">
          <ScoreDisplay
            :evidence-data="combinedEvidenceData"
            :schema-id="currentScoringSchemaId"
            :auto-refresh="true"
            @score-updated="handleScoreUpdated"
            @classification-changed="handleClassificationChanged"
          />
        </v-window-item>

        <!-- History Tab -->
        <v-window-item value="history">
          <v-card>
            <v-card-title class="d-flex align-center">
              <v-icon start>mdi-history</v-icon>
              Assignment History
            </v-card-title>
            <v-card-text>
              <v-timeline v-if="assignmentHistory.length" density="compact">
                <v-timeline-item
                  v-for="event in assignmentHistory"
                  :key="event.id"
                  :dot-color="getEventColor(event.event_type)"
                  size="small"
                >
                  <template #icon>
                    <v-icon size="small">{{ getEventIcon(event.event_type) }}</v-icon>
                  </template>

                  <div class="d-flex justify-space-between align-center mb-1">
                    <span class="font-weight-medium">{{ formatEventType(event.event_type) }}</span>
                    <span class="text-caption text-medium-emphasis">
                      {{ formatDateTime(event.created_at) }}
                    </span>
                  </div>

                  <div class="text-body-2 mb-1">{{ event.description }}</div>

                  <div class="text-caption text-medium-emphasis">
                    By: {{ event.user_name }} ({{ event.user_role }})
                  </div>

                  <div v-if="event.details" class="text-body-2 mt-2 pa-2 bg-grey-lighten-4 rounded">
                    {{ event.details }}
                  </div>
                </v-timeline-item>
              </v-timeline>

              <div v-else class="text-center py-8 text-medium-emphasis">
                <v-icon size="64" class="mb-4">mdi-history</v-icon>
                <div class="text-body-1">No history available</div>
              </div>
            </v-card-text>
          </v-card>
        </v-window-item>
      </v-window>
    </div>

    <v-alert v-else-if="error" type="error" variant="tonal">
      <template #prepend>
        <v-icon>mdi-alert-circle</v-icon>
      </template>
      Failed to load assignment: {{ error }}
    </v-alert>
  </v-container>
</template>

<script setup lang="ts">
  import { useLogger } from '@/composables/useLogger'
  import { ref, computed, onMounted, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { useAssignmentsStore } from '@/stores'
  import DynamicForm from '@/components/dynamic/DynamicForm.vue'
  import ScoreDisplay from '@/components/dynamic/ScoreDisplay.vue'

  // Assignment payload shape used by this view (stores are JS, so typed locally)
  interface AssignmentDetailRecord {
    id: string
    workflow_pair_id: string
    precuration_status?: string | null
    current_stage?: string | null
    status: string
    gene_symbol?: string | null
    gene_name?: string | null
    disease_name?: string | null
    omim_id?: string | null
    scope_display_name?: string | null
    workflow_pair_name?: string | null
    assigned_to?: string | null
    assignee_name?: string | null
    due_date?: string | null
    notes?: string | null
    precuration_schema_id?: string | null
    curation_schema_id?: string | null
    precuration_data?: Record<string, unknown> | null
    curation_data?: Record<string, unknown> | null
  }

  interface AssignmentHistoryEvent {
    id: string
    event_type: string
    description?: string | null
    created_at: string
    user_name?: string | null
    user_role?: string | null
    details?: string | null
  }

  type FormData = Record<string, unknown>

  interface LegacyAssignmentsStore {
    fetchAssignmentById: (id: string) => Promise<AssignmentDetailRecord>
    fetchAssignmentHistory: (id: string) => Promise<AssignmentHistoryEvent[]>
    submitPrecuration: (id: string, data: FormData) => Promise<unknown>
    savePrecurationDraft: (id: string, data: FormData) => Promise<unknown>
    submitCuration: (id: string, data: FormData) => Promise<unknown>
    saveCurationDraft: (id: string, data: FormData) => Promise<unknown>
  }
  type ErrorLike = { message?: string; stack?: string }

  const logger = useLogger()
  const route = useRoute()
  // TODO(stage2): missing store API fetchAssignmentById, fetchAssignmentHistory,
  // submitPrecuration, savePrecurationDraft, submitCuration, saveCurationDraft -- the store has
  // none of them, so loadAssignmentData always fails into the error state.
  const assignmentsStore = useAssignmentsStore() as unknown as LegacyAssignmentsStore

  const loading = ref(false)
  const error = ref<string | null>(null)
  const activeTab = ref('precuration')
  const assignment = ref<AssignmentDetailRecord | null>(null)
  const precurationData = ref<FormData>({})
  const curationData = ref<FormData>({})
  const assignmentHistory = ref<AssignmentHistoryEvent[]>([])

  const assignmentId = computed(() => route.params.id as string)

  const canAccessCuration = computed(() => {
    return (
      assignment.value?.precuration_status === 'completed' ||
      assignment.value?.current_stage === 'curation' ||
      assignment.value?.current_stage === 'completed'
    )
  })

  const combinedEvidenceData = computed(() => {
    return {
      ...precurationData.value,
      ...curationData.value
    }
  })

  const currentScoringSchemaId = computed(() => {
    if (activeTab.value === 'precuration') {
      return assignment.value?.precuration_schema_id
    }
    return assignment.value?.curation_schema_id
  })

  // Helper functions
  const getStatusColor = (status: string): string => {
    const colorMap: Record<string, string> = {
      draft: 'grey',
      assigned: 'info',
      in_progress: 'primary',
      pending_review: 'warning',
      under_review: 'warning',
      completed: 'success',
      rejected: 'error',
      on_hold: 'orange'
    }
    return colorMap[status] || 'grey'
  }

  const formatStatus = (status: string): string => {
    return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString()
  }

  const formatDateTime = (dateString: string): string => {
    return new Date(dateString).toLocaleString()
  }

  const getDueDateClass = (dateString: string): string => {
    const dueDate = new Date(dateString)
    const today = new Date()
    const diffDays = Math.ceil((dueDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))

    if (diffDays < 0) return 'text-error'
    if (diffDays < 7) return 'text-warning'
    return 'text-success'
  }

  const getEventColor = (eventType: string): string => {
    const colorMap: Record<string, string> = {
      created: 'primary',
      assigned: 'info',
      precuration_submitted: 'success',
      curation_submitted: 'success',
      review_requested: 'warning',
      approved: 'success',
      rejected: 'error',
      draft_saved: 'grey'
    }
    return colorMap[eventType] || 'grey'
  }

  const getEventIcon = (eventType: string): string => {
    const iconMap: Record<string, string> = {
      created: 'mdi-plus',
      assigned: 'mdi-account-plus',
      precuration_submitted: 'mdi-file-check',
      curation_submitted: 'mdi-file-check',
      review_requested: 'mdi-eye',
      approved: 'mdi-check-circle',
      rejected: 'mdi-close-circle',
      draft_saved: 'mdi-content-save'
    }
    return iconMap[eventType] || 'mdi-circle'
  }

  const formatEventType = (eventType: string): string => {
    return eventType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  // Event handlers
  const handlePrecurationSubmit = async (data: FormData) => {
    try {
      await assignmentsStore.submitPrecuration(assignmentId.value, data)
      precurationData.value = data

      // Switch to curation tab if available
      if (canAccessCuration.value) {
        activeTab.value = 'curation'
      }
    } catch (error) {
      const err = error as ErrorLike
      logger.error('Precuration submission failed:', { error: err.message, stack: err.stack })
    }
  }

  const handlePrecurationDraft = async (data: FormData) => {
    try {
      await assignmentsStore.savePrecurationDraft(assignmentId.value, data)
      precurationData.value = data
    } catch (error) {
      const err = error as ErrorLike
      logger.error('Precuration draft save failed:', { error: err.message, stack: err.stack })
    }
  }

  const handleCurationSubmit = async (data: FormData) => {
    try {
      await assignmentsStore.submitCuration(assignmentId.value, data)
      curationData.value = data

      // Switch to scoring tab
      activeTab.value = 'scoring'
    } catch (error) {
      const err = error as ErrorLike
      logger.error('Curation submission failed:', { error: err.message, stack: err.stack })
    }
  }

  const handleCurationDraft = async (data: FormData) => {
    try {
      await assignmentsStore.saveCurationDraft(assignmentId.value, data)
      curationData.value = data
    } catch (error) {
      const err = error as ErrorLike
      logger.error('Curation draft save failed:', { error: err.message, stack: err.stack })
    }
  }

  const handleScoreUpdated = (scoreResult: Record<string, unknown>) => {
    logger.info('Scores updated:', scoreResult)
  }

  const handleClassificationChanged = (classification: Record<string, unknown>) => {
    logger.info('Classification changed:', classification)
  }

  // Data loading
  const loadAssignmentData = async () => {
    loading.value = true
    error.value = null

    try {
      const [assignmentData, historyData] = await Promise.all([
        assignmentsStore.fetchAssignmentById(assignmentId.value),
        assignmentsStore.fetchAssignmentHistory(assignmentId.value)
      ])

      assignment.value = assignmentData
      assignmentHistory.value = historyData

      // Load existing evidence data
      if (assignmentData.precuration_data) {
        precurationData.value = assignmentData.precuration_data
      }

      if (assignmentData.curation_data) {
        curationData.value = assignmentData.curation_data
      }
    } catch (err) {
      const e = err as ErrorLike
      error.value = e.message || 'Failed to load assignment'
      logger.error('Failed to load assignment:', { error: e.message, stack: e.stack })
    } finally {
      loading.value = false
    }
  }

  // Watch for route changes
  watch(
    () => route.params.id,
    newId => {
      if (newId) {
        loadAssignmentData()
      }
    }
  )

  onMounted(() => {
    loadAssignmentData()
  })
</script>

<style scoped>
  .v-window {
    min-height: 400px;
  }
</style>
