<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <!-- Header -->
        <div class="d-flex align-center mb-6">
          <v-btn
            icon="mdi-arrow-left"
            variant="text"
            class="mr-3"
            aria-label="Go back"
            @click="handleCancel"
          />
          <h1 class="text-h4">
            {{ isEdit ? 'Edit Curation' : 'New Curation' }}
          </h1>
        </div>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <v-card>
          <CurationForm
            :gene-id="geneId"
            :curation-id="curationId"
            :scope-id="scopeId"
            @submit="handleSubmit"
            @cancel="handleCancel"
            @saved="handleSaved"
          />
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
  /**
   * CurationFormView
   *
   * Scope-aware wrapper for creating/editing curations.
   * Handles routing and integrates with the scope-based architecture.
   *
   * Routes:
   * - /scopes/:scopeId/curations/new (new curation)
   * - /scopes/:scopeId/curations/:curationId/edit (edit existing)
   * - /scopes/:scopeId/genes/:geneId/curation/new (new from gene)
   *
   * @example
   * // Create new curation
   * router.push(`/scopes/${scopeId}/curations/new`)
   *
   * // Edit existing curation
   * router.push(`/scopes/${scopeId}/curations/${curationId}/edit`)
   *
   * // Create curation for specific gene
   * router.push(`/scopes/${scopeId}/genes/${geneId}/curation/new`)
   */

  import { computed } from 'vue'
  import { useRouter, useRoute } from 'vue-router'
  import { useNotificationsStore } from '@/stores/notifications'
  import CurationForm from '@/components/forms/CurationForm.vue'

  const router = useRouter()
  const route = useRoute()
  const notificationStore = useNotificationsStore()

  // Props from route params
  const scopeId = computed(() => route.params.scopeId)
  const curationId = computed(() => route.params.curationId || null)
  const geneId = computed(() => route.params.geneId || route.query.gene_id || null)

  // Determine if this is an edit or create operation
  const isEdit = computed(() => !!curationId.value)

  /**
   * Handle form submission
   */
  function handleSubmit(curation) {
    notificationStore.addToast('Curation saved successfully', 'success')

    // Navigate to the curation detail page
    router.push({
      name: 'curation-detail',
      params: {
        scopeId: scopeId.value,
        curationId: curation.curation_id || curation.id
      }
    })
  }

  /**
   * Handle form cancellation
   */
  function handleCancel() {
    // Navigate back to scope dashboard or previous page
    if (geneId.value) {
      // If came from gene detail, go back there
      router.push({
        name: 'scope-dashboard',
        params: { scopeId: scopeId.value }
      })
    } else {
      // Otherwise go back to scope dashboard
      router.back()
    }
  }

  /**
   * Handle auto-save
   */
  function handleSaved() {
    notificationStore.addToast('Draft saved', 'info')
  }
</script>

<style scoped>
  /* Header styling */
  h1 {
    font-weight: 600;
  }

  /* Ensure proper spacing */
  .v-container {
    max-width: 1400px;
  }
</style>
