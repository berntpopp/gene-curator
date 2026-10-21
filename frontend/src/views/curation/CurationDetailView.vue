<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <!-- Header -->
        <div class="d-flex justify-space-between align-center mb-6">
          <div class="d-flex align-center">
            <v-btn aria-label="Go back" icon variant="text" class="mr-3" @click="goBack">
              <v-icon>mdi-arrow-left</v-icon>
            </v-btn>
            <h1 class="text-h4 d-inline">{{ pageTitle }}</h1>
          </div>
          <div class="d-flex ga-2">
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
          <!-- Classification Banner -->
          <v-card class="mb-6" :color="classificationColor" variant="tonal">
            <v-card-text>
              <v-row align="center">
                <v-col cols="12" md="4" class="text-center text-md-left">
                  <div class="text-h2 font-weight-bold">
                    {{ scores.total.toFixed(2) }}
                  </div>
                  <div class="text-subtitle-1">Total Points</div>
                </v-col>
                <v-col cols="12" md="4" class="text-center">
                  <v-chip :color="classificationColor" size="x-large" variant="elevated">
                    {{ classification }}
                  </v-chip>
                  <div class="text-caption mt-2">Gene-Disease Validity Classification</div>
                </v-col>
                <v-col cols="12" md="4">
                  <div class="d-flex justify-center justify-md-end ga-6">
                    <div class="text-center">
                      <div class="text-h5 font-weight-medium">{{ scores.genetic.toFixed(2) }}</div>
                      <div class="text-caption">Genetic (max 12)</div>
                    </div>
                    <v-divider vertical />
                    <div class="text-center">
                      <div class="text-h5 font-weight-medium">
                        {{ scores.experimental.toFixed(2) }}
                      </div>
                      <div class="text-caption">Experimental (max 6)</div>
                    </div>
                  </div>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- Main Info Row -->
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
                        <div class="d-flex align-center ga-2 mt-1">
                          <v-chip color="primary" variant="tonal" size="large">
                            <v-icon start>mdi-dna</v-icon>
                            {{ curation.gene_symbol || 'Unknown' }}
                          </v-chip>
                          <v-chip
                            v-if="curation.hgnc_id"
                            :href="`https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/${curation.hgnc_id}`"
                            target="_blank"
                            variant="outlined"
                            size="small"
                          >
                            {{ curation.hgnc_id }}
                            <v-icon end size="x-small">mdi-open-in-new</v-icon>
                          </v-chip>
                        </div>
                      </div>
                      <div class="mb-4">
                        <div class="text-caption text-medium-emphasis">Disease Name</div>
                        <div class="text-h6 mt-1">
                          {{ curation.disease_name || 'Not specified' }}
                        </div>
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
                        <div class="text-caption text-medium-emphasis">Mode of Inheritance</div>
                        <v-chip
                          v-if="curation.mode_of_inheritance"
                          :color="getInheritanceColor(curation.mode_of_inheritance)"
                          variant="tonal"
                          class="mt-1"
                        >
                          {{ formatInheritance(curation.mode_of_inheritance) }}
                        </v-chip>
                        <span v-else class="text-body-1 mt-1">Not specified</span>
                      </div>
                      <div class="mb-4">
                        <div class="text-caption text-medium-emphasis">Status</div>
                        <v-chip
                          :color="curationStatusColor(curation.status)"
                          variant="tonal"
                          class="mt-1"
                        >
                          {{ curationStatusLabel(curation.status) }}
                        </v-chip>
                      </div>
                      <div class="mb-4">
                        <div class="text-caption text-medium-emphasis">Curator</div>
                        <div class="text-body-1 mt-1">
                          <v-icon start size="small">mdi-account</v-icon>
                          {{ curation.curator_name || 'Unassigned' }}
                        </div>
                      </div>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>
            </v-col>

            <v-col cols="12" md="4">
              <!-- Workflow Actions -->
              <v-card class="workflow-actions">
                <v-card-title>
                  <v-icon start>mdi-cog</v-icon>
                  Workflow Actions
                </v-card-title>
                <v-card-text>
                  <div
                    v-if="curation.status === 'in_review'"
                    class="text-body-2 text-medium-emphasis mb-3"
                  >
                    Submitted by {{ curation.curator_name || 'unknown' }}
                    {{ formatDateTime(curation.updated_at) }}
                  </div>
                  <div class="d-flex flex-column ga-2">
                    <v-btn
                      v-if="canSubmitForReview"
                      color="primary"
                      variant="elevated"
                      prepend-icon="mdi-send"
                      block
                      @click="showSubmitDialog = true"
                    >
                      Submit for Review
                    </v-btn>
                    <!-- Review Actions (for submitted curations) -->
                    <v-btn
                      v-if="canReview"
                      color="success"
                      variant="elevated"
                      prepend-icon="mdi-check-circle"
                      block
                      @click="openReview('approve')"
                    >
                      Approve
                    </v-btn>
                    <v-btn
                      v-if="canReview"
                      color="warning"
                      variant="outlined"
                      prepend-icon="mdi-undo"
                      block
                      @click="openReview('reject')"
                    >
                      Request Changes
                    </v-btn>
                    <v-divider v-if="canDelete && (canSubmitForReview || canReview)" class="my-2" />
                    <v-btn
                      v-if="canDelete"
                      color="error"
                      variant="outlined"
                      prepend-icon="mdi-delete"
                      block
                      data-test="delete"
                      @click="showDeleteDialog = true"
                    >
                      Delete
                    </v-btn>
                    <div
                      v-if="!canSubmitForReview && !canDelete && !canReview"
                      class="text-body-2 text-medium-emphasis text-center py-2"
                    >
                      {{
                        isAuthorInReview
                          ? 'Waiting for review by another scope reviewer (4-eyes)'
                          : 'No actions available'
                      }}
                    </div>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <!-- Score Breakdown -->
          <v-row class="mb-6">
            <v-col cols="12">
              <CurationScoreBreakdown :scores="scores" />
            </v-col>
          </v-row>

          <!-- Evidence Details (Schema-Agnostic) -->
          <v-row v-if="isClinGenSchema || curationSchemaId" class="mb-6">
            <v-col cols="12">
              <v-card>
                <v-card-title>
                  <v-icon start>mdi-file-document-outline</v-icon>
                  Evidence Details
                </v-card-title>
                <v-card-text>
                  <CurationEvidenceReadonly
                    v-if="isClinGenSchema"
                    :evidence="evidence"
                    :moi="curation.mode_of_inheritance ?? undefined"
                  />
                  <DynamicForm
                    v-else-if="curationSchemaId"
                    :schema-id="curationSchemaId"
                    :initial-data="curation.evidence_data || {}"
                    :readonly="true"
                    title=""
                  />
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
                      <div class="text-caption text-medium-emphasis">Workflow Stage</div>
                      <div class="text-body-1">{{ curation.workflow_stage }}</div>
                    </v-col>
                    <v-col cols="12" md="3">
                      <div class="text-caption text-medium-emphasis">Version</div>
                      <div class="text-body-1">{{ curation.lock_version }}</div>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </div>
      </v-col>
    </v-row>

    <!-- Submit Confirmation Dialog -->
    <v-dialog v-model="showSubmitDialog" max-width="500">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start color="primary">mdi-send</v-icon>
          Submit for Review
        </v-card-title>
        <v-card-text>
          <p>
            Submit this curation for <strong>{{ curation?.gene_symbol }}</strong> for review?
          </p>
          <p class="text-body-2 text-medium-emphasis mt-2">
            Once submitted, the curation will be locked for editing until the review is complete.
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showSubmitDialog = false">Cancel</v-btn>
          <v-btn color="primary" variant="elevated" :loading="submitting" @click="submitForReview">
            Submit
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="showDeleteDialog" max-width="500">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start color="error">mdi-delete-alert</v-icon>
          Delete Curation
        </v-card-title>
        <v-card-text>
          <v-alert type="warning" variant="tonal" class="mb-4">
            This action cannot be undone.
          </v-alert>
          <p>
            Are you sure you want to delete the curation for
            <strong>{{ curation?.gene_symbol }}</strong
            >?
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDeleteDialog = false">Cancel</v-btn>
          <v-btn color="error" variant="elevated" :loading="deleting" @click="deleteCuration">
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <CurationReviewDialogs
      v-model:approve-open="showApproveDialog"
      v-model:reject-open="showRejectDialog"
      :gene-symbol="curation?.gene_symbol"
      :classification="classification"
      :scores="scores"
      :summary="evidence.evidence_summary"
      :counts="evidenceCountsText(curation?.evidence_data)"
      :busy="approving || rejecting"
      :error-detail="reviewError"
      @approve="approveCuration"
      @reject="rejectCuration"
    />
  </v-container>
