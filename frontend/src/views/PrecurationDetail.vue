<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <!-- Header -->
        <div class="d-flex justify-space-between align-center mb-6">
          <div>
            <v-btn icon variant="text" class="mr-3" @click="$router.back()">
              <v-icon>mdi-arrow-left</v-icon>
            </v-btn>
            <h1 class="text-h4 d-inline">Pre-curation Details</h1>
          </div>
          <div class="d-flex gap-2">
            <v-btn
              v-if="canEdit && !isEditing"
              color="primary"
              variant="outlined"
              prepend-icon="mdi-pencil"
              @click="startEditing"
            >
              Edit
            </v-btn>
            <v-btn
              v-if="canCreateCuration"
              color="success"
              prepend-icon="mdi-arrow-right-circle"
              @click="createCuration"
            >
              Create Curation
            </v-btn>
          </div>
        </div>

        <!-- Loading State -->
        <v-card v-if="loading" class="text-center py-8">
          <v-progress-circular indeterminate color="primary" />
          <p class="mt-4">Loading pre-curation details...</p>
        </v-card>

        <!-- Error State -->
        <v-alert v-else-if="error" type="error" class="mb-4">
          {{ error }}
        </v-alert>

        <!-- Content -->
        <div v-else-if="precuration">
          <!-- Status and Basic Info -->
          <v-row class="mb-6">
            <v-col cols="12" md="8">
              <v-card>
                <v-card-title class="d-flex align-center">
                  <v-icon start>mdi-clipboard-text</v-icon>
                  Pre-curation Information
                </v-card-title>
                <v-card-text>
                  <v-row>
                    <v-col cols="12" md="6">
                      <div class="mb-4">
                        <div class="text-caption text-medium-emphasis">Gene Symbol</div>
                        <v-chip
                          :to="{ name: 'GeneDetail', params: { id: precuration.gene_id } }"
                          color="primary"
                          variant="outlined"
                          clickable
                          class="mt-1"
                        >
                          <v-icon start>mdi-dna</v-icon>
                          {{ precuration.gene?.approved_symbol || 'Unknown' }}
                        </v-chip>
                      </div>
                      <div class="mb-4">
                        <div class="text-caption text-medium-emphasis">MONDO ID</div>
                        <v-chip
                          :href="`https://monarchinitiative.org/disease/${precuration.mondo_id}`"
                          target="_blank"
                          color="info"
                          variant="outlined"
                          clickable
                          class="mt-1"
                        >
                          {{ precuration.mondo_id }}
                          <v-icon end size="small">mdi-open-in-new</v-icon>
                        </v-chip>
                      </div>
                      <div class="mb-4">
                        <div class="text-caption text-medium-emphasis">Mode of Inheritance</div>
                        <v-chip
                          :color="getInheritanceColor(precuration.mode_of_inheritance)"
                          variant="tonal"
                          class="mt-1"
                        >
                          {{ precuration.mode_of_inheritance }}
                        </v-chip>
                      </div>
                    </v-col>
                    <v-col cols="12" md="6">
                      <div class="mb-4">
                        <div class="text-caption text-medium-emphasis">Status</div>
                        <v-chip
                          :color="getStatusColor(precuration.status)"
                          variant="tonal"
                          class="mt-1"
                        >
                          {{ precuration.status.replace('_', ' ') }}
                        </v-chip>
                      </div>
                      <div class="mb-4">
                        <div class="text-caption text-medium-emphasis">
                          Lumping/Splitting Decision
                        </div>
                        <v-chip
                          :color="getDecisionColor(precuration.lumping_splitting_decision)"
                          :variant="
                            precuration.lumping_splitting_decision === 'Undecided'
                              ? 'outlined'
                              : 'tonal'
                          "
                          class="mt-1"
                        >
                          {{ precuration.lumping_splitting_decision }}
                        </v-chip>
                      </div>
                      <div class="mb-4">
                        <div class="text-caption text-medium-emphasis">Created</div>
                        <div class="text-body-1 mt-1">{{ formatDate(precuration.created_at) }}</div>
                      </div>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>
            </v-col>

            <v-col cols="12" md="4">
              <!-- Workflow Actions -->
              <v-card>
                <v-card-title>
                  <v-icon start>mdi-workflow</v-icon>
                  Workflow Actions
                </v-card-title>
                <v-card-text>
                  <div class="d-flex flex-column gap-2">
                    <v-btn
                      v-if="canSubmitForReview"
                      color="primary"
                      variant="outlined"
                      prepend-icon="mdi-send"
                      block
                      @click="submitForReview"
                    >
                      Submit for Review
                    </v-btn>
                    <v-btn
                      v-if="canApprove"
                      color="success"
                      variant="outlined"
                      prepend-icon="mdi-check"
                      block
                      @click="approve"
                    >
                      Approve
                    </v-btn>
                    <v-btn
                      v-if="authStore.isAdmin"
                      color="error"
                      variant="outlined"
                      prepend-icon="mdi-delete"
                      block
                      @click="deletePrecuration"
                    >
                      Delete
                    </v-btn>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <!-- Gene Information (if available) -->
          <v-row v-if="precuration.gene" class="mb-6">
            <v-col cols="12">
              <v-card>
                <v-card-title>
                  <v-icon start>mdi-dna</v-icon>
                  Gene Information
                </v-card-title>
                <v-card-text>
                  <v-row>
                    <v-col cols="12" md="3">
                      <div class="text-caption text-medium-emphasis">Gene Symbol</div>
                      <div class="text-body-1 font-weight-medium">
                        {{ precuration.gene.approved_symbol }}
                      </div>
                    </v-col>
                    <v-col cols="12" md="3">
                      <div class="text-caption text-medium-emphasis">HGNC ID</div>
                      <div class="text-body-1">{{ precuration.gene.hgnc_id }}</div>
                    </v-col>
                    <v-col cols="12" md="3">
                      <div class="text-caption text-medium-emphasis">Chromosome</div>
                      <div class="text-body-1">{{ precuration.gene.chromosome || 'Unknown' }}</div>
                    </v-col>
                    <v-col cols="12" md="3">
                      <div class="text-caption text-medium-emphasis">Dyadic Name</div>
                      <div class="text-body-1">
                        {{ precuration.gene.current_dyadic_name || 'Not set' }}
                      </div>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <!-- Rationale -->
          <v-row class="mb-6">
            <v-col cols="12">
              <v-card>
                <v-card-title>
                  <v-icon start>mdi-text-box</v-icon>
                  Rationale
                </v-card-title>
                <v-card-text>
                  <div class="text-body-1 whitespace-pre-wrap">
                    {{ precuration.rationale || 'No rationale provided' }}
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <!-- Metadata -->
          <v-row>
            <v-col cols="12">
              <v-card>
                <v-card-title>
                  <v-icon start>mdi-information</v-icon>
                  Metadata
                </v-card-title>
                <v-card-text>
                  <v-row>
                    <v-col cols="12" md="4">
                      <div class="text-caption text-medium-emphasis">Created At</div>
                      <div class="text-body-1">{{ formatDateTime(precuration.created_at) }}</div>
                    </v-col>
                    <v-col cols="12" md="4">
                      <div class="text-caption text-medium-emphasis">Updated At</div>
                      <div class="text-body-1">{{ formatDateTime(precuration.updated_at) }}</div>
                    </v-col>
                    <v-col cols="12" md="4">
                      <div class="text-caption text-medium-emphasis">Contributors</div>
                      <div class="text-body-1">
                        <v-chip
                          v-for="contributor in precuration.contributors || []"
                          :key="contributor"
                          size="small"
                          variant="outlined"
                          class="mr-1"
                        >
                          {{ contributor }}
                        </v-chip>
                        <span v-if="!precuration.contributors?.length" class="text-medium-emphasis"
                          >None</span
                        >
                      </div>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </div>

        <!-- Edit Form Dialog -->
        <v-dialog v-model="editDialog" max-width="800px" scrollable>
          <v-card>
            <v-card-title>
              <span class="text-h5">Edit Pre-curation</span>
            </v-card-title>
            <v-card-text>
              <PrecurationForm
                v-if="precuration"
                :precuration="precuration"
                @submit="handleUpdate"
                @cancel="cancelEditing"
              />
            </v-card-text>
          </v-card>
        </v-dialog>

        <!-- Confirmation Dialog -->
        <v-dialog v-model="confirmDialog" max-width="400px">
          <v-card>
            <v-card-title>{{ confirmTitle }}</v-card-title>
            <v-card-text>{{ confirmMessage }}</v-card-text>
            <v-card-actions>
              <v-spacer />
              <v-btn @click="confirmDialog = false">Cancel</v-btn>
              <v-btn
                :color="confirmAction.color"
                :loading="actionLoading"
                @click="executeConfirmedAction"
              >
                {{ confirmAction.text }}
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { useLogger } from '@/composables/useLogger'

