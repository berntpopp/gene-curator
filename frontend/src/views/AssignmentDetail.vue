<template>
  <v-container fluid>
    <div v-if="loading" class="text-center py-12">
      <v-progress-circular indeterminate color="primary" size="64" />
      <div class="mt-4 text-title-large">Loading assignment...</div>
    </div>

    <v-alert v-else-if="error" type="error" variant="tonal">
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="load">Retry</v-btn>
      </template>
    </v-alert>

    <template v-else-if="assignment">
      <div class="d-flex align-center mb-6">
        <v-btn
          icon="mdi-arrow-left"
          variant="text"
          class="mr-4"
          aria-label="Back"
          @click="router.back()"
        />
        <div>
          <h1 class="text-headline-large font-weight-bold">
            {{ assignment.gene_symbol ?? 'Gene' }}
          </h1>
          <p class="text-body-large text-medium-emphasis mt-1">
            {{ assignment.scope_display_name ?? assignment.scope_name }}
          </p>
        </div>
        <v-spacer />
        <v-chip :color="assignment.is_active ? 'success' : 'grey'" size="large" variant="flat">
          {{ assignment.is_active ? 'Active' : 'Inactive' }}
        </v-chip>
      </div>

      <v-card class="mb-6">
        <v-card-title>Assignment</v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" sm="6" md="3">
              <div class="text-body-small text-medium-emphasis">Gene</div>
              <router-link
                :to="`/genes/${assignment.gene_id}`"
                class="text-body-large text-primary text-decoration-none"
              >
                {{ assignment.gene_symbol }}
              </router-link>
              <div class="text-body-medium">{{ assignment.gene_hgnc_id }}</div>
            </v-col>
            <v-col cols="12" sm="6" md="3">
              <div class="text-body-small text-medium-emphasis">Curator</div>
              <div class="text-body-large">{{ assignment.curator_name ?? 'Unassigned' }}</div>
            </v-col>
            <v-col cols="12" sm="6" md="3">
              <div class="text-body-small text-medium-emphasis">Priority</div>
              <div class="text-body-large text-capitalize">{{ assignment.priority }}</div>
            </v-col>
            <v-col cols="12" sm="6" md="3">
              <div class="text-body-small text-medium-emphasis">Due date</div>
              <div class="text-body-large">
                {{ assignment.due_date ? formatDate(assignment.due_date) : 'No due date' }}
              </div>
              <div class="text-body-small text-medium-emphasis mt-2">Assigned</div>
              <div class="text-body-large">{{ formatDate(assignment.assigned_at) }}</div>
            </v-col>
          </v-row>
          <p v-if="assignment.assignment_notes" class="mt-4 mb-0">
            {{ assignment.assignment_notes }}
          </p>
        </v-card-text>
        <v-card-actions>
          <v-btn color="primary" variant="flat" :to="action.to">{{ action.label }}</v-btn>
          <span v-if="action.stage" class="text-body-medium text-medium-emphasis ml-2">
            Stage: {{ action.stage }}
          </span>
        </v-card-actions>
      </v-card>
    </template>
  </v-container>
</template>

<script setup lang="ts">
  import { formatDate } from '@/utils/format'
  import { computed, onMounted, ref } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { useAssignmentsStore } from '@/stores/assignments'
  import { precurationsAPI, curationsAPI } from '@/api'
  import {
    shouldReplaceCuration,
    shouldReplacePrecuration,
    type CurationStatus,
    type PrecurationStatus
  } from '@/components/gene/useGeneWorkflowStatus'
  import type { Schema } from '@/types/api'

  type Assignment = Schema<'GeneScopeAssignmentWithDetails'>

  const route = useRoute()
  const router = useRouter()
  const assignmentsStore = useAssignmentsStore()

  const assignment = ref<Assignment | null>(null)
  const loading = ref(true)
  const error = ref<string | null>(null)
  const assignmentId = computed(() => String(route.params.id))

  // Precuration and curation live on the scope's gene routes; this page links into them
  const precuration = ref<PrecurationStatus | null>(null)
  const curation = ref<CurationStatus | null>(null)

  // One primary action: the furthest workflow step that already exists for this gene and scope
  const action = computed(() => {
    const params = { scopeId: assignment.value?.scope_id, geneId: assignment.value?.gene_id }
    if (curation.value) {
      return {
        label: 'Open curation',
        to: {
          name: 'curation-detail',
          params: { scopeId: params.scopeId, curationId: curation.value.id }
        },
        stage: curation.value.workflow_stage ?? curation.value.status
      }
    }
    if (precuration.value) {
      return {
        label: 'Continue precuration',
        to: { name: 'scope-dashboard', params: { scopeId: params.scopeId, tab: 'genes' } },
        stage: precuration.value.workflow_stage ?? precuration.value.status
      }
    }
    return {
      label: 'Start precuration',
      to: { name: 'gene-precuration-create', params },
      stage: ''
    }
  })

  /** Latest record for the gene, using the same precedence as the gene list. */
  function best(
    records: CurationStatus[],
    replace: (a: CurationStatus, b: CurationStatus) => boolean
  ): CurationStatus | null {
    return records.reduce<CurationStatus | null>(
      (acc, r) => (!acc || replace(acc, r) ? r : acc),
      null
    )
  }

  async function load() {
    loading.value = true
    error.value = null
    try {
      assignment.value = await assignmentsStore.fetchAssignmentById(assignmentId.value)
      const query = { scope_id: assignment.value.scope_id, gene_id: assignment.value.gene_id }
      const [pre, cur] = (await Promise.all([
        precurationsAPI.getPrecurations(query),
        curationsAPI.getCurations(query)
      ])) as [{ precurations?: PrecurationStatus[] }, { curations?: CurationStatus[] }]
      precuration.value = best(pre.precurations ?? [], shouldReplacePrecuration)
      curation.value = best(cur.curations ?? [], shouldReplaceCuration)
    } catch {
      error.value = 'Failed to load assignment'
    } finally {
      loading.value = false
    }
  }

  onMounted(load)
</script>
