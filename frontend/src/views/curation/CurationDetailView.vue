<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <!-- Header -->
        <div class="d-flex flex-wrap justify-space-between align-center ga-2 mb-6">
          <div class="d-flex align-center">
            <v-btn aria-label="Go back" icon variant="text" class="mr-3" @click="goBack">
              <v-icon>mdi-arrow-left</v-icon>
            </v-btn>
            <h1 class="text-headline-large d-inline">{{ pageTitle }}</h1>
          </div>
          <div class="d-flex flex-wrap ga-2">
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
              v-if="canRecurate"
              data-testid="recurate"
              color="primary"
              variant="flat"
              @click="startRecuration"
            >
              Start re-curation
            </v-btn>
            <v-btn
              v-if="curation"
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
        <v-card v-if="loading" variant="outlined" class="text-center py-8">
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
                <v-col cols="12" md="6" class="text-center text-md-left">
                  <div class="text-display-large font-weight-bold">
                    {{ formatScore(scores.total) }}
                  </div>
                  <div class="text-body-large">Total Points</div>
                </v-col>
                <v-col cols="12" md="6" class="text-center">
                  <ClassificationMark :classification="final" class="text-title-large" />
                  <div class="text-body-small mt-2">Gene-Disease Validity Classification</div>
                  <div
                    v-if="final !== classification"
                    class="text-body-small text-medium-emphasis"
                    data-testid="calculated-classification"
                  >
                    Curator classification; calculated: {{ classification || '—' }}
                  </div>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- Main Info Row -->
          <v-row class="mb-6">
            <v-col cols="12" md="8">
              <v-card variant="outlined">
                <v-card-title class="d-flex align-center"> Gene-Disease Association </v-card-title>
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
                        <v-chip
                          v-if="relationshipLabel(curation.relationship_type)"
                          variant="outlined"
                          class="mt-1 ml-1"
                        >
                          {{ relationshipLabel(curation.relationship_type) }}
                        </v-chip>
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
              <v-card variant="outlined" class="workflow-actions">
                <v-card-title> Workflow actions </v-card-title>
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
                    <!-- Approve waits while this reviewer's approval needs others (0 left: activates) -->
                    <v-btn
                      v-if="canReview && !(curation.has_approved && curation.approvals_remaining)"
                      color="success"
                      variant="elevated"
                      prepend-icon="mdi-check-circle"
                      block
                      @click="review.open('approve')"
                    >
                      Approve
                    </v-btn>
                    <div v-else-if="curation.has_approved" class="text-body-medium text-center">
                      You approved; {{ curation.approvals_remaining }} more needed
                    </div>
                    <v-btn
                      v-if="canReview"
                      color="warning"
                      variant="outlined"
                      prepend-icon="mdi-undo"
                      block
                      @click="review.open('reject')"
                    >
                      Request changes
                    </v-btn>
                    <v-btn v-if="canReview" :to="secondView" block>AI second view</v-btn>
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

          <ReviewDiff
            v-if="showReviewDiff"
            class="mb-6"
            :curation-id="curationId"
            :me="myId"
            :creator-id="curation.created_by ?? ''"
            :reviewer="canReview"
            :can-reply="canReview || isCreator"
            :only-with-comments="curation.status !== 'in_review'"
            :context="reviewContext"
          />

          <!-- Score Breakdown -->
          <v-row class="mb-6">
            <v-col cols="12">
              <CurationScoreBreakdown :scores="scores" :classification="classification" />
            </v-col>
          </v-row>

          <!-- Evidence Details (Schema-Agnostic) -->
          <v-row v-if="isClinGenSchema || curationSchemaId" class="mb-6">
            <v-col cols="12">
              <v-card variant="outlined">
                <v-card-title> Evidence details </v-card-title>
                <v-card-text>
                  <CurationEvidenceReadonly
                    v-if="isClinGenSchema && curationSchemaId"
                    :evidence="evidence"
                    :schema-id="curationSchemaId"
                    :version-id="curation.methodology_version_id"
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
              <v-card variant="outlined">
                <v-card-title> Metadata </v-card-title>
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
      <template #title>Submit for review?</template>
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

    <!-- Delete Confirmation Dialog: deleting archives the curation -->
    <BaseDialog v-model="showDeleteDialog" size="md">
      <template #title>
        {{
          isActive
            ? `Delete the active curation for ${curation?.gene_symbol}?`
            : `Delete the curation for ${curation?.gene_symbol}?`
        }}
      </template>
      <template v-if="isActive">
        <p>
          This is the published assertion for {{ curation?.gene_symbol }} in this scope. Deleting it
          archives it and leaves {{ curation?.gene_symbol }} without an active classification here
          until another curation is approved. This cannot be undone.
        </p>
        <p v-if="canRecurate" class="text-body-medium text-medium-emphasis mt-2">
          To revise it, start a re-curation instead: the active curation stays public until the new
          one is approved.
        </p>
      </template>
      <p v-else>
        The curation is archived and removed from the scope's lists. This cannot be undone.
      </p>
      <template #actions>
        <v-btn variant="text" @click="showDeleteDialog = false">Cancel</v-btn>
        <v-btn
          v-if="isActive && canRecurate"
          variant="outlined"
          data-testid="delete-recurate"
          @click="startRecuration"
        >
          Start re-curation instead
        </v-btn>
        <v-btn color="error" variant="flat" :loading="deleting" @click="deleteCuration">
          Delete
        </v-btn>
      </template></BaseDialog
    >

    <ApproveChecklistDialog
      v-model="review.showApprove.value"
      :gene-symbol="curation?.gene_symbol"
      :scope-name="scopeName"
      :classification="final"
      :calculated="classification"
      :rationale="rationale"
      :replaces="replaces"
      :total="formatScore(scores.total)"
      :curator="curation?.curator_name"
      :blockers="blockers"
      :busy="review.busy.value"
      :error="review.error.value"
      @approve="review.approve"
    />
    <RequestChangesDialog
      v-model="review.showReject.value"
      :gene-symbol="curation?.gene_symbol"
      :todos="todos"
      :busy="review.busy.value"
      :error="review.error.value"
      @reject="review.reject"
    />
  </v-container>
