<template>
  <v-alert v-if="failed" type="warning" variant="tonal">
    The methodology this curation was recorded with could not be loaded.
  </v-alert>
  <v-skeleton-loader v-else-if="!version" type="article" />
  <!-- Rendered read-only from the version the curation is pinned to -->
  <DynamicForm
    v-else
    :schema-id="schemaId"
    :definition="version.snapshot"
    :methodology-version-id="version.id"
    :initial-data="evidence"
    title=""
    readonly
    hide-actions
    hide-scoring
  />
</template>

<script setup lang="ts">
  import { onMounted, ref } from 'vue'
  import DynamicForm from '@/components/dynamic/DynamicForm.vue'
  import { useSchemasStore } from '@/stores/schemas'
  import type { Schema } from '@/types/api'

  const props = defineProps<{
    evidence: Record<string, unknown>
    schemaId: string
    versionId?: string | null
  }>()

  const version = ref<Schema<'MethodologyVersion'> | null>(null)
  const failed = ref(false)

  onMounted(async () => {
    try {
      version.value = await useSchemasStore().fetchPinnedVersion(props.versionId, props.schemaId)
    } catch {
      failed.value = true
    }
  })
</script>
