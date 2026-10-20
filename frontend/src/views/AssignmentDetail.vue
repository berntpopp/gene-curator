<template>
  <v-container fluid>
    <div v-if="loading" class="text-center py-12">
      <v-progress-circular indeterminate color="primary" size="64" />
      <div class="mt-4 text-h6">Loading assignment...</div>
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
          <h1 class="text-h4 font-weight-bold">{{ assignment.gene_symbol ?? 'Gene' }}</h1>
          <p class="text-body-1 text-medium-emphasis mt-1">
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
              <div class="text-caption text-medium-emphasis">Gene</div>
              <router-link :to="`/genes/${assignment.gene_id}`" class="text-body-1">
                {{ assignment.gene_symbol }}
              </router-link>
              <div class="text-body-2">{{ assignment.gene_hgnc_id }}</div>
            </v-col>
            <v-col cols="12" sm="6" md="3">
              <div class="text-caption text-medium-emphasis">Curator</div>
              <div class="text-body-1">{{ assignment.curator_name ?? 'Unassigned' }}</div>
            </v-col>
            <v-col cols="12" sm="6" md="3">
              <div class="text-caption text-medium-emphasis">Priority</div>
              <div class="text-body-1 text-capitalize">{{ assignment.priority }}</div>
            </v-col>
            <v-col cols="12" sm="6" md="3">
              <div class="text-caption text-medium-emphasis">Due date</div>
              <div class="text-body-1">{{ formatDate(assignment.due_date) }}</div>
            </v-col>
          </v-row>
          <p v-if="assignment.assignment_notes" class="mt-4 mb-0">
            {{ assignment.assignment_notes }}
          </p>
        </v-card-text>
        <v-card-actions>
          <v-btn color="primary" variant="flat" :to="workflowRoute('gene-precuration-create')">
            Start precuration
          </v-btn>
          <v-btn variant="outlined" :to="workflowRoute('gene-curation-create')">
            Start curation
          </v-btn>
        </v-card-actions>
      </v-card>
    </template>
  </v-container>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { useAssignmentsStore } from '@/stores/assignments'
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
  const workflowRoute = (name: string) => ({
    name,
    params: { scopeId: assignment.value?.scope_id, geneId: assignment.value?.gene_id }
  })

  const formatDate = (value?: string | null) =>
    value ? new Date(value).toLocaleDateString() : 'No due date'

  async function load() {
    loading.value = true
    error.value = null
    try {
      assignment.value = await assignmentsStore.fetchAssignmentById(assignmentId.value)
    } catch {
      error.value = 'Failed to load assignment'
    } finally {
      loading.value = false
    }
  }

  onMounted(load)
</script>
