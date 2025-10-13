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
            <h1 class="text-h4 d-inline">ClinGen Curation Details</h1>
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
              color="info"
              variant="outlined"
              prepend-icon="mdi-download"
              @click="exportCuration"
            >
              Export
            </v-btn>
          </div>
        </div>

        <!-- Loading State -->
        <v-card v-if="loading" class="text-center py-8">
          <v-progress-circular indeterminate color="primary" />
          <p class="mt-4">Loading curation details...</p>
        </v-card>

        <!-- Error State -->
        <v-alert v-else-if="error" type="error" class="mb-4">
          {{ error }}
        </v-alert>

        <!-- Content -->
        <div v-else-if="curation">
          <!-- Basic Information and Score -->
          <v-row class="mb-6">
            <v-col cols="12" md="8">
              <v-card>
                <v-card-title class="d-flex align-center">
                  <v-icon start>mdi-clipboard-check-multiple</v-icon>
                  Gene-Disease Association
                </v-card-title>
                <v-card-text>
                  <v-row>
                    <v-col cols="12" md="6">
                      <div class="mb-4">
                        <div class="text-caption text-medium-emphasis">Gene Symbol</div>
                        <v-chip
                          :to="{ name: 'GeneDetail', params: { id: curation.gene_id } }"
                          color="primary"
                          variant="outlined"
                          clickable
                          class="mt-1"
                        >
                          <v-icon start>mdi-dna</v-icon>
                          {{ curation.gene?.approved_symbol || 'Unknown' }}
                        </v-chip>
                      </div>
                      <div class="mb-4">
                        <div class="text-caption text-medium-emphasis">Disease Name</div>
                        <div class="text-h6 mt-1">{{ curation.disease_name }}</div>
                      </div>
                      <div class="mb-4">
                        <div class="text-caption text-medium-emphasis">MONDO ID</div>
                        <v-chip
                          :href="`https://monarchinitiative.org/disease/${curation.mondo_id}`"
                          target="_blank"
                          color="info"
                          variant="outlined"
                          clickable
                          class="mt-1"
                        >
                          {{ curation.mondo_id }}
                          <v-icon end size="small">mdi-open-in-new</v-icon>
                        </v-chip>
                      </div>
                    </v-col>
                    <v-col cols="12" md="6">
                      <div class="mb-4">
                        <div class="text-caption text-medium-emphasis">Status</div>
                        <v-chip
                          :color="getStatusColor(curation.status)"
                          variant="tonal"
                          class="mt-1"
                        >
                          {{ curation.status.replace('_', ' ') }}
                        </v-chip>
                      </div>
                      <div class="mb-4">
                        <div class="text-caption text-medium-emphasis">GCEP Affiliation</div>
                        <v-chip color="info" variant="outlined" class="mt-1">
                          {{ curation.gcep_affiliation }}
                        </v-chip>
                      </div>
                      <div v-if="curation.has_contradictory_evidence" class="mb-4">
                        <div class="text-caption text-medium-emphasis">Contradictory Evidence</div>
                        <v-chip color="warning" variant="tonal" class="mt-1">
                          <v-icon start>mdi-alert-triangle</v-icon>
                          Present
                        </v-chip>
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
                      v-if="canPublish"
                      color="info"
                      variant="outlined"
                      prepend-icon="mdi-publish"
                      block
                      @click="publish"
                    >
                      Publish
                    </v-btn>
                    <v-btn
                      v-if="authStore.isAdmin"
                      color="error"
                      variant="outlined"
                      prepend-icon="mdi-delete"
                      block
                      @click="deleteCuration"
                    >
                      Delete
                    </v-btn>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <!-- ClinGen Score Card -->
          <v-row class="mb-6">
            <v-col cols="12">
              <ClinGenScoreCard :score="curation" :show-actions="false" />
            </v-col>
          </v-row>

          <!-- Evidence Summary -->
          <v-row v-if="curation.summary_text" class="mb-6">
            <v-col cols="12">
              <v-card>
                <v-card-title>
                  <v-icon start>mdi-text-box-outline</v-icon>
                  Evidence Summary
                </v-card-title>
                <v-card-text>
                  <div class="text-body-1 whitespace-pre-wrap">{{ curation.summary_text }}</div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <!-- Evidence Details -->
          <v-row v-if="curation.details" class="mb-6">
            <v-col cols="12">
              <v-card>
                <v-card-title>
                  <v-icon start>mdi-clipboard-list</v-icon>
                  Evidence Details
                </v-card-title>
                <v-card-text>
                  <v-tabs v-model="evidenceTab">
                    <v-tab value="genetic">Genetic Evidence</v-tab>
                    <v-tab value="experimental">Experimental Evidence</v-tab>
                    <v-tab v-if="curation.details.contradictory_evidence" value="contradictory"
                      >Contradictory Evidence</v-tab
                    >
                    <v-tab v-if="curation.details.lumping_splitting_details" value="lumping"
                      >Lumping/Splitting</v-tab
                    >
                  </v-tabs>

                  <v-tabs-window v-model="evidenceTab" class="mt-4">
                    <!-- Genetic Evidence -->
                    <v-tabs-window-item value="genetic">
                      <div v-if="curation.details.genetic_evidence">
                        <div
                          v-for="(evidence, category) in curation.details.genetic_evidence"
                          :key="category"
                          class="mb-4"
                        >
                          <h4 class="text-h6 mb-2 text-capitalize">
                            {{ category.replace('_', ' ') }}
                          </h4>
                          <v-card
                            v-for="(item, index) in evidence"
                            :key="index"
                            variant="outlined"
                            class="mb-2"
                          >
                            <v-card-text>
                              <div v-if="item.pmid" class="mb-2">
                                <strong>PMID:</strong>
                                <a
                                  :href="`https://pubmed.ncbi.nlm.nih.gov/${item.pmid}`"
                                  target="_blank"
                                  class="text-primary"
                                >
                                  {{ item.pmid }}
                                </a>
                              </div>
                              <div v-if="item.score" class="mb-2">
                                <strong>Score:</strong> {{ item.score }}
                              </div>
                              <div v-if="item.description">
                                <strong>Description:</strong> {{ item.description }}
                              </div>
                            </v-card-text>
                          </v-card>
                        </div>
                      </div>
                      <div v-else class="text-center py-4 text-medium-emphasis">
                        No genetic evidence recorded
                      </div>
                    </v-tabs-window-item>

                    <!-- Experimental Evidence -->
                    <v-tabs-window-item value="experimental">
                      <div v-if="curation.details.experimental_evidence">
                        <div
                          v-for="(evidence, category) in curation.details.experimental_evidence"
                          :key="category"
                          class="mb-4"
                        >
                          <h4 class="text-h6 mb-2 text-capitalize">
                            {{ category.replace('_', ' ') }}
                          </h4>
                          <v-card
                            v-for="(item, index) in evidence"
                            :key="index"
                            variant="outlined"
                            class="mb-2"
                          >
                            <v-card-text>
                              <div v-if="item.pmid" class="mb-2">
                                <strong>PMID:</strong>
                                <a
                                  :href="`https://pubmed.ncbi.nlm.nih.gov/${item.pmid}`"
                                  target="_blank"
                                  class="text-primary"
                                >
                                  {{ item.pmid }}
                                </a>
                              </div>
                              <div v-if="item.score" class="mb-2">
                                <strong>Score:</strong> {{ item.score }}
                              </div>
                              <div v-if="item.description">
                                <strong>Description:</strong> {{ item.description }}
                              </div>
                            </v-card-text>
                          </v-card>
                        </div>
                      </div>
                      <div v-else class="text-center py-4 text-medium-emphasis">
                        No experimental evidence recorded
                      </div>
                    </v-tabs-window-item>

                    <!-- Contradictory Evidence -->
                    <v-tabs-window-item value="contradictory">
                      <div v-if="curation.details.contradictory_evidence">
                        <v-card
                          v-for="(item, index) in curation.details.contradictory_evidence"
                          :key="index"
                          variant="outlined"
                          class="mb-2"
                        >
                          <v-card-text>
                            <div v-if="item.pmid" class="mb-2">
                              <strong>PMID:</strong>
                              <a
                                :href="`https://pubmed.ncbi.nlm.nih.gov/${item.pmid}`"
                                target="_blank"
                                class="text-primary"
                              >
                                {{ item.pmid }}
                              </a>
                            </div>
                            <div v-if="item.description">
                              <strong>Description:</strong> {{ item.description }}
                            </div>
                          </v-card-text>
                        </v-card>
                      </div>
                      <div v-else class="text-center py-4 text-medium-emphasis">
                        No contradictory evidence recorded
                      </div>
                    </v-tabs-window-item>

                    <!-- Lumping/Splitting Details -->
                    <v-tabs-window-item value="lumping">
                      <div v-if="curation.details.lumping_splitting_details">
                        <div class="text-body-1 whitespace-pre-wrap">
                          {{ curation.details.lumping_splitting_details }}
                        </div>
                      </div>
                      <div v-else class="text-center py-4 text-medium-emphasis">
                        No lumping/splitting details recorded
                      </div>
                    </v-tabs-window-item>
                  </v-tabs-window>
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
                    <v-col cols="12" md="3">
                      <div class="text-caption text-medium-emphasis">Created At</div>
                      <div class="text-body-1">{{ formatDateTime(curation.created_at) }}</div>
                    </v-col>
                    <v-col cols="12" md="3">
                      <div class="text-caption text-medium-emphasis">Updated At</div>
                      <div class="text-body-1">{{ formatDateTime(curation.updated_at) }}</div>
                    </v-col>
                    <v-col cols="12" md="3">
                      <div class="text-caption text-medium-emphasis">SOP Version</div>
                      <div class="text-body-1">{{ curation.sop_version || 'v11' }}</div>
                    </v-col>
                    <v-col cols="12" md="3">
                      <div class="text-caption text-medium-emphasis">Contributors</div>
                      <div class="text-body-1">
                        <v-chip
                          v-for="contributor in curation.contributors || []"
                          :key="contributor"
                          size="small"
                          variant="outlined"
                          class="mr-1"
                        >
                          {{ contributor }}
                        </v-chip>
                        <span v-if="!curation.contributors?.length" class="text-medium-emphasis"
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
        <v-dialog v-model="editDialog" max-width="1200px" scrollable>
          <v-card>
            <v-card-title>
              <span class="text-h5">Edit Curation</span>
            </v-card-title>
            <v-card-text>
              <CurationForm
                v-if="curation"
                :curation="curation"
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
  import { useCurationsStore, useAuthStore } from '@/stores'
  import { showError, showSuccess } from '@/composables/useNotifications.js'
  import ClinGenScoreCard from '@/components/clingen/ClinGenScoreCard.vue'
  import CurationForm from '@/components/clingen/CurationForm.vue'

  const props = defineProps({
    id: {
      type: String,
      required: true
    }
  })

  const router = useRouter()
  const curationsStore = useCurationsStore()
  const authStore = useAuthStore()

  // Reactive state
  const curation = ref(null)
  const loading = ref(true)
  const error = ref(null)
  const isEditing = ref(false)
  const editDialog = ref(false)
  const confirmDialog = ref(false)
  const actionLoading = ref(false)
  const confirmTitle = ref('')
  const confirmMessage = ref('')
  const confirmAction = ref({ text: '', color: 'primary', callback: null })
  const evidenceTab = ref('genetic')

  // Computed properties
  const canEdit = computed(() => {
    return (
      authStore.isCurator &&
      curation.value &&
      ['Draft', 'In_Primary_Review'].includes(curation.value.status)
    )
  })

  const canApprove = computed(() => {
    return authStore.isAdmin && curation.value?.status === 'In_Primary_Review'
  })

  const canSubmitForReview = computed(() => {
    return authStore.isCurator && curation.value?.status === 'Draft'
  })

  const canPublish = computed(() => {
    return authStore.isCurator && curation.value?.status === 'Approved'
  })

  // Utility functions
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
      Published: 'info',
      Rejected: 'error'
    }
    return colors[status] || 'grey'
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
      const updated = await curationsStore.updateCuration(props.id, updatedData)
      curation.value = updated
      showSuccess('Curation updated successfully')
      editDialog.value = false
      isEditing.value = false
    } catch (error) {
      showError('Failed to update curation')
    } finally {
      actionLoading.value = false
    }
  }

  const submitForReview = () => {
    confirmTitle.value = 'Submit for Review'
    confirmMessage.value = `Submit this curation for ${curation.value.gene?.approved_symbol} for review?`
    confirmAction.value = {
      text: 'Submit',
      color: 'primary',
      callback: () => workflowAction('submit_for_review')
    }
    confirmDialog.value = true
  }

  const approve = () => {
    confirmTitle.value = 'Approve Curation'
    confirmMessage.value = `Are you sure you want to approve this curation for ${curation.value.gene?.approved_symbol}?`
    confirmAction.value = {
      text: 'Approve',
      color: 'success',
      callback: () => workflowAction('approve')
    }
    confirmDialog.value = true
  }

  const publish = () => {
    confirmTitle.value = 'Publish Curation'
    confirmMessage.value = `Publish this curation for ${curation.value.gene?.approved_symbol}? It will be publicly available.`
    confirmAction.value = {
      text: 'Publish',
      color: 'info',
      callback: () => workflowAction('publish')
    }
    confirmDialog.value = true
  }

  const deleteCuration = () => {
    confirmTitle.value = 'Delete Curation'
    confirmMessage.value =
      'Are you sure you want to delete this curation? This action cannot be undone.'
    confirmAction.value = {
      text: 'Delete',
      color: 'error',
      callback: async () => {
        await curationsStore.deleteCuration(props.id)
        router.push({ name: 'Curations' })
      }
    }
    confirmDialog.value = true
  }

  const exportCuration = () => {
    // Create a downloadable JSON export of the curation
    const exportData = {
      ...curation.value,
      exported_at: new Date().toISOString(),
      sop_version: 'v11'
    }

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json'
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `curation_${curation.value.gene?.approved_symbol}_${props.id}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    showSuccess('Curation exported successfully')
  }

  const workflowAction = async action => {
    try {
      actionLoading.value = true
      const updated = await curationsStore.workflowAction(props.id, { action })
      curation.value = updated
      showSuccess(`Curation ${action.replace('_', ' ')} successful`)
    } catch (error) {
      showError(`Failed to ${action.replace('_', ' ')} curation`)
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
  const loadCuration = async () => {
    try {
      loading.value = true
      error.value = null
      curation.value = await curationsStore.fetchCuration(props.id)
    } catch (err) {
      error.value = 'Failed to load curation details'
      logger.error('Error loading curation:', { error: err.message, stack: err.stack })
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    loadCuration()
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
