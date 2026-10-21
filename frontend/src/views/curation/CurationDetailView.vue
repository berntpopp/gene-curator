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
            <h1 class="text-headline-large d-inline">{{ pageTitle }}</h1>
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
          <v-card class="mb-6" variant="outlined">
            <v-card-text>
              <v-row align="center">
                <v-col cols="12" md="4" class="text-center text-md-left">
                  <div class="text-display-large font-weight-bold">
                    {{ scores.total.toFixed(2) }}
                  </div>
                  <div class="text-body-large">Total Points</div>
                </v-col>
                <v-col cols="12" md="4" class="text-center">
                  <ClassificationMark :classification="classification" class="text-title-large" />
                  <div class="text-body-small mt-2">Gene-Disease Validity Classification</div>
                </v-col>
                <v-col cols="12" md="4">
                  <div class="d-flex justify-center justify-md-end ga-6">
                    <div class="text-center">
                      <div class="text-headline-small font-weight-medium">
                        {{ scores.genetic.toFixed(2) }}
                      </div>
                      <div class="text-body-small">Genetic (max 12)</div>
                    </div>
                    <v-divider vertical />
                    <div class="text-center">
                      <div class="text-headline-small font-weight-medium">
                        {{ scores.experimental.toFixed(2) }}
                      </div>
                      <div class="text-body-small">Experimental (max 6)</div>
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
                        <div class="text-body-small text-medium-emphasis">Gene Symbol</div>
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
                        <div class="text-body-small text-medium-emphasis">Disease Name</div>
                        <div class="text-title-large mt-1">
                          {{ curation.disease_name || 'Not specified' }}
                        </div>
                      </div>
                      <div v-if="curation.mondo_id" class="mb-4">
                        <div class="text-body-small text-medium-emphasis">MONDO ID</div>
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
                        <div class="text-body-small text-medium-emphasis">Mode of Inheritance</div>
                        <v-chip v-if="curation.mode_of_inheritance" variant="outlined" class="mt-1">
                          {{ formatInheritance(curation.mode_of_inheritance) }}
                        </v-chip>
                        <span v-else class="text-body-large mt-1">Not specified</span>
                      </div>
                      <div class="mb-4">
                        <div class="text-body-small text-medium-emphasis">Status</div>
                        <v-chip
                          :color="curationStatusColor(curation.status)"
                          variant="tonal"
                          class="mt-1"
                        >
                          {{ curationStatusLabel(curation.status) }}
                        </v-chip>
                      </div>
                      <div class="mb-4">
                        <div class="text-body-small text-medium-emphasis">Curator</div>
                        <div class="text-body-large mt-1">
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
                  Workflow actions
                </v-card-title>
                <v-card-text>
                  <div
                    v-if="curation.status === 'in_review'"
                    class="text-body-medium text-medium-emphasis mb-3"
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
                      Submit for review
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
                      Request changes
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
                      class="text-body-medium text-medium-emphasis text-center py-2"
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
                  Evidence details
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
                      <div class="text-body-small text-medium-emphasis">Created At</div>
                      <div class="text-body-large">{{ formatDateTime(curation.created_at) }}</div>
                    </v-col>
                    <v-col cols="12" md="3">
                      <div class="text-body-small text-medium-emphasis">Updated At</div>
                      <div class="text-body-large">{{ formatDateTime(curation.updated_at) }}</div>
                    </v-col>
                    <v-col cols="12" md="3">
                      <div class="text-body-small text-medium-emphasis">Workflow Stage</div>
                      <div class="text-body-large">{{ curation.workflow_stage }}</div>
                    </v-col>
                    <v-col cols="12" md="3">
                      <div class="text-body-small text-medium-emphasis">Version</div>
                      <div class="text-body-large">{{ curation.lock_version }}</div>
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
    <BaseDialog v-model="showSubmitDialog" size="md">
      <template #title><v-icon start color="primary">mdi-send</v-icon> Submit for review</template>
      <p>
        Submit this curation for <strong>{{ curation?.gene_symbol }}</strong> for review?
      </p>
      <p class="text-body-medium text-medium-emphasis mt-2">
        Once submitted, the curation will be locked for editing until the review is complete.
      </p>
      <template #actions>
        <v-btn variant="text" @click="showSubmitDialog = false">Cancel</v-btn>
        <v-btn color="primary" variant="elevated" :loading="submitting" @click="submitForReview">
          Submit
        </v-btn>
      </template></BaseDialog
    >

    <!-- Delete Confirmation Dialog -->
    <BaseDialog v-model="showDeleteDialog" size="md">
      <template #title
        ><v-icon start color="error">mdi-delete-alert</v-icon> Delete curation</template
      >
      <v-alert type="warning" variant="tonal" class="mb-4"> This action cannot be undone. </v-alert>
      <p>
        Are you sure you want to delete the curation for
        <strong>{{ curation?.gene_symbol }}</strong
        >?
      </p>
      <template #actions>
        <v-btn variant="text" @click="showDeleteDialog = false">Cancel</v-btn>
        <v-btn color="error" variant="elevated" :loading="deleting" @click="deleteCuration">
          Delete
        </v-btn>
      </template></BaseDialog
    >

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
  import { formatDateTime } from '@/utils/format'
  import ClassificationMark from '@/components/common/ClassificationMark.vue'
  import { ref, computed, onMounted } from 'vue'
  import { useRouter, useRoute } from 'vue-router'
  import { curationsAPI, workflowAPI, schemasAPI } from '@/api'
  import { curationStatusColor, curationStatusLabel } from '@/config/status'
  import { useNotificationsStore } from '@/stores/notifications'
  import { humanize } from '@/components/dynamic/fieldLabels'
  import { useLogger } from '@/composables/useLogger'
  import { useAuthStore } from '@/stores/auth'
  import DynamicForm from '@/components/dynamic/DynamicForm.vue'
  import CurationScoreBreakdown from '@/components/curation/CurationScoreBreakdown.vue'
  import CurationEvidenceReadonly from '@/components/curation/CurationEvidenceReadonly.vue'
  import CurationReviewDialogs from '@/components/curation/CurationReviewDialogs.vue'
  import { evidenceCountsText } from '@/components/curation/evidenceCounts'
  import type { ClinGenEvidenceData } from '@/components/clingen/types'
  import type { EvidenceData } from './curationScores'
  import { useCurationClassification } from './useCurationClassification'
  import BaseDialog from '@/components/BaseDialog.vue'

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

  const { scores, classification } = useCurationClassification(() => curation.value?.evidence_data)

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
  const formatInheritance = (moi: string): string => {
    const labels: Record<string, string> = {
      AD: 'Autosomal dominant',
      AR: 'Autosomal recessive',
      XLD: 'X-linked dominant',
      XLR: 'X-linked recessive',
      MT: 'Mitochondrial'
    }
    return labels[moi] || humanize(moi.toLowerCase())
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
      // MainNavigation re-counts the review badge on visibilitychange; no shared store holds it yet
      document.dispatchEvent(new Event('visibilitychange'))
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
