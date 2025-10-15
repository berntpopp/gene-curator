<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <!-- Header -->
        <div class="d-flex justify-space-between align-center mb-6">
          <div class="d-flex align-center">
            <v-btn
              icon="mdi-arrow-left"
              variant="text"
              class="mr-3"
              aria-label="Go back"
              @click="goBack"
            />
            <h1 class="text-h4">Curation Details</h1>
          </div>
          <div class="d-flex gap-2">
            <v-btn
              v-if="canEdit"
              color="primary"
              variant="outlined"
              prepend-icon="mdi-pencil"
              @click="editCuration"
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
        <v-card v-if="loading" class="text-center py-12">
          <v-progress-circular indeterminate color="primary" size="64" />
          <p class="mt-4 text-h6">Loading curation details...</p>
        </v-card>

        <!-- Error State -->
        <v-alert v-else-if="error" type="error" variant="tonal" class="mb-4">
          <v-alert-title>{{ error }}</v-alert-title>
          <div>Failed to load curation details. Please try again.</div>
          <template #append>
            <v-btn variant="outlined" @click="loadCuration">Retry</v-btn>
          </template>
        </v-alert>

        <!-- Content -->
        <div v-else-if="curation">
          <!-- Basic Information -->
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
                        <v-chip color="primary" variant="outlined" class="mt-1">
                          <v-icon start>mdi-dna</v-icon>
                          {{ curation.gene_symbol || 'Unknown' }}
                        </v-chip>
                      </div>
                      <div class="mb-4">
                        <div class="text-caption text-medium-emphasis">Disease Name</div>
                        <div class="text-h6 mt-1">{{ curation.disease_name || 'N/A' }}</div>
                      </div>
                      <div v-if="curation.mondo_id" class="mb-4">
                        <div class="text-caption text-medium-emphasis">MONDO ID</div>
                        <v-chip
                          :href="`https://monarchinitiative.org/disease/${curation.mondo_id}`"
                          target="_blank"
                          color="info"
                          variant="outlined"
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
                          {{ formatStatus(curation.status) }}
                        </v-chip>
                      </div>
                      <div class="mb-4">
                        <div class="text-caption text-medium-emphasis">Curator</div>
                        <div class="text-body-1 mt-1">
                          {{ curation.curator_name || 'Unassigned' }}
                        </div>
                      </div>
                      <div class="mb-4">
                        <div class="text-caption text-medium-emphasis">Last Updated</div>
                        <div class="text-body-1 mt-1">{{ formatDate(curation.updated_at) }}</div>
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
                  Actions
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
                      v-if="canDelete"
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

          <!-- Score Card -->
          <v-row v-if="curation.calculated_score" class="mb-6">
            <v-col cols="12">
              <ClinGenScoreCard :breakdown="curation.calculated_score" />
            </v-col>
          </v-row>

          <!-- Evidence Summary -->
          <v-row v-if="curation.summary" class="mb-6">
            <v-col cols="12">
              <v-card>
                <v-card-title>
                  <v-icon start>mdi-text-box-outline</v-icon>
                  Evidence Summary
                </v-card-title>
                <v-card-text>
                  <div class="text-body-1 whitespace-pre-wrap">{{ curation.summary }}</div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
  /**
   * CurationDetailView
   *
   * Scope-aware wrapper for viewing curation details.
   * Displays full curation information with ClinGen score breakdown.
   *
   * Route: /scopes/:scopeId/curations/:curationId
   *
   * @example
   * router.push(`/scopes/${scopeId}/curations/${curationId}`)
   */

  import { ref, computed, onMounted } from 'vue'
  import { useRouter, useRoute } from 'vue-router'
  import { curationsAPI } from '@/api'
  import { useAuthStore } from '@/stores/auth'
  import { useNotificationsStore } from '@/stores/notifications'
  import { useLogger } from '@/composables/useLogger'
  import ClinGenScoreCard from '@/components/clingen/ClinGenScoreCard.vue'

  const router = useRouter()
  const route = useRoute()
  const authStore = useAuthStore()
  const notificationStore = useNotificationsStore()
  const logger = useLogger()

  // Route params
  const scopeId = computed(() => route.params.scopeId)
  const curationId = computed(() => route.params.curationId)

  // State
  const curation = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Permissions
  const canEdit = computed(() => {
    const userRole = authStore.user?.role
    return (
      ['admin', 'scope_admin', 'curator'].includes(userRole) && curation.value?.status === 'draft'
    )
  })

  const canSubmitForReview = computed(() => {
    return canEdit.value && curation.value?.status === 'draft'
  })

  const canDelete = computed(() => {
    const userRole = authStore.user?.role
    const userId = authStore.user?.user_id
    return (
      ['admin', 'scope_admin'].includes(userRole) ||
      (curation.value?.curator_id === userId && curation.value?.status === 'draft')
    )
  })

  /**
   * Load curation data
   */
  async function loadCuration() {
    loading.value = true
    error.value = null

    try {
      const data = await curationsAPI.getCuration(curationId.value)
      curation.value = data

      logger.debug('Curation loaded', { curation_id: curationId.value })
    } catch (err) {
      error.value = 'Failed to load curation details'
      logger.error('Failed to load curation', {
        error: err.message,
        curation_id: curationId.value
      })
    } finally {
      loading.value = false
    }
  }

  /**
   * Navigate to edit page
   */
  function editCuration() {
    router.push({
      name: 'curation-edit',
      params: {
        scopeId: scopeId.value,
        curationId: curationId.value
      }
    })
  }

  /**
   * Submit curation for review
   */
  async function submitForReview() {
    if (!confirm('Submit this curation for review?')) return

    try {
      await curationsAPI.submitForReview(curationId.value)
      notificationStore.addToast('Curation submitted for review', 'success')
      await loadCuration() // Reload to update status
    } catch (err) {
      logger.error('Failed to submit curation', { error: err.message })
      notificationStore.addToast('Failed to submit curation', 'error')
    }
  }

  /**
   * Delete curation
   */
  async function deleteCuration() {
    if (!confirm('Delete this curation? This action cannot be undone.')) return

    try {
      await curationsAPI.deleteCuration(curationId.value)
      notificationStore.addToast('Curation deleted successfully', 'success')
      router.push({ name: 'scope-dashboard', params: { scopeId: scopeId.value } })
    } catch (err) {
      logger.error('Failed to delete curation', { error: err.message })
      notificationStore.addToast('Failed to delete curation', 'error')
    }
  }

  /**
   * Export curation as JSON
   */
  function exportCuration() {
    const exportData = {
      ...curation.value,
      exported_at: new Date().toISOString()
    }

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json'
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `curation_${curation.value.gene_symbol}_${curationId.value}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    notificationStore.addToast('Curation exported successfully', 'success')
  }

  /**
   * Go back to previous page or scope dashboard
   */
  function goBack() {
    router.push({ name: 'scope-dashboard', params: { scopeId: scopeId.value } })
  }

  /**
   * Get status color
   */
  function getStatusColor(status) {
    const colors = {
      draft: 'grey',
      submitted: 'info',
      under_review: 'warning',
      approved: 'success',
      active: 'primary',
      rejected: 'error'
    }
    return colors[status] || 'grey'
  }

  /**
   * Format status label
   */
  function formatStatus(status) {
    if (!status) return 'Unknown'
    return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  /**
   * Format date
   */
  function formatDate(dateString) {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString()
  }

  // Lifecycle
  onMounted(() => {
    loadCuration()
  })
</script>

<style scoped>
  /* Header styling */
  .gap-2 {
    gap: 8px;
  }

  .whitespace-pre-wrap {
    white-space: pre-wrap;
  }

  /* Ensure proper spacing */
  .v-container {
    max-width: 1400px;
  }
</style>
