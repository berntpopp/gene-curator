<template>
  <p v-if="synopsis" class="synopsis mb-4" data-testid="curation-synopsis">
    <span class="text-body-small text-medium-emphasis d-block">Synopsis</span>{{ synopsis }}
  </p>
  <v-alert v-if="failed" type="warning" variant="tonal">
    The methodology this curation was recorded with could not be loaded.
  </v-alert>
  <v-skeleton-loader v-else-if="!version" type="article" />
  <!-- Rendered read-only from the pinned version's snapshot: the server JSON schema flattens tables (monkey B1) -->
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
  >
    <template #section="{ section }">
      <ScoreSummary
        v-if="section.component === 'ScoreSummary' && scores"
        :scores="scores"
        :classification="classification"
      />
    </template>
  </DynamicForm>
</template>

<script setup lang="ts">
  import { computed, onMounted, provide, ref } from 'vue'
  import { ROW_PROVENANCE } from '@/components/dynamic/rowAuthorship'
  import { synopsisOf } from '@/utils/synopsis'
  import DynamicForm from '@/components/dynamic/DynamicForm.vue'
  import ScoreSummary from '@/components/forms/ScoreSummary.vue'
  import type { EvidenceScores } from '@/views/curation/curationScores'
  import { useSchemasStore } from '@/stores/schemas'
  import type { Schema } from '@/types/api'

  const props = defineProps<{
    evidence: Record<string, unknown>
    schemaId: string
    versionId?: string | null
    /** The curation's row_provenance: who added and changed each evidence row (#593) */
    rowProvenance?: Record<string, unknown> | null
    /** The saved score, for the schema's Score summary section */
    scores?: EvidenceScores
    classification?: string
  }>()
  provide(
    ROW_PROVENANCE,
    computed(() => props.rowProvenance)
  )

  const version = ref<Schema<'MethodologyVersion'> | null>(null)
  const failed = ref(false)
  const synopsis = computed(() =>
    synopsisOf(props.evidence, version.value?.snapshot?.ui_configuration)
  )

  onMounted(async () => {
    try {
      version.value = await useSchemasStore().fetchPinnedVersion(props.versionId, props.schemaId)
    } catch {
      failed.value = true
    }
  })
</script>

<style scoped>
  .synopsis {
    white-space: pre-wrap;
    max-width: 75ch;
  }
</style>