</template>

<script setup lang="ts">
  import { readableApiError } from '@/utils/apiErrorText'
  import { formatDateTime } from '@/utils/format'
  import ClassificationMark from '@/components/common/ClassificationMark.vue'
  import { registerClassifications } from '@/config/classification'
  import { ref, computed, onMounted, watch } from 'vue'
  import { useRouter, useRoute } from 'vue-router'
  import { curationsAPI, schemasAPI } from '@/api'
  import { curationStatusColor, curationStatusLabel } from '@/config/status'
  import { useNotificationsStore } from '@/stores/notifications'
  import { formatInheritance, relationshipLabel } from '@/utils/inheritance'
  import { useLogger } from '@/composables/useLogger'
  import { useAuthStore } from '@/stores/auth'
  import DynamicForm from '@/components/dynamic/DynamicForm.vue'
  import { formatScore } from './curationScores'
  import CurationScoreBreakdown from '@/components/curation/CurationScoreBreakdown.vue'
  import CurationEvidenceReadonly from '@/components/curation/CurationEvidenceReadonly.vue'
  import ApproveChecklistDialog from '@/components/review/ApproveChecklistDialog.vue'
  import RequestChangesDialog from '@/components/review/RequestChangesDialog.vue'
  import ReviewDiff from '@/components/review/ReviewDiff.vue'
  import { useReviewTransitions } from '@/components/review/useReviewTransitions'
  import { approveBlockers, groupDiff, queryTodos } from '@/components/review/reviewModel'
  import { useReviewStore } from '@/stores/review'
  import { useScopesStore } from '@/stores/scopes'
  import { useCurationClassification, type ScoredCuration } from './useCurationClassification'
  import { replacesActive } from './replacesActive'
  import BaseDialog from '@/components/BaseDialog.vue'
  import { useCurateGuard } from '@/components/workspace/useCurateGuard'

  interface CurationRecord extends ScoredCuration {
    status: string
    gene_id?: string
    scope_id?: string
    precuration_id?: string | null
    workflow_pair_id?: string
    methodology_version_id?: string | null
    evidence_data?: Record<string, unknown> | null
    gene_symbol?: string | null
    hgnc_id?: string | null
    disease_name?: string | null
    mondo_id?: string | null
    mode_of_inheritance?: string | null
    relationship_type?: string | null
    workflow_stage?: string | null
    curator_name?: string | null
    created_by?: string | null
    lock_version?: number | null
    created_at?: string | null
    updated_at?: string | null
    can_edit?: boolean
    can_delete?: boolean
    can_review?: boolean
    has_approved?: boolean
    approvals_remaining?: number | null
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
  const submitting = ref(false)
  const deleting = ref(false)
  const curationSchemaId = ref<string | null>(null)

  const evidence = computed(() => (curation.value?.evidence_data ?? {}) as Record<string, unknown>)
  // ClinGen schemas (by scoring engine) get the read-only evidence view
  const isClinGenSchema = ref(false)
  const schemaFields = ref<Record<string, unknown> | null>(null)
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

  const { scores, classification, final, rationale } = useCurationClassification(
    () => curation.value
  )

  // Permissions - use backend-computed values based on scope-specific roles
  const canEdit = computed(() => curation.value?.can_edit ?? false)

  const canSubmitForReview = computed(() => canEdit.value && curation.value?.status === 'draft')

  const canDelete = computed(() => curation.value?.can_delete ?? false)

  // Backend: scope REVIEW role; the creator never reviews their own curation (D1), whatever the flag
  const myId = computed(() => (authStore.user as { id?: string } | null)?.id ?? '')
  const isCreator = computed(() => !!myId.value && curation.value?.created_by === myId.value)
  const canReview = computed(() => (curation.value?.can_review ?? false) && !isCreator.value)
  const secondView = computed(() => ({ name: 'llm-second-view', params: route.params }))

  const reviewStore = useReviewStore()
  const scopeName = computed(() => {
    const sc = useScopesStore().scopes.find(x => x.id === scopeId.value)
    return sc?.display_name || sc?.name || 'this scope'
  })
  const showReviewDiff = computed(
    () => curation.value.status === 'in_review' || curation.value.status === 'draft'
  )
  const reviewContext = computed(() => ({ fields: schemaFields.value, evidence: evidence.value }))
  // A review that is not loaded (failed, or another curation's) must block approval, never pass
  const blockers = computed(() =>
    reviewStore.ready(curationId.value)
      ? approveBlockers(
          groupDiff(reviewStore.diff?.items ?? [], reviewContext.value),
          reviewStore.comments,
          myId.value
        )
      : [{ key: '', label: 'The review has not loaded' }]
  )
  const todos = computed(() =>
    queryTodos(curation.value?.created_by ?? '', reviewStore.comments, reviewContext.value)
  )

  async function loadCurationSchema() {
    if (!curation.value?.workflow_pair_id) return
    try {
      const workflowPair = await schemasAPI.getWorkflowPairById(curation.value.workflow_pair_id)
      curationSchemaId.value = workflowPair.curation_schema_id || null
      if (curationSchemaId.value) {
        const schema = await schemasAPI.getSchemaById(curationSchemaId.value)
        isClinGenSchema.value = schema.scoring_configuration?.engine === 'clingen_sop_v11'
        registerClassifications(schema.scoring_configuration?.classifications)
        schemaFields.value = schema.field_definitions
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
      if (curation.value.workflow_stage === 'active') void curateGuard.check()
      await loadCurationSchema()
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status
      error.value = [403, 404].includes(status ?? 0)
        ? 'Curation not found. It does not exist, or you are not a member of its scope.'
        : 'Failed to load curation details'
      logger.error('Failed to load curation', {
        error: (err as ErrorLike).message,
        curation_id: curationId.value
      })
    } finally {
      loading.value = false
    }
  }

  // Re-curation: curators and scope admins start a new curation from the active one
  const curateGuard = useCurateGuard(() => scopeId.value)
  const isActive = computed(() => curation.value?.workflow_stage === 'active')
  const canRecurate = computed(() => isActive.value && curateGuard.allowed.value)
  function startRecuration() {
    router.push({
      name: 'gene-curation-create',
      params: { scopeId: scopeId.value, geneId: curation.value.gene_id },
      query: { from: curationId.value }
    })
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
      const errorDetail = readableApiError(err, 'Request failed')
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

  const review = useReviewTransitions(() => curationId.value, loadCuration)
  const replaces = ref(false)
  watch(review.showApprove, async open => {
    if (open) replaces.value = await replacesActive(curation.value).catch(() => false)
  })

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