const logger = useLogger()
  import { ref, computed, onMounted } from 'vue'
  import { useRouter } from 'vue-router'
  import { usePrecurationsStore, useAuthStore } from '@/stores'
  import { showError, showSuccess } from '@/composables/useNotifications.js'
  import PrecurationForm from '@/components/clingen/PrecurationForm.vue'

  const props = defineProps({
    id: {
      type: String,
      required: true
    }
  })

  const router = useRouter()
  const precurationsStore = usePrecurationsStore()
  const authStore = useAuthStore()

  // Reactive state
  const precuration = ref(null)
  const loading = ref(true)
  const error = ref(null)
  const isEditing = ref(false)
  const editDialog = ref(false)
  const confirmDialog = ref(false)
  const actionLoading = ref(false)
  const confirmTitle = ref('')
  const confirmMessage = ref('')
  const confirmAction = ref({ text: '', color: 'primary', callback: null })

  // Computed properties
  const canEdit = computed(() => {
    return (
      authStore.isCurator &&
      precuration.value &&
      ['Draft', 'In_Primary_Review'].includes(precuration.value.status)
    )
  })

  const canApprove = computed(() => {
    return authStore.isAdmin && precuration.value?.status === 'In_Primary_Review'
  })

  const canSubmitForReview = computed(() => {
    return authStore.isCurator && precuration.value?.status === 'Draft'
  })

  const canCreateCuration = computed(() => {
    return authStore.isCurator && precuration.value?.status === 'Approved'
  })

  // Utility functions
  const formatDate = dateString => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString()
  }

  const formatDateTime = dateString => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString()
  }

  const getStatusColor = status => {
    const colors = {
      Draft: 'grey',
      In_Primary_Review: 'orange',
      In_Secondary_Review: 'warning',
      Approved: 'success',
      Rejected: 'error'
    }
    return colors[status] || 'grey'
  }

  const getDecisionColor = decision => {
    const colors = {
      Lump: 'info',
      Split: 'warning',
      Undecided: 'grey'
    }
    return colors[decision] || 'grey'
  }

  const getInheritanceColor = inheritance => {
    const colors = {
      'Autosomal Dominant': 'blue',
      'Autosomal Recessive': 'green',
      'X-linked': 'purple',
      Mitochondrial: 'orange'
    }
    return colors[inheritance] || 'grey'
  }

  // Actions
  const startEditing = () => {
    editDialog.value = true
  }

  const cancelEditing = () => {
    editDialog.value = false
    isEditing.value = false
  }

  const handleUpdate = async updatedData => {
    try {
      actionLoading.value = true
      const updated = await precurationsStore.updatePrecuration(props.id, updatedData)
      precuration.value = updated
      showSuccess('Pre-curation updated successfully')
      editDialog.value = false
      isEditing.value = false
    } catch (error) {
      showError('Failed to update pre-curation')
    } finally {
      actionLoading.value = false
    }
  }

  const submitForReview = () => {
    confirmTitle.value = 'Submit for Review'
    confirmMessage.value = `Submit this pre-curation for ${precuration.value.gene?.approved_symbol} for review?`
    confirmAction.value = {
      text: 'Submit',
      color: 'primary',
      callback: () => workflowAction('submit_for_review')
    }
    confirmDialog.value = true
  }

  const approve = () => {
    confirmTitle.value = 'Approve Pre-curation'
    confirmMessage.value = `Are you sure you want to approve this pre-curation for ${precuration.value.gene?.approved_symbol}?`
    confirmAction.value = {
      text: 'Approve',
      color: 'success',
      callback: () => workflowAction('approve')
    }
    confirmDialog.value = true
  }

  const deletePrecuration = () => {
    confirmTitle.value = 'Delete Pre-curation'
    confirmMessage.value =
      'Are you sure you want to delete this pre-curation? This action cannot be undone.'
    confirmAction.value = {
      text: 'Delete',
      color: 'error',
      callback: async () => {
        await precurationsStore.deletePrecuration(props.id)
        router.push({ name: 'Precurations' })
      }
    }
    confirmDialog.value = true
  }

  const createCuration = () => {
    router.push({
      name: 'CreateCuration',
      query: {
        precuration_id: props.id,
        gene_id: precuration.value.gene_id
      }
    })
  }

  const workflowAction = async action => {
    try {
      actionLoading.value = true
      const updated = await precurationsStore.workflowAction(props.id, { action })
      precuration.value = updated
      showSuccess(`Pre-curation ${action.replace('_', ' ')} successful`)
    } catch (error) {
      showError(`Failed to ${action.replace('_', ' ')} pre-curation`)
    } finally {
      actionLoading.value = false
    }
  }

  const executeConfirmedAction = async () => {
    try {
      actionLoading.value = true
      await confirmAction.value.callback()
      confirmDialog.value = false
    } catch (error) {
      showError('Action failed')
    } finally {
      actionLoading.value = false
    }
  }

  // Load data
  const loadPrecuration = async () => {
    try {
      loading.value = true
      error.value = null
      precuration.value = await precurationsStore.fetchPrecurationById(props.id)
    } catch (err) {
      error.value = 'Failed to load pre-curation details'
      logger.error('Error loading precuration:', { error: err.message, stack: err.stack })
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    loadPrecuration()
  })
</script>

<style scoped>
  .gap-2 {
    gap: 8px;
  }

  .whitespace-pre-wrap {
    white-space: pre-wrap;
  }
</style>
