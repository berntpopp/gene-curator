<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <!-- Header -->
        <div class="d-flex justify-space-between align-center mb-6">
          <div class="d-flex align-center">
            <v-btn icon variant="text" class="mr-3" @click="goBack">
              <v-icon>mdi-arrow-left</v-icon>
            </v-btn>
            <h1 class="text-h4 d-inline">Curation Details</h1>
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
                  <div class="d-flex justify-center justify-md-end gap-6">
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
                        <div class="d-flex align-center gap-2 mt-1">
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
              <v-card>
                <v-card-title>
                  <v-icon start>mdi-cog</v-icon>
                  Workflow Actions
                </v-card-title>
                <v-card-text>
                  <div class="d-flex flex-column gap-2">
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
                      @click="showApproveDialog = true"
                    >
                      Approve
                    </v-btn>
                    <v-btn
                      v-if="canReview"
                      color="warning"
                      variant="outlined"
                      prepend-icon="mdi-undo"
                      block
                      @click="showRejectDialog = true"
                    >
                      Request Changes
                    </v-btn>
                    <v-btn
                      v-if="canDelete"
                      color="error"
                      variant="outlined"
                      prepend-icon="mdi-delete"
                      block
                      @click="showDeleteDialog = true"
                    >
                      Delete
                    </v-btn>
                    <div
                      v-if="!canSubmitForReview && !canDelete && !canReview"
                      class="text-body-2 text-medium-emphasis text-center py-2"
                    >
                      No actions available
                    </div>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <!-- Score Breakdown -->
          <v-row class="mb-6">
            <v-col cols="12">
              <v-card>
                <v-card-title>
                  <v-icon start>mdi-chart-bar</v-icon>
                  Evidence Score Breakdown
                </v-card-title>
                <v-card-text>
                  <v-row>
                    <!-- Genetic Evidence -->
                    <v-col cols="12" md="6">
                      <div class="text-subtitle-1 font-weight-medium mb-3">
                        <v-icon start color="primary">mdi-dna</v-icon>
                        Genetic Evidence
                        <v-chip size="small" class="ml-2" color="primary" variant="tonal">
                          {{ scores.genetic.toFixed(2) }} / 12
                        </v-chip>
                      </div>
                      <v-table density="compact">
                        <tbody>
                          <tr>
                            <td>Case-Level (AD/XL Null)</td>
                            <td class="text-right">{{ scores.caseLevel.adxlNull.toFixed(2) }}</td>
                          </tr>
                          <tr>
                            <td>Case-Level (AD/XL Other)</td>
                            <td class="text-right">{{ scores.caseLevel.adxlOther.toFixed(2) }}</td>
                          </tr>
                          <tr>
                            <td>Case-Level (AR Null)</td>
                            <td class="text-right">{{ scores.caseLevel.arNull.toFixed(2) }}</td>
                          </tr>
                          <tr>
                            <td>Case-Level (AR Other)</td>
                            <td class="text-right">{{ scores.caseLevel.arOther.toFixed(2) }}</td>
                          </tr>
                          <tr>
                            <td>Segregation</td>
                            <td class="text-right">{{ scores.segregation.toFixed(2) }}</td>
                          </tr>
                          <tr>
                            <td>Case-Control</td>
                            <td class="text-right">{{ scores.caseControl.toFixed(2) }}</td>
                          </tr>
                        </tbody>
                      </v-table>
                    </v-col>

                    <!-- Experimental Evidence -->
                    <v-col cols="12" md="6">
                      <div class="text-subtitle-1 font-weight-medium mb-3">
                        <v-icon start color="secondary">mdi-flask</v-icon>
                        Experimental Evidence
                        <v-chip size="small" class="ml-2" color="secondary" variant="tonal">
                          {{ scores.experimental.toFixed(2) }} / 6
                        </v-chip>
                      </div>
                      <v-table density="compact">
                        <tbody>
                          <tr>
                            <td>Biochemical Function</td>
                            <td class="text-right">{{ scores.function.biochemical.toFixed(2) }}</td>
                          </tr>
                          <tr>
                            <td>Protein Interaction</td>
                            <td class="text-right">
                              {{ scores.function.proteinInteraction.toFixed(2) }}
                            </td>
                          </tr>
                          <tr>
                            <td>Expression</td>
                            <td class="text-right">{{ scores.function.expression.toFixed(2) }}</td>
                          </tr>
                          <tr>
                            <td>Functional Alteration</td>
                            <td class="text-right">{{ scores.functionalAlteration.toFixed(2) }}</td>
                          </tr>
                          <tr>
                            <td>Models</td>
                            <td class="text-right">{{ scores.models.toFixed(2) }}</td>
                          </tr>
                          <tr>
                            <td>Rescue</td>
                            <td class="text-right">{{ scores.rescue.toFixed(2) }}</td>
                          </tr>
                        </tbody>
                      </v-table>
                    </v-col>
                  </v-row>
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

    <!-- Approve Confirmation Dialog -->
    <v-dialog v-model="showApproveDialog" max-width="600">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start color="success">mdi-check-circle</v-icon>
          Approve Curation
        </v-card-title>
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            Approving this curation will move it to the <strong>Active</strong> stage.
          </v-alert>
          <p class="mb-4">
            Approve the <strong>{{ classification }}</strong> classification for
            <strong>{{ curation?.gene_symbol }}</strong
            >?
          </p>
          <div class="d-flex justify-space-between mb-4">
            <div>
              <span class="text-medium-emphasis">Total Score:</span>
              <strong class="ml-2">{{ scores.total.toFixed(2) }}</strong>
            </div>
            <div>
              <span class="text-medium-emphasis">Genetic:</span>
              <strong class="ml-2">{{ scores.genetic.toFixed(2) }}</strong>
            </div>
            <div>
              <span class="text-medium-emphasis">Experimental:</span>
              <strong class="ml-2">{{ scores.experimental.toFixed(2) }}</strong>
            </div>
          </div>
          <v-textarea
            v-model="reviewComments"
            label="Approval Comments (optional)"
            placeholder="Add any comments about this approval..."
            rows="3"
            variant="outlined"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showApproveDialog = false">Cancel</v-btn>
          <v-btn color="success" variant="elevated" :loading="approving" @click="approveCuration">
            Approve
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Request Changes Dialog -->
    <v-dialog v-model="showRejectDialog" max-width="600">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start color="warning">mdi-undo</v-icon>
          Request Changes
        </v-card-title>
        <v-card-text>
          <v-alert type="warning" variant="tonal" class="mb-4">
            This will return the curation to the curator for revisions.
          </v-alert>
          <p class="mb-4">
            Request changes for the curation of <strong>{{ curation?.gene_symbol }}</strong
            >?
          </p>
          <v-textarea
            v-model="reviewComments"
            label="Feedback for Curator"
            placeholder="Describe what changes are needed..."
            rows="4"
            variant="outlined"
            :rules="[v => !!v || 'Please provide feedback for the curator']"
            required
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showRejectDialog = false">Cancel</v-btn>
          <v-btn
            color="warning"
            variant="elevated"
            :loading="rejecting"
            :disabled="!reviewComments"
            @click="rejectCuration"
          >
            Request Changes
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
  import { ref, computed, onMounted } from 'vue'
  import { useRouter, useRoute } from 'vue-router'
  import { curationsAPI, workflowAPI } from '@/api'
  import { useNotificationsStore } from '@/stores/notifications'
  import { useLogger } from '@/composables/useLogger'

  const router = useRouter()
  const route = useRoute()
  const notificationStore = useNotificationsStore()
  const logger = useLogger()

  // Route params
  const scopeId = computed(() => route.params.scopeId)
  const curationId = computed(() => route.params.curationId)

  // State
  const curation = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const showSubmitDialog = ref(false)
  const showDeleteDialog = ref(false)
  const showApproveDialog = ref(false)
  const showRejectDialog = ref(false)
  const submitting = ref(false)
  const deleting = ref(false)
  const approving = ref(false)
  const rejecting = ref(false)
  const reviewComments = ref('')

  // Calculate scores from evidence_data
  const scores = computed(() => {
    const evidence = curation.value?.evidence_data || {}
    const genetic = evidence.genetic_evidence || {}
    const experimental = evidence.experimental_evidence || {}

    // Case-level scores
    const caseLevel = genetic.case_level || {}
    const adxl = caseLevel.autosomal_dominant_or_x_linked || {}
    const ar = caseLevel.autosomal_recessive || {}

    const adxlNull = (adxl.predicted_or_proven_null || []).reduce(
      (sum, v) => sum + (v.proband_counted_points || 0),
      0
    )
    const adxlOther = (adxl.other_variant_type || []).reduce(
      (sum, v) => sum + (v.proband_counted_points || 0),
      0
    )
    const arNull = (ar.predicted_or_proven_null || []).reduce(
      (sum, v) => sum + (v.proband_counted_points || 0),
      0
    )
    const arOther = (ar.other_variant_type || []).reduce(
      (sum, v) => sum + (v.proband_counted_points || 0),
      0
    )

    // Segregation
    const segregation = (genetic.segregation || []).reduce((sum, s) => sum + (s.points || 0), 0)

    // Case-control
    const caseControlData = genetic.case_control || {}
    const singleVariant = (caseControlData.single_variant_analysis || []).reduce(
      (sum, c) => sum + (c.points || 0),
      0
    )
    const aggregateVariant = (caseControlData.aggregate_variant_analysis || []).reduce(
      (sum, c) => sum + (c.points || 0),
      0
    )
    const caseControl = singleVariant + aggregateVariant

    // Genetic total (capped at 12)
    const geneticRaw = adxlNull + adxlOther + arNull + arOther + segregation + caseControl
    const geneticTotal = Math.min(geneticRaw, 12)

    // Experimental scores
    const func = experimental.function || {}
    const biochemical = (func.biochemical_function || []).reduce(
      (sum, f) => sum + (f.points || 0),
      0
    )
    const proteinInteraction = (func.protein_interaction || []).reduce(
      (sum, f) => sum + (f.points || 0),
      0
    )
    const expression = (func.expression || []).reduce((sum, f) => sum + (f.points || 0), 0)

    const functionalAltData = experimental.functional_alteration || {}
    const functionalAlteration =
      (functionalAltData.patient_cells || []).reduce((sum, f) => sum + (f.points || 0), 0) +
      (functionalAltData.non_patient_cells || []).reduce((sum, f) => sum + (f.points || 0), 0)

    const modelsData = experimental.models || {}
    const models =
      (modelsData.non_human_model_organism || []).reduce((sum, m) => sum + (m.points || 0), 0) +
      (modelsData.cell_culture_model || []).reduce((sum, m) => sum + (m.points || 0), 0)

    const rescueData = experimental.rescue || {}
    const rescue =
      (rescueData.human || []).reduce((sum, r) => sum + (r.points || 0), 0) +
      (rescueData.non_human_model_organism || []).reduce((sum, r) => sum + (r.points || 0), 0) +
      (rescueData.cell_culture || []).reduce((sum, r) => sum + (r.points || 0), 0) +
      (rescueData.patient_cells || []).reduce((sum, r) => sum + (r.points || 0), 0)

    // Experimental total (capped at 6)
    const experimentalRaw =
      biochemical + proteinInteraction + expression + functionalAlteration + models + rescue
    const experimentalTotal = Math.min(experimentalRaw, 6)

    return {
      caseLevel: { adxlNull, adxlOther, arNull, arOther },
      segregation,
      caseControl,
      genetic: geneticTotal,
      function: { biochemical, proteinInteraction, expression },
      functionalAlteration,
      models,
      rescue,
      experimental: experimentalTotal,
      total: geneticTotal + experimentalTotal
    }
  })

  // Classification based on score
  const classification = computed(() => {
    const total = scores.value.total
    const genetic = scores.value.genetic

    if (total >= 12 && genetic >= 6) return 'Definitive'
    if (total >= 12 && genetic >= 4.5) return 'Strong'
    if (total >= 9 && genetic >= 3) return 'Moderate'
    if (total >= 1) return 'Limited'
    return 'No Known Disease Relationship'
  })

  const classificationColor = computed(() => {
    const colors = {
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
  const formatStatus = status => {
    if (!status) return 'Unknown'
    return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const formatDateTime = dateString => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString()
  }

  const formatInheritance = moi => {
    const labels = {
      AD: 'Autosomal Dominant',
      AR: 'Autosomal Recessive',
      XLD: 'X-linked Dominant',
      XLR: 'X-linked Recessive',
      MT: 'Mitochondrial'
    }
    return labels[moi] || moi
  }

  const getStatusColor = status => {
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

  const getInheritanceColor = moi => {
    const colors = {
      AD: 'blue',
      AR: 'green',
      XLD: 'purple',
      XLR: 'purple',
      MT: 'orange'
    }
    return colors[moi] || 'grey'
  }

  // Actions
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
      const errorDetail = err.response?.data?.detail || err.message
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
      logger.error('Failed to delete curation', { error: err.message })
      notificationStore.addToast('Failed to delete curation', 'error')
    } finally {
      deleting.value = false
    }
  }

  async function approveCuration() {
    approving.value = true
    try {
      // Transition to active stage (approval)
      await workflowAPI.transitionCuration(curationId.value, {
        target_stage: 'active',
        notes: reviewComments.value || null
      })
      showApproveDialog.value = false
      reviewComments.value = ''
      notificationStore.addToast('Curation approved and activated', 'success')
      await loadCuration()
    } catch (err) {
      const errorDetail = err.response?.data?.detail || err.message
      logger.error('Failed to approve curation', { error: errorDetail })
      notificationStore.addToast(`Failed to approve: ${errorDetail}`, 'error')
    } finally {
      approving.value = false
    }
  }

  async function rejectCuration() {
    rejecting.value = true
    try {
      // Transition back to curation stage (request changes)
      await workflowAPI.transitionCuration(curationId.value, {
        target_stage: 'curation',
        notes: reviewComments.value
      })
      showRejectDialog.value = false
      reviewComments.value = ''
      notificationStore.addToast('Curation returned to curator for changes', 'success')
      await loadCuration()
    } catch (err) {
      const errorDetail = err.response?.data?.detail || err.message
      logger.error('Failed to request changes', { error: errorDetail })
      notificationStore.addToast(`Failed to request changes: ${errorDetail}`, 'error')
    } finally {
      rejecting.value = false
    }
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
    a.download = `curation_${curation.value.gene_symbol || 'unknown'}_${curationId.value}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    notificationStore.addToast('Curation exported successfully', 'success')
  }

  function goBack() {
    router.push({ name: 'scope-dashboard', params: { scopeId: scopeId.value } })
  }

  // Lifecycle
  onMounted(() => {
    loadCuration()
  })
</script>

<style scoped>
  .gap-2 {
    gap: 8px;
  }

  .gap-6 {
    gap: 24px;
  }
</style>
