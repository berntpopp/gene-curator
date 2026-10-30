<template>
  <v-dialog :model-value="modelValue" max-width="680" scrollable @update:model-value="close">
    <v-card>
      <v-card-title>Publish a new version of {{ schemaName }}</v-card-title>
      <v-card-text>
        <div v-if="loading" class="text-center py-6">
          <v-progress-circular indeterminate color="primary" />
          <div class="mt-2">Checking the saved schema…</div>
        </div>
        <template v-else>
          <p class="mb-4">
            Publishes the saved schema as version {{ (latest?.version ?? 0) + 1 }}. Existing
            curations keep the version they were created with; new curations use this one.
          </p>

          <div class="text-title-small mb-2">Validator report</div>
          <v-alert
            :type="problems.length ? 'error' : 'success'"
            variant="tonal"
            density="compact"
            class="mb-4"
            data-testid="publish-report"
          >
            <div v-if="!problems.length">No errors.</div>
            <ul v-else class="ps-4">
              <li v-for="e in problems" :key="e">{{ e }}</li>
            </ul>
            <ul v-if="warnings.length" class="ps-4 mt-1">
              <li v-for="w in warnings" :key="w">Warning: {{ w }}</li>
            </ul>
          </v-alert>

          <div class="text-title-small mb-2">Impact</div>
          <v-list density="compact" class="mb-2" data-testid="publish-impact">
            <v-list-item v-if="!pairs.length" title="No workflow pair uses this schema" />
            <v-list-item
              v-for="pair in pairs"
              :key="pair.id"
              prepend-icon="mdi-sitemap"
              :title="`${pair.name} v${pair.version}`"
              :subtitle="defaultFor(pair.id)"
            />
          </v-list>
        </template>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="close">Cancel</v-btn>
        <v-btn
          color="primary"
          variant="flat"
          :loading="publishing"
          :disabled="loading || problems.length > 0"
          @click="publish"
        >
          Publish version
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
  import { ref, watch } from 'vue'
  import { useSchemasStore } from '@/stores'
  import { errorMessage, toApiError } from '@/stores/apiError'
  import { showError, showSuccess } from '@/composables/useNotifications'
  import type { Schema } from '@/types/api'

  // Publish the saved schema: validator report and the pairs/scopes it reaches, then confirm
  const props = defineProps<{ modelValue: boolean; schemaId: string; schemaName: string }>()
  const emit = defineEmits<{
    'update:modelValue': [open: boolean]
    published: [version: Schema<'MethodologyVersion'>]
  }>()
  const schemasStore = useSchemasStore()

  const loading = ref(false)
  const publishing = ref(false)
  const problems = ref<string[]>([])
  const warnings = ref<string[]>([])
  const pairs = ref<Schema<'WorkflowPair'>[]>([])
  const scopes = ref<Schema<'ScopeListItem'>[]>([])
  const latest = ref<Schema<'MethodologyVersion'> | null>(null)

  const close = () => emit('update:modelValue', false)

  const defaultFor = (pairId: string) => {
    const names = scopes.value
      .filter(s => s.default_workflow_pair_id === pairId)
      .map(s => s.display_name || s.name)
    return names.length ? `Default in: ${names.join(', ')}` : 'Not a scope default'
  }

  const load = async () => {
    loading.value = true
    try {
      const [report, impact] = await Promise.all([
        schemasStore.validateSchema(props.schemaId),
        schemasStore.fetchPublishImpact(props.schemaId)
      ])
      problems.value = report.errors ?? []
      warnings.value = report.warnings ?? []
      pairs.value = impact.pairs
      scopes.value = impact.scopes
      latest.value = impact.latest
    } catch (error) {
      showError(errorMessage(error, 'Could not check the schema'))
      close()
    } finally {
      loading.value = false
    }
  }

  watch(
    () => props.modelValue,
    open => {
      if (open) load()
    },
    { immediate: true }
  )

  const publish = async () => {
    publishing.value = true
    try {
      const version = await schemasStore.publishVersion(props.schemaId)
      showSuccess(`Published version ${version.version}`)
      emit('published', version)
      close()
    } catch (error) {
      // 422: { detail: { message, errors: [...] } } lists static and scoring-test failures
      const detail = toApiError(error).response?.data?.detail as { errors?: string[] } | undefined
      if (detail?.errors?.length) problems.value = detail.errors
      else showError(errorMessage(error, 'Failed to publish version'))
    } finally {
      publishing.value = false
    }
  }
</script>