</template>

<script setup lang="ts">
  import { ref, computed, onMounted } from 'vue'
  import { useRouter, useRoute } from 'vue-router'
  import { curationsAPI, workflowAPI, schemasAPI } from '@/api'
  import { curationStatusColor, curationStatusLabel } from '@/config/status'
  import { useNotificationsStore } from '@/stores/notifications'
  import { useLogger } from '@/composables/useLogger'
  import { useAuthStore } from '@/stores/auth'
  import DynamicForm from '@/components/dynamic/DynamicForm.vue'
  import CurationScoreBreakdown from '@/components/curation/CurationScoreBreakdown.vue'
  import CurationEvidenceReadonly from '@/components/curation/CurationEvidenceReadonly.vue'
  import CurationReviewDialogs from '@/components/curation/CurationReviewDialogs.vue'
  import { evidenceCountsText } from '@/components/curation/evidenceCounts'
  import type { ClinGenEvidenceData } from '@/components/clingen/types'
  import { computeScores, classifyScores, type EvidenceData } from './curationScores'

  interface CurationRecord {
    status: string
    workflow_pair_id?: string
    evidence_data?: EvidenceData | null
    gene_symbol?: string | null
    hgnc_id?: string | null
    disease_name?: string | null
    mondo_id?: string | null
    mode_of_inheritance?: string | null
    workflow_stage?: string | null
    curator_name?: string | null
    created_by?: string | null
    lock_version?: number | null
    created_at?: string | null
    updated_at?: string | null
    can_edit?: boolean
    can_delete?: boolean
    can_review?: boolean
  }

  // Error shape from axios (API) and plain Error alike
  interface ErrorLike {
    message?: string
    response?: { data?: { detail?: string } }
  }

  const router = useRouter()
  const route = useRoute()
  const notificationStore = useNotificationsStore()
  const logger = useLogger()
  const authStore = useAuthStore()

  // Route params
  const scopeId = computed(() => route.params.scopeId as string)
  const curationId = computed(() => route.params.curationId as string)

  // State
  // Null until loaded; the template renders only once loaded. Typed non-null because
  // vue-tsc drops v-if narrowing inside slot closures and after awaits.
  const curation = ref(null as unknown as CurationRecord)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const showSubmitDialog = ref(false)
  const showDeleteDialog = ref(false)
  const showApproveDialog = ref(false)
  const showRejectDialog = ref(false)
  const submitting = ref(false)
  const deleting = ref(false)
  const approving = ref(false)
  const rejecting = ref(false)
  const reviewError = ref<string | null>(null)
  const curationSchemaId = ref<string | null>(null)

  const evidence = computed(
    () => (curation.value?.evidence_data ?? {}) as Partial<ClinGenEvidenceData>
  )
  // ClinGen schemas (by scoring engine) get the read-only evidence view
  const isClinGenSchema = ref(false)
  const pageTitle = computed(() =>
    curation.value?.gene_symbol
      ? [curation.value.gene_symbol, curation.value.disease_name].filter(Boolean).join(' – ')
      : 'Curation Details'
  )
  const isAuthorInReview = computed(
    () =>
      curation.value?.status === 'in_review' &&
      !!curation.value.created_by &&
      curation.value.created_by === (authStore.user as { id?: string } | null)?.id
  )

  // Calculate scores from evidence_data
  const scores = computed(() => computeScores(curation.value?.evidence_data))

  // Classification based on score
  const classification = computed(() => {
    const evidence = curation.value?.evidence_data as
      { contradictory_evidence?: unknown[]; replicated_over_time?: boolean } | undefined
    return classifyScores(
      scores.value.total,
      scores.value.genetic,
      (evidence?.contradictory_evidence?.length ?? 0) > 0,
      evidence?.replicated_over_time === true
    )
  })

  const classificationColor = computed<string>(() => {
    const colors: Record<string, string> = {
      Definitive: 'success',
      Strong: 'info',
      Moderate: 'warning',
      Limited: 'orange',
      'No Known Disease Relationship': 'grey'
    }
    return colors[classification.value] || 'grey'
  })

  // Permissions - use backend-computed values based on scope-specific roles
  const canEdit = computed(() => {
    // Use backend-provided permission if available
    return curation.value?.can_edit ?? false
  })

  const canSubmitForReview = computed(() => {
    return canEdit.value && curation.value?.status === 'draft'
  })

  const canDelete = computed(() => {
    // Use backend-provided permission if available
    return curation.value?.can_delete ?? false
  })

  // Can review: backend checks scope-specific roles and 4-eyes principle
  const canReview = computed(() => {
    // Use backend-provided permission if available
    return curation.value?.can_review ?? false
  })

  // Utility functions
  const formatDateTime = (dateString: string | null | undefined): string => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString()
  }

  const formatInheritance = (moi: string): string => {
    const labels: Record<string, string> = {
      AD: 'Autosomal Dominant',
      AR: 'Autosomal Recessive',
      XLD: 'X-linked Dominant',
      XLR: 'X-linked Recessive',
      MT: 'Mitochondrial'
    }
    return labels[moi] || moi.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  }

  const getInheritanceColor = (moi: string): string => {
    const colors: Record<string, string> = {
      AD: 'blue',
      AR: 'green',
      XLD: 'purple',
      XLR: 'purple',
      MT: 'orange'
    }
    return colors[moi] || 'grey'
  }

  // Actions
  async function loadCurationSchema() {
    if (!curation.value?.workflow_pair_id) return
    try {
      const workflowPair = await schemasAPI.getWorkflowPairById(curation.value.workflow_pair_id)
      curationSchemaId.value = workflowPair.curation_schema_id || null
      if (curationSchemaId.value) {
        const schema = await schemasAPI.getSchemaById(curationSchemaId.value)
        isClinGenSchema.value = schema.scoring_configuration?.engine === 'clingen_sop_v11'
      }
      logger.debug('Curation schema loaded', {
        workflow_pair_id: curation.value.workflow_pair_id,
        curation_schema_id: curationSchemaId.value
      })
    } catch (err) {
      logger.warn('Failed to load curation schema for evidence display', {
        error: (err as ErrorLike).message,
        workflow_pair_id: curation.value.workflow_pair_id
      })
    }
  }

  async function loadCuration() {
    loading.value = true
    error.value = null

    try {
      const data = await curationsAPI.getCuration(curationId.value)
      curation.value = data as CurationRecord
      logger.debug('Curation loaded', { curation_id: curationId.value })
      await loadCurationSchema()
    } catch (err) {
      error.value = 'Failed to load curation details'
      logger.error('Failed to load curation', {
        error: (err as ErrorLike).message,
        curation_id: curationId.value
      })
    } finally {
      loading.value = false
    }
  }

  function editCuration() {
    router.push({
      name: 'curation-edit',
      params: { scopeId: scopeId.value, curationId: curationId.value }
    })
  }

  async function submitForReview() {
    submitting.value = true
    try {
      // Use submitCuration with lock_version for optimistic locking
      await curationsAPI.submitCuration(curationId.value, {
        lock_version: curation.value?.lock_version ?? 0,
        notes: null
      })
      showSubmitDialog.value = false
      notificationStore.addToast('Curation submitted for review', 'success')
      await loadCuration()
    } catch (err) {
      const errorDetail = (err as ErrorLike).response?.data?.detail || (err as ErrorLike).message
      logger.error('Failed to submit curation', { error: errorDetail })
      notificationStore.addToast(`Failed to submit: ${errorDetail}`, 'error')
    } finally {
      submitting.value = false
    }
  }

  async function deleteCuration() {
    deleting.value = true
    try {
      await curationsAPI.deleteCuration(curationId.value)
      showDeleteDialog.value = false
      notificationStore.addToast('Curation deleted successfully', 'success')
      router.push({ name: 'scope-dashboard', params: { scopeId: scopeId.value } })
    } catch (err) {
      logger.error('Failed to delete curation', { error: (err as ErrorLike).message })
      notificationStore.addToast('Failed to delete curation', 'error')
    } finally {
      deleting.value = false
    }
  }

  function openReview(kind: 'approve' | 'reject') {
    reviewError.value = null
    if (kind === 'approve') showApproveDialog.value = true
    else showRejectDialog.value = true
  }

  // Shared by both review dialogs: show the API detail inside the dialog, not just a toast
  async function transition(
    target_stage: 'active' | 'curation',
    notes: string | null,
    doneMessage: string
  ) {
    reviewError.value = null
    try {
      await workflowAPI.transitionCuration(curationId.value, { target_stage, notes })
      showApproveDialog.value = false
      showRejectDialog.value = false
      notificationStore.addToast(doneMessage, 'success')
      await loadCuration()
    } catch (err) {
      const detail = (err as ErrorLike).response?.data?.detail || (err as ErrorLike).message
      reviewError.value = detail ?? 'Request failed'
      logger.error('Failed review transition', { target_stage, error: detail })
    }
  }

  async function approveCuration(comment: string) {
    approving.value = true
    await transition('active', comment || null, 'Curation approved and activated')
    approving.value = false
  }

  async function rejectCuration(comment: string) {
    rejecting.value = true
    await transition('curation', comment, 'Curation returned to curator for changes')
    rejecting.value = false
  }

  function exportCuration() {
    const exportData = {
      ...curation.value,
      calculated_scores: scores.value,
      classification: classification.value,
      exported_at: new Date().toISOString()
    }

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `curation_${curation.value?.gene_symbol || 'unknown'}_${curationId.value}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    notificationStore.addToast('Curation exported successfully', 'success')
  }

  function goBack() {
    // Return to wherever the user came from (e.g. the Review Queue), else the scope dashboard
    if (window.history.state?.back) return router.back()
    router.push({ name: 'scope-dashboard', params: { scopeId: scopeId.value } })
  }

  // Lifecycle
  onMounted(() => {
    loadCuration()
  })
</script>

<style scoped></style>
